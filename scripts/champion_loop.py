#!/usr/bin/env python
"""Champion Self-Improvement Loop.

Runs the current champion agent against a randomized pool of challengers,
captures snapshot data for evaluator refinement, and documents TrueSkill
progression toward an agent that reliably beats a human player.

Each iteration:
  1. Selects 3 challenger agents at random from a diverse pool.
  2. Runs an arena tournament (champion vs pool), with snapshots enabled.
  3. Parses the summary and updates the persistent registry.
  4. Writes a detailed Markdown report of all progress so far.
  5. Optionally re-calibrates the evaluator weights from accumulated data.

Usage:
    # Run 10 improvement iterations with 20 games each
    python scripts/champion_loop.py --iterations 10 --games-per-iter 20

    # Run with evaluator re-calibration every 5 iterations
    python scripts/champion_loop.py --iterations 20 --eval-update-interval 5

    # Show progress report without running new games
    python scripts/champion_loop.py --show

    # Smoke test (2 iterations, 4 games each)
    python scripts/champion_loop.py --iterations 2 --games-per-iter 4
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCRIPTS_DIR = ROOT / "scripts"
REGISTRY_PATH = DATA_DIR / "champion_registry.json"
PROGRESS_MD_PATH = DATA_DIR / "champion_progress.md"
CALIBRATED_WEIGHTS_PATH = DATA_DIR / "layer6_calibrated_weights.json"

# ---------------------------------------------------------------------------
# Champion baseline parameters (from challenge_champion_config + Layer 9 best)
# ---------------------------------------------------------------------------

CHAMPION_BASE_PARAMS: Dict[str, Any] = {
    "deterministic_time_budget": True,
    "iterations_per_ms": 0.5,
    "exploration_constant": 1.414,
    "use_transposition_table": True,
    "rollout_policy": "random",
    "rollout_cutoff_depth": 5,
    "minimax_backup_alpha": 0.25,
    "rave_enabled": True,
    "rave_k": 1000,
    "progressive_widening_enabled": True,
    "pw_c": 2.0,
    "pw_alpha": 0.5,
    "adaptive_rollout_depth_enabled": True,
    "adaptive_rollout_depth_base": 5,
    "adaptive_rollout_depth_avg_bf": 80.0,
    "state_eval_weights": {
        "squares_placed": 0.0295,
        "remaining_piece_area": -0.0295,
        "accessible_corners": 0.243,
        "reachable_empty_squares": 0.081,
        "largest_remaining_piece_size": -0.231,
        "opponent_avg_mobility": -0.3,
        "center_proximity": 0.0,
        "territory_enclosure_area": 0.0,
    },
}

CHAMPION_THINKING_TIME_MS = 500

# ---------------------------------------------------------------------------
# Challenger pool definitions
# Each entry is a full agent config dict (name, type, thinking_time_ms, params).
# Pool is sampled to fill the 3 non-champion seats each iteration.
# ---------------------------------------------------------------------------

_BASE_MCTS = {
    "deterministic_time_budget": True,
    "iterations_per_ms": 0.5,
    "exploration_constant": 1.414,
    "rollout_policy": "random",
    "rollout_cutoff_depth": 5,
    "minimax_backup_alpha": 0.25,
    "rave_enabled": True,
    "rave_k": 1000,
    "state_eval_weights": {
        "squares_placed": 0.0295,
        "remaining_piece_area": -0.0295,
        "accessible_corners": 0.243,
        "reachable_empty_squares": 0.081,
        "largest_remaining_piece_size": -0.231,
        "opponent_avg_mobility": -0.3,
        "center_proximity": 0.0,
        "territory_enclosure_area": 0.0,
    },
}

CHALLENGER_POOL: List[Dict[str, Any]] = [
    # ---- Baseline agents (always weak, anchor the floor) ----
    {"name": "random", "type": "random"},
    {"name": "heuristic", "type": "heuristic"},
    # ---- MCTS at reduced compute (100ms → 50 iters) ----
    {
        "name": "mcts_light",
        "type": "mcts",
        "thinking_time_ms": 100,
        "params": dict(_BASE_MCTS),
    },
    # ---- MCTS at standard compute (200ms → 100 iters) ----
    {
        "name": "mcts_standard",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": dict(_BASE_MCTS),
    },
    # ---- MCTS at 300ms (competitive challenger) ----
    {
        "name": "mcts_strong",
        "type": "mcts",
        "thinking_time_ms": 300,
        "params": dict(_BASE_MCTS),
    },
    # ---- Higher exploration (broader tree) ----
    {
        "name": "mcts_explorer",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {**_BASE_MCTS, "exploration_constant": 2.0},
    },
    # ---- Conservative exploration (deeper exploitation) ----
    {
        "name": "mcts_exploiter",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {**_BASE_MCTS, "exploration_constant": 0.707},
    },
    # ---- Heavy RAVE bias ----
    {
        "name": "mcts_rave_heavy",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {**_BASE_MCTS, "rave_k": 5000},
    },
    # ---- No rollout cutoff (full random rollouts) ----
    {
        "name": "mcts_full_rollout",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {k: v for k, v in _BASE_MCTS.items() if k != "rollout_cutoff_depth"},
    },
    # ---- Adaptive rollout depth enabled ----
    {
        "name": "mcts_adaptive_depth",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            **_BASE_MCTS,
            "adaptive_rollout_depth_enabled": True,
            "adaptive_rollout_depth_base": 5,
            "adaptive_rollout_depth_avg_bf": 80.0,
        },
    },
    # ---- Champion clone at half budget (tests compute efficiency) ----
    {
        "name": "champion_clone_250ms",
        "type": "mcts",
        "thinking_time_ms": 250,
        "params": dict(CHAMPION_BASE_PARAMS),
    },
]

# Pool tiers for sampling: always include at least 1 "strong" MCTS agent.
_STRONG_POOL = [c["name"] for c in CHALLENGER_POOL if c.get("type") == "mcts"]
_WEAK_POOL = [c["name"] for c in CHALLENGER_POOL if c.get("type") != "mcts"]
_POOL_BY_NAME = {c["name"]: c for c in CHALLENGER_POOL}


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------


def _load_registry() -> Dict[str, Any]:
    if REGISTRY_PATH.exists():
        with REGISTRY_PATH.open() as f:
            return json.load(f)
    return {
        "current_version": "v1",
        "versions": {},
        "iterations": [],
        "snapshot_csv_paths": [],
        "total_games_played": 0,
    }


def _save_registry(registry: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with REGISTRY_PATH.open("w") as f:
        json.dump(registry, f, indent=2)


def _get_champion_params(registry: Dict[str, Any]) -> Dict[str, Any]:
    """Return the current champion's MCTS params, falling back to baseline."""
    version = registry.get("current_version", "v1")
    versions = registry.get("versions", {})
    if version in versions:
        return versions[version].get("params", CHAMPION_BASE_PARAMS)
    return CHAMPION_BASE_PARAMS


