#!/usr/bin/env python
"""Champion Self-Improvement Loop.

Runs the champion MCTS agent against a randomized pool of challengers,
accumulates snapshot data for evaluator retraining, tracks TrueSkill
across runs, and documents results in a detailed progress report.

Pipeline per iteration:
  1. Select 3 challengers from tier buckets (seeded by run number)
  2. Build a one-off arena config: champion + 3 challengers + snapshots enabled
  3. Run arena.py subprocess → produces run_dir with summary.json
  4. Parse results: champion win_rate, avg_score, run TrueSkill
  5. Append game records to data/champion_games.jsonl
  6. Append snapshots to data/champion_snapshots_cumulative.csv
  7. Recompute cumulative TrueSkill from all accumulated games
  8. If snapshot rows >= retrain_threshold: retrain evaluator model
  9. Optional promotion trial: test learned eval vs current; promote if better
 10. Append to data/champion_run_log.json
 11. Render reports/champion_progress.md

Usage:
    python scripts/champion_loop.py --num-runs 5 --num-games 20
    python scripts/champion_loop.py --show
    python scripts/champion_loop.py --retrain --num-games 20
    python scripts/champion_loop.py --show-report

Challenger pool tiers:
    T0/T1 (weak):   random, heuristic, 50ms basic MCTS, 50ms MCTS+RAVE
    T2 (mid):       100ms MCTS+L4, 100ms MCTS+L5, 100ms MCTS+L6
    T3 (strong):    200ms MCTS+L9 (no adaptive), 200ms MCTS+L9 (full, fixed eval)

Each run picks 1 challenger from each tier, ensuring diverse opposition
and good training signal for the evaluator across game phases.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.tournament.trueskill_rating import TrueSkillTracker

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
CONFIG_DIR = REPO_ROOT / "config"
MODELS_DIR = REPO_ROOT / "models"
REPORTS_DIR = REPO_ROOT / "reports"

CHAMPION_ARENA_PARAMS_PATH = CONFIG_DIR / "champion_arena_params.json"
RUN_LOG_PATH = DATA_DIR / "champion_run_log.json"
CUMULATIVE_GAMES_PATH = DATA_DIR / "champion_games.jsonl"
CUMULATIVE_SNAPSHOTS_PATH = DATA_DIR / "champion_snapshots_cumulative.csv"

# ---------------------------------------------------------------------------
# Champion configuration
# ---------------------------------------------------------------------------

CHAMPION_NAME = "champion"
CHAMPION_THINKING_TIME_MS = 200

# Default champion params — best known configuration.
# Combines: L3 progressive widening, L4 cutoff+minimax, L5 RAVE,
# L6 calibrated phase weights, L9 adaptive features.
CHAMPION_PARAMS_DEFAULT: Dict[str, Any] = {
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
    "adaptive_exploration_enabled": True,
    "adaptive_exploration_base": 1.414,
    "adaptive_exploration_avg_bf": 80.0,
    "sufficiency_threshold_enabled": True,
    "loss_avoidance_enabled": True,
    "loss_avoidance_threshold": -50.0,
    "state_eval_phase_weights": {
        "early": {
            "squares_placed": -0.17599664484103847,
            "remaining_piece_area": 0.17599664484103822,
            "accessible_corners": 0.3,
            "reachable_empty_squares": 0.0,
            "largest_remaining_piece_size": 0.0,
            "opponent_avg_mobility": -0.05287834609528694,
            "center_proximity": 0.0,
            "territory_enclosure_area": 0.0,
        },
        "mid": {
            "squares_placed": -0.00387502185581506,
            "remaining_piece_area": 0.0038750218558150614,
            "accessible_corners": 0.3,
            "reachable_empty_squares": 0.22774497158891033,
            "largest_remaining_piece_size": -0.238473591231953,
            "opponent_avg_mobility": -0.20277351241243552,
            "center_proximity": 0.0,
            "territory_enclosure_area": 0.0,
        },
        "late": {
            "squares_placed": 0.3,
            "remaining_piece_area": -0.3,
            "accessible_corners": 0.17573409689186584,
            "reachable_empty_squares": 0.13361753070802862,
            "largest_remaining_piece_size": -0.08518919739412929,
            "opponent_avg_mobility": -0.06278383996091268,
            "center_proximity": 0.0,
            "territory_enclosure_area": 0.0,
        },
    },
}

# Snapshot row thresholds for evaluator retraining
RETRAIN_THRESHOLD = 1000
MIN_NEW_ROWS_FOR_RETRAIN = 300

# ---------------------------------------------------------------------------
# Challenger pool — tiered by approximate strength
# ---------------------------------------------------------------------------
# Each gauntlet run picks 1 from each tier so the champion faces a weak,
# mid, and strong opponent every run.  Fixed names allow cross-run TrueSkill.

_CALIBRATED_WEIGHTS = {
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
        "squares_placed": -0.17599664484103847,
        "remaining_piece_area": 0.17599664484103822,
        "accessible_corners": 0.3,
        "reachable_empty_squares": 0.0,
        "largest_remaining_piece_size": 0.0,
        "opponent_avg_mobility": -0.05287834609528694,
        "center_proximity": 0.0,
        "territory_enclosure_area": 0.0,
    },
    "mid": {
        "squares_placed": -0.00387502185581506,
        "remaining_piece_area": 0.0038750218558150614,
        "accessible_corners": 0.3,
        "reachable_empty_squares": 0.22774497158891033,
        "largest_remaining_piece_size": -0.238473591231953,
        "opponent_avg_mobility": -0.20277351241243552,
        "center_proximity": 0.0,
        "territory_enclosure_area": 0.0,
    },
    "late": {
        "squares_placed": 0.3,
        "remaining_piece_area": -0.3,
        "accessible_corners": 0.17573409689186584,
        "reachable_empty_squares": 0.13361753070802862,
        "largest_remaining_piece_size": -0.08518919739412929,
        "opponent_avg_mobility": -0.06278383996091268,
        "center_proximity": 0.0,
        "territory_enclosure_area": 0.0,
    },
}

POOL_TIER_WEAK: List[Dict[str, Any]] = [
    {
        "name": "pool_t0_random",
        "type": "random",
        "thinking_time_ms": None,
        "params": {},
    },
    {
        "name": "pool_t0_heuristic",
        "type": "heuristic",
        "thinking_time_ms": None,
        "params": {},
    },
    {
        "name": "pool_t1_mcts_50ms",
        "type": "mcts",
        "thinking_time_ms": 50,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.25,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
        },
    },
    {
        "name": "pool_t1_mcts_50ms_rave",
        "type": "mcts",
        "thinking_time_ms": 50,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.25,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rave_enabled": True,
            "rave_k": 1000,
        },
    },
]

POOL_TIER_MID: List[Dict[str, Any]] = [
    {
        "name": "pool_t2_mcts_100ms_l4",
        "type": "mcts",
        "thinking_time_ms": 100,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.25,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
        },
    },
    {
        "name": "pool_t2_mcts_100ms_l5",
        "type": "mcts",
        "thinking_time_ms": 100,
        "params": {
            "deterministic_time_budget": True,
            "iterations_per_ms": 0.5,
            "exploration_constant": 1.414,
            "rollout_policy": "random",
            "rollout_cutoff_depth": 5,
            "minimax_backup_alpha": 0.25,
            "rave_enabled": True,
            "rave_k": 1000,
            "state_eval_weights": _CALIBRATED_WEIGHTS,
        },
    },
    {
        "name": "pool_t2_mcts_100ms_l6",
        "type": "mcts",
        "thinking_time_ms": 100,
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
            "state_eval_phase_weights": _PHASE_WEIGHTS,
        },
    },
]

POOL_TIER_STRONG: List[Dict[str, Any]] = [
    {
        "name": "pool_t3_mcts_200ms_l9",
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
            "state_eval_weights": _CALIBRATED_WEIGHTS,
        },
    },
    {
        "name": "pool_t3_mcts_200ms_l9_full",
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
            "adaptive_exploration_enabled": True,
            "adaptive_exploration_base": 1.414,
            "adaptive_exploration_avg_bf": 80.0,
            "sufficiency_threshold_enabled": True,
            "loss_avoidance_enabled": True,
            "loss_avoidance_threshold": -50.0,
            "state_eval_weights": _CALIBRATED_WEIGHTS,
        },
    },
]

# ---------------------------------------------------------------------------
# Champion params I/O
# ---------------------------------------------------------------------------


def _load_champion_params() -> Dict[str, Any]:
    """Load champion arena params, initializing defaults if the file is missing."""
    if not CHAMPION_ARENA_PARAMS_PATH.exists():
        _save_champion_params(dict(CHAMPION_PARAMS_DEFAULT))
        return dict(CHAMPION_PARAMS_DEFAULT)
    with CHAMPION_ARENA_PARAMS_PATH.open() as f:
        data = json.load(f)
    # Strip metadata-only keys that aren't MCTS params
    return {k: v for k, v in data.items() if k not in {"description", "eval_version"}}


def _save_champion_params(params: Dict[str, Any], eval_version: str = "") -> None:
    """Save updated champion arena params with metadata."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "description": (
            "Champion arena MCTS params. Updated by champion_loop.py "
            "when a learned evaluator is promoted."
        ),
        "eval_version": eval_version or _get_current_eval_version(params),
    }
    payload.update(params)
    with CHAMPION_ARENA_PARAMS_PATH.open("w") as f:
        json.dump(payload, f, indent=2)


