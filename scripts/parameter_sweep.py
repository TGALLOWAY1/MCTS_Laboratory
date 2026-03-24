#!/usr/bin/env python3
"""
Parameter Sweep Runner — automated parameter grid search for MCTS variants.

Runs arena tournaments across parameter values and aggregates results
for visualization in the MCTS Visualization Platform.

Usage:
    # Sweep exploration constant
    python scripts/parameter_sweep.py \
        --param exploration_constant \
        --values 0.5,1.0,1.414,2.0,3.0 \
        --games 20

    # Sweep rollout depth
    python scripts/parameter_sweep.py \
        --param rollout_cutoff_depth \
        --values 5,10,20,50 \
        --games 20

    # Sweep with custom base config
    python scripts/parameter_sweep.py \
        --param rave_k \
        --values 100,500,1000,5000 \
        --games 20 \
        --base-config scripts/arena_config.json

Output:
    data/sweeps/<sweep_id>/results.json
"""

import argparse
import copy
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics.tournament.arena_runner import AgentConfig, RunConfig, run_experiment


@dataclass
class SweepResult:
    """Results for a single parameter value."""
    parameter_value: Any
    win_rate: float
    avg_rank: float
    avg_score: float
    avg_iterations: float
    avg_tree_size: float
    avg_depth_max: float
    games_played: int


@dataclass
class SweepSummary:
    """Full sweep results."""
    sweep_id: str
    parameter_name: str
    parameter_values: List[Any]
    results: List[SweepResult]
    base_agent_name: str
    opponents: List[str]
    games_per_value: int
    seed: int
    timestamp: str
    elapsed_seconds: float


def parse_value(s: str) -> Any:
    """Parse a parameter value string to appropriate type."""
    s = s.strip()
    if s.lower() == 'true':
        return True
    if s.lower() == 'false':
        return False
    if s.lower() == 'none':
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def build_sweep_config(
    base_config: Dict[str, Any],
    param_name: str,
    param_value: Any,
    agent_index: int = 0,
) -> Dict[str, Any]:
    """Create a config dict with the sweep parameter overridden."""
    config = copy.deepcopy(base_config)
    agent = config["agents"][agent_index]

    # Support nested params like "params.exploration_constant"
    if "." in param_name:
        parts = param_name.split(".")
        obj = agent
        for part in parts[:-1]:
            obj = obj.setdefault(part, {})
        obj[parts[-1]] = param_value
    elif param_name in ("thinking_time_ms", "name", "type"):
        agent[param_name] = param_value
    else:
        agent.setdefault("params", {})[param_name] = param_value

    # Update agent name to reflect sweep
    agent["name"] = f"{agent.get('name', 'sweep')}_{param_name}={param_value}"
    return config