# ---------------------------------------------------------------------------
# Arena config generation
# ---------------------------------------------------------------------------


def _sample_challengers(registry: Dict[str, Any], rng: random.Random) -> List[str]:
    """Sample 3 challenger names, ensuring diversity."""
    # Always pick at least 1 strong MCTS challenger
    strong = rng.choice(_STRONG_POOL)
    # Fill remaining 2 slots from the full pool (excluding the chosen strong one)
    rest_pool = [n for n in (_STRONG_POOL + _WEAK_POOL) if n != strong]
    others = rng.sample(rest_pool, k=min(2, len(rest_pool)))
    return [strong] + others


def _build_arena_config(
    champion_params: Dict[str, Any],
    challenger_names: List[str],
    games: int,
    seed: int,
    iteration: int,
) -> Dict[str, Any]:
    """Construct a RunConfig dict for one improvement iteration."""
    agents: List[Dict[str, Any]] = [
        {
            "name": "champion",
            "type": "mcts",
            "thinking_time_ms": CHAMPION_THINKING_TIME_MS,
            "params": champion_params,
        }
    ]
    for name in challenger_names:
        cfg = _POOL_BY_NAME[name]
        agents.append(
            {
                "name": cfg["name"],
                "type": cfg["type"],
                "thinking_time_ms": cfg.get("thinking_time_ms"),
                "params": dict(cfg.get("params", {})),
            }
        )

    return {
        "agents": agents,
        "num_games": games,
        "seed": seed,
        "seat_policy": "round_robin",
        "output_root": "arena_runs",
        "max_turns": 2500,
        "snapshots": {
            "enabled": True,
            "strategy": "fixed_ply",
            "checkpoints": [8, 16, 24, 32, 40, 48, 56, 64],
        },
        "notes": f"Champion loop iteration {iteration} — champion vs {', '.join(challenger_names)}",
    }


