# Arena Run Summary: 20260325_210306_4024cab3

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_baseline_200ms`: win_rate=0.120, win_points=3.00, outright=1, shared=4
- `mcts_baseline_50ms`: win_rate=0.240, win_points=6.00, outright=5, shared=2
- `mcts_rave_200ms`: win_rate=0.280, win_points=7.00, outright=6, shared=2
- `mcts_rave_50ms`: win_rate=0.360, win_points=9.00, outright=7, shared=4

## Win Rates by Seat
- `mcts_baseline_200ms`: seat0: 0.167 (6 games), seat1: 0.000 (6 games), seat2: 0.286 (7 games), seat3: 0.000 (6 games)
- `mcts_baseline_50ms`: seat0: 0.286 (7 games), seat1: 0.167 (6 games), seat2: 0.500 (6 games), seat3: 0.000 (6 games)
- `mcts_rave_200ms`: seat0: 0.500 (6 games), seat1: 0.333 (6 games), seat2: 0.333 (6 games), seat3: 0.000 (7 games)
- `mcts_rave_50ms`: seat0: 0.667 (6 games), seat1: 0.429 (7 games), seat2: 0.333 (6 games), seat3: 0.000 (6 games)

## Score Stats
- `mcts_baseline_200ms`: mean=68.64, median=69.0, std=4.790657574905556, p25=67.0, p75=71.0, min=59.0, max=79.0
- `mcts_baseline_50ms`: mean=72.28, median=73.0, std=6.732131906016102, p25=69.0, p75=73.0, min=62.0, max=90.0
- `mcts_rave_200ms`: mean=72.84, median=73.0, std=7.4440849001069305, p25=66.0, p75=73.0, min=62.0, max=90.0
- `mcts_rave_50ms`: mean=74.44, median=73.0, std=8.366982729753898, p25=68.0, p75=77.0, min=62.0, max=94.0

## Pairwise Matchups
- `mcts_baseline_200ms__vs__mcts_baseline_50ms`: mcts_baseline_200ms>mcts_baseline_50ms=13, mcts_baseline_50ms>mcts_baseline_200ms=12, tie=0 (total=25)
- `mcts_baseline_200ms__vs__mcts_rave_200ms`: mcts_baseline_200ms>mcts_rave_200ms=8, mcts_rave_200ms>mcts_baseline_200ms=17, tie=0 (total=25)
- `mcts_baseline_200ms__vs__mcts_rave_50ms`: mcts_baseline_200ms>mcts_rave_50ms=6, mcts_rave_50ms>mcts_baseline_200ms=15, tie=4 (total=25)
- `mcts_baseline_50ms__vs__mcts_rave_200ms`: mcts_baseline_50ms>mcts_rave_200ms=12, mcts_rave_200ms>mcts_baseline_50ms=11, tie=2 (total=25)
- `mcts_baseline_50ms__vs__mcts_rave_50ms`: mcts_baseline_50ms>mcts_rave_50ms=10, mcts_rave_50ms>mcts_baseline_50ms=15, tie=0 (total=25)
- `mcts_rave_200ms__vs__mcts_rave_50ms`: mcts_rave_200ms>mcts_rave_50ms=12, mcts_rave_50ms>mcts_rave_200ms=13, tie=0 (total=25)

## Time and Simulation Efficiency
- `mcts_baseline_200ms`: avg_time_ms=875.1871213540659, avg_sims_per_move=50.0, sims_per_sec=57.130639585556686, win_rate_per_sec=0.13711353500533605, score_per_sec=78.42894202305223
- `mcts_baseline_50ms`: avg_time_ms=201.18266443966488, avg_sims_per_move=12.0, sims_per_sec=59.64728637739474, win_rate_per_sec=1.1929457275478947, score_per_sec=359.275488279841
- `mcts_rave_200ms`: avg_time_ms=802.7437987392896, avg_sims_per_move=50.0, sims_per_sec=62.286373408956976, win_rate_per_sec=0.34880369109015913, score_per_sec=90.73878878216853
- `mcts_rave_50ms`: avg_time_ms=192.80912729115013, avg_sims_per_move=12.0, sims_per_sec=62.23771752194843, win_rate_per_sec=1.8671315256584529, score_per_sec=386.0813076944868

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_rave_50ms` | 29.88 | 7.62 | **7.02** | 25 |
| 2 | `mcts_rave_200ms` | 26.15 | 7.58 | **3.42** | 25 |
| 3 | `mcts_baseline_50ms` | 24.04 | 7.49 | **1.57** | 25 |
| 4 | `mcts_baseline_200ms` | 19.84 | 7.40 | **-2.36** | 25 |

## Score Margins (winner - last place)
- Mean: `15.84`, Median: `13.0`, Std: `8.22`, Range: `[7.0, 28.0]`

## Score by Seat Position
- `mcts_baseline_200ms`: P1: 71.67±2.04 (n=6), P2: 69.0±0.0 (n=6), P3: 71.57±0.75 (n=7), P4: 61.83±1.01 (n=6)
- `mcts_baseline_50ms`: P1: 75.0±3.87 (n=7), P2: 75.67±1.58 (n=6), P3: 72.67±0.33 (n=6), P4: 65.33±0.67 (n=6)
- `mcts_rave_200ms`: P1: 79.17±3.53 (n=6), P2: 75.33±2.74 (n=6), P3: 73.67±0.42 (n=6), P4: 64.57±0.69 (n=7)
- `mcts_rave_50ms`: P1: 84.33±4.26 (n=6), P2: 73.0±0.0 (n=7), P3: 75.5±1.5 (n=6), P4: 65.17±0.65 (n=6)
