"""1.4 — Q-Value Convergence Check.

Samples game states from real games and runs MCTS at increasing iteration
budgets (1K → 100K) to measure how quickly Q-values stabilise.
"""

from __future__ import annotations

import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from analytics.baseline.plots import save_plot, setup_plot_style
from engine.board import Board, Player
from engine.game import BlokusGame
from engine.move_generator import LegalMoveGenerator, Move, get_shared_generator

DEFAULT_BUDGETS = [1000, 5000, 10000, 50000, 100000]


# ------------------------------------------------------------------
# State sampling
# ------------------------------------------------------------------


def sample_states(
    steps: List[Dict[str, Any]],
    n_early: int = 10,
    n_mid: int = 20,
    n_late: int = 20,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Sample game states from step logs for convergence analysis.

    Early = turns 1-20, mid = turns 21-52, late = turns 53+.

    Returns list of ``{game_id, turn_index, phase}``.
    """
    rng = random.Random(seed)

    by_phase: Dict[str, List[Dict[str, Any]]] = {"early": [], "mid": [], "late": []}
    for step in steps:
        turn = step.get("turn_index", 0)
        game_id = step.get("game_id", "")
        bf = step.get("legal_moves_before", 0)
        if bf == 0:
            continue  # skip turns with no legal moves
        if turn <= 20:
            phase = "early"
        elif turn <= 52:
            phase = "mid"
        else:
            phase = "late"
        by_phase[phase].append({"game_id": game_id, "turn_index": turn, "phase": phase})

    sampled: List[Dict[str, Any]] = []
    for phase, count in [("early", n_early), ("mid", n_mid), ("late", n_late)]:
        pool = by_phase[phase]
        if not pool:
            continue
        k = min(count, len(pool))
        sampled.extend(rng.sample(pool, k))

    return sampled


# ------------------------------------------------------------------
# Board state reconstruction from step logs
# ------------------------------------------------------------------


def reconstruct_board_state(
    steps: List[Dict[str, Any]],
    game_id: str,
    target_turn: int,
) -> Optional[Tuple[Board, Player, List[Move]]]:
    """Replay moves from step logs to reconstruct a board state.

    Args:
        steps: All step log entries (will be filtered by game_id).
        game_id: The game to reconstruct.
        target_turn: Stop replaying BEFORE this turn index (so the
            returned board is the state the player sees when deciding).

    Returns:
        ``(board, current_player, legal_moves)`` or ``None`` if the
        game/turn could not be reconstructed.
    """
    game_steps = sorted(
        [s for s in steps if s.get("game_id") == game_id],
        key=lambda s: s.get("turn_index", 0),
    )

    game = BlokusGame(enable_telemetry=False)
    move_gen = get_shared_generator()

    for step in game_steps:
        if step["turn_index"] >= target_turn:
            break

        action = step.get("action", {})
        piece_id = action.get("piece_id")
        orientation = action.get("orientation")
        anchor_row = action.get("anchor_row")
        anchor_col = action.get("anchor_col")

        if piece_id is None:
            # Pass / skip
            game.board._update_current_player()
            continue

        move = Move(
            piece_id=int(piece_id),
            orientation=int(orientation),
            anchor_row=int(anchor_row),
            anchor_col=int(anchor_col),
        )
        if not game.make_move(move, game.board.current_player):
            # If move fails, skip and advance player
            game.board._update_current_player()

    current_player = game.board.current_player
    legal_moves = move_gen.get_legal_moves(game.board, current_player)
    if not legal_moves:
        return None

    return game.board, current_player, legal_moves


# ------------------------------------------------------------------
# Convergence check: run MCTS at multiple budgets
# ------------------------------------------------------------------


def _move_id(move: Move) -> str:
    return f"{move.piece_id}-{move.orientation}-{move.anchor_row}-{move.anchor_col}"


def run_convergence_check_for_state(
    board: Board,
    player: Player,
    legal_moves: List[Move],
    budgets: List[int] | None = None,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    """Run MCTS at varying iteration budgets and record Q-value data.

    Uses ``GameplayFastMCTSAgent`` (the current production agent) at each
    budget level with deterministic iteration count.

    Returns one entry per budget level with Q-value, best-move identity,
    and regret gap.
    """
    from agents.gameplay_fast_mcts import GameplayFastMCTSAgent

    if budgets is None:
        budgets = list(DEFAULT_BUDGETS)

    results: List[Dict[str, Any]] = []

    for budget in budgets:
        agent = GameplayFastMCTSAgent(
            iterations=budget,
            exploration_constant=1.414,
            seed=seed,
        )
        agent._agent.enable_diagnostics = True

        board_copy = board.copy()
        move, stats = agent.choose_move(
            board_copy,
            player,
            legal_moves,
            time_budget_ms=10_000_000,  # effectively unlimited time
        )

        diagnostics = (stats or {}).get("diagnostics", {})
        top_moves = diagnostics.get("rootPolicy", [])
        best = top_moves[0] if top_moves else {}
        second = top_moves[1] if len(top_moves) > 1 else {}

        best_q = best.get("q_value")
        second_q = second.get("q_value")

        results.append(
            {
                "budget": budget,
                "best_move_id": _move_id(move) if move else None,
                "best_q": best_q,
                "best_visits": best.get("visits"),
                "second_q": second_q,
                "regret_gap": (
                    (best_q - second_q)
                    if best_q is not None and second_q is not None
                    else None
                ),
                "simulations": diagnostics.get("simulations"),
                "num_legal_moves": len(legal_moves),
            }
        )

    return results


def run_convergence_analysis(
    steps: List[Dict[str, Any]],
    sampled_states: List[Dict[str, Any]],
    budgets: List[int] | None = None,
    seed: int = 42,
    progress_callback=None,
) -> List[Dict[str, Any]]:
    """Run the full convergence analysis across all sampled states.

    Args:
        steps: All step log entries.
        sampled_states: Output of :func:`sample_states`.
        budgets: Iteration budgets to test.
        seed: RNG seed for MCTS.
        progress_callback: Optional ``fn(i, total)`` called after each state.

    Returns:
        List of result dicts, one per (state, budget) combination.
    """
    if budgets is None:
        budgets = list(DEFAULT_BUDGETS)

    all_results: List[Dict[str, Any]] = []
    total = len(sampled_states)

    for i, state_info in enumerate(sampled_states):
        reconstructed = reconstruct_board_state(
            steps, state_info["game_id"], state_info["turn_index"]
        )
        if reconstructed is None:
            continue

        board, player, legal_moves = reconstructed
        state_results = run_convergence_check_for_state(
            board, player, legal_moves, budgets=budgets, seed=seed
        )

        for result in state_results:
            result["game_id"] = state_info["game_id"]
            result["turn_index"] = state_info["turn_index"]
            result["phase"] = state_info["phase"]

        all_results.extend(state_results)

        if progress_callback:
            progress_callback(i + 1, total)

    return all_results


# ------------------------------------------------------------------
# Analysis helpers
# ------------------------------------------------------------------


def compute_convergence_summary(
    results: List[Dict[str, Any]],
    budgets: List[int] | None = None,
) -> Dict[str, Any]:
    """Aggregate convergence results into summary metrics.

    For each budget transition, computes:
    - Fraction of states where best move identity changed
    - Mean Q-value shift
    - Mean regret gap
    """
    if budgets is None:
        budgets = list(DEFAULT_BUDGETS)

    # Group by (game_id, turn_index)
    by_state: Dict[Tuple[str, int], Dict[int, Dict]] = defaultdict(dict)
    for r in results:
        key = (r["game_id"], r["turn_index"])
        by_state[key][r["budget"]] = r

    per_budget: Dict[int, Dict[str, Any]] = {}
    for budget in budgets:
        q_values = []
        regret_gaps = []
        for state_results in by_state.values():
            entry = state_results.get(budget)
            if entry and entry.get("best_q") is not None:
                q_values.append(entry["best_q"])
            if entry and entry.get("regret_gap") is not None:
                regret_gaps.append(entry["regret_gap"])

        per_budget[budget] = {
            "mean_best_q": sum(q_values) / len(q_values) if q_values else None,
            "std_best_q": (
                math.sqrt(sum((v - sum(q_values) / len(q_values)) ** 2 for v in q_values) / len(q_values))
                if len(q_values) > 1
                else None
            ),
            "mean_regret_gap": sum(regret_gaps) / len(regret_gaps) if regret_gaps else None,
            "states_measured": len(q_values),
        }

    # Move-change analysis between consecutive budgets
    move_changes: List[Dict[str, Any]] = []
    for idx in range(len(budgets) - 1):
        lo, hi = budgets[idx], budgets[idx + 1]
        changed = 0
        total = 0
        for state_results in by_state.values():
            lo_entry = state_results.get(lo)
            hi_entry = state_results.get(hi)
            if lo_entry and hi_entry:
                total += 1
                if lo_entry.get("best_move_id") != hi_entry.get("best_move_id"):
                    changed += 1
        move_changes.append(
            {
                "from_budget": lo,
                "to_budget": hi,
                "total_states": total,
                "moves_changed": changed,
                "change_rate": changed / total if total > 0 else None,
            }
        )

    return {
        "per_budget": per_budget,
        "move_changes": move_changes,
        "total_states": len(by_state),
        "budgets": budgets,
    }


# ------------------------------------------------------------------
# Plotting
# ------------------------------------------------------------------


def plot_convergence_heatmap(
    results: List[Dict[str, Any]],
    budgets: List[int] | None = None,
    output_path: str | Path = "qvalue_convergence_heatmap.png",
) -> None:
    """Heatmap: turn_number x budget, colored by Q-value stability.

    Stability is measured as the standard deviation of Q-values across
    the last 3 budget levels for each state.
    """
    if budgets is None:
        budgets = list(DEFAULT_BUDGETS)

    setup_plot_style()

    # Group by (game_id, turn_index)
    by_state: Dict[Tuple[str, int], Dict[int, float]] = defaultdict(dict)
    turn_indices: Dict[Tuple[str, int], int] = {}
    for r in results:
        key = (r["game_id"], r["turn_index"])
        if r.get("best_q") is not None:
            by_state[key][r["budget"]] = r["best_q"]
        turn_indices[key] = r["turn_index"]

    if not by_state:
        return

    # Sort states by turn_index
    sorted_states = sorted(by_state.keys(), key=lambda k: turn_indices[k])

    # Build heatmap data: Q-value at each (state, budget)
    n_states = len(sorted_states)
    n_budgets = len(budgets)
    data = np.full((n_states, n_budgets), np.nan)

    for i, state_key in enumerate(sorted_states):
        for j, budget in enumerate(budgets):
            if budget in by_state[state_key]:
                data[i, j] = by_state[state_key][budget]

    fig, ax = plt.subplots(figsize=(10, max(6, n_states * 0.3)))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", interpolation="nearest")
    ax.set_xticks(range(n_budgets))
    ax.set_xticklabels([f"{b // 1000}K" for b in budgets])
    ax.set_xlabel("Iteration budget")

    y_labels = [f"t{turn_indices[k]}" for k in sorted_states]
    ax.set_yticks(range(n_states))
    ax.set_yticklabels(y_labels, fontsize=7)
    ax.set_ylabel("State (by turn)")

    ax.set_title("1.4 — Q-Value Convergence Heatmap")
    fig.colorbar(im, ax=ax, label="Best move Q-value")
    save_plot(fig, output_path)


def plot_per_state_convergence(
    results: List[Dict[str, Any]],
    budgets: List[int] | None = None,
    output_path: str | Path = "qvalue_convergence_per_state.png",
    max_states: int = 12,
) -> None:
    """Per-state Q-value vs budget line plots (subplot grid)."""
    if budgets is None:
        budgets = list(DEFAULT_BUDGETS)

    setup_plot_style()

    # Group by (game_id, turn_index)
    by_state: Dict[Tuple[str, int], List[Dict]] = defaultdict(list)
    for r in results:
        key = (r["game_id"], r["turn_index"])
        by_state[key].append(r)

    states = sorted(by_state.keys(), key=lambda k: k[1])[:max_states]
    if not states:
        return

    cols = min(4, len(states))
    rows = math.ceil(len(states) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(4 * cols, 3 * rows), squeeze=False)

    for idx, state_key in enumerate(states):
        ax = axes[idx // cols][idx % cols]
        entries = sorted(by_state[state_key], key=lambda e: e["budget"])
        x = [e["budget"] for e in entries]
        y = [e.get("best_q", 0) or 0 for e in entries]
        ax.plot(x, y, "o-", color="steelblue", markersize=4)
        ax.set_title(f"Turn {state_key[1]}", fontsize=9)
        ax.set_xscale("log")
        ax.set_xlabel("Budget", fontsize=8)
        ax.set_ylabel("Q", fontsize=8)
        ax.tick_params(labelsize=7)

    # Hide unused subplots
    for idx in range(len(states), rows * cols):
        axes[idx // cols][idx % cols].set_visible(False)

    fig.suptitle("1.4 — Q-Value Convergence per State", fontsize=13)
    fig.tight_layout()
    save_plot(fig, output_path)