# ---------------------------------------------------------------------------
# Arena execution
# ---------------------------------------------------------------------------


def _run_arena(config: Dict[str, Any]) -> str:
    """Write a temp config, run arena.py, return the run directory."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="champion_iter_",
        dir=str(SCRIPTS_DIR),
        delete=False,
    ) as tmp:
        json.dump(config, tmp, indent=2)
        tmp_path = tmp.name

    try:
        cmd = [sys.executable, str(SCRIPTS_DIR / "arena.py"), "--config", tmp_path]
        print(f"  [arena] {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"arena.py exited with code {result.returncode}")
    finally:
        os.unlink(tmp_path)

    run_dir = _find_latest_run()
    if run_dir is None:
        raise RuntimeError("Could not locate arena output directory after run.")
    return run_dir


def _find_latest_run(output_root: str = "arena_runs") -> Optional[str]:
    root = Path(output_root)
    if not root.exists():
        return None
    runs = sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for r in runs:
        if r.is_dir() and (r / "summary.json").exists():
            return str(r)
    return None


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------


def _parse_summary(run_dir: str) -> Dict[str, Any]:
    with open(Path(run_dir) / "summary.json") as f:
        data = json.load(f)

    agents_out: Dict[str, Any] = {}
    for agent_name, agent_data in data.get("agents", {}).items():
        trueskill_mu = agent_data.get("trueskill_mu")
        trueskill_sigma = agent_data.get("trueskill_sigma")
        conservative = (
            trueskill_mu - 3.0 * trueskill_sigma
            if trueskill_mu is not None and trueskill_sigma is not None
            else None
        )
        agents_out[agent_name] = {
            "wins": agent_data.get("wins", 0),
            "win_rate": agent_data.get("win_rate", 0.0),
            "avg_score": agent_data.get("avg_score", 0.0),
            "trueskill_mu": trueskill_mu,
            "trueskill_sigma": trueskill_sigma,
            "trueskill_conservative": conservative,
        }

    snapshot_csv: Optional[str] = None
    snapshots_meta = data.get("snapshots", {})
    if isinstance(snapshots_meta, dict) and snapshots_meta.get("path_csv"):
        snapshot_csv = snapshots_meta["path_csv"]

    return {
        "num_games": data.get("num_games", 0),
        "completed_games": data.get("completed_games", 0),
        "agents": agents_out,
        "snapshot_csv": snapshot_csv,
    }


# ---------------------------------------------------------------------------
# Evaluator weight improvement
# ---------------------------------------------------------------------------


def _try_improve_evaluator(snapshot_csv_paths: List[str]) -> Optional[Dict[str, float]]:
    """Concatenate snapshots and rerun feature analysis to get new weights.

    Returns updated weight dict if successful, None otherwise.
    """
    try:
        import pandas as pd  # type: ignore
        from sklearn.linear_model import LinearRegression  # type: ignore
    except ImportError:
        print("  [eval] pandas or sklearn not available — skipping evaluator update.")
        return None

    valid_paths = [p for p in snapshot_csv_paths if p and Path(p).exists()]
    if not valid_paths:
        print("  [eval] No valid snapshot CSVs found — skipping evaluator update.")
        return None

    dfs = []
    for path in valid_paths:
        try:
            dfs.append(pd.read_csv(path))
        except Exception as exc:
            print(f"  [eval] Warning: could not read {path}: {exc}")

    if not dfs:
        return None

    df = pd.concat(dfs, ignore_index=True)
    print(f"  [eval] Loaded {len(df)} snapshot rows from {len(dfs)} files.")

    # Feature columns produced by BlokusStateEvaluator, prefixed with "se_"
    feature_names = [
        "squares_placed",
        "remaining_piece_area",
        "accessible_corners",
        "reachable_empty_squares",
        "largest_remaining_piece_size",
        "opponent_avg_mobility",
        "center_proximity",
        "territory_enclosure_area",
    ]
    se_cols = [f"se_{f}" for f in feature_names]
    available = [c for c in se_cols if c in df.columns]

    if len(available) < 4:
        print(f"  [eval] Only {len(available)} SE feature columns present — skipping.")
        return None

    label_col = "label_is_winner"
    if label_col not in df.columns:
        print("  [eval] label_is_winner column not found — skipping.")
        return None

    X = df[available].fillna(0.0).values.astype(float)
    y = df[label_col].fillna(0.0).values.astype(float)

    if len(X) < 100:
        print(f"  [eval] Only {len(X)} rows — not enough data for regression.")
        return None

    lr = LinearRegression().fit(X, y)
    raw_coefs = dict(zip(available, lr.coef_))

    # Map back to feature names and apply max-abs normalisation to [-0.3, 0.3]
    coefs = {f: raw_coefs.get(f"se_{f}", 0.0) for f in feature_names}
    max_abs = max(abs(v) for v in coefs.values()) or 1.0
    scale = 0.3 / max_abs
    new_weights = {f: round(v * scale, 6) for f, v in coefs.items()}

    print("  [eval] Derived new evaluator weights:")
    for f, w in new_weights.items():
        print(f"    {f}: {w:+.4f}")

    return new_weights


def _validate_new_weights(
    old_params: Dict[str, Any],
    new_weights: Dict[str, float],
    games: int,
    seed: int,
) -> bool:
    """Run a mini arena: champion_new vs champion_old. Return True if new wins more."""
    new_params = {**old_params, "state_eval_weights": new_weights}
    config = {
        "agents": [
            {
                "name": "champion_new_weights",
                "type": "mcts",
                "thinking_time_ms": CHAMPION_THINKING_TIME_MS,
                "params": new_params,
            },
            {
                "name": "champion_old_weights",
                "type": "mcts",
                "thinking_time_ms": CHAMPION_THINKING_TIME_MS,
                "params": old_params,
            },
            {"name": "random_a", "type": "random"},
            {"name": "random_b", "type": "random"},
        ],
        "num_games": games,
        "seed": seed,
        "seat_policy": "round_robin",
        "output_root": "arena_runs",
        "max_turns": 2500,
        "snapshots": {"enabled": False, "checkpoints": []},
        "notes": "Champion evaluator weight validation run",
    }
    print("  [eval] Running weight validation arena...")
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="weight_val_",
        dir=str(SCRIPTS_DIR),
        delete=False,
    ) as tmp:
        json.dump(config, tmp, indent=2)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "arena.py"), "--config", tmp_path],
            capture_output=False,
            text=True,
        )
        if result.returncode != 0:
            print("  [eval] Validation arena failed.")
            return False
    finally:
        os.unlink(tmp_path)

    run_dir = _find_latest_run()
    if run_dir is None:
        return False

    parsed = _parse_summary(run_dir)
    new_wr = parsed["agents"].get("champion_new_weights", {}).get("win_rate", 0.0)
    old_wr = parsed["agents"].get("champion_old_weights", {}).get("win_rate", 0.0)
    print(f"  [eval] Validation: new_weights WR={new_wr:.1%}  old_weights WR={old_wr:.1%}")
    return new_wr > old_wr


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------


def _render_markdown(registry: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Champion Self-Improvement Progress")
    lines.append("")
    lines.append(f"**Current champion version:** {registry.get('current_version', '?')}")
    lines.append(f"**Total games played:** {registry.get('total_games_played', 0)}")
    lines.append(
        f"**Report generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    lines.append("")

    versions = registry.get("versions", {})
    if versions:
        lines.append("## Champion Version History")
        lines.append("")
        lines.append("| Version | Promoted at | Avg WR vs Pool | Avg TrueSkill μ | Avg Score |")
        lines.append("|---------|-------------|----------------|-----------------|-----------|")
        for ver, info in versions.items():
            promoted = info.get("promoted_at", "—")[:19]
            avg_wr = info.get("avg_win_rate")
            avg_mu = info.get("avg_trueskill_mu")
            avg_sc = info.get("avg_score")
            wr_str = f"{avg_wr:.1%}" if avg_wr is not None else "—"
            mu_str = f"{avg_mu:.1f}" if avg_mu is not None else "—"
            sc_str = f"{avg_sc:.1f}" if avg_sc is not None else "—"
            lines.append(f"| {ver} | {promoted} | {wr_str} | {mu_str} | {sc_str} |")
        lines.append("")

    iterations = registry.get("iterations", [])
    if not iterations:
        lines.append("*No iterations completed yet.*")
        return "\n".join(lines)

    lines.append("## Iteration Log")
    lines.append("")
    lines.append(
        "| Iter | Champion WR | Champion μ | Champion σ | Conservative | Challengers | Games |"
    )
    lines.append(
        "|------|------------|-----------|-----------|--------------|-------------|-------|"
    )
    for entry in iterations:
        idx = entry.get("iteration", "?")
        champ = entry.get("champion_stats", {})
        wr = champ.get("win_rate")
        mu = champ.get("trueskill_mu")
        sigma = champ.get("trueskill_sigma")
        conservative = champ.get("trueskill_conservative")
        challengers = ", ".join(entry.get("challengers", []))
        games = entry.get("completed_games", entry.get("num_games", "?"))
        wr_s = f"{wr:.1%}" if wr is not None else "—"
        mu_s = f"{mu:.1f}" if mu is not None else "—"
        sig_s = f"{sigma:.2f}" if sigma is not None else "—"
        con_s = f"{conservative:.1f}" if conservative is not None else "—"
        lines.append(
            f"| {idx} | {wr_s} | {mu_s} | {sig_s} | {con_s} | {challengers} | {games} |"
        )
    lines.append("")

    # Trend summary
    champ_wrs = [
        e["champion_stats"]["win_rate"]
        for e in iterations
        if e.get("champion_stats", {}).get("win_rate") is not None
    ]
    champ_mus = [
        e["champion_stats"]["trueskill_mu"]
        for e in iterations
        if e.get("champion_stats", {}).get("trueskill_mu") is not None
    ]
    if len(champ_wrs) >= 2:
        delta_wr = (champ_wrs[-1] - champ_wrs[0]) * 100
        sign = "+" if delta_wr >= 0 else ""
        lines.append("## Trend Summary")
        lines.append("")
        lines.append(
            f"- **Win rate change (first→latest):** {sign}{delta_wr:.1f} percentage points"
        )
        if len(champ_mus) >= 2:
            delta_mu = champ_mus[-1] - champ_mus[0]
            sign_mu = "+" if delta_mu >= 0 else ""
            lines.append(f"- **TrueSkill μ change:** {sign_mu}{delta_mu:.2f}")
        lines.append("")

    # Evaluator update log
    eval_updates = [e for e in iterations if e.get("eval_updated")]
    if eval_updates:
        lines.append("## Evaluator Weight Updates")
        lines.append("")
        for e in eval_updates:
            idx = e.get("iteration", "?")
            new_w = e.get("new_eval_weights", {})
            lines.append(f"### After iteration {idx}")
            lines.append("")
            lines.append("| Feature | Weight |")
            lines.append("|---------|--------|")
            for feat, w in new_w.items():
                lines.append(f"| `{feat}` | `{w:+.4f}` |")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_Human baseline target: champion must sustain WR > 35% across diverse pool "
        "with sufficient game count for statistical confidence._"
    )
    lines.append("")
    return "\n".join(lines)


def _write_report(registry: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_MD_PATH.write_text(_render_markdown(registry), encoding="utf-8")
    print(f"  [report] Written: {PROGRESS_MD_PATH}")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def _run_iteration(
    iteration: int,
    registry: Dict[str, Any],
    games: int,
    base_seed: int,
    rng: random.Random,
) -> Dict[str, Any]:
    """Execute one improvement iteration and return the entry to log."""
    version = registry.get("current_version", "v1")
    champion_params = _get_champion_params(registry)
    challengers = _sample_challengers(registry, rng)
    seed = base_seed + iteration

    print(f"\n{'='*70}")
    print(f"  Iteration {iteration}  |  Champion: {version}  |  Pool: {', '.join(challengers)}")
    print(f"{'='*70}")

    config = _build_arena_config(champion_params, challengers, games, seed, iteration)
    run_dir = _run_arena(config)
    parsed = _parse_summary(run_dir)

    champ_stats = parsed["agents"].get("champion", {})
    print(
        f"  Champion WR={champ_stats.get('win_rate', 0):.1%}  "
        f"μ={champ_stats.get('trueskill_mu', 0):.1f}  "
        f"σ={champ_stats.get('trueskill_sigma', 0):.2f}  "
        f"avg_score={champ_stats.get('avg_score', 0):.1f}"
    )
    for name in challengers:
        s = parsed["agents"].get(name, {})
        print(
            f"  {name:30s}  WR={s.get('win_rate', 0):.1%}  "
            f"μ={s.get('trueskill_mu', 0):.1f}"
        )

    return {
        "iteration": iteration,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "champion_version": version,
        "challengers": challengers,
        "run_dir": run_dir,
        "num_games": parsed["num_games"],
        "completed_games": parsed["completed_games"],
        "champion_stats": champ_stats,
        "challenger_stats": {n: parsed["agents"].get(n, {}) for n in challengers},
        "snapshot_csv": parsed.get("snapshot_csv"),
        "eval_updated": False,
        "new_eval_weights": None,
    }


def _update_version_stats(registry: Dict[str, Any], version: str, entry: Dict[str, Any]) -> None:
    """Update the running average stats for the given champion version."""
    versions = registry.setdefault("versions", {})
    if version not in versions:
        versions[version] = {
            "promoted_at": entry["timestamp"],
            "params": _get_champion_params(registry),
            "_wr_acc": 0.0,
            "_mu_acc": 0.0,
            "_sc_acc": 0.0,
            "_count": 0,
        }
    v = versions[version]
    cs = entry.get("champion_stats", {})
    v["_count"] += 1
    n = v["_count"]
    v["_wr_acc"] += cs.get("win_rate", 0.0)
    v["_mu_acc"] += cs.get("trueskill_mu", 0.0) or 0.0
    v["_sc_acc"] += cs.get("avg_score", 0.0)
    v["avg_win_rate"] = v["_wr_acc"] / n
    v["avg_trueskill_mu"] = v["_mu_acc"] / n
    v["avg_score"] = v["_sc_acc"] / n


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Champion Self-Improvement Loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--iterations", type=int, default=10, help="Number of arena iterations to run."
    )
    parser.add_argument(
        "--games-per-iter", type=int, default=20, help="Arena games per iteration."
    )
    parser.add_argument(
        "--seed", type=int, default=20260429, help="Base RNG seed for the loop."
    )
    parser.add_argument(
        "--eval-update-interval",
        type=int,
        default=5,
        help="Re-calibrate evaluator weights every N iterations (0 = never).",
    )
    parser.add_argument(
        "--eval-validation-games",
        type=int,
        default=16,
        help="Games used to validate new evaluator weights before adopting.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Print progress report and exit without running new iterations.",
    )
    args = parser.parse_args()

    registry = _load_registry()

    if args.show:
        print(_render_markdown(registry))
        return

    rng = random.Random(args.seed)
    completed_so_far = len(registry.get("iterations", []))

    for i in range(1, args.iterations + 1):
        global_iter = completed_so_far + i

        entry = _run_iteration(
            iteration=global_iter,
            registry=registry,
            games=args.games_per_iter,
            base_seed=args.seed,
            rng=rng,
        )

        # Track snapshot paths for later evaluator improvement
        if entry.get("snapshot_csv"):
            registry.setdefault("snapshot_csv_paths", []).append(entry["snapshot_csv"])

        registry["total_games_played"] = (
            registry.get("total_games_played", 0) + entry["completed_games"]
        )

        version = registry.get("current_version", "v1")
        _update_version_stats(registry, version, entry)

        # ----- Evaluator improvement ----------------------------------------
        if (
            args.eval_update_interval > 0
            and global_iter % args.eval_update_interval == 0
        ):
            print(f"\n  [eval] Interval reached — attempting evaluator calibration...")
            snapshot_paths = registry.get("snapshot_csv_paths", [])
            new_weights = _try_improve_evaluator(snapshot_paths)
            if new_weights is not None:
                old_params = _get_champion_params(registry)
                accepted = _validate_new_weights(
                    old_params,
                    new_weights,
                    games=args.eval_validation_games,
                    seed=args.seed + global_iter * 1000,
                )
                if accepted:
                    # Promote to new champion version
                    old_version = registry.get("current_version", "v1")
                    ver_num = int(old_version.lstrip("v") or "1") + 1
                    new_version = f"v{ver_num}"
                    new_params = {**old_params, "state_eval_weights": new_weights}
                    registry["current_version"] = new_version
                    registry.setdefault("versions", {})[new_version] = {
                        "promoted_at": datetime.now(timezone.utc).isoformat(),
                        "params": new_params,
                        "promoted_from": old_version,
                        "promotion_reason": f"Evaluator recalibration at iteration {global_iter}",
                        "_wr_acc": 0.0,
                        "_mu_acc": 0.0,
                        "_sc_acc": 0.0,
                        "_count": 0,
                    }
                    # Also update calibrated weights file
                    cal = {}
                    if CALIBRATED_WEIGHTS_PATH.exists():
                        with CALIBRATED_WEIGHTS_PATH.open() as f:
                            cal = json.load(f)
                    cal["single_weights"] = new_weights
                    with CALIBRATED_WEIGHTS_PATH.open("w") as f:
                        json.dump(cal, f, indent=2)
                    print(
                        f"  [eval] Accepted new weights → promoted champion to {new_version}!"
                    )
                    entry["eval_updated"] = True
                    entry["new_eval_weights"] = new_weights
                else:
                    print("  [eval] New weights did not improve performance — keeping current.")
            else:
                print("  [eval] Calibration skipped.")

        registry.setdefault("iterations", []).append(entry)
        _save_registry(registry)
        _write_report(registry)

        champ_wr = entry["champion_stats"].get("win_rate", 0.0)
        print(f"\n  Iteration {global_iter} complete. Champion WR this run: {champ_wr:.1%}")

    # Final summary
    print(f"\n{'='*70}")
    print(f"  Champion loop complete — {args.iterations} iteration(s) run.")
    print(f"  Current champion: {registry.get('current_version', '?')}")
    print(f"  Total games played: {registry.get('total_games_played', 0)}")
    print(f"  Progress report: {PROGRESS_MD_PATH}")
    print(f"  Registry: {REGISTRY_PATH}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