def run_sweep(
    base_config_path: str,
    param_name: str,
    values: List[Any],
    games_per_value: int,
    seed: int = 42,
    output_dir: Optional[str] = None,
    agent_index: int = 0,
) -> SweepSummary:
    """Run parameter sweep and return aggregated results."""
    with open(base_config_path) as f:
        base_config = json.load(f)

    sweep_id = f"sweep_{param_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if output_dir is None:
        output_dir = f"data/sweeps/{sweep_id}"
    os.makedirs(output_dir, exist_ok=True)

    base_agent_name = base_config["agents"][agent_index].get("name", "agent_0")
    opponent_names = [
        a.get("name", f"agent_{i}")
        for i, a in enumerate(base_config["agents"])
        if i != agent_index
    ]

    results: List[SweepResult] = []
    start_time = time.time()

    for val_idx, value in enumerate(values):
        print(f"\n{'='*60}")
        print(f"Sweep {val_idx + 1}/{len(values)}: {param_name} = {value}")
        print(f"{'='*60}")

        config = build_sweep_config(base_config, param_name, value, agent_index)
        config["num_games"] = games_per_value
        config["seed"] = seed + val_idx * 1000

        # Build RunConfig
        agents = [
            AgentConfig(
                name=a.get("name", f"agent_{i}"),
                type=a.get("type", "mcts"),
                thinking_time_ms=a.get("thinking_time_ms"),
                params=a.get("params", {}),
            )
            for i, a in enumerate(config["agents"])
        ]
        run_config = RunConfig(
            agents=agents,
            num_games=games_per_value,
            seed=config["seed"],
            seat_policy=config.get("seat_policy", "round_robin"),
        )

        # Run the experiment
        val_output = os.path.join(output_dir, f"value_{val_idx}")
        os.makedirs(val_output, exist_ok=True)

        try:
            summary = run_experiment(run_config, output_root=val_output)
        except Exception as e:
            print(f"ERROR running value {value}: {e}")
            results.append(SweepResult(
                parameter_value=value,
                win_rate=0.0, avg_rank=0.0, avg_score=0.0,
                avg_iterations=0.0, avg_tree_size=0.0, avg_depth_max=0.0,
                games_played=0,
            ))
            continue

        # Extract metrics for the sweep agent
        sweep_agent_name = config["agents"][agent_index]["name"]
        agent_stats = summary.get("agent_stats", {}).get(sweep_agent_name, {})

        results.append(SweepResult(
            parameter_value=value,
            win_rate=agent_stats.get("win_rate", 0.0),
            avg_rank=agent_stats.get("avg_rank", 0.0),
            avg_score=agent_stats.get("avg_score", 0.0),
            avg_iterations=agent_stats.get("avg_iterations", 0.0),
            avg_tree_size=agent_stats.get("avg_tree_size", 0.0),
            avg_depth_max=agent_stats.get("avg_depth_max", 0.0),
            games_played=games_per_value,
        ))

        print(f"  win_rate={results[-1].win_rate:.3f}, "
              f"avg_rank={results[-1].avg_rank:.2f}, "
              f"avg_score={results[-1].avg_score:.1f}")

    elapsed = time.time() - start_time
    sweep_summary = SweepSummary(
        sweep_id=sweep_id,
        parameter_name=param_name,
        parameter_values=values,
        results=results,
        base_agent_name=base_agent_name,
        opponents=opponent_names,
        games_per_value=games_per_value,
        seed=seed,
        timestamp=datetime.now().isoformat(),
        elapsed_seconds=round(elapsed, 1),
    )

    # Save results
    results_path = os.path.join(output_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(asdict(sweep_summary), f, indent=2)
    print(f"\nSweep results saved to {results_path}")

    return sweep_summary


def main():
    parser = argparse.ArgumentParser(description="MCTS Parameter Sweep Runner")
    parser.add_argument("--param", required=True, help="Parameter to sweep (e.g. exploration_constant)")
    parser.add_argument("--values", required=True, help="Comma-separated values to try")
    parser.add_argument("--games", type=int, default=20, help="Games per parameter value")
    parser.add_argument("--seed", type=int, default=42, help="Base random seed")
    parser.add_argument("--base-config", default="scripts/arena_config.json", help="Base arena config")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--agent-index", type=int, default=0, help="Index of agent to sweep (0-3)")
    args = parser.parse_args()

    values = [parse_value(v) for v in args.values.split(",")]
    print(f"Parameter sweep: {args.param}")
    print(f"Values: {values}")
    print(f"Games per value: {args.games}")

    summary = run_sweep(
        base_config_path=args.base_config,
        param_name=args.param,
        values=values,
        games_per_value=args.games,
        seed=args.seed,
        output_dir=args.output,
        agent_index=args.agent_index,
    )

    # Print summary table
    print(f"\n{'='*70}")
    print(f"SWEEP COMPLETE: {args.param}")
    print(f"{'='*70}")
    print(f"{'Value':>12} {'Win Rate':>10} {'Avg Rank':>10} {'Avg Score':>10}")
    print(f"{'-'*12} {'-'*10} {'-'*10} {'-'*10}")
    for r in summary.results:
        print(f"{str(r.parameter_value):>12} {r.win_rate:>10.3f} {r.avg_rank:>10.2f} {r.avg_score:>10.1f}")


if __name__ == "__main__":
    main()
