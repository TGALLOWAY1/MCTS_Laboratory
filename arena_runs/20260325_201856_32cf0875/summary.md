# Arena Run Summary: 20260325_201856_32cf0875

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `5/5` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_baseline`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `mcts_progressive_history`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `mcts_progressive_widening`: win_rate=0.800, win_points=4.00, outright=4, shared=0
- `mcts_pw_plus_ph`: win_rate=0.200, win_points=1.00, outright=1, shared=0

## Win Rates by Seat
- `mcts_baseline`: seat0: 0.000 (2 games), seat1: 0.000 (1 games), seat2: 0.000 (1 games), seat3: 0.000 (1 games)
- `mcts_progressive_history`: seat0: 0.000 (1 games), seat1: 0.000 (1 games), seat2: 0.000 (2 games), seat3: 0.000 (1 games)
- `mcts_progressive_widening`: seat0: 1.000 (1 games), seat1: 1.000 (2 games), seat2: 1.000 (1 games), seat3: 0.000 (1 games)
- `mcts_pw_plus_ph`: seat0: 0.000 (1 games), seat1: 1.000 (1 games), seat2: 0.000 (1 games), seat3: 0.000 (2 games)

## Score Stats
- `mcts_baseline`: mean=75.0, median=73.0, std=6.54217089351845, p25=73.0, p75=77.0, min=66.0, max=86.0
- `mcts_progressive_history`: mean=77.6, median=77.0, std=3.6110940170535577, p25=76.0, p75=78.0, min=73.0, max=84.0
- `mcts_progressive_widening`: mean=95.6, median=96.0, std=4.029888335921977, p25=94.0, p75=98.0, min=89.0, max=101.0
- `mcts_pw_plus_ph`: mean=84.4, median=88.0, std=8.357032966310472, p25=76.0, p75=91.0, min=73.0, max=94.0

## Pairwise Matchups
- `mcts_baseline__vs__mcts_progressive_history`: mcts_baseline>mcts_progressive_history=1, mcts_progressive_history>mcts_baseline=4, tie=0 (total=5)
- `mcts_baseline__vs__mcts_progressive_widening`: mcts_baseline>mcts_progressive_widening=0, mcts_progressive_widening>mcts_baseline=5, tie=0 (total=5)
- `mcts_baseline__vs__mcts_pw_plus_ph`: mcts_baseline>mcts_pw_plus_ph=1, mcts_pw_plus_ph>mcts_baseline=3, tie=1 (total=5)
- `mcts_progressive_history__vs__mcts_progressive_widening`: mcts_progressive_history>mcts_progressive_widening=0, mcts_progressive_widening>mcts_progressive_history=5, tie=0 (total=5)
- `mcts_progressive_history__vs__mcts_pw_plus_ph`: mcts_progressive_history>mcts_pw_plus_ph=2, mcts_pw_plus_ph>mcts_progressive_history=3, tie=0 (total=5)
- `mcts_progressive_widening__vs__mcts_pw_plus_ph`: mcts_progressive_widening>mcts_pw_plus_ph=4, mcts_pw_plus_ph>mcts_progressive_widening=1, tie=0 (total=5)

## Time and Simulation Efficiency
- `mcts_baseline`: avg_time_ms=608.3829433887036, avg_sims_per_move=25.0, sims_per_sec=41.09253928249461, win_rate_per_sec=0.0, score_per_sec=123.27761784748385
- `mcts_progressive_history`: avg_time_ms=568.4475520762002, avg_sims_per_move=25.0, sims_per_sec=43.9794311870812, win_rate_per_sec=0.0, score_per_sec=136.51215440470003
- `mcts_progressive_widening`: avg_time_ms=548.4554612118264, avg_sims_per_move=25.0, sims_per_sec=45.5825527651085, win_rate_per_sec=1.4586416884834723, score_per_sec=174.30768177377493
- `mcts_pw_plus_ph`: avg_time_ms=616.8206856574541, avg_sims_per_move=25.0, sims_per_sec=40.530417642127404, win_rate_per_sec=0.32424334113701925, score_per_sec=136.83068995982214

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_progressive_widening` | 32.48 | 8.24 | **7.75** | 5 |
| 2 | `mcts_progressive_history` | 23.97 | 8.11 | **-0.36** | 5 |
| 3 | `mcts_pw_plus_ph` | 23.52 | 8.15 | **-0.93** | 5 |
| 4 | `mcts_baseline` | 20.12 | 8.08 | **-4.11** | 5 |

## Score Margins (winner - last place)
- Mean: `23.8`, Median: `25.0`, Std: `4.07`, Range: `[18.0, 30.0]`

## Score by Seat Position
- `mcts_baseline`: P1: 75.0±2.0 (n=2), P2: 73.0±0.0 (n=1), P3: 86.0±0.0 (n=1), P4: 66.0±0.0 (n=1)
- `mcts_progressive_history`: P1: 73.0±0.0 (n=1), P2: 78.0±0.0 (n=1), P3: 80.0±4.0 (n=2), P4: 77.0±0.0 (n=1)
- `mcts_progressive_widening`: P1: 96.0±0.0 (n=1), P2: 97.5±3.5 (n=2), P3: 98.0±0.0 (n=1), P4: 89.0±0.0 (n=1)
- `mcts_pw_plus_ph`: P1: 88.0±0.0 (n=1), P2: 91.0±0.0 (n=1), P3: 94.0±0.0 (n=1), P4: 74.5±1.5 (n=2)
