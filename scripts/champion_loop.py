#!/usr/bin/env python
"""Champion Self-Improvement Loop.

Runs the champion agent against a randomized pool of opponents each
iteration, accumulates snapshot data for periodic evaluator retraining,
and tracks TrueSkill progression toward reliably beating human players.

Each iteration:
  1. Loads current calibrated evaluation weights.
  2. Samples 3 opponents at random from a diverse pool (baselines through
     near-peer tier-5 agents).
  3. Runs a 4-player arena experiment with snapshots enabled.
  4. Logs champion TrueSkill, win rate, and avg score to data/champion_log.json.
  5. Writes a human-readable progress report to data/champion_progress.md.
  6. Every RETRAIN_GAME_INTERVAL cumulative games, collects fresh self-play data
     and re-runs the Layer 6 regression to update calibrated weights.

Usage:
    # One iteration, 20 games (default)
    python scripts/champion_loop.py

    # Five consecutive iterations
    python scripts/champion_loop.py --iterations 5

    # Larger game count for stronger TrueSkill signal
    python scripts/champion_loop.py --num-games 40

    # Force evaluator retraining after this run
    python scripts/champion_loop.py --retrain

    # Stronger champion (1 second per move)
    python scripts/champion_loop.py --champion-time 1000

    # Show history without running
    python scripts/champion_loop.py --show
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_LOG = "data/champion_log.json"
CALIBRATED_WEIGHTS_PATH = "data/layer6_calibrated_weights.json"
CHAMPION_DATA_PATH = "data/champion_selfplay.parquet"
REPORT_PATH = "data/champion_progress.md"
ARENA_RUNS_ROOT = "arena_runs"
CHAMPION_NAME = "champion"

# Retrain evaluator after this many total games have been played across all
# iterations.  Lower → fresher weights; higher → less overhead per iteration.
RETRAIN_GAME_INTERVAL = 200

# Games to collect for a single retraining cycle (collect_layer6_data.py).
DATA_COLLECTION_GAMES = 100

# Default champion thinking budget (ms).  With iterations_per_ms=0.5 this
# maps to 250 MCTS iterations per move — consistent with Layer 4-9 calibration
# convention for configurations that use rollout_cutoff_depth=5.
DEFAULT_CHAMPION_TIME_MS = 500

# ---------------------------------------------------------------------------
# Calibrated weight loader
# ---------------------------------------------------------------------------

_DEFAULT_SINGLE_WEIGHTS: Dict[str, float] = {
    "squares_placed": 0.0295,
    "remaining_piece_area": -0.0295,
    "accessible_corners": 0.243,
    "reachable_empty_squares": 0.081,
    "largest_remaining_piece_size": -0.231,
    "opponent_avg_mobility": -0.3,
    "center_proximity": 0.0,
    "territory_enclosure_area": 0.0,
}


def _load_calibrated_weights() -> Dict[str, Any]:
    """Load phase and single weights; fall back to embedded defaults."""
    p = Path(CALIBRATED_WEIGHTS_PATH)
    if p.exists():
        with open(p) as f:
            return json.load(f)
    return {"single_weights": _DEFAULT_SINGLE_WEIGHTS, "phase_weights": None}


# ---------------------------------------------------------------------------
# Champion agent definition
# ---------------------------------------------------------------------------

def build_champion_agent(thinking_time_ms: int = DEFAULT_CHAMPION_TIME_MS) -> Dict[str, Any]:
    """Build the champion agent config with all beneficial layers enabled.

    Layer 3:  Progressive widening (c=2.0, α=0.5)
    Layer 4:  Random rollout, cutoff depth=5, minimax backup α=0.25
    Layer 5:  RAVE (k=1000)
    Layer 6:  Phase-dependent calibrated evaluation weights
    Layer 7:  Opponent modeling — alliance + king-maker detection
    Layer 9:  Adaptive exploration C, adaptive rollout depth, sufficiency
              threshold, loss avoidance
    """
    cal = _load_calibrated_weights()

    params: Dict[str, Any] = {
        # Budget
        "deterministic_time_budget": True,
        "iterations_per_ms": 0.5,        # Calibrated for cutoff_depth=5 configs
        # Layer 1/2
        "exploration_constant": 1.414,
        "use_transposition_table": True,
        # Layer 3
        "progressive_widening_enabled": True,
        "pw_c": 2.0,
        "pw_alpha": 0.5,
        # Layer 4
        "rollout_policy": "random",
        "rollout_cutoff_depth": 5,
        "minimax_backup_alpha": 0.25,
        # Layer 5
        "rave_enabled": True,
        "rave_k": 1000,
        # Layer 6 — single weights (phase weights injected below if available)
        "state_eval_weights": cal["single_weights"],
        # Layer 7
        "opponent_modeling_enabled": True,
        "alliance_detection_enabled": True,
        "alliance_threshold": 2.0,
        "kingmaker_detection_enabled": True,
        "kingmaker_score_gap": 15,
        # Layer 9
        "adaptive_rollout_depth_enabled": True,
        "adaptive_rollout_depth_base": 5,
        "adaptive_rollout_depth_avg_bf": 80.0,
        "adaptive_exploration_enabled": True,
        "adaptive_exploration_base": 1.414,
        "adaptive_exploration_avg_bf": 80.0,
        "sufficiency_threshold_enabled": True,
        "loss_avoidance_enabled": True,
        "loss_avoidance_threshold": -50.0,
    }

    if cal.get("phase_weights"):
        params["state_eval_phase_weights"] = cal["phase_weights"]

    return {
        "name": CHAMPION_NAME,
        "type": "mcts",
        "thinking_time_ms": thinking_time_ms,
        "params": params,
    }


# ---------------------------------------------------------------------------
# Opponent pool  (11 agents across 5 tiers)
# ---------------------------------------------------------------------------
#
# Tier 1  Baselines       — random, heuristic
# Tier 2  Vanilla MCTS    — plain UCT at 25 / 50 / 100 / 200 ms
# Tier 3  L4+5 enhanced   — rollout cutoff, minimax, RAVE
# Tier 4  L9 partial      — adaptive meta-opts at 200 ms, no opponent model
# Tier 5  Near-peer       — same time budget as champion, same L4-9 layers
#                           but no opponent modelling (isolates that advantage)
#
# Pool agents use "fast" throughput (10 iter/ms) when they have no
# rollout_cutoff_depth, and "slow" throughput (0.5 iter/ms) when they do,
# matching the Layer 4-9 calibration convention.

OPPONENT_POOL: List[Dict[str, Any]] = [
    # --- Tier 1: Baselines ---
    {"name": "pool_random",    "type": "random",    "params": {}},
    {"name": "pool_heuristic", "type": "heuristic", "params": {}},

    # --- Tier 2: Vanilla MCTS ---
    {
        "name": "pool_mcts_25ms", "type": "mcts", "thinking_time_ms": 25,
        "params": {"deterministic_time_budget": True, "iterations_per_ms": 10.0},
    },
    {
        "name": "pool_mcts_50ms", "type": "mcts", "thinking_time_ms": 50,
        "params": {"deterministic_time_budget": True, "iterations_per_ms": 10.0},
    },
    {
        "name": "pool_mcts_100ms", "type": "mcts", "thinking_time_ms": 100,
        "params": {"deterministic_time_budget": True, "iterations_per_ms": 10.0},
    },
    {
        "name": "pool_mcts_200ms", "type": "mcts", "thinking_time_ms": 200,
        "params": {"deterministic_time_budget": True, "iterations_per_ms": 10.0},
    },

    # --- Tier 3: Layer 4+5 enhanced ---
    {
        "name": "pool_rave_100ms", "type": "mcts", "thinking_time_ms": 100,
        "params": {
            "deterministic_time_budget": True, "iterations_per_ms": 10.0,
            "rave_enabled": True, "rave_k": 1000,
        },
    },
    {
        "name": "pool_l4_cutoff_100ms", "type": "mcts", "thinking_time_ms": 100,
        "params": {
            "deterministic_time_budget": True, "iterations_per_ms": 0.5,
            "rollout_policy": "random", "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
        },
    },
    {
        "name": "pool_l45_full_100ms", "type": "mcts", "thinking_time_ms": 100,
        "params": {
            "deterministic_time_budget": True, "iterations_per_ms": 0.5,
            "rollout_policy": "random", "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True, "rave_k": 1000,
        },
    },

    # --- Tier 4: Layer 9 partial (200 ms, no opponent model) ---
    {
        "name": "pool_l9_partial_200ms", "type": "mcts", "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True, "iterations_per_ms": 0.5,
            "rollout_policy": "random", "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True, "rave_k": 1000,
            "adaptive_exploration_enabled": True,
            "adaptive_exploration_base": 1.414,
            "adaptive_exploration_avg_bf": 80.0,
            "adaptive_rollout_depth_enabled": True,
            "adaptive_rollout_depth_base": 5,
            "sufficiency_threshold_enabled": True,
            "loss_avoidance_enabled": True,
        },
    },

    # --- Tier 5: Near-peer at same budget, without opponent modeling ---
    {
        "name": "pool_peer_500ms", "type": "mcts", "thinking_time_ms": 500,
        "params": {
            "deterministic_time_budget": True, "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "use_transposition_table": True,
            "rollout_policy": "random", "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True, "rave_k": 1000,
            "progressive_widening_enabled": True, "pw_c": 2.0, "pw_alpha": 0.5,
            "adaptive_rollout_depth_enabled": True,
            "adaptive_rollout_depth_base": 5,
            "adaptive_rollout_depth_avg_bf": 80.0,
            "adaptive_exploration_enabled": True,
            "adaptive_exploration_base": 1.414,
            "adaptive_exploration_avg_bf": 80.0,
            "sufficiency_threshold_enabled": True,
            "loss_avoidance_enabled": True,
        },
    },
]

_POOL_NAMES = {o["name"] for o in OPPONENT_POOL}


def sample_opponents(n: int, rng: random.Random) -> List[Dict[str, Any]]:
    """Return n opponents sampled without replacement from OPPONENT_POOL."""
    return rng.sample(OPPONENT_POOL, n)


# ---------------------------------------------------------------------------
# Arena orchestration
# ---------------------------------------------------------------------------

def build_arena_config(
    champion: Dict[str, Any],
    opponents: List[Dict[str, Any]],
    num_games: int,
    seed: int,
) -> Dict[str, Any]:
    """Assemble a complete arena config dict (4 agents total)."""
    opp_names = ", ".join(o["name"] for o in opponents)
    return {
        "agents": [champion] + opponents,
        "num_games": num_games,
        "seed": seed,
        "seat_policy": "randomized",
        "output_root": ARENA_RUNS_ROOT,
        "max_turns": 2500,
        "snapshots": {
            "enabled": True,
            "strategy": "fixed_ply",
            "checkpoints": [8, 16, 24, 32, 40, 48, 56, 64],
        },
        "notes": f"Champion loop — opponents: {opp_names}",
    }


def _find_latest_run() -> Optional[str]:
    """Return the most recently modified arena run directory."""
    root = Path(ARENA_RUNS_ROOT)
    if not root.exists():
        return None
    runs = sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for r in runs:
        if r.is_dir() and (r / "summary.json").exists():
            return str(r)
    return None


def run_arena(config: Dict[str, Any]) -> str:
    """Write config to a temp file, run arena.py, return run_dir path."""
    # Write to scripts/ dir so relative imports inside arena.py remain valid
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir="scripts",
        delete=False, prefix="_champ_tmp_",
    )
    try:
        json.dump(config, tmp, indent=2)
        tmp.close()
        cmd = [sys.executable, "scripts/arena.py", "--config", tmp.name]
        print(f"[champion_loop] Running: {' '.join(cmd)}")
        proc = subprocess.run(cmd, text=True, capture_output=False)
        if proc.returncode != 0:
            print(f"[champion_loop] Arena exited with code {proc.returncode}")
            sys.exit(1)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    run_dir = _find_latest_run()
    if run_dir is None:
        print("[champion_loop] ERROR: Could not locate arena output directory.")
        sys.exit(1)
    print(f"[champion_loop] Run output: {run_dir}")
    return run_dir


def parse_summary(run_dir: str) -> Dict[str, Any]:
    """Extract per-agent metrics from a run's summary.json."""
    with open(os.path.join(run_dir, "summary.json")) as f:
        data = json.load(f)

    agents: Dict[str, Dict] = {}
    for name, stats in data.get("agents", {}).items():
        agents[name] = {
            "wins": stats.get("wins", 0),
            "win_rate": stats.get("win_rate", 0.0),
            "avg_score": stats.get("avg_score", 0.0),
            "trueskill_mu": stats.get("trueskill_mu"),
            "trueskill_sigma": stats.get("trueskill_sigma"),
        }

    return {"num_games": data.get("num_games", 0), "agents": agents}