def _get_current_eval_version(params: Optional[Dict[str, Any]] = None) -> str:
    """Derive current eval version from champion params."""
    if params is None:
        params = _load_champion_params()
    model_path = params.get("learned_model_path")
    if not model_path:
        return "v0_hand_tuned"
    stem = Path(model_path).stem
    return stem.split("_v", 1)[1] if "_v" in stem else stem


# ---------------------------------------------------------------------------
# Challenger selection
# ---------------------------------------------------------------------------


def _select_challengers(run_number: int) -> List[Dict[str, Any]]:
    """Pick one challenger from each tier, seeded by run number for reproducibility."""
    rng = random.Random(run_number * 31337 + 42)
    return [
        rng.choice(POOL_TIER_WEAK),
        rng.choice(POOL_TIER_MID),
        rng.choice(POOL_TIER_STRONG),
    ]


# ---------------------------------------------------------------------------
# Arena config building and execution
# ---------------------------------------------------------------------------


def _build_arena_config(
    champion_params: Dict[str, Any],
    challengers: List[Dict[str, Any]],
    num_games: int,
    seed: int,
    output_root: str = "arena_runs",
    notes: str = "",
) -> Dict[str, Any]:
    """Build a full RunConfig-compatible dict for one gauntlet run."""
    agents = [
        {
            "name": CHAMPION_NAME,
            "type": "mcts",
            "thinking_time_ms": CHAMPION_THINKING_TIME_MS,
            "params": champion_params,
        }
    ] + challengers
    return {
        "agents": agents,
        "num_games": num_games,
        "seed": seed,
        "seat_policy": "round_robin",
        "output_root": output_root,
        "max_turns": 2500,
        "notes": notes,
        "snapshots": {
            "enabled": True,
            "strategy": "fixed_ply",
            "checkpoints": [8, 16, 24, 32, 40, 48, 56, 64],
        },
    }


