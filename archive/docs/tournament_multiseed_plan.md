# Multi-Seed Tournament Implementation Plan

## Milestone 0: Audit Findings
After auditing the current state of output folders and stats entrypoints:
1. **Run Folder Schema**: We currently emit `tuning_config.json`, `matchups.json`, `summary.json`, `tuning_summary.json/md`, and `games.jsonl` for a single run inside `arena_runs/<run_id>/`.
2. **Stats Entrypoints**: `analytics/tournament/tuning_stats.py` currently holds `compute_tuning_summary` (which parses standard arena summary outputs to extract parameter-specific insights) and `wilson_score_interval` (which computes binomial CIs). We can repurpose or extract CI logic for aggregated testing.
3. **`games.jsonl` Schema**: A parsed row correctly outputs:
   - `winner_agents`
   - `final_ranks` (by seat, "1": 4)
   - `final_scores` (by seat, "1": 93)
   - `seat_assignment` (maps seat ID to tuning name)
   - `agent_move_stats` (contains full details including `total_time_ms`, `simulations`, etc.)
This means reading `games.jsonl` across all seed runs provides exactly what we need for pairwise comparisons (Milestone 3) and direct re-aggregation without intermediate data-loss (Milestone 2).

## Minimal Change Plan

### M1 - Multi-Seed Runner
- Modify `scripts/arena_tuning.py` to accept `--seeds` (comma separated list) or `--seed-start` and `--seed-count`.
- Loop through the seeds and invoke the core logic that currently creates a run directory per iteration.
- Output aggregate metadata into a central `arena_runs/...` meta folder containing pointers to each discrete seed folder.

### M2 - Aggregation
- Implement `analytics/tournament/aggregate.py` to parse an N-length list of `tuning_summary.json` outputs.
- Aggregate metrics: Simple means across seeds for win_rate, rank, score. 
- Use standard error/bootstrap over the N seeds to generate `win_rate_ci_95`. 
- Output `aggregate_summary.json` and `aggregate_summary.md`.

### M3 - Pairwise Dominance
- Walk `games.jsonl` for every seed and compute a standard W/L/T matrix.
- Extract `pairwise_wpct` (wins + 0.5*ties) / total.
- Append this field into the newly built `AggregateReport`.
- Optionally fit Bradley-Terry strengths if time permits using standard gradient descent or just report empirical odds.

### M4 & M5 - Adaptive Bias
- Edit `tuning.py` to parse an `adaptive_bias` object whose `params` are dynamically overwritten based on `AgentConfig.thinking_time_ms` prior to execution.
- Ensure resolved parameter traces to `tuning_config.json`.
- Execute benchmark arrays over 50, 200, and 400ms.
