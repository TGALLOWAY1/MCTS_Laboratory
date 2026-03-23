#!/usr/bin/env python3
"""Layer 1: Baseline Characterization — Master orchestration script.

Runs all 5 sub-analyses and generates a comprehensive baseline report.

Usage:
    # Full run (500 self-play + 100 heuristic + convergence check)
    python scripts/run_layer1_baseline.py

    # Quick smoke test
    python scripts/run_layer1_baseline.py --num-games 4 --num-heuristic-games 4 --skip-convergence

    # Resume an incomplete run (runs remaining games, then analysis)
    python scripts/run_layer1_baseline.py --resume baseline_runs/layer1_20260322_154726

    # Analysis only (skip game runs, use existing data)
    python scripts/run_layer1_baseline.py --analyze-only --selfplay-dir baseline_runs/<selfplay_run_id> --heuristic-dir baseline_runs/<heuristic_run_id>

    # Skip slow convergence check
    python scripts/run_layer1_baseline.py --skip-convergence

    # Custom output directory
    python scripts/run_layer1_baseline.py --output-dir baseline_runs/my_baseline
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics.baseline.branching_factor import (
    compute_branching_factor_curve,
    find_peak,
    plot_branching_factor_curve,
)
from analytics.baseline.iteration_efficiency import (
    compute_utilization_curve,
    plot_utilization_curve,
    summarize_utilization,
)
from analytics.baseline.qvalue_convergence import (
    compute_convergence_summary,
    plot_convergence_heatmap,
    plot_per_state_convergence,
    run_convergence_analysis,
    sample_states,
)
from analytics.baseline.report import generate_baseline_report
from analytics.baseline.seat_bias import compute_seat_bias, plot_seat_bias
from analytics.baseline.simulation_quality import compute_simulation_quality
from analytics.logging.reader import load_jsonl
from analytics.tournament.arena_runner import RunConfig, run_experiment
from analytics.tournament.arena_stats import load_games_jsonl


def _load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _count_games(run_dir: Path) -> int:
    """Count lines in games.jsonl under a run directory."""
    games_path = run_dir / "games.jsonl"
    if not games_path.exists():
        return 0
    with games_path.open() as f:
        return sum(1 for line in f if line.strip())


def _find_run_subdir(parent: Path) -> Optional[Path]:
    """Find the run subdirectory (e.g. selfplay/20260322_154726_abc123).
    If multiple exist, returns the one with the most games (most complete).
    """
    if not parent.exists():
        return None
    subdirs = [d for d in parent.iterdir() if d.is_dir()]
    if not subdirs:
        return None
    if len(subdirs) == 1:
        return subdirs[0]
    # Multiple: pick the one with most games
    return max(subdirs, key=_count_games)


def _run_selfplay(args, output_dir: Path, resume_dir: Optional[Path] = None) -> Path:
    """Run the 500-game self-play tournament and return the run directory."""
    config_path = args.selfplay_config or str(
        Path(__file__).resolve().parent / "layer1_selfplay_config.json"
    )
    config_dict = _load_config(config_path)

    if args.num_games is not None:
        config_dict["num_games"] = args.num_games
    config_dict["output_root"] = str(output_dir / "selfplay")

    run_config = RunConfig.from_dict(config_dict)
    target_games = run_config.num_games
    resume_run_dir = None
    if resume_dir is not None:
        existing = _count_games(resume_dir)
        if existing >= target_games:
            print(f"[1/6] Self-play complete: {existing} games (skipping)")
            return resume_dir
        resume_run_dir = str(resume_dir)
        print(
            f"[1/6] Resuming self-play: {existing}/{target_games} games "
            f"({target_games - existing} to go)"
        )
    else:
        print(
            f"[1/6] Running self-play tournament: {target_games} games "
            f"with {', '.join(a.name for a in run_config.agents)}"
        )

    start = time.time()
    result = run_experiment(
        run_config,
        verbose=args.verbose,
        enable_game_logging=True,
        resume_run_dir=resume_run_dir,
    )
    elapsed = time.time() - start
    run_dir = Path(result["run_dir"])
    print(f"      Done in {elapsed:.0f}s — {run_dir}")
    return run_dir


def _run_heuristic(args, output_dir: Path, resume_dir: Optional[Path] = None) -> Path:
    """Run the 100-game heuristic-only tournament and return the run dir."""
    config_path = args.heuristic_config or str(
        Path(__file__).resolve().parent / "layer1_heuristic_config.json"
    )
    config_dict = _load_config(config_path)

    if args.num_heuristic_games is not None:
        config_dict["num_games"] = args.num_heuristic_games
    config_dict["output_root"] = str(output_dir / "heuristic")

    run_config = RunConfig.from_dict(config_dict)
    target_games = run_config.num_games
    resume_run_dir = None
    if resume_dir is not None:
        existing = _count_games(resume_dir)
        if existing >= target_games:
            print(f"[2/6] Heuristic complete: {existing} games (skipping)")
            return resume_dir
        resume_run_dir = str(resume_dir)
        print(
            f"[2/6] Resuming heuristic: {existing}/{target_games} games "
            f"({target_games - existing} to go)"
        )
    else:
        print(f"[2/6] Running heuristic-only tournament: {target_games} games")

    start = time.time()
    result = run_experiment(
        run_config,
        verbose=args.verbose,
        resume_run_dir=resume_run_dir,
    )
    elapsed = time.time() - start
    run_dir = Path(result["run_dir"])
    print(f"      Done in {elapsed:.0f}s — {run_dir}")
    return run_dir


def _analyze_branching_factor(
    steps: list, output_dir: Path, iteration_budget: int
) -> dict:
    """1.1 — Branching Factor Curve."""
    print("[3/6] Analysing branching factor curve...")
    curve = compute_branching_factor_curve(steps)
    peak_info = find_peak(curve, iteration_budget=iteration_budget)
    plot_branching_factor_curve(
        curve, peak_info, output_dir / "plots" / "branching_factor_curve.png"
    )
    print(
        f"      Peak: {peak_info.get('peak_bf', 0):.0f} moves at turn "
        f"{peak_info.get('peak_turn', '?')} "
        f"(~{peak_info.get('implied_visits_per_child', 0):.1f} visits/child)"
    )
    return {"curve": curve, "peak": peak_info}


def _analyze_iteration_efficiency(steps: list, output_dir: Path) -> dict:
    """1.2 — Iteration Efficiency Analysis."""
    print("[3/6] Analysing iteration efficiency...")
    curve = compute_utilization_curve(steps)
    summary = summarize_utilization(curve)
    plot_utilization_curve(
        curve, output_dir / "plots" / "utilization_curve.png"
    )
    overall = summary.get("overall_mean")
    print(
        f"      Overall utilization: {overall:.1%}" if overall else "      No MCTS diagnostics found"
    )
    return {"curve": curve, "summary": summary}


def _analyze_simulation_quality(
    selfplay_dir: Path, heuristic_dir: Path
) -> dict:
    """1.3 — Simulation Quality Audit."""
    print("[4/6] Computing simulation quality audit...")
    selfplay_games = selfplay_dir / "games.jsonl"
    heuristic_games = heuristic_dir / "games.jsonl"
    result = compute_simulation_quality(heuristic_games, selfplay_games)
    print(
        f"      Heuristic avg: {result['heuristic_avg_score']:.1f}, "
        f"MCTS avg: {result['mcts_avg_score']:.1f}, "
        f"delta: {result['delta']:+.1f}"
    )
    return result


def _analyze_qvalue_convergence(
    steps: list, output_dir: Path, seed: int
) -> dict:
    """1.4 — Q-Value Convergence Check."""
    print("[5/6] Running Q-value convergence check (this may take a while)...")
    sampled = sample_states(steps, seed=seed)
    print(f"      Sampled {len(sampled)} states")

    start = time.time()

    def _progress(i: int, total: int) -> None:
        elapsed = time.time() - start
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total - i) / rate if rate > 0 else 0
        print(f"      [{i}/{total}] {elapsed:.0f}s elapsed, ~{eta:.0f}s remaining", end="\r")

    results = run_convergence_analysis(
        steps, sampled, seed=seed, progress_callback=_progress
    )
    print()  # clear progress line

    summary = compute_convergence_summary(results)

    plot_convergence_heatmap(
        results, output_path=output_dir / "plots" / "qvalue_convergence_heatmap.png"
    )
    plot_per_state_convergence(
        results, output_path=output_dir / "plots" / "qvalue_convergence_per_state.png"
    )

    # Save raw convergence data
    convergence_dir = output_dir / "convergence"
    convergence_dir.mkdir(parents=True, exist_ok=True)
    with (convergence_dir / "sampled_states.json").open("w") as f:
        json.dump(sampled, f, indent=2)
    with (convergence_dir / "convergence_results.json").open("w") as f:
        json.dump(results, f, indent=2)

    print(f"      Completed {len(results)} measurements across {summary['total_states']} states")
    return {"results": results, "summary": summary, "sampled_states": sampled}


def _analyze_seat_bias(games: list, output_dir: Path) -> dict:
    """1.5 — Seat-Position Bias Analysis."""
    print("[6/6] Analysing seat-position bias...")
    result = compute_seat_bias(games)
    plot_seat_bias(result, output_dir / "plots" / "seat_bias.png")
    anova = result.get("anova", {})
    p_val = anova.get("p_value")
    p_str = f"p={p_val:.4f}" if p_val is not None else "p=N/A"
    print(f"      ANOVA: F={anova.get('f_statistic', 'N/A')}, {p_str}")
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Layer 1: Baseline Characterization — run all analyses"
    )
    parser.add_argument(
        "--num-games", type=int, default=None,
        help="Override self-play game count (default: from config, typically 500)",
    )
    parser.add_argument(
        "--num-heuristic-games", type=int, default=None,
        help="Override heuristic game count (default: from config, typically 100)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Output directory (default: baseline_runs/layer1_<timestamp>)",
    )
    parser.add_argument(
        "--selfplay-config", type=str, default=None,
        help="Path to self-play arena config JSON",
    )
    parser.add_argument(
        "--heuristic-config", type=str, default=None,
        help="Path to heuristic arena config JSON",
    )
    parser.add_argument(
        "--skip-convergence", action="store_true",
        help="Skip the slow Q-value convergence check (1.4)",
    )
    parser.add_argument(
        "--resume", type=str, default=None, metavar="OUTPUT_DIR",
        help="Resume an incomplete run. Runs remaining games for self-play and heuristic phases, then analysis.",
    )
    parser.add_argument(
        "--analyze-only", action="store_true",
        help="Skip game runs, analyse existing data",
    )
    parser.add_argument(
        "--selfplay-dir", type=str, default=None,
        help="Path to existing self-play run directory (with --analyze-only)",
    )
    parser.add_argument(
        "--heuristic-dir", type=str, default=None,
        help="Path to existing heuristic run directory (with --analyze-only)",
    )
    parser.add_argument(
        "--iteration-budget", type=int, default=2000,
        help="MCTS iteration budget for visits-per-child annotation (default: 2000)",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for sampling")
    parser.add_argument("--verbose", action="store_true", help="Print per-game results")
    args = parser.parse_args()

    # Resolve output directory
    if args.resume:
        output_dir = Path(args.resume)
        if not output_dir.exists():
            parser.error(f"--resume directory does not exist: {output_dir}")
        selfplay_resume = _find_run_subdir(output_dir / "selfplay")
        heuristic_resume = _find_run_subdir(output_dir / "heuristic")
    elif args.output_dir:
        output_dir = Path(args.output_dir)
        selfplay_resume = heuristic_resume = None
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("baseline_runs") / f"layer1_{ts}"
        selfplay_resume = heuristic_resume = None
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Layer 1 Baseline Characterization")
    print(f"Output: {output_dir}")
    if args.resume:
        print("Mode:   Resume")
    print(f"{'=' * 60}\n")

    # Phase 1: Run games (or locate existing runs)
    if args.analyze_only:
        if not args.selfplay_dir or not args.heuristic_dir:
            parser.error("--analyze-only requires --selfplay-dir and --heuristic-dir")
        selfplay_dir = Path(args.selfplay_dir)
        heuristic_dir = Path(args.heuristic_dir)
    else:
        selfplay_dir = _run_selfplay(args, output_dir, resume_dir=selfplay_resume)
        heuristic_dir = _run_heuristic(args, output_dir, resume_dir=heuristic_resume)

    # Phase 2: Load data
    steps_path = selfplay_dir / "game_logs" / "steps.jsonl"
    games_path = selfplay_dir / "games.jsonl"

    if not steps_path.exists():
        print(f"WARNING: Step logs not found at {steps_path}")
        print("         Run with --enable-logging or check the self-play config.")
        steps = []
    else:
        steps = load_jsonl(str(steps_path))
        print(f"\nLoaded {len(steps)} step log entries")

    games = load_games_jsonl(str(games_path)) if games_path.exists() else []
    print(f"Loaded {len(games)} game records\n")

    # Phase 3: Run analyses
    all_results: dict = {}

    all_results["branching_factor"] = _analyze_branching_factor(
        steps, output_dir, args.iteration_budget
    )

    all_results["iteration_efficiency"] = _analyze_iteration_efficiency(
        steps, output_dir
    )

    all_results["simulation_quality"] = _analyze_simulation_quality(
        selfplay_dir, heuristic_dir
    )

    if not args.skip_convergence:
        all_results["qvalue_convergence"] = _analyze_qvalue_convergence(
            steps, output_dir, seed=args.seed
        )
    else:
        print("[5/6] Skipping Q-value convergence check (--skip-convergence)")
        all_results["qvalue_convergence"] = {"summary": {}, "results": []}

    all_results["seat_bias"] = _analyze_seat_bias(games, output_dir)

    # Phase 4: Generate report
    print(f"\nGenerating baseline report...")
    report_path = output_dir / "baseline_report.md"
    generate_baseline_report(all_results, report_path)

    # Save raw data (excluding large curve/results that are in sub-dirs)
    data_path = output_dir / "baseline_data.json"
    # Serialize only JSON-safe parts
    serializable = {}
    for key, value in all_results.items():
        if key == "qvalue_convergence":
            serializable[key] = {
                "summary": value.get("summary", {}),
                "sampled_states": value.get("sampled_states", []),
            }
        elif key == "branching_factor":
            serializable[key] = {
                "peak": value.get("peak", {}),
                "curve_summary": {
                    "num_turns": len(value.get("curve", {})),
                },
            }
        elif key == "iteration_efficiency":
            serializable[key] = {"summary": value.get("summary", {})}
        else:
            serializable[key] = value
    with data_path.open("w") as f:
        json.dump(serializable, f, indent=2, default=str)

    print(f"\n{'=' * 60}")
    print(f"Layer 1 Baseline Characterization Complete")
    print(f"{'=' * 60}")
    print(f"Report:  {report_path}")
    print(f"Data:    {data_path}")
    print(f"Plots:   {output_dir / 'plots'}")
    if not args.skip_convergence:
        print(f"Conv.:   {output_dir / 'convergence'}")


if __name__ == "__main__":
    main()