# ---------------------------------------------------------------------------
# Snapshot accumulation
# ---------------------------------------------------------------------------

def accumulate_snapshots(run_dir: str) -> int:
    """Append arena snapshot rows to the champion selfplay parquet.

    Returns the number of new rows added.
    """
    snap_path = Path(run_dir) / "snapshots.parquet"
    if not snap_path.exists():
        return 0

    try:
        import pandas as pd
    except ImportError:
        print("[champion_loop] pandas not available — skipping snapshot accumulation")
        return 0

    new_df = pd.read_parquet(str(snap_path))
    if new_df.empty:
        return 0

    out = Path(CHAMPION_DATA_PATH)
    out.parent.mkdir(parents=True, exist_ok=True)

    if out.exists():
        existing = pd.read_parquet(str(out))
        combined = pd.concat([existing, new_df], ignore_index=True)
    else:
        combined = new_df

    combined.to_parquet(str(out), index=False)
    return len(new_df)


# ---------------------------------------------------------------------------
# Evaluator retraining
# ---------------------------------------------------------------------------

def retrain_evaluator(num_games: int = DATA_COLLECTION_GAMES) -> Dict[str, Any]:
    """Run a full evaluator retraining cycle.

    Steps:
      1. Collect `num_games` MCTS self-play games with both SE and winprob
         features (scripts/collect_layer6_data.py).
      2. Run per-phase regression and SHAP analysis
         (scripts/analyze_layer6_features.py) which overwrites
         data/layer6_calibrated_weights.json.

    Returns a dict with retrain metadata.
    """
    print(f"\n[champion_loop] {'=' * 60}")
    print(f"[champion_loop] Evaluator Retraining Cycle")
    print(f"[champion_loop] Collecting {num_games} self-play games …")

    data_path = "data/champion_selfplay_latest.parquet"

    # Step 1: collect self-play data
    cmd1 = [
        sys.executable, "scripts/collect_layer6_data.py",
        "--num-games", str(num_games),
        "--agent-type", "mcts",
        "--thinking-time-ms", "100",
        "--workers", "2",
        "--output", data_path,
    ]
    print(f"[champion_loop] {' '.join(cmd1)}")
    r1 = subprocess.run(cmd1, text=True, capture_output=False)
    if r1.returncode != 0:
        print(f"[champion_loop] Data collection failed (exit {r1.returncode})")
        return {"success": False, "step": "data_collection"}

    # Step 2: run regression / SHAP analysis and write calibrated weights
    cmd2 = [
        sys.executable, "scripts/analyze_layer6_features.py",
        "--input", data_path,
        "--output-dir", "data",
    ]
    print(f"[champion_loop] {' '.join(cmd2)}")
    r2 = subprocess.run(cmd2, text=True, capture_output=False)
    if r2.returncode != 0:
        print(f"[champion_loop] Feature analysis failed (exit {r2.returncode})")
        return {"success": False, "step": "analysis"}

    print(f"[champion_loop] Retrain complete — weights updated: {CALIBRATED_WEIGHTS_PATH}")
    return {"success": True, "data_games": num_games}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def load_log(log_path: str = DEFAULT_LOG) -> List[Dict]:
    p = Path(log_path)
    if not p.exists():
        return []
    with open(p) as f:
        return json.load(f)


