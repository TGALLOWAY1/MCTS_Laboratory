# CLAUDE.md — Project Guidelines for Claude Code

## Agent Selection

- **Do NOT use `fast_mcts` (FastMCTSAgent / GameplayFastMCTSAgent) unless the user explicitly asks for it.**
  The fast_mcts agent uses a simplified rollout policy and lightweight node structure that trades accuracy for speed. Layer 2 analysis found that the evaluation function underperforms under the constrained search time of fast_mcts. Default to the full `mcts` agent type (MCTSAgent) for arena runs and testing.

- When creating new arena configs, prefer `"type": "mcts"` over `"type": "gameplay_fast_mcts"` or `"type": "fast_mcts"`.

## Running Arena Tests

```bash
# Standard arena run
python scripts/arena.py --config scripts/arena_config.json

# Extended rollout test (4x rollout, fewer games)
python scripts/arena.py --config scripts/arena_config_extended_rollout.json

# Smoke test with reduced games
python scripts/arena.py --config scripts/arena_config_extended_rollout.json --num-games 4
```

## Key MCTS Parameters

- `max_rollout_moves`: Controls rollout simulation length (default: 50). The extended rollout config uses 200 (4x).
- `iterations`: Max MCTS iterations per move (default: 1000 for full MCTS).
- `iterations_per_ms`: Conversion rate for deterministic time budgets (10.0 for full MCTS, 20.0 for fast_mcts).
- `exploration_constant`: UCB1 exploration parameter (default: 1.414).

## Project Structure

- `mcts/mcts_agent.py` — Full MCTSAgent with configurable rollout length
- `agents/fast_mcts_agent.py` — Lightweight FastMCTSAgent (use only when explicitly requested)
- `scripts/arena.py` — Arena CLI entry point
- `scripts/arena_config*.json` — Arena configuration files
- `analytics/tournament/arena_runner.py` — Arena harness and agent construction
