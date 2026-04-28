#!/usr/bin/env python
"""Champion Arena — continuous improvement loop for the best MCTS agent.

Runs the current champion against a randomized pool of strategy checkpoints.
Every game captures board-state snapshots for evaluator retraining.
TrueSkill ratings persist across runs; the champion is promoted automatically
when a challenger's conservative rating surpasses it with enough evidence.

Detailed per-run reports land in data/champion_reports/. A cumulative history
is appended to data/champion_state.json.

Usage:
    python scripts/champion_arena.py                     # 40 games, auto pool
    python scripts/champion_arena.py --num-games 20
    python scripts/champion_arena.py --pool random heuristic pool_deploy_hard
    python scripts/champion_arena.py --show              # print history, no run
    python scripts/champion_arena.py --no-promote        # skip auto-promotion
    python scripts/champion_arena.py --seed 12345        # reproducible run
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
CHAMPION_STATE_PATH = "data/champion_state.json"
REPORTS_DIR = "data/champion_reports"
TEMP_CONFIG_PATH = "data/_champion_arena_tmp.json"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_NUM_GAMES = 40
DEFAULT_POOL_SIZE = 3          # agents alongside champion per game (total = 4)
MIN_GAMES_FOR_PROMOTION = 20   # challenger needs this many games before promotion check

# ---------------------------------------------------------------------------
# Champion — starting configuration (challenge champion profile translated to
# plain mcts params so it runs in the standard arena harness at fixed budget).
# ---------------------------------------------------------------------------
CHAMPION_INITIAL_CONFIG: Dict[str, Any] = {
    "name": "champion",
    "type": "mcts",
    "thinking_time_ms": 200,
    "params": {
        "deterministic_time_budget": True,
        "iterations_per_ms": 0.5,
        "exploration_constant": 1.414,
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
    },
}

# ---------------------------------------------------------------------------
# Calibrated weights (from data/layer6_calibrated_weights.json)
# ---------------------------------------------------------------------------
_SINGLE_WEIGHTS = {
    "squares_placed": 0.0295,
    "remaining_piece_area": -0.0295,
    "accessible_corners": 0.243,
    "reachable_empty_squares": 0.081,
    "largest_remaining_piece_size": -0.231,
    "opponent_avg_mobility": -0.3,
    "center_proximity": 0.0,
    "territory_enclosure_area": 0.0,
}

_PHASE_WEIGHTS = {
    "early": {
        "squares_placed": -0.176,
        "remaining_piece_area": 0.176,
        "accessible_corners": 0.3,
        "reachable_empty_squares": 0.0,
        "largest_remaining_piece_size": 0.0,
        "opponent_avg_mobility": -0.053,
        "center_proximity": 0.0,
        "territory_enclosure_area": 0.0,
    },
    "mid": {
        "squares_placed": -0.004,
        "remaining_piece_area": 0.004,
        "accessible_corners": 0.3,
        "reachable_empty_squares": 0.228,
        "largest_remaining_piece_size": -0.238,
        "opponent_avg_mobility": -0.203,
        "center_proximity": 0.0,
        "territory_enclosure_area": 0.0,
    },
    "late": {
        "squares_placed": 0.3,
        "remaining_piece_area": -0.3,
        "accessible_corners": 0.176,
        "reachable_empty_squares": 0.134,
        "largest_remaining_piece_size": -0.085,
        "opponent_avg_mobility": -0.063,
        "center_proximity": 0.0,
        "territory_enclosure_area": 0.0,
    },
}

# ---------------------------------------------------------------------------
# Pool catalog — named strategy checkpoints. Names are stable across runs so
# TrueSkill ratings accumulate. Add new entries here as new strategies emerge.
# ---------------------------------------------------------------------------
POOL_CATALOG: List[Dict[str, Any]] = [
    # --- Baselines (rating anchors) ---
    {"name": "pool_random", "type": "random"},
    {"name": "pool_heuristic", "type": "heuristic"},
    # --- Time-budget sweep (plain UCB1) ---
    {
        "name": "pool_mcts_50ms",
        "type": "mcts",
        "thinking_time_ms": 50,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 10.0,
            "exploration_constant": 1.414,
        },
    },
    {
        "name": "pool_mcts_100ms",
        "type": "mcts",
        "thinking_time_ms": 100,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 10.0,
            "exploration_constant": 1.414,
        },
    },
    # --- Deploy difficulty proxies ---
    {
        "name": "pool_deploy_easy",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
        },
    },
    {
        "name": "pool_deploy_medium",
        "type": "mcts",
        "thinking_time_ms": 450,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "adaptive_rollout_depth_enabled": True,
            "adaptive_rollout_depth_base": 5,
            "adaptive_rollout_depth_avg_bf": 80.0,
        },
    },
    {
        "name": "pool_deploy_hard",
        "type": "mcts",
        "thinking_time_ms": 900,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "adaptive_rollout_depth_enabled": True,
            "adaptive_rollout_depth_base": 5,
            "adaptive_rollout_depth_avg_bf": 80.0,
            "sufficiency_threshold_enabled": True,
            "loss_avoidance_enabled": True,
            "loss_avoidance_threshold": -50.0,
        },
    },
    # --- RAVE k sweep ---
    {
        "name": "pool_rave_k500",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 500,
            "state_eval_weights": _SINGLE_WEIGHTS,
        },
    },
    {
        "name": "pool_rave_k5000",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 5000,
            "state_eval_weights": _SINGLE_WEIGHTS,
        },
    },
    # --- Phase-calibrated evaluation ---
    {
        "name": "pool_phase_weights",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "state_eval_phase_weights": _PHASE_WEIGHTS,
        },
    },
    # --- Rollout policy variants ---
    {
        "name": "pool_heuristic_rollout",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "heuristic",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "state_eval_weights": _SINGLE_WEIGHTS,
        },
    },
    {
        "name": "pool_full_rollout",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "state_eval_weights": _SINGLE_WEIGHTS,
        },
    },
    # --- Progressive widening ---
    {
        "name": "pool_progressive_widening",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "state_eval_weights": _SINGLE_WEIGHTS,
            "progressive_widening_enabled": True,
            "pw_c": 2.0,
            "pw_alpha": 0.5,
        },
    },
    # --- L9 full meta-optimization stack ---
    {
        "name": "pool_l9_full",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "state_eval_weights": _SINGLE_WEIGHTS,
            "adaptive_exploration_enabled": True,
            "adaptive_exploration_base": 1.414,
            "adaptive_exploration_avg_bf": 80.0,
            "adaptive_rollout_depth_enabled": True,
            "adaptive_rollout_depth_base": 5,
            "adaptive_rollout_depth_avg_bf": 80.0,
            "sufficiency_threshold_enabled": True,
            "loss_avoidance_enabled": True,
            "loss_avoidance_threshold": -50.0,
        },
    },
    # --- NST rollout bias ---
    {
        "name": "pool_nst",
        "type": "mcts",
        "thinking_time_ms": 200,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "state_eval_weights": _SINGLE_WEIGHTS,
            "nst_enabled": True,
            "nst_weight": 0.5,
        },
    },
]

# Index catalog by name for fast lookup
POOL_BY_NAME: Dict[str, Dict[str, Any]] = {a["name"]: a for a in POOL_CATALOG}


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def load_state() -> Dict[str, Any]:
    """Load persistent champion state, or return defaults."""
    path = Path(CHAMPION_STATE_PATH)
    if path.exists():
        with path.open() as f:
            return json.load(f)
    return {
        "champion_config": CHAMPION_INITIAL_CONFIG,
        "ratings": {},      # agent_name -> {mu, sigma, games_played}
        "history": [],      # list of run summaries
        "generation": 0,    # incremented on each promotion
    }


def save_state(state: Dict[str, Any]) -> None:
    Path(CHAMPION_STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CHAMPION_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# ---------------------------------------------------------------------------
# TrueSkill helpers
# ---------------------------------------------------------------------------

def _build_tracker_with_priors(
    prior_ratings: Dict[str, Dict[str, float]],
) -> Any:
    """Construct a TrueSkillTracker pre-seeded with prior mu/sigma values."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analytics.tournament.trueskill_rating import TrueSkillTracker

    tracker = TrueSkillTracker()
    tracker.load_ratings(prior_ratings)
    return tracker