def append_log(entry: Dict[str, Any], log_path: str = DEFAULT_LOG) -> List[Dict]:
    log = load_log(log_path)
    log.append(entry)
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)
    return log


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _conservative(mu: Optional[float], sigma: Optional[float]) -> Optional[float]:
    return (mu - 3.0 * sigma) if (mu is not None and sigma is not None) else None


def generate_report(log: List[Dict], report_path: str = REPORT_PATH) -> None:
    """Write a detailed markdown progress report."""
    if not log:
        return

    total_games = sum(e.get("num_games", 0) for e in log)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: List[str] = [
        "# Champion Self-Improvement Progress",
        "",
        f"_Last updated: {now}_",
        "",
        f"**Goal:** Build an MCTS agent that reliably beats a human Blokus player.",
        f"**Iterations run:** {len(log)}  |  **Total games:** {total_games}",
        "",
    ]

    # -- Champion configuration snapshot --
    cal = _load_calibrated_weights()
    sw = cal.get("single_weights", _DEFAULT_SINGLE_WEIGHTS)
    has_phase = bool(cal.get("phase_weights"))

    lines += [
        "## Champion Configuration",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| thinking_time_ms | {DEFAULT_CHAMPION_TIME_MS} |",
        "| iterations_per_ms | 0.5 (→ 250 iter/move) |",
        "| rollout_policy | random |",
        "| rollout_cutoff_depth | 5 |",
        "| minimax_backup_alpha | 0.25 |",
        "| rave_k | 1000 |",
        "| progressive_widening | c=2.0, α=0.5 |",
        "| opponent_modeling | alliance + kingmaker |",
        "| adaptive_exploration | enabled |",
        "| adaptive_rollout_depth | base=5 |",
        "| sufficiency_threshold | enabled |",
        "| loss_avoidance | enabled |",
        f"| phase-dependent weights | {'yes' if has_phase else 'no (defaults)'} |",
        "",
        "**Current evaluation weights:**",
        "",
        "| Feature | Weight |",
        "|---------|--------|",
    ]
    for k, v in sorted(sw.items(), key=lambda x: abs(x[1]), reverse=True):
        lines.append(f"| {k} | {v:+.4f} |")
    lines.append("")

    # -- TrueSkill progression table --
    lines += [
        "## TrueSkill Progression",
        "",
        "| # | Date | Games | Opponents | WR% | Avg Score | μ | σ | Conservative |",
        "|---|------|-------|-----------|-----|-----------|---|---|--------------|",
    ]
    for i, entry in enumerate(log, 1):
        ts = entry.get("timestamp", "?")[:10]
        games = entry.get("num_games", "?")
        opp = [n.replace("pool_", "") for n in entry.get("opponents_sampled", [])]
        opp_str = ", ".join(opp) if opp else "—"
        c = entry.get("agents", {}).get(CHAMPION_NAME, {})
        wr = c.get("win_rate", 0.0) * 100
        avg = c.get("avg_score", 0.0)
        mu = c.get("trueskill_mu")
        sigma = c.get("trueskill_sigma")
        cons = _conservative(mu, sigma)
        mu_s    = f"{mu:.1f}"   if mu    is not None else "—"
        sig_s   = f"{sigma:.2f}" if sigma is not None else "—"
        cons_s  = f"{cons:.1f}" if cons  is not None else "—"
        lines.append(
            f"| {i} | {ts} | {games} | {opp_str} | {wr:.1f} | {avg:.1f}"
            f" | {mu_s} | {sig_s} | {cons_s} |"
        )
    lines.append("")

    # -- Per-opponent win rates (aggregate) --
    opp_records: Dict[str, List[float]] = {}
    for entry in log:
        for name, stats in entry.get("agents", {}).items():
            if name == CHAMPION_NAME:
                continue
            opp_records.setdefault(name, []).append(stats.get("win_rate", 0.0))

    if opp_records:
        lines += [
            "## Champion Win Rate vs Opponent Types",
            "",
            "_Win rate shown is the **opponent's** rate — lower means champion is "
            "dominating that slot._",
            "",
            "| Opponent | Appearances | Opp WR% | Trend |",
            "|----------|-------------|---------|-------|",
        ]
        for name in sorted(opp_records):
            wrs = opp_records[name]
            avg_wr = sum(wrs) / len(wrs) * 100
            if len(wrs) >= 3:
                if wrs[-1] < wrs[0] - 0.02:
                    trend = "▲ champion improving"
                elif wrs[-1] > wrs[0] + 0.02:
                    trend = "▼ opponent catching up"
                else:
                    trend = "→ stable"
            else:
                trend = "—"
            lines.append(f"| {name} | {len(wrs)} | {avg_wr:.1f} | {trend} |")
        lines.append("")

    # -- Trend summary --
    if len(log) >= 2:
        first_c = log[0].get("agents", {}).get(CHAMPION_NAME, {})
        last_c  = log[-1].get("agents", {}).get(CHAMPION_NAME, {})
        delta_wr    = (last_c.get("win_rate", 0) - first_c.get("win_rate", 0)) * 100
        delta_score = last_c.get("avg_score", 0) - first_c.get("avg_score", 0)
        latest_wr   = last_c.get("win_rate", 0) * 100

        sign_wr  = "+" if delta_wr >= 0 else ""
        sign_sc  = "+" if delta_score >= 0 else ""

        if latest_wr >= 55.0:
            status = f"**On track.** Champion wins {latest_wr:.0f}% vs mixed pool — likely competitive with human players."
        elif latest_wr >= 35.0:
            status = f"**Developing.** Champion WR={latest_wr:.0f}% vs mixed pool. Continue iterating."
        else:
            status = f"**Early stage.** Champion WR={latest_wr:.0f}% — pool dominates. More iterations needed."

        lines += [
            "## Improvement Trend",
            "",
            f"- Win rate shift (first → latest): **{sign_wr}{delta_wr:.1f} pp**",
            f"- Avg score shift: **{sign_sc}{delta_score:.1f}**",
            f"- {status}",
            "",
        ]

    # -- Retraining events --
    retrain_events = [e for e in log if e.get("retrained")]
    if retrain_events:
        lines += [
            "## Evaluator Retraining Events",
            "",
            "| # | Date | Games at time | Notes |",
            "|---|------|---------------|-------|",
        ]
        cumulative = 0
        for i, e in enumerate(log):
            cumulative += e.get("num_games", 0)
            if e.get("retrained"):
                ts = e.get("timestamp", "?")[:10]
                notes = e.get("retrain_notes", "weights updated")
                idx = sum(1 for x in log[:log.index(e) + 1] if x.get("retrained"))
                lines.append(f"| {idx} | {ts} | {cumulative} | {notes} |")
        lines.append("")

    # -- Opponent pool reference --
    lines += [
        "## Opponent Pool",
        "",
        "| Name | Type | Budget | Tier |",
        "|------|------|--------|------|",
    ]
    tier_map = {
        "pool_random": "1 — Baseline",
        "pool_heuristic": "1 — Baseline",
        "pool_mcts_25ms": "2 — Vanilla MCTS",
        "pool_mcts_50ms": "2 — Vanilla MCTS",
        "pool_mcts_100ms": "2 — Vanilla MCTS",
        "pool_mcts_200ms": "2 — Vanilla MCTS",
        "pool_rave_100ms": "3 — L4+5 Enhanced",
        "pool_l4_cutoff_100ms": "3 — L4+5 Enhanced",
        "pool_l45_full_100ms": "3 — L4+5 Enhanced",
        "pool_l9_partial_200ms": "4 — L9 Partial",
        "pool_peer_500ms": "5 — Near-Peer",
    }
    for opp in OPPONENT_POOL:
        tms = opp.get("thinking_time_ms")
        budget = f"{tms} ms" if tms else "—"
        tier = tier_map.get(opp["name"], "?")
        lines.append(f"| {opp['name']} | {opp['type']} | {budget} | {tier} |")
    lines.append("")

    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[champion_loop] Report written → {report_path}")


