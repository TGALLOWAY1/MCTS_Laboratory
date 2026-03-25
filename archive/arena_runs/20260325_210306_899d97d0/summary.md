# Arena Run Summary: 20260325_210306_899d97d0

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_rave_k100`: win_rate=0.120, win_points=3.00, outright=0, shared=6
- `mcts_rave_k1000`: win_rate=0.360, win_points=9.00, outright=6, shared=6
- `mcts_rave_k500`: win_rate=0.280, win_points=7.00, outright=4, shared=6
- `mcts_rave_k5000`: win_rate=0.240, win_points=6.00, outright=3, shared=6

## Win Rates by Seat
- `mcts_rave_k100`: seat0: 0.000 (7 games), seat1: 0.250 (6 games), seat2: 0.250 (6 games), seat3: 0.000 (6 games)
- `mcts_rave_k1000`: seat0: 0.500 (6 games), seat1: 0.250 (6 games), seat2: 0.643 (7 games), seat3: 0.000 (6 games)
- `mcts_rave_k500`: seat0: 0.167 (6 games), seat1: 0.357 (7 games), seat2: 0.583 (6 games), seat3: 0.000 (6 games)
- `mcts_rave_k5000`: seat0: 0.167 (6 games), seat1: 0.250 (6 games), seat2: 0.583 (6 games), seat3: 0.000 (7 games)

## Score Stats
- `mcts_rave_k100`: mean=69.44, median=69.0, std=3.371409200912877, p25=69.0, p75=73.0, min=62.0, max=73.0
- `mcts_rave_k1000`: mean=72.2, median=73.0, std=6.486909896090742, p25=69.0, p75=73.0, min=62.0, max=90.0
- `mcts_rave_k500`: mean=71.0, median=71.0, std=4.732863826479693, p25=69.0, p75=73.0, min=62.0, max=86.0
- `mcts_rave_k5000`: mean=70.88, median=72.0, std=5.163874514354508, p25=66.0, p75=73.0, min=62.0, max=90.0

## Pairwise Matchups
- `mcts_rave_k1000__vs__mcts_rave_k500`: mcts_rave_k1000>mcts_rave_k500=13, mcts_rave_k500>mcts_rave_k1000=8, tie=4 (total=25)
- `mcts_rave_k1000__vs__mcts_rave_k5000`: mcts_rave_k1000>mcts_rave_k5000=10, mcts_rave_k5000>mcts_rave_k1000=12, tie=3 (total=25)
- `mcts_rave_k100__vs__mcts_rave_k1000`: mcts_rave_k100>mcts_rave_k1000=9, mcts_rave_k1000>mcts_rave_k100=16, tie=0 (total=25)
- `mcts_rave_k100__vs__mcts_rave_k500`: mcts_rave_k100>mcts_rave_k500=7, mcts_rave_k500>mcts_rave_k100=15, tie=3 (total=25)
- `mcts_rave_k100__vs__mcts_rave_k5000`: mcts_rave_k100>mcts_rave_k5000=12, mcts_rave_k5000>mcts_rave_k100=10, tie=3 (total=25)
- `mcts_rave_k500__vs__mcts_rave_k5000`: mcts_rave_k500>mcts_rave_k5000=13, mcts_rave_k5000>mcts_rave_k500=12, tie=0 (total=25)

## Time and Simulation Efficiency
- `mcts_rave_k100`: avg_time_ms=436.97474759834813, avg_sims_per_move=25.0, sims_per_sec=57.21154400203264, win_rate_per_sec=0.27461541120975663, score_per_sec=158.91078462004586
- `mcts_rave_k1000`: avg_time_ms=408.97597604327734, avg_sims_per_move=25.0, sims_per_sec=61.12828494687554, win_rate_per_sec=0.8802473032350077, score_per_sec=176.53848692657655
- `mcts_rave_k500`: avg_time_ms=420.2115468003533, avg_sims_per_move=25.0, sims_per_sec=59.49384349468566, win_rate_per_sec=0.6663310471404795, score_per_sec=168.9625155249073
- `mcts_rave_k5000`: avg_time_ms=417.6012094725262, avg_sims_per_move=25.0, sims_per_sec=59.865726997241225, win_rate_per_sec=0.5747109791735158, score_per_sec=169.73130918257831

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_rave_k1000` | 27.25 | 7.56 | **4.56** | 25 |
| 2 | `mcts_rave_k500` | 26.70 | 7.55 | **4.06** | 25 |
| 3 | `mcts_rave_k5000` | 23.71 | 7.52 | **1.15** | 25 |
| 4 | `mcts_rave_k100` | 22.17 | 7.45 | **-0.18** | 25 |

## Score Margins (winner - last place)
- Mean: `11.28`, Median: `8.0`, Std: `6.22`, Range: `[7.0, 28.0]`

## Score by Seat Position
- `mcts_rave_k100`: P1: 69.0±0.0 (n=7), P2: 72.67±0.21 (n=6), P3: 71.83±0.54 (n=6), P4: 64.33±0.8 (n=6)
- `mcts_rave_k1000`: P1: 78.5±4.01 (n=6), P2: 72.17±0.4 (n=6), P3: 73.0±0.0 (n=7), P4: 65.0±0.63 (n=6)
- `mcts_rave_k500`: P1: 72.83±2.66 (n=6), P2: 73.29±0.99 (n=7), P3: 72.5±0.5 (n=6), P4: 65.0±0.63 (n=6)
- `mcts_rave_k5000`: P1: 73.5±3.32 (n=6), P2: 72.83±0.17 (n=6), P3: 73.0±0.0 (n=6), P4: 65.14±0.55 (n=7)