def _update_ratings_from_games(
    games: List[Dict[str, Any]],
    prior_ratings: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """Feed game records into a tracker (with priors) and return updated ratings."""
    tracker = _build_tracker_with_priors(prior_ratings)
    for game in games:
        agent_scores = game.get("agent_scores")
        if not agent_scores:
            continue
        tracker.update_game({str(k): int(v) for k, v in agent_scores.items()})
    updated = {}
    for agent_id in tracker.agent_ids:
        updated[agent_id] = tracker.get_rating(agent_id)
    return updated


# ---------------------------------------------------------------------------
# Arena helpers
# ---------------------------------------------------------------------------

def _pick_pool_agents(
    exclude_names: Optional[List[str]],
    n: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """Sample n agents from the catalog, excluding the given names."""
    exclude = set(exclude_names or [])
    candidates = [a for a in POOL_CATALOG if a["name"] not in exclude]
    if len(candidates) < n:
        raise ValueError(
            f"Pool catalog has only {len(candidates)} eligible agents; need {n}."
        )
    return rng.sample(candidates, n)


def _build_arena_config(
    champion_config: Dict[str, Any],
    pool_agents: List[Dict[str, Any]],
    num_games: int,
    seed: int,
) -> Dict[str, Any]:
    agents = [champion_config] + pool_agents
    return {
        "agents": agents,
        "num_games": num_games,
        "seed": seed,
        "seat_policy": "round_robin",
        "output_root": "arena_runs",
        "max_turns": 2500,
        "snapshots": {
            "enabled": True,
            "strategy": "fixed_ply",
            "checkpoints": [8, 16, 24, 32, 40, 48, 56, 64],
        },
        "notes": (
            "Champion arena — champion vs randomized pool. "
            f"Pool: {[a['name'] for a in pool_agents]}."
        ),
    }


def _find_latest_run(output_root: str = "arena_runs") -> Optional[str]:
    root = Path(output_root)
    if not root.exists():
        return None
    runs = sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    for r in runs:
        if r.is_dir() and (r / "summary.json").exists():
            return str(r)
    return None


def run_arena(config_path: str, num_games: Optional[int] = None) -> str:
    """Execute arena.py and return the output run directory."""
    cmd = [sys.executable, "scripts/arena.py", "--config", config_path]
    if num_games is not None:
        cmd += ["--num-games", str(num_games)]
    print(f"[champion_arena] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"[champion_arena] Arena exited with code {result.returncode}")
        sys.exit(1)
    run_dir = _find_latest_run()
    if run_dir is None:
        print("[champion_arena] ERROR: could not find arena output directory.")
        sys.exit(1)
    return run_dir


# ---------------------------------------------------------------------------
# Summary parsing
# ---------------------------------------------------------------------------

def _load_games(run_dir: str) -> List[Dict[str, Any]]:
    games_path = Path(run_dir) / "games.jsonl"
    games = []
    if not games_path.exists():
        return games
    with games_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    games.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return games


def _parse_summary(run_dir: str) -> Dict[str, Any]:
    summary_path = Path(run_dir) / "summary.json"
    with summary_path.open() as f:
        return json.load(f)


def _agent_win_stats(games: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Compute wins, ties, losses, avg_score per agent from game records."""
    stats: Dict[str, Dict[str, Any]] = {}
    for g in games:
        agent_scores = g.get("agent_scores", {})
        winner_agents = g.get("winner_agents", [])
        is_tie = g.get("is_tie", False)
        for name, score in agent_scores.items():
            if name not in stats:
                stats[name] = {"wins": 0, "ties": 0, "losses": 0, "scores": []}
            stats[name]["scores"].append(score)
            if is_tie:
                stats[name]["ties"] += 1
            elif name in winner_agents:
                stats[name]["wins"] += 1
            else:
                stats[name]["losses"] += 1
    for name, s in stats.items():
        n = len(s["scores"])
        s["games"] = n
        s["avg_score"] = sum(s["scores"]) / n if n else 0.0
        s["win_rate"] = s["wins"] / n if n else 0.0
        del s["scores"]
    return stats


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 20) -> str:
    filled = int(round(value * width))
    return "█" * filled + "░" * (width - filled)


def _write_report(
    run_dir: str,
    pool_names: List[str],
    win_stats: Dict[str, Dict[str, Any]],
    ratings_before: Dict[str, Dict[str, float]],
    ratings_after: Dict[str, Dict[str, float]],
    promoted: Optional[str],
    generation: int,
    report_path: Path,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Champion Arena Run Report",
        f"",
        f"**Date:** {ts}  ",
        f"**Run dir:** `{run_dir}`  ",
        f"**Champion generation:** {generation}  ",
        f"**Pool:** {', '.join(pool_names)}",
        f"",
        f"---",
        f"",
        f"## Win/Loss Summary",
        f"",
        f"| Agent | Games | Wins | Win% | Avg Score |",
        f"|-------|-------|------|------|-----------|",
    ]
    for name in sorted(win_stats, key=lambda n: -win_stats[n]["win_rate"]):
        s = win_stats[name]
        bar = _bar(s["win_rate"])
        lines.append(
            f"| {name} | {s['games']} | {s['wins']} "
            f"| {s['win_rate']*100:.1f}% {bar} | {s['avg_score']:.1f} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## TrueSkill Ratings",
        f"",
        f"Conservative estimate = μ − 3σ (leaderboard metric).  ",
        f"Δμ and Δcons show change from this run's prior.",
        f"",
        f"| Rank | Agent | μ | σ | Conservative | Δμ | Δcons | Games |",
        f"|------|-------|---|---|-------------|----|----|-------|",
    ]

    leaderboard = sorted(
        ratings_after.items(),
        key=lambda x: x[1]["conservative"],
        reverse=True,
    )
    for rank, (name, r) in enumerate(leaderboard, 1):
        prev = ratings_before.get(name, {})
        prev_mu = prev.get("mu", 25.0)
        prev_cons = prev.get("conservative", prev_mu - 3 * prev.get("sigma", 8.333))
        delta_mu = r["mu"] - prev_mu
        delta_cons = r["conservative"] - prev_cons
        sign_mu = "+" if delta_mu >= 0 else ""
        sign_cons = "+" if delta_cons >= 0 else ""
        champion_marker = " 👑" if name == "champion" else ""
        lines.append(
            f"| {rank} | {name}{champion_marker} | {r['mu']:.2f} | {r['sigma']:.2f} "
            f"| {r['conservative']:.2f} | {sign_mu}{delta_mu:.2f} "
            f"| {sign_cons}{delta_cons:.2f} | {r['games_played']} |"
        )

    if promoted:
        lines += [
            f"",
            f"---",
            f"",
            f"## ⬆️ Champion Promotion",
            f"",
            f"**New champion:** `{promoted}`  ",
            f"The challenger's conservative TrueSkill surpassed the previous champion "
            f"with sufficient game evidence (≥{MIN_GAMES_FOR_PROMOTION} games).",
        ]
    else:
        lines += [
            f"",
            f"---",
            f"",
            f"## Champion Status",
            f"",
            f"Champion held. No challenger exceeded the champion's conservative TrueSkill "
            f"with sufficient game evidence.",
        ]

    lines += [
        f"",
        f"---",
        f"",
        f"## Snapshot Data",
        f"",
        f"Board-state snapshots are saved in `{run_dir}/snapshots.parquet` "
        f"(or `snapshots.csv`). Use `scripts/analyze_layer6_features.py` to update "
        f"the evaluator weights.",
    ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    print(f"[champion_arena] Report written: {report_path}")


# ---------------------------------------------------------------------------
# History display
# ---------------------------------------------------------------------------

def show_history(state: Dict[str, Any]) -> None:
    history = state.get("history", [])
    ratings = state.get("ratings", {})
    generation = state.get("generation", 0)

    print(f"\n{'='*72}")
    print(f" Champion Arena History — generation {generation}, {len(history)} run(s)")
    print(f"{'='*72}")

    if not history:
        print(" No runs yet.")
        return

    for i, entry in enumerate(history):
        ts = entry.get("timestamp", "?")
        games = entry.get("num_games", "?")
        pool = ", ".join(entry.get("pool", []))
        promoted = entry.get("promoted_to")
        print(f"\n Run {i+1}  {ts}  ({games} games)  pool=[{pool}]")
        if promoted:
            print(f"   *** Promoted champion → {promoted} ***")
        for name, s in sorted(
            entry.get("win_stats", {}).items(),
            key=lambda x: -x[1].get("win_rate", 0),
        ):
            wr = s.get("win_rate", 0) * 100
            avg = s.get("avg_score", 0)
            mu = entry.get("ratings_after", {}).get(name, {}).get("mu")
            cons = entry.get("ratings_after", {}).get(name, {}).get("conservative")
            mu_str = f"  μ={mu:.1f}" if mu is not None else ""
            cons_str = f"  cons={cons:.1f}" if cons is not None else ""
            marker = " 👑" if name == "champion" else ""
            print(f"   {name+marker:38s} WR={wr:5.1f}%  AvgScore={avg:5.1f}{mu_str}{cons_str}")

    print(f"\n{'='*72}")
    print(" Current TrueSkill Leaderboard")
    print(f"{'='*72}")
    leaderboard = sorted(ratings.items(), key=lambda x: x[1].get("conservative", 0), reverse=True)
    for rank, (name, r) in enumerate(leaderboard, 1):
        marker = " 👑" if name == "champion" else ""
        print(
            f"  {rank:2d}. {name+marker:38s}  "
            f"μ={r['mu']:.2f}  σ={r['sigma']:.2f}  "
            f"cons={r['conservative']:.2f}  "
            f"games={r['games_played']}"
        )
    print()


# ---------------------------------------------------------------------------
# Promotion logic
# ---------------------------------------------------------------------------

def _check_promotion(
    ratings_after: Dict[str, Dict[str, float]],
    champion_name: str,
    auto_promote: bool,
) -> Optional[str]:
    """Return the name of a challenger to promote, or None."""
    if not auto_promote:
        return None
    champ_rating = ratings_after.get(champion_name)
    if champ_rating is None:
        return None
    champ_cons = champ_rating["conservative"]
    best_challenger: Optional[str] = None
    best_cons = champ_cons
    for name, r in ratings_after.items():
        if name == champion_name:
            continue
        if r["games_played"] < MIN_GAMES_FOR_PROMOTION:
            continue
        if r["conservative"] > best_cons:
            best_cons = r["conservative"]
            best_challenger = name
    return best_challenger


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Champion Arena — continuous improvement loop")
    parser.add_argument(
        "--num-games", type=int, default=DEFAULT_NUM_GAMES,
        help=f"Number of games per run (default: {DEFAULT_NUM_GAMES})",
    )
    parser.add_argument(
        "--pool", nargs="+", default=None,
        help="Explicit pool agent names from POOL_CATALOG (default: random sample)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducibility (default: based on current time)",
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Print history and leaderboard without running a new arena session",
    )
    parser.add_argument(
        "--no-promote", action="store_true",
        help="Disable automatic champion promotion",
    )
    args = parser.parse_args()

    state = load_state()

    if args.show:
        show_history(state)
        return

    # Determine pool
    rng_seed = args.seed if args.seed is not None else int(datetime.now().timestamp())
    rng = random.Random(rng_seed)

    if args.pool:
        unknown = [n for n in args.pool if n not in POOL_BY_NAME]
        if unknown:
            print(f"[champion_arena] Unknown pool agents: {unknown}")
            print(f"  Available: {sorted(POOL_BY_NAME.keys())}")
            sys.exit(1)
        pool_agents = [POOL_BY_NAME[n] for n in args.pool]
    else:
        pool_agents = _pick_pool_agents(
            exclude_names=["champion"],
            n=DEFAULT_POOL_SIZE,
            rng=rng,
        )

    pool_names = [a["name"] for a in pool_agents]
    champion_config = state["champion_config"]
    print(f"\n[champion_arena] Champion: {champion_config['name']}")
    print(f"[champion_arena] Pool ({len(pool_agents)}): {pool_names}")
    print(f"[champion_arena] Games: {args.num_games}  Seed: {rng_seed}")

    # Build & write temporary arena config
    arena_seed = rng.randint(10_000_000, 99_999_999)
    arena_config = _build_arena_config(
        champion_config=champion_config,
        pool_agents=pool_agents,
        num_games=args.num_games,
        seed=arena_seed,
    )
    Path(TEMP_CONFIG_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(TEMP_CONFIG_PATH, "w") as f:
        json.dump(arena_config, f, indent=2)

    # Run arena
    run_dir = run_arena(TEMP_CONFIG_PATH)
    print(f"[champion_arena] Run complete: {run_dir}")

    # Load results
    games = _load_games(run_dir)
    win_stats = _agent_win_stats(games)
    completed = len(games)

    # Update TrueSkill with priors from persistent state
    ratings_before = {
        k: dict(v) for k, v in state["ratings"].items()
    }
    ratings_after = _update_ratings_from_games(games, ratings_before)

    # Check for promotion
    promoted = _check_promotion(
        ratings_after=ratings_after,
        champion_name=champion_config["name"],
        auto_promote=not args.no_promote,
    )
    generation = state["generation"]
    if promoted:
        new_champion_config = dict(POOL_BY_NAME[promoted])
        new_champion_config["name"] = "champion"
        state["champion_config"] = new_champion_config
        generation += 1
        state["generation"] = generation
        print(f"[champion_arena] *** Champion promoted: {promoted} → generation {generation} ***")

    # Persist updated ratings
    state["ratings"] = ratings_after

    # Append history entry
    history_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_dir": run_dir,
        "num_games": completed,
        "pool": pool_names,
        "arena_seed": arena_seed,
        "win_stats": win_stats,
        "ratings_after": ratings_after,
        "promoted_to": promoted,
        "generation": generation,
    }
    state["history"].append(history_entry)
    save_state(state)
    print(f"[champion_arena] State saved → {CHAMPION_STATE_PATH}")

    # Write markdown report
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = Path(REPORTS_DIR) / f"run_{ts_str}_gen{generation}.md"
    _write_report(
        run_dir=run_dir,
        pool_names=pool_names,
        win_stats=win_stats,
        ratings_before=ratings_before,
        ratings_after=ratings_after,
        promoted=promoted,
        generation=generation,
        report_path=report_path,
    )

    # Print leaderboard
    show_history(state)


if __name__ == "__main__":
    main()
