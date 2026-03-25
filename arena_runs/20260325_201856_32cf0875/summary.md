# Arena Run Summary: 20260325_201856_32cf0875

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `20/20` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_baseline`: win_rate=0.050, win_points=1.00, outright=1, shared=0
- `mcts_progressive_history`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `mcts_progressive_widening`: win_rate=0.650, win_points=13.00, outright=13, shared=0
- `mcts_pw_plus_ph`: win_rate=0.300, win_points=6.00, outright=6, shared=0

## Win Rates by Seat
- `mcts_baseline`: seat0: 0.000 (5 games), seat1: 0.000 (5 games), seat2: 0.200 (5 games), seat3: 0.000 (5 games)
- `mcts_progressive_history`: seat0: 0.000 (5 games), seat1: 0.000 (5 games), seat2: 0.000 (5 games), seat3: 0.000 (5 games)
- `mcts_progressive_widening`: seat0: 0.800 (5 games), seat1: 0.800 (5 games), seat2: 0.800 (5 games), seat3: 0.200 (5 games)
- `mcts_pw_plus_ph`: seat0: 0.200 (5 games), seat1: 0.600 (5 games), seat2: 0.200 (5 games), seat3: 0.200 (5 games)

## Score Stats
- `mcts_baseline`: mean=76.3, median=73.0, std=10.91833320612629, p25=70.75, p75=79.75, min=61.0, max=112.0
- `mcts_progressive_history`: mean=76.55, median=77.5, std=6.336205489092032, p25=74.5, p75=80.0, min=64.0, max=89.0
- `mcts_progressive_widening`: mean=92.8, median=94.0, std=6.297618597533516, p25=89.0, p75=96.5, min=79.0, max=103.0
- `mcts_pw_plus_ph`: mean=87.15, median=89.0, std=8.020442631176909, p25=80.25, p75=93.25, min=73.0, max=99.0

## Pairwise Matchups
- `mcts_baseline__vs__mcts_progressive_history`: mcts_baseline>mcts_progressive_history=8, mcts_progressive_history>mcts_baseline=12, tie=0 (total=20)
- `mcts_baseline__vs__mcts_progressive_widening`: mcts_baseline>mcts_progressive_widening=3, mcts_progressive_widening>mcts_baseline=17, tie=0 (total=20)
- `mcts_baseline__vs__mcts_pw_plus_ph`: mcts_baseline>mcts_pw_plus_ph=2, mcts_pw_plus_ph>mcts_baseline=17, tie=1 (total=20)
- `mcts_progressive_history__vs__mcts_progressive_widening`: mcts_progressive_history>mcts_progressive_widening=0, mcts_progressive_widening>mcts_progressive_history=20, tie=0 (total=20)
- `mcts_progressive_history__vs__mcts_pw_plus_ph`: mcts_progressive_history>mcts_pw_plus_ph=4, mcts_pw_plus_ph>mcts_progressive_history=16, tie=0 (total=20)
- `mcts_progressive_widening__vs__mcts_pw_plus_ph`: mcts_progressive_widening>mcts_pw_plus_ph=14, mcts_pw_plus_ph>mcts_progressive_widening=6, tie=0 (total=20)

## Time and Simulation Efficiency
- `mcts_baseline`: avg_time_ms=574.2022901211145, avg_sims_per_move=25.0, sims_per_sec=43.53866299405883, win_rate_per_sec=0.08707732598811765, score_per_sec=132.87999945786754
- `mcts_progressive_history`: avg_time_ms=561.979546868728, avg_sims_per_move=25.0, sims_per_sec=44.48560475073609, win_rate_per_sec=0.0, score_per_sec=136.2149217467539
- `mcts_progressive_widening`: avg_time_ms=552.012586060849, avg_sims_per_move=25.0, sims_per_sec=45.28882244950158, win_rate_per_sec=1.177509383687041, score_per_sec=168.11210893254986
- `mcts_pw_plus_ph`: avg_time_ms=590.6943901475654, avg_sims_per_move=25.0, sims_per_sec=42.3230699613629, win_rate_per_sec=0.5078768395363548, score_per_sec=147.53822188531106

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_progressive_widening` | 44.31 | 7.86 | **20.73** | 20 |
| 2 | `mcts_pw_plus_ph` | 33.57 | 7.73 | **10.36** | 20 |
| 3 | `mcts_progressive_history` | 12.74 | 7.55 | **-9.92** | 20 |
| 4 | `mcts_baseline` | 10.38 | 7.57 | **-12.34** | 20 |

## Score Margins (winner - last place)
- Mean: `24.7`, Median: `24.0`, Std: `8.79`, Range: `[13.0, 48.0]`

## Score by Seat Position
- `mcts_baseline`: P1: 72.6±1.33 (n=5), P2: 73.6±1.21 (n=5), P3: 89.4±6.31 (n=5), P4: 69.6±4.11 (n=5)
- `mcts_progressive_history`: P1: 75.6±3.47 (n=5), P2: 77.8±1.46 (n=5), P3: 81.0±2.49 (n=5), P4: 71.8±2.92 (n=5)
- `mcts_progressive_widening`: P1: 95.6±1.96 (n=5), P2: 92.8±2.56 (n=5), P3: 97.2±0.97 (n=5), P4: 85.6±2.93 (n=5)
- `mcts_pw_plus_ph`: P1: 91.2±2.08 (n=5), P2: 87.8±2.85 (n=5), P3: 90.8±4.14 (n=5), P4: 78.8±3.12 (n=5)
