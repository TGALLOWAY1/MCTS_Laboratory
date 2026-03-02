"""Reproducible arena harness for multi-agent Blokus experiments."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from agents.fast_mcts_agent import FastMCTSAgent
from agents.gameplay_fast_mcts import GameplayFastMCTSAgent
from agents.heuristic_agent import HeuristicAgent
from agents.random_agent import RandomAgent
from analytics.tournament.arena_stats import compute_summary, render_summary_markdown
from engine.board import Player
from engine.game import BlokusGame
from engine.move_generator import Move
from mcts.mcts_agent import MCTSAgent


DEFAULT_OUTPUT_ROOT = "arena_runs"
DEFAULT_MAX_TURNS = 2500
SUPPORTED_SEAT_POLICIES = {"randomized", "round_robin"}


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for a single arena agent."""

    name: str
    type: str
    thinking_time_ms: Optional[int] = None
    params: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, item: Mapping[str, Any]) -> "AgentConfig":
        if "name" not in item:
            raise ValueError("Agent entries must include 'name'")
        if "type" not in item:
            raise ValueError(f"Agent '{item['name']}' is missing required field 'type'")
        params = dict(item.get("params") or {})
        for key, value in item.items():
            if key in {"name", "type", "thinking_time_ms", "params"}:
                continue
            params[key] = value
        thinking_time = item.get("thinking_time_ms")
        thinking_time_ms = int(thinking_time) if thinking_time is not None else None
        return cls(
            name=str(item["name"]),
            type=str(item["type"]),
            thinking_time_ms=thinking_time_ms,
            params=params,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "thinking_time_ms": self.thinking_time_ms,
            "params": dict(self.params),
        }


@dataclass(frozen=True)
class RunConfig:
    """Top-level experiment configuration."""

    agents: List[AgentConfig]
    num_games: int
    seed: int
    seat_policy: str = "randomized"
    output_root: str = DEFAULT_OUTPUT_ROOT
    max_turns: int = DEFAULT_MAX_TURNS
    notes: str = ""

    @classmethod
    def from_dict(cls, config: Mapping[str, Any]) -> "RunConfig":
        agents_raw = config.get("agents")
        if agents_raw is None:
            agents_raw = _legacy_agents_to_list(config)
        if not isinstance(agents_raw, list):
            raise ValueError("RunConfig 'agents' must be a list.")

        agents = [AgentConfig.from_dict(item) for item in agents_raw]
        num_games = int(config.get("num_games", 100))
        seed = int(config.get("seed", 0))
        seat_policy = str(config.get("seat_policy", "randomized"))
        output_root = str(config.get("output_root", DEFAULT_OUTPUT_ROOT))
        max_turns = int(config.get("max_turns", DEFAULT_MAX_TURNS))
        notes = str(config.get("notes", ""))
        run_config = cls(
            agents=agents,
            num_games=num_games,
            seed=seed,
            seat_policy=seat_policy,
            output_root=output_root,
            max_turns=max_turns,
            notes=notes,
        )
        run_config.validate()
        return run_config

    def validate(self) -> None:
        if self.num_games <= 0:
            raise ValueError("num_games must be > 0.")
        if len(self.agents) != len(Player):
            raise ValueError(
                f"Arena expects exactly {len(Player)} agents; received {len(self.agents)}."
            )
        if len({agent.name for agent in self.agents}) != len(self.agents):
            raise ValueError("Agent names must be unique.")
        if self.seat_policy not in SUPPORTED_SEAT_POLICIES:
            raise ValueError(
                f"Unsupported seat_policy '{self.seat_policy}'. Expected one of {sorted(SUPPORTED_SEAT_POLICIES)}."
            )
        if self.max_turns <= 0:
            raise ValueError("max_turns must be > 0.")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agents": [agent.to_dict() for agent in self.agents],
            "num_games": self.num_games,
            "seed": self.seed,
            "seat_policy": self.seat_policy,
            "output_root": self.output_root,
            "max_turns": self.max_turns,
            "notes": self.notes,
        }

    @property
    def agent_names(self) -> List[str]:
        return [agent.name for agent in self.agents]