# ---------------------------------------------------------------------------
# Console history display
# ---------------------------------------------------------------------------

def show_history(log_path: str = DEFAULT_LOG) -> None:
    log = load_log(log_path)
    if not log:
        print(f"[champion_loop] No history found at {log_path}")
        return

    total_games = sum(e.get("num_games", 0) for e in log)
    print(f"\n{'=' * 72}")
    print(f"  Champion Progress — {len(log)} iteration(s), {total_games} total games")
    print(f"{'=' * 72}")

    for i, entry in enumerate(log, 1):
        ts   = entry.get("timestamp", "?")[:19].replace("T", " ")
        ng   = entry.get("num_games", "?")
        opps = ", ".join(entry.get("opponents_sampled", []))
        print(f"\n--- Iteration {i}  ({ts}, {ng} games) ---")
        print(f"  Opponents: {opps}")
        ranked = sorted(
            entry.get("agents", {}).items(),
            key=lambda x: x[1].get("win_rate", 0),
            reverse=True,
        )
        for name, s in ranked:
            wr    = s.get("win_rate", 0) * 100
            avg   = s.get("avg_score", 0)
            mu    = s.get("trueskill_mu")
            mu_s  = f"  μ={mu:.1f}" if mu is not None else ""
            tag   = "  *** CHAMPION ***" if name == CHAMPION_NAME else ""
            print(f"  {name:38s}  WR={wr:5.1f}%  AvgScore={avg:6.1f}{mu_s}{tag}")
        if entry.get("retrained"):
            print(f"  [retrained evaluator]")

    if len(log) >= 2:
        first_c = log[0].get("agents", {}).get(CHAMPION_NAME, {})
        last_c  = log[-1].get("agents", {}).get(CHAMPION_NAME, {})
        dwr = (last_c.get("win_rate", 0) - first_c.get("win_rate", 0)) * 100
        dsc = last_c.get("avg_score", 0) - first_c.get("avg_score", 0)
        print(f"\n{'=' * 72}")
        print("  Trend (first → latest)")
        print(f"{'=' * 72}")
        print(f"  Champion WR:        {'+' if dwr >= 0 else ''}{dwr:.1f} pp  "
              f"({first_c.get('win_rate', 0)*100:.1f}% → {last_c.get('win_rate', 0)*100:.1f}%)")
        print(f"  Champion AvgScore:  {'+' if dsc >= 0 else ''}{dsc:.1f}")
    print()