def _run_arena_config(config: Dict[str, Any]) -> str:
    """Write config to a temp file, run arena.py, return the resulting run_dir."""
    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="champion_loop_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
        cmd = [sys.executable, "scripts/arena.py", "--config", tmp_path]
        print(f"[champion_loop] Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=False, text=True)
        if result.returncode != 0:
            print(f"[champion_loop] Arena exited with code {result.returncode}")
            sys.exit(1)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    run_dir = _find_latest_run(config.get("output_root", "arena_runs"))
    if run_dir is None:
        print("[champion_loop] ERROR: Could not find arena output directory.")
        sys.exit(1)
    print(f"[champion_loop] Arena output: {run_dir}")
    return run_dir


def _find_latest_run(output_root: str = "arena_runs") -> Optional[str]:
    root = Path(output_root)
    if not root.exists():
        return None
    candidates = sorted(
        (r for r in root.iterdir() if r.is_dir() and (r / "summary.json").exists()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return str(candidates[0]) if candidates else None


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------


def _parse_run_summary(run_dir: str, champion_name: str) -> Dict[str, Any]:
    """Extract per-agent stats and champion matchups from summary.json."""
    with (Path(run_dir) / "summary.json").open() as f:
        data = json.load(f)

    win_stats = data.get("win_stats", {})
    score_stats = data.get("score_stats", {})
    ts_leaderboard = data.get("trueskill_ratings", {}).get("leaderboard", [])
    ts_by_agent = {entry["agent_id"]: entry for entry in ts_leaderboard}

    agents: Dict[str, Any] = {}
    for agent_name, ws in win_stats.items():
        ss = score_stats.get(agent_name, {})
        ts = ts_by_agent.get(agent_name, {})
        agents[agent_name] = {
            "wins": int(ws.get("outright_wins", 0)),
            "win_points": float(ws.get("win_points", 0.0)),
            "win_rate": float(ws.get("win_rate", 0.0)),
            "games_played": int(ws.get("games_played", 0)),
            "avg_score": float(ss.get("mean") or 0.0),
            "trueskill_mu": float(ts.get("mu", 25.0)),
            "trueskill_sigma": float(ts.get("sigma", 8.333)),
            "trueskill_conservative": float(ts.get("conservative", 0.0)),
        }

    # Extract champion pairwise matchups
    champion_matchups: Dict[str, Any] = {}
    for key, pm in data.get("pairwise_matchups", {}).items():
        if champion_name not in (pm["agent_a"], pm["agent_b"]):
            continue
        other = pm["agent_b"] if pm["agent_a"] == champion_name else pm["agent_a"]
        is_a = pm["agent_a"] == champion_name
        champ_wins = pm["a_beats_b"] if is_a else pm["b_beats_a"]
        other_wins = pm["b_beats_a"] if is_a else pm["a_beats_b"]
        total = pm["total"]
        champion_matchups[other] = {
            "champion_wins": champ_wins,
            "other_wins": other_wins,
            "ties": pm.get("tie", 0),
            "total": total,
            "champion_win_rate": champ_wins / total if total > 0 else 0.0,
        }

    snapshots = data.get("snapshots", {})
    return {
        "num_games": int(data.get("num_games", 0)),
        "completed_games": int(data.get("completed_games", 0)),
        "agents": agents,
        "champion_matchups": champion_matchups,
        "snapshot_rows": int(snapshots.get("rows", 0)),
        "snapshot_csv": snapshots.get("path_csv"),
    }


# ---------------------------------------------------------------------------
# Data accumulation
# ---------------------------------------------------------------------------


def _accumulate_games(run_dir: str) -> int:
    """Append this run's game records to the cumulative JSONL. Returns total count."""
    games_path = Path(run_dir) / "games.jsonl"
    if not games_path.exists():
        return _count_lines(CUMULATIVE_GAMES_PATH)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with games_path.open() as src, CUMULATIVE_GAMES_PATH.open("a") as dst:
        for line in src:
            if line.strip():
                dst.write(line)
    return _count_lines(CUMULATIVE_GAMES_PATH)


def _accumulate_snapshots(run_dir: str, snapshot_csv_path: Optional[str]) -> int:
    """Append this run's snapshot rows to the cumulative CSV. Returns total row count."""
    csv_path = Path(snapshot_csv_path) if snapshot_csv_path else Path(run_dir) / "snapshots.csv"
    if not csv_path.exists():
        return _count_snapshot_rows()
    new_rows: List[Dict[str, Any]] = []
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        new_rows = list(reader)
    if not new_rows:
        return _count_snapshot_rows()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not CUMULATIVE_SNAPSHOTS_PATH.exists()
    with CUMULATIVE_SNAPSHOTS_PATH.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(new_rows[0].keys()))
        if write_header:
            writer.writeheader()
        writer.writerows(new_rows)
    return _count_snapshot_rows()


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open() as f:
        return sum(1 for line in f if line.strip())


def _count_snapshot_rows() -> int:
    """Count data rows (excluding header) in the cumulative snapshots CSV."""
    if not CUMULATIVE_SNAPSHOTS_PATH.exists():
        return 0
    with CUMULATIVE_SNAPSHOTS_PATH.open() as f:
        total = sum(1 for _ in f)
    return max(0, total - 1)  # subtract header


# ---------------------------------------------------------------------------
# Cumulative TrueSkill
# ---------------------------------------------------------------------------


def _compute_cumulative_trueskill() -> Dict[str, Dict[str, float]]:
    """Recompute TrueSkill ratings from all accumulated game records."""
    if not CUMULATIVE_GAMES_PATH.exists():
        return {}
    tracker = TrueSkillTracker()
    with CUMULATIVE_GAMES_PATH.open() as f:
        for line in f:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                agent_scores = record.get("agent_scores", {})
                if len(agent_scores) >= 2:
                    tracker.update_game({str(k): int(v) for k, v in agent_scores.items()})
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
    return tracker.get_ratings()


# ---------------------------------------------------------------------------
# Evaluator retraining and promotion
# ---------------------------------------------------------------------------


def _get_next_eval_version() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(MODELS_DIR.glob("champion_eval_v*.pkl"))
    versions = []
    for p in existing:
        stem = p.stem
        if "_v" in stem:
            try:
                versions.append(int(stem.rsplit("_v", 1)[1]))
            except ValueError:
                pass
    return max(versions) + 1 if versions else 1


def _retrain_evaluator(version: int) -> Optional[str]:
    """Train a new GBT evaluator from cumulative snapshots. Returns model path or None."""
    if not CUMULATIVE_SNAPSHOTS_PATH.exists():
        print("[champion_loop] No snapshot data available for retraining.")
        return None
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = str(MODELS_DIR / f"champion_eval_v{version}.pkl")
    cmd = [
        sys.executable, "scripts/train_eval_model.py",
        "--data", str(CUMULATIVE_SNAPSHOTS_PATH),
        "--model-type", "pairwise_gbt_phase",
        "--output", model_path,
        "--seed", "42",
    ]
    print(f"[champion_loop] Retraining: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"[champion_loop] Training failed (exit {result.returncode})")
        return None
    print(f"[champion_loop] Saved evaluator: {model_path}")
    return model_path


def _run_promotion_trial(
    current_params: Dict[str, Any],
    learned_params: Dict[str, Any],
    num_games: int,
    run_number: int,
) -> Tuple[float, float]:
    """Head-to-head: champion_current vs champion_learned + 2 mid/strong opponents.

    Returns (current_win_rate, learned_win_rate).
    """
    config = {
        "agents": [
            {
                "name": "champion_current",
                "type": "mcts",
                "thinking_time_ms": CHAMPION_THINKING_TIME_MS,
                "params": current_params,
            },
            {
                "name": "champion_learned",
                "type": "mcts",
                "thinking_time_ms": CHAMPION_THINKING_TIME_MS,
                "params": learned_params,
            },
            POOL_TIER_MID[1],   # pool_t2_mcts_100ms_l5
            POOL_TIER_STRONG[0],  # pool_t3_mcts_200ms_l9
        ],
        "num_games": num_games,
        "seed": run_number * 1000000 + 20260504,
        "seat_policy": "round_robin",
        "output_root": "arena_runs",
        "max_turns": 2500,
        "notes": f"Champion promotion trial run {run_number}: current vs learned",
        "snapshots": {"enabled": False},
    }
    fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="champion_promote_")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(config, f, indent=2)
        result = subprocess.run(
            [sys.executable, "scripts/arena.py", "--config", tmp_path],
            capture_output=False,
            text=True,
        )
        if result.returncode != 0:
            return 0.0, 0.0
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    run_dir = _find_latest_run("arena_runs")
    if not run_dir:
        return 0.0, 0.0
    trial = _parse_run_summary(run_dir, "champion_current")
    current_wr = trial["agents"].get("champion_current", {}).get("win_rate", 0.0)
    learned_wr = trial["agents"].get("champion_learned", {}).get("win_rate", 0.0)
    return current_wr, learned_wr


# ---------------------------------------------------------------------------
# Run log I/O
# ---------------------------------------------------------------------------


def _load_run_log() -> List[Dict[str, Any]]:
    if not RUN_LOG_PATH.exists():
        return []
    with RUN_LOG_PATH.open() as f:
        return json.load(f)


def _save_run_log(log: List[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with RUN_LOG_PATH.open("w") as f:
        json.dump(log, f, indent=2)


def _append_run_log(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    log = _load_run_log()
    log.append(entry)
    _save_run_log(log)
    return log


def _get_next_run_number() -> int:
    log = _load_run_log()
    return max((e.get("run_number", 0) for e in log), default=0) + 1


# ---------------------------------------------------------------------------
# Progress report rendering
# ---------------------------------------------------------------------------


def _tier_label(agent_name: str) -> str:
    if agent_name.startswith("pool_t0") or agent_name.startswith("pool_t1"):
        return "weak"
    if agent_name.startswith("pool_t2"):
        return "mid"
    return "strong"


def _render_progress_report(
    log: List[Dict[str, Any]],
    cumulative_trueskill: Dict[str, Dict[str, float]],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    total_games = _count_lines(CUMULATIVE_GAMES_PATH)
    total_snap = _count_snapshot_rows()

    lines = [
        "# Champion Progress Report",
        "",
        f"*Last updated: {now}*",
        "",
        "**Goal**: Build an agent that reliably beats a human player.",
        "",
        f"**Cumulative games played**: {total_games}  |  "
        f"**Snapshot rows**: {total_snap}  |  "
        f"**Runs completed**: {len(log)}",
        "",
        "---",
        "",
        "## TrueSkill Trajectory (Cumulative)",
        "",
        "μ and σ are recomputed from all games ever played by the champion.",
        "Conservative = μ − 3σ (the leaderboard metric).",
        "",
        "| Run | Date | Games | μ | σ | Conservative | Challengers |",
        "|-----|------|-------|---|---|--------------|-------------|",
    ]
    for entry in log:
        run_n = entry.get("run_number", "?")
        ts = entry.get("timestamp", "")[:10]
        cum_g = entry.get("cumulative_games", 0)
        ct = entry.get("champion_cumulative_trueskill", {})
        mu = ct.get("mu", 25.0)
        sigma = ct.get("sigma", 8.333)
        conservative = ct.get("conservative", 0.0)
        challengers = ", ".join(f"`{c}`" for c in entry.get("challengers", []))
        lines.append(
            f"| {run_n} | {ts} | {cum_g} | {mu:.2f} | {sigma:.2f} | "
            f"**{conservative:.2f}** | {challengers} |"
        )

    lines += [
        "",
        "## Champion Win Rate vs Challenger Tiers",
        "",
        "| Run | vs Weak (T0/T1) | vs Mid (T2) | vs Strong (T3) | Overall WR |",
        "|-----|-----------------|-------------|----------------|------------|",
    ]
    for entry in log:
        run_n = entry.get("run_number", "?")
        matchups = entry.get("champion_matchups", {})
        tier_wrs: Dict[str, List[float]] = {"weak": [], "mid": [], "strong": []}
        for c in entry.get("challengers", []):
            wr = matchups.get(c, {}).get("champion_win_rate")
            if wr is not None:
                tier_wrs[_tier_label(c)].append(wr)

        def _fmt(wrs: List[float]) -> str:
            return f"{sum(wrs)/len(wrs)*100:.1f}%" if wrs else "—"

        overall = entry.get("champion_stats", {}).get("win_rate", 0.0) * 100
        lines.append(
            f"| {run_n} | {_fmt(tier_wrs['weak'])} | {_fmt(tier_wrs['mid'])} | "
            f"{_fmt(tier_wrs['strong'])} | {overall:.1f}% |"
        )

    # ASCII TrueSkill μ bar chart
    mus = [e.get("champion_cumulative_trueskill", {}).get("mu", 25.0) for e in log]
    if len(mus) >= 2:
        min_mu = min(mus)
        max_mu = max(mus)
        bar_width = 40
        lines += ["", "## TrueSkill μ Trajectory (ASCII)", "", "```"]
        for entry, mu in zip(log, mus):
            frac = (mu - min_mu) / (max_mu - min_mu) if max_mu > min_mu else 0.5
            bars = max(1, int(frac * bar_width))
            run_n = entry.get("run_number", "?")
            lines.append(f"Run {run_n:3} | {'█' * bars:<{bar_width}} | μ={mu:.2f}")
        lines.append("```")

    lines += [
        "",
        "## Evaluator Version History",
        "",
        "| Run | Eval Version | Action | Snapshot Rows |",
        "|-----|--------------|--------|---------------|",
    ]
    for entry in log:
        run_n = entry.get("run_number", "?")
        ev = entry.get("eval_version", "v0_hand_tuned")
        action = entry.get("eval_action", "—")
        snap = entry.get("cumulative_snapshot_rows", 0)
        lines.append(f"| {run_n} | {ev} | {action} | {snap} |")

    lines += [
        "",
        "## Cumulative Pool TrueSkill",
        "",
        "Ratings for all agents (champion + challengers) computed from all accumulated games.",
        "",
        "| Rank | Agent | μ | σ | Conservative | Games |",
        "|------|-------|---|---|--------------|-------|",
    ]
    sorted_agents = sorted(
        cumulative_trueskill.items(),
        key=lambda x: x[1].get("conservative", 0.0),
        reverse=True,
    )
    for rank, (agent_id, rating) in enumerate(sorted_agents, 1):
        mu = rating.get("mu", 25.0)
        sigma = rating.get("sigma", 8.333)
        conservative = rating.get("conservative", 0.0)
        games = rating.get("games_played", 0)
        bold = "**" if agent_id == CHAMPION_NAME else ""
        lines.append(
            f"| {rank} | {bold}`{agent_id}`{bold} | {mu:.2f} | {sigma:.2f} | "
            f"**{conservative:.2f}** | {games} |"
        )

    lines += [
        "",
        "---",
        "",
        "*Generated automatically by `scripts/champion_loop.py`*",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Console history display
# ---------------------------------------------------------------------------


def _show_history() -> None:
    log = _load_run_log()
    if not log:
        print("[champion_loop] No runs logged yet.")
        return
    total_games = _count_lines(CUMULATIVE_GAMES_PATH)
    print(f"\n{'='*70}")
    print(f" Champion Progress — {len(log)} run(s), {total_games} total games")
    print(f"{'='*70}")
    for entry in log:
        run_n = entry.get("run_number", "?")
        ts = entry.get("timestamp", "")[:19]
        games = entry.get("num_games", "?")
        challengers = ", ".join(entry.get("challengers", []))
        champ_stats = entry.get("champion_stats", {})
        rt = entry.get("champion_run_trueskill", {})
        ct = entry.get("champion_cumulative_trueskill", {})
        snap = entry.get("cumulative_snapshot_rows", 0)
        ev = entry.get("eval_version", "v0")
        eval_action = entry.get("eval_action", "—")
        wr = champ_stats.get("win_rate", 0.0) * 100
        avg = champ_stats.get("avg_score", 0.0)
        print(f"\n  Run {run_n} ({ts}, {games} games)")
        print(f"    Challengers:    {challengers}")
        print(
            f"    Champion:       WR={wr:.1f}%  AvgScore={avg:.1f}  "
            f"Eval={ev}  Action={eval_action}"
        )
        print(
            f"    Run TrueSkill:  μ={rt.get('mu', 25):.2f}  "
            f"σ={rt.get('sigma', 8.3):.2f}  "
            f"conservative={rt.get('conservative', 0):.2f}"
        )
        print(
            f"    Cum TrueSkill:  μ={ct.get('mu', 25):.2f}  "
            f"σ={ct.get('sigma', 8.3):.2f}  "
            f"conservative={ct.get('conservative', 0):.2f}"
        )
        print(f"    Snapshot rows:  {snap}")

    if len(log) >= 2:
        first_ct = log[0].get("champion_cumulative_trueskill", {})
        last_ct = log[-1].get("champion_cumulative_trueskill", {})
        delta_mu = last_ct.get("mu", 25.0) - first_ct.get("mu", 25.0)
        delta_cons = last_ct.get("conservative", 0.0) - first_ct.get("conservative", 0.0)
        print(f"\n{'='*70}")
        print(f" Trend (run 1 → run {log[-1].get('run_number', '?')})")
        sign_mu = "+" if delta_mu >= 0 else ""
        sign_c = "+" if delta_cons >= 0 else ""
        print(f"    Δμ (cumulative):            {sign_mu}{delta_mu:.3f}")
        print(f"    Δconservative (cumulative): {sign_c}{delta_cons:.3f}")
    print()


# ---------------------------------------------------------------------------
# Main iteration logic
# ---------------------------------------------------------------------------


def run_iteration(
    *,
    num_games: int,
    retrain_threshold: int = RETRAIN_THRESHOLD,
    force_retrain: bool = False,
    promote: bool = True,
    promotion_games: int = 10,
) -> None:
    run_number = _get_next_run_number()
    timestamp = datetime.now(timezone.utc).isoformat()

    print(f"\n{'='*70}")
    print(f" Champion Loop — Run #{run_number}")
    print(f" {timestamp}")
    print(f"{'='*70}\n")

    # Load champion
    champion_params = _load_champion_params()
    eval_version = _get_current_eval_version(champion_params)
    print(f"[champion_loop] Champion eval version: {eval_version}")

    # Select challengers
    challengers = _select_challengers(run_number)
    challenger_names = [c["name"] for c in challengers]
    print(f"[champion_loop] Challengers: {', '.join(challenger_names)}")

    # Build and run gauntlet
    seed = run_number * 1_000_000 + 20_260_503
    notes = f"Champion loop run {run_number}: champion vs {', '.join(challenger_names)}"
    arena_config = _build_arena_config(
        champion_params, challengers, num_games, seed, notes=notes
    )
    run_dir = _run_arena_config(arena_config)

    # Parse results
    summary = _parse_run_summary(run_dir, CHAMPION_NAME)
    champion_stats = summary["agents"].get(CHAMPION_NAME, {})
    print(
        f"\n[champion_loop] Champion: WR={champion_stats.get('win_rate', 0)*100:.1f}%  "
        f"AvgScore={champion_stats.get('avg_score', 0):.1f}  "
        f"μ_run={champion_stats.get('trueskill_mu', 25):.2f}"
    )
    for c_name, matchup in summary["champion_matchups"].items():
        print(
            f"  vs {c_name}: {matchup['champion_wins']}-{matchup['other_wins']}"
            f"-{matchup['ties']}  "
            f"(WR {matchup['champion_win_rate']*100:.1f}%)"
        )

    # Accumulate data
    cumulative_games = _accumulate_games(run_dir)
    cumulative_rows = _accumulate_snapshots(run_dir, summary.get("snapshot_csv"))
    print(
        f"\n[champion_loop] Cumulative: {cumulative_games} games, "
        f"{cumulative_rows} snapshot rows"
    )

    # Compute cumulative TrueSkill from all accumulated games
    cumulative_trueskill = _compute_cumulative_trueskill()
    default_ts = {"mu": 25.0, "sigma": 8.333, "conservative": 0.0, "games_played": 0}
    champion_cum_ts = cumulative_trueskill.get(CHAMPION_NAME, default_ts)
    print(
        f"[champion_loop] Cumulative TrueSkill: "
        f"μ={champion_cum_ts['mu']:.2f}  "
        f"σ={champion_cum_ts['sigma']:.2f}  "
        f"conservative={champion_cum_ts['conservative']:.2f}"
    )

    # Retrain evaluator if threshold met
    eval_action = "—"
    new_model_path = None
    rows_since_last_train = _rows_since_last_training()

    should_retrain = force_retrain or (
        cumulative_rows >= retrain_threshold
        and rows_since_last_train >= MIN_NEW_ROWS_FOR_RETRAIN
    )
    if should_retrain:
        next_v = _get_next_eval_version()
        print(f"\n[champion_loop] Retraining evaluator v{next_v} "
              f"({cumulative_rows} rows, {rows_since_last_train} new)")
        new_model_path = _retrain_evaluator(next_v)
        eval_action = f"trained v{next_v}"

        if new_model_path and promote:
            print(f"[champion_loop] Running promotion trial ({promotion_games} games)...")
            learned_params = dict(champion_params)
            learned_params["learned_model_path"] = new_model_path
            learned_params["leaf_evaluation_enabled"] = True
            current_wr, learned_wr = _run_promotion_trial(
                champion_params, learned_params, promotion_games, run_number
            )
            print(
                f"[champion_loop] Promotion trial — "
                f"current WR={current_wr:.3f}, learned WR={learned_wr:.3f}"
            )
            if learned_wr > current_wr:
                print(f"[champion_loop] PROMOTED to eval v{next_v}!")
                champion_params["learned_model_path"] = new_model_path
                champion_params["leaf_evaluation_enabled"] = True
                new_eval_version = f"v{next_v}"
                _save_champion_params(champion_params, new_eval_version)
                eval_action = f"promoted to v{next_v}"
                eval_version = new_eval_version
            else:
                print("[champion_loop] Not promoted (learned WR did not improve).")
                eval_action = f"trained v{next_v}, not promoted"
        elif new_model_path:
            eval_action = f"trained v{next_v} (promotion skipped)"

    # Append log entry
    entry: Dict[str, Any] = {
        "run_number": run_number,
        "timestamp": timestamp,
        "run_dir": run_dir,
        "challengers": challenger_names,
        "num_games": summary["completed_games"],
        "champion_stats": {
            "win_rate": champion_stats.get("win_rate", 0.0),
            "win_points": champion_stats.get("win_points", 0.0),
            "avg_score": champion_stats.get("avg_score", 0.0),
            "games_played": champion_stats.get("games_played", 0),
        },
        "champion_run_trueskill": {
            "mu": champion_stats.get("trueskill_mu", 25.0),
            "sigma": champion_stats.get("trueskill_sigma", 8.333),
            "conservative": champion_stats.get("trueskill_conservative", 0.0),
        },
        "champion_cumulative_trueskill": {
            "mu": champion_cum_ts["mu"],
            "sigma": champion_cum_ts["sigma"],
            "conservative": champion_cum_ts["conservative"],
            "games_played": champion_cum_ts["games_played"],
        },
        "challengers_summary": {
            c: {
                "win_rate": summary["agents"].get(c, {}).get("win_rate", 0.0),
                "avg_score": summary["agents"].get(c, {}).get("avg_score", 0.0),
            }
            for c in challenger_names
        },
        "champion_matchups": summary.get("champion_matchups", {}),
        "cumulative_games": cumulative_games,
        "cumulative_snapshot_rows": cumulative_rows,
        "eval_version": eval_version,
        "eval_action": eval_action,
        "eval_trained": new_model_path is not None,
    }
    log = _append_run_log(entry)

    # Render and save progress report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "champion_progress.md"
    report_path.write_text(
        _render_progress_report(log, cumulative_trueskill), encoding="utf-8"
    )
    print(f"\n[champion_loop] Report written: {report_path}")
    print(f"[champion_loop] Run log:         {RUN_LOG_PATH}")
    _show_history()


def _rows_since_last_training() -> int:
    """How many snapshot rows have accumulated since the last evaluator training."""
    log = _load_run_log()
    last_rows = max(
        (e.get("cumulative_snapshot_rows", 0) for e in log if e.get("eval_trained")),
        default=0,
    )
    return _count_snapshot_rows() - last_rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Champion Self-Improvement Loop — champion vs randomized challenger pool."
    )
    parser.add_argument(
        "--num-runs", type=int, default=1,
        help="Number of gauntlet iterations to run (default: 1)"
    )
    parser.add_argument(
        "--num-games", type=int, default=20,
        help="Games per arena run (default: 20)"
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Print improvement history and exit"
    )
    parser.add_argument(
        "--show-report", action="store_true",
        help="Print the latest champion_progress.md and exit"
    )
    parser.add_argument(
        "--retrain", action="store_true",
        help="Force evaluator retrain on the first iteration"
    )
    parser.add_argument(
        "--no-promote", action="store_true",
        help="Skip the promotion trial after retraining"
    )
    parser.add_argument(
        "--retrain-threshold", type=int, default=RETRAIN_THRESHOLD,
        help=f"Snapshot rows needed to trigger auto-retrain (default: {RETRAIN_THRESHOLD})"
    )
    parser.add_argument(
        "--promotion-games", type=int, default=10,
        help="Number of games in promotion trial (default: 10)"
    )
    args = parser.parse_args()

    if args.show:
        _show_history()
        return

    if args.show_report:
        if REPORTS_DIR.joinpath("champion_progress.md").exists():
            print((REPORTS_DIR / "champion_progress.md").read_text())
        else:
            print("[champion_loop] No report yet. Run at least one iteration first.")
        return

    for i in range(args.num_runs):
        if args.num_runs > 1:
            print(f"\n[champion_loop] ===== Iteration {i + 1}/{args.num_runs} =====")
        run_iteration(
            num_games=args.num_games,
            retrain_threshold=args.retrain_threshold,
            force_retrain=(args.retrain and i == 0),
            promote=not args.no_promote,
            promotion_games=args.promotion_games,
        )


if __name__ == "__main__":
    main()