def _legacy_agents_to_list(config: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Support legacy scripts/arena_config.json shape."""
    legacy_agents: List[Dict[str, Any]] = []
    for name, item in config.items():
        if not isinstance(item, Mapping) or "type" not in item:
            continue
        thinking_time_ms = item.get("thinking_time_ms")
        if thinking_time_ms is None and item.get("time_limit") is not None:
            thinking_time_ms = int(float(item["time_limit"]) * 1000)
        params: Dict[str, Any] = {}
        for key, value in item.items():
            if key in {"type", "thinking_time_ms"}:
                continue
            params[key] = value
        legacy_agents.append(
            {
                "name": str(name),
                "type": str(item["type"]),
                "thinking_time_ms": thinking_time_ms,
                "params": params,
            }
        )
    if not legacy_agents:
        raise ValueError(
            "Invalid run config: missing 'agents' list and no legacy agent entries were found."
        )
    return legacy_agents


def load_run_config(config_path: str) -> RunConfig:
    """Load a RunConfig from JSON."""
    with Path(config_path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Run config must be a JSON object.")
    return RunConfig.from_dict(payload)


def stable_hash_int(*parts: Any, mod: int = 2**31 - 1) -> int:
    """Stable integer hash suitable for seeds."""
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:16], 16) % mod


def game_seed_from_run_seed(run_seed: int, game_index: int) -> int:
    """Derive deterministic per-game seed from run seed and game index."""
    return stable_hash_int(run_seed, game_index, "game_seed")


def _agent_seed(run_seed: int, game_index: int, agent_name: str) -> int:
    return stable_hash_int(run_seed, game_index, agent_name, "agent_seed")


def _resolve_run_id(config: RunConfig) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    hash_input = json.dumps(config.to_dict(), sort_keys=True)
    short_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:8]
    return f"{timestamp}_{short_hash}"


def _prepare_run_directory(config: RunConfig) -> Tuple[str, Path]:
    root = Path(config.output_root)
    root.mkdir(parents=True, exist_ok=True)
    base_run_id = _resolve_run_id(config)
    run_id = base_run_id
    run_dir = root / run_id
    attempt = 1
    while run_dir.exists():
        run_id = f"{base_run_id}_{attempt:02d}"
        run_dir = root / run_id
        attempt += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_id, run_dir


def _seat_assignment_for_game(
    agent_names: Sequence[str],
    game_index: int,
    game_seed: int,
    seat_policy: str,
) -> Dict[str, str]:
    ordered_agents = list(agent_names)
    if seat_policy == "round_robin":
        shift = game_index % len(ordered_agents)
        ordered_agents = ordered_agents[shift:] + ordered_agents[:shift]
    else:
        seat_rng = random.Random(stable_hash_int(game_seed, "seat_assignment"))
        seat_rng.shuffle(ordered_agents)
    return {str(player.value): ordered_agents[idx] for idx, player in enumerate(Player)}


class _ArenaAgentAdapter:
    """Minimal adapter to normalize move selection + per-move telemetry."""

    def choose_move(
        self,
        board: Any,
        player: Player,
        legal_moves: List[Move],
        thinking_time_ms: Optional[int],
    ) -> Tuple[Optional[Move], Dict[str, Any]]:
        raise NotImplementedError


class _SelectActionAdapter(_ArenaAgentAdapter):
    def __init__(self, agent: Any):
        self.agent = agent

    def choose_move(
        self,
        board: Any,
        player: Player,
        legal_moves: List[Move],
        thinking_time_ms: Optional[int],
    ) -> Tuple[Optional[Move], Dict[str, Any]]:
        start = time.perf_counter()
        move = self.agent.select_action(board, player, legal_moves)
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        move_stats: Dict[str, Any] = {"timeSpentMs": elapsed_ms}
        if isinstance(self.agent, MCTSAgent):
            info = self.agent.get_action_info()
            mcts_stats = info.get("stats", {})
            if mcts_stats.get("iterations_run") is not None:
                move_stats["iterations_run"] = mcts_stats["iterations_run"]
            if mcts_stats.get("time_elapsed") is not None:
                move_stats["timeSpentMs"] = float(mcts_stats["time_elapsed"]) * 1000.0
        return move, move_stats


class _FastMCTSAdapter(_ArenaAgentAdapter):
    def __init__(
        self,
        agent: FastMCTSAgent,
        *,
        deterministic_time_budget: bool,
        iterations_per_ms: float,
    ):
        self.agent = agent
        self.deterministic_time_budget = deterministic_time_budget
        self.iterations_per_ms = iterations_per_ms

    def choose_move(
        self,
        board: Any,
        player: Player,
        legal_moves: List[Move],
        thinking_time_ms: Optional[int],
    ) -> Tuple[Optional[Move], Dict[str, Any]]:
        budget = int(thinking_time_ms or max(int(self.agent.time_limit * 1000), 1))
        if self.deterministic_time_budget:
            iteration_cap = max(1, int(round(self.iterations_per_ms * budget)))
            original_iterations = self.agent.iterations
            self.agent.iterations = iteration_cap
            try:
                result = self.agent.think(
                    board,
                    player,
                    legal_moves,
                    max(10_000_000, budget),
                )
            finally:
                self.agent.iterations = original_iterations
            stats = dict(result.get("stats") or {})
            stats["timeBudgetMs"] = budget
            stats["iterationCap"] = iteration_cap
            return result.get("move"), stats
        result = self.agent.think(board, player, legal_moves, budget)
        return result.get("move"), dict(result.get("stats") or {})


class _GameplayFastMCTSAdapter(_ArenaAgentAdapter):
    def __init__(
        self,
        agent: GameplayFastMCTSAgent,
        *,
        deterministic_time_budget: bool,
        iterations_per_ms: float,
    ):
        self.agent = agent
        self.deterministic_time_budget = deterministic_time_budget
        self.iterations_per_ms = iterations_per_ms

    def choose_move(
        self,
        board: Any,
        player: Player,
        legal_moves: List[Move],
        thinking_time_ms: Optional[int],
    ) -> Tuple[Optional[Move], Dict[str, Any]]:
        budget = int(thinking_time_ms or 1)
        if self.deterministic_time_budget:
            iteration_cap = max(1, int(round(self.iterations_per_ms * budget)))
            original_iterations = self.agent._agent.iterations
            self.agent._agent.iterations = iteration_cap
            try:
                move, stats = self.agent.choose_move(
                    board,
                    player,
                    legal_moves,
                    max(10_000_000, budget),
                )
            finally:
                self.agent._agent.iterations = original_iterations
            output_stats = dict(stats or {})
            output_stats["timeBudgetMs"] = budget
            output_stats["iterationCap"] = iteration_cap
            return move, output_stats
        move, stats = self.agent.choose_move(board, player, legal_moves, budget)
        return move, dict(stats or {})


def build_agent(config: AgentConfig, seed: int) -> _ArenaAgentAdapter:
    """Instantiate an agent adapter from configuration."""
    agent_type = config.type.lower()
    params = dict(config.params)

    if agent_type == "random":
        return _SelectActionAdapter(RandomAgent(seed=seed))

    if agent_type == "heuristic":
        agent = HeuristicAgent(seed=seed)
        weights = params.get("weights")
        if isinstance(weights, Mapping):
            agent.set_weights(dict(weights))
        return _SelectActionAdapter(agent)

    if agent_type == "mcts":
        deterministic_time_budget = bool(params.get("deterministic_time_budget", True))
        iterations_per_ms = float(params.get("iterations_per_ms", 10.0))
        iterations = int(params.get("iterations", 1000))
        time_limit = params.get("time_limit")
        if deterministic_time_budget and config.thinking_time_ms is not None:
            iterations = max(1, int(round(iterations_per_ms * config.thinking_time_ms)))
            time_limit = None
        elif time_limit is None and config.thinking_time_ms is not None:
            time_limit = float(config.thinking_time_ms) / 1000.0
        agent = MCTSAgent(
            iterations=iterations,
            time_limit=float(time_limit) if time_limit is not None else None,
            exploration_constant=float(params.get("exploration_constant", 1.414)),
            use_transposition_table=bool(params.get("use_transposition_table", True)),
            seed=seed,
        )
        return _SelectActionAdapter(agent)

    if agent_type == "fast_mcts":
        deterministic_time_budget = bool(params.get("deterministic_time_budget", True))
        iterations_per_ms = float(params.get("iterations_per_ms", 20.0))
        default_time = (
            float(config.thinking_time_ms) / 1000.0
            if config.thinking_time_ms is not None
            else float(params.get("time_limit", 0.1))
        )
        agent = FastMCTSAgent(
            iterations=int(params.get("iterations", 5000)),
            time_limit=default_time,
            exploration_constant=float(params.get("exploration_constant", 1.414)),
            seed=seed,
        )
        return _FastMCTSAdapter(
            agent,
            deterministic_time_budget=deterministic_time_budget,
            iterations_per_ms=iterations_per_ms,
        )

    if agent_type in {"gameplay_fast_mcts", "gameplay_mcts"}:
        deterministic_time_budget = bool(params.get("deterministic_time_budget", True))
        iterations_per_ms = float(params.get("iterations_per_ms", 20.0))
        agent = GameplayFastMCTSAgent(
            iterations=int(params.get("iterations", 5000)),
            exploration_constant=float(params.get("exploration_constant", 1.414)),
            seed=seed,
        )
        return _GameplayFastMCTSAdapter(
            agent,
            deterministic_time_budget=deterministic_time_budget,
            iterations_per_ms=iterations_per_ms,
        )

    raise ValueError(f"Unsupported agent type: {config.type}")


def _extract_move_telemetry(
    raw_stats: Mapping[str, Any],
    fallback_elapsed_ms: float,
) -> Tuple[float, Optional[float]]:
    time_spent_ms = raw_stats.get("timeSpentMs")
    if time_spent_ms is None and raw_stats.get("time_elapsed") is not None:
        time_spent_ms = float(raw_stats["time_elapsed"]) * 1000.0
    if time_spent_ms is None:
        time_spent_ms = fallback_elapsed_ms
    simulations = None
    for key in ("nodesEvaluated", "iterations_run", "simulations", "rollouts"):
        value = raw_stats.get(key)
        if value is not None:
            try:
                simulations = float(value)
                break
            except (TypeError, ValueError):
                continue
    return float(time_spent_ms), simulations


def _compute_ranks(scores_by_player: Mapping[str, int]) -> Dict[str, int]:
    unique_scores = sorted(set(scores_by_player.values()), reverse=True)
    score_to_rank = {score: rank + 1 for rank, score in enumerate(unique_scores)}
    return {player_id: score_to_rank[score] for player_id, score in scores_by_player.items()}


def run_single_game(
    *,
    run_id: str,
    game_index: int,
    game_seed: int,
    run_config: RunConfig,
    seat_assignment: Mapping[str, str],
    agent_configs: Mapping[str, AgentConfig],
) -> Dict[str, Any]:
    """Run one game and return a machine-readable game record."""
    random.seed(game_seed)
    np.random.seed(game_seed)
    game_id = f"{run_id}_g{game_index:04d}"
    start = time.perf_counter()

    agent_instances: Dict[str, _ArenaAgentAdapter] = {}
    for agent_name in set(seat_assignment.values()):
        config = agent_configs[agent_name]
        seed = _agent_seed(run_config.seed, game_index, agent_name)
        agent_instances[agent_name] = build_agent(config, seed=seed)

    per_agent_stats: Dict[str, Dict[str, float]] = {
        agent.name: {
            "moves": 0.0,
            "total_time_ms": 0.0,
            "total_simulations": 0.0,
            "moves_with_simulations": 0.0,
        }
        for agent in run_config.agents
    }

    game = BlokusGame()
    passes = 0
    invalid_actions = 0
    turn_count = 0
    truncated = False
    error: Optional[str] = None

    try:
        while not game.is_game_over() and turn_count < run_config.max_turns:
            current_player = game.get_current_player()
            player_id = str(current_player.value)
            agent_name = seat_assignment[player_id]
            agent_cfg = agent_configs[agent_name]
            agent = agent_instances[agent_name]
            legal_moves = game.get_legal_moves(current_player)

            turn_count += 1
            if not legal_moves:
                passes += 1
                game.board._update_current_player()
                game._check_game_over()
                continue

            move_start = time.perf_counter()
            move, raw_stats = agent.choose_move(
                game.board,
                current_player,
                legal_moves,
                agent_cfg.thinking_time_ms,
            )
            move_elapsed_ms = (time.perf_counter() - move_start) * 1000.0
            elapsed_ms, simulations = _extract_move_telemetry(raw_stats, move_elapsed_ms)
            stats_entry = per_agent_stats[agent_name]
            stats_entry["moves"] += 1
            stats_entry["total_time_ms"] += elapsed_ms
            if simulations is not None:
                stats_entry["total_simulations"] += simulations
                stats_entry["moves_with_simulations"] += 1

            if move is None:
                passes += 1
                game.board._update_current_player()
                game._check_game_over()
                continue

            if not game.make_move(move, current_player):
                invalid_actions += 1
                passes += 1
                game.board._update_current_player()
                game._check_game_over()
                continue
    except Exception as exc:
        error = str(exc)

    if turn_count >= run_config.max_turns and not game.is_game_over():
        truncated = True
        game.board.game_over = True

    game_result = game.get_game_result()
    scores_by_player = {str(player_id): int(score) for player_id, score in game_result.scores.items()}
    winner_ids = [int(player_id) for player_id in game_result.winner_ids]
    winner_agents = [seat_assignment[str(player_id)] for player_id in winner_ids]
    agent_scores = {
        seat_assignment[player_id]: score for player_id, score in scores_by_player.items()
    }
    agent_ranks = {
        seat_assignment[player_id]: rank
        for player_id, rank in _compute_ranks(scores_by_player).items()
    }

    duration_sec = time.perf_counter() - start
    for agent_name, stats_entry in per_agent_stats.items():
        moves = stats_entry["moves"]
        stats_entry["avg_time_ms"] = (
            stats_entry["total_time_ms"] / moves if moves > 0 else 0.0
        )
        if stats_entry["moves_with_simulations"] > 0:
            stats_entry["avg_simulations_per_move"] = (
                stats_entry["total_simulations"] / stats_entry["moves_with_simulations"]
            )
            total_time_s = stats_entry["total_time_ms"] / 1000.0
            stats_entry["simulations_per_second"] = (
                stats_entry["total_simulations"] / total_time_s if total_time_s > 0 else None
            )
        else:
            stats_entry["avg_simulations_per_move"] = None
            stats_entry["simulations_per_second"] = None
            stats_entry["total_simulations"] = None

    record = {
        "run_id": run_id,
        "game_id": game_id,
        "game_index": game_index,
        "game_seed": game_seed,
        "seat_assignment": dict(seat_assignment),
        "seat_policy": run_config.seat_policy,
        "winner_ids": winner_ids,
        "winner_agents": winner_agents,
        "is_tie": bool(game_result.is_tie),
        "final_scores": scores_by_player,
        "final_ranks": _compute_ranks(scores_by_player),
        "agent_scores": agent_scores,
        "agent_ranks": agent_ranks,
        "moves_made": int(game.board.move_count),
        "turn_count": int(turn_count),
        "passes": int(passes),
        "invalid_actions": int(invalid_actions),
        "duration_sec": float(duration_sec),
        "truncated": bool(truncated),
        "agent_move_stats": per_agent_stats,
        "error": error,
    }
    return record


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _append_index_row(
    *,
    output_root: Path,
    run_id: str,
    timestamp: str,
    run_config: RunConfig,
    completed_games: int,
) -> None:
    index_path = output_root / "index.csv"
    row = {
        "run_id": run_id,
        "timestamp": timestamp,
        "num_games": run_config.num_games,
        "completed_games": completed_games,
        "agents": "|".join(
            f"{agent.name}:{agent.type}:{agent.thinking_time_ms}" for agent in run_config.agents
        ),
        "seed": run_config.seed,
        "seat_policy": run_config.seat_policy,
        "notes": run_config.notes,
    }
    write_header = not index_path.exists()
    with index_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row.keys()))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def run_experiment(run_config: RunConfig, *, verbose: bool = False) -> Dict[str, Any]:
    """Run a full arena experiment and write all required artifacts."""
    run_id, run_dir = _prepare_run_directory(run_config)
    timestamp_iso = datetime.now().isoformat(timespec="seconds")
    run_config_payload = run_config.to_dict()
    run_config_payload["run_id"] = run_id
    run_config_payload["created_at"] = timestamp_iso

    _write_json(run_dir / "run_config.json", run_config_payload)

    games_path = run_dir / "games.jsonl"
    all_games: List[Dict[str, Any]] = []
    agent_configs = {agent.name: agent for agent in run_config.agents}
    with games_path.open("w", encoding="utf-8") as handle:
        for game_index in range(run_config.num_games):
            game_seed = game_seed_from_run_seed(run_config.seed, game_index)
            seat_assignment = _seat_assignment_for_game(
                run_config.agent_names,
                game_index,
                game_seed,
                run_config.seat_policy,
            )
            record = run_single_game(
                run_id=run_id,
                game_index=game_index,
                game_seed=game_seed,
                run_config=run_config,
                seat_assignment=seat_assignment,
                agent_configs=agent_configs,
            )
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            all_games.append(record)
            if verbose:
                winners = ",".join(record["winner_agents"])
                print(
                    f"[{game_index + 1}/{run_config.num_games}] "
                    f"seed={game_seed} winners={winners} scores={record['agent_scores']}"
                )

    summary = compute_summary(
        all_games,
        run_id=run_id,
        run_seed=run_config.seed,
        seat_policy=run_config.seat_policy,
        agent_names=run_config.agent_names,
        thinking_time_ms_by_agent={
            agent.name: agent.thinking_time_ms for agent in run_config.agents
        },
        run_config=run_config_payload,
    )
    _write_json(run_dir / "summary.json", summary)
    (run_dir / "summary.md").write_text(
        render_summary_markdown(summary),
        encoding="utf-8",
    )
    _append_index_row(
        output_root=Path(run_config.output_root),
        run_id=run_id,
        timestamp=timestamp_iso,
        run_config=run_config,
        completed_games=int(summary["completed_games"]),
    )

    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "summary": summary,
    }