# ---------------------------------------------------------------------------
# Single iteration
# ---------------------------------------------------------------------------

def run_iteration(
    *,
    num_games: int,
    seed: int,
    champion_time_ms: int,
    force_retrain: bool,
    log_path: str,
) -> None:
    rng = random.Random(seed)

    # Build champion with current calibrated weights
    champion  = build_champion_agent(champion_time_ms)
    opponents = sample_opponents(3, rng)
    opp_names = [o["name"] for o in opponents]

    print(f"\n[champion_loop] Iteration seed={seed}")
    print(f"[champion_loop] Champion: {CHAMPION_NAME} @ {champion_time_ms} ms")
    print(f"[champion_loop] Opponents: {', '.join(opp_names)}")

    config  = build_arena_config(champion, opponents, num_games, seed)
    run_dir = run_arena(config)
    summary = parse_summary(run_dir)

    snap_rows = accumulate_snapshots(run_dir)
    if snap_rows:
        print(f"[champion_loop] Accumulated {snap_rows} snapshot rows")

    # Determine whether to retrain
    prev_log   = load_log(log_path)
    prev_total = sum(e.get("num_games", 0) for e in prev_log)
    new_total  = prev_total + summary["num_games"]
    crossed_interval = (
        new_total // RETRAIN_GAME_INTERVAL > prev_total // RETRAIN_GAME_INTERVAL
    )
    should_retrain = force_retrain or crossed_interval

    retrain_meta: Dict[str, Any] = {}
    if should_retrain:
        retrain_meta = retrain_evaluator()
        print(f"[champion_loop] Retrain result: {retrain_meta}")

    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "opponents_sampled": opp_names,
        "run_dir": run_dir,
        "num_games": summary["num_games"],
        "agents": summary["agents"],
        "snapshot_rows_collected": snap_rows,
    }
    if should_retrain:
        entry["retrained"] = retrain_meta.get("success", False)
        entry["retrain_notes"] = (
            f"After {new_total} total games; "
            f"collected {retrain_meta.get('data_games', '?')} self-play games"
        )

    history = append_log(entry, log_path)
    print(f"\n[champion_loop] Logged iteration #{len(history)} to {log_path}")

    # Print champion stats
    c   = summary["agents"].get(CHAMPION_NAME, {})
    wr  = c.get("win_rate", 0.0) * 100
    avg = c.get("avg_score", 0.0)
    mu  = c.get("trueskill_mu")
    sig = c.get("trueskill_sigma")
    print(f"\n  Champion results ({CHAMPION_NAME}):")
    print(f"    Win rate:   {wr:.1f}%")
    print(f"    Avg score:  {avg:.1f}")
    if mu is not None:
        print(f"    TrueSkill:  μ={mu:.2f}  σ={sig:.2f}  conservative={_conservative(mu, sig):.2f}")

    generate_report(history, REPORT_PATH)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Champion Self-Improvement Loop — champion vs randomized opponent "
            "pool with TrueSkill tracking and periodic evaluator retraining."
        )
    )
    parser.add_argument(
        "--iterations", type=int, default=1,
        help="Number of arena iterations to run (default: 1)",
    )
    parser.add_argument(
        "--num-games", type=int, default=20,
        help="Arena games per iteration (default: 20)",
    )
    parser.add_argument(
        "--champion-time", type=int, default=DEFAULT_CHAMPION_TIME_MS,
        help=f"Champion thinking time in ms (default: {DEFAULT_CHAMPION_TIME_MS})",
    )
    parser.add_argument(
        "--retrain", action="store_true",
        help="Force evaluator retraining after the final iteration",
    )
    parser.add_argument(
        "--log", type=str, default=DEFAULT_LOG,
        help=f"Champion log path (default: {DEFAULT_LOG})",
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Print history and exit without running a new iteration",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Base random seed (default: derived from current time)",
    )
    args = parser.parse_args()

    if args.show:
        show_history(args.log)
        return

    base_seed = args.seed if args.seed is not None else int(time.time()) & 0xFFFFFF

    for i in range(args.iterations):
        run_iteration(
            num_games=args.num_games,
            seed=base_seed + i,
            champion_time_ms=args.champion_time,
            force_retrain=(args.retrain and i == args.iterations - 1),
            log_path=args.log,
        )
        if args.iterations > 1 and i < args.iterations - 1:
            print(f"\n[champion_loop] Completed {i + 1}/{args.iterations} iterations")


if __name__ == "__main__":
    main()
