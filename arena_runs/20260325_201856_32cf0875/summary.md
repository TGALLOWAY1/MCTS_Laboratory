# Arena Run Summary: 20260325_201856_32cf0875

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_baseline`: win_rate=0.040, win_points=1.00, outright=1, shared=0
- `mcts_progressive_history`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `mcts_progressive_widening`: win_rate=0.640, win_points=16.00, outright=16, shared=0
- `mcts_pw_plus_ph`: win_rate=0.320, win_points=8.00, outright=8, shared=0

## Win Rates by Seat
- `mcts_baseline`: seat0: 0.000 (7 games), seat1: 0.000 (6 games), seat2: 0.167 (6 games), seat3: 0.000 (6 games)
- `mcts_progressive_history`: seat0: 0.000 (6 games), seat1: 0.000 (6 games), seat2: 0.000 (7 games), seat3: 0.000 (6 games)
- `mcts_progressive_widening`: seat0: 0.833 (6 games), seat1: 0.857 (7 games), seat2: 0.667 (6 games), seat3: 0.167 (6 games)
- `mcts_pw_plus_ph`: seat0: 0.333 (6 games), seat1: 0.667 (6 games), seat2: 0.167 (6 games), seat3: 0.143 (7 games)

## Score Stats
- `mcts_baseline`: mean=75.96, median=73.0, std=9.85689606316309, p25=71.0, p75=77.0, min=61.0, max=112.0
- `mcts_progressive_history`: mean=76.56, median=77.0, std=6.437887852393826, p25=73.0, p75=80.0, min=64.0, max=89.0
- `mcts_progressive_widening`: mean=92.4, median=94.0, std=6.013318551349163, p25=89.0, p75=96.0, min=79.0, max=103.0
- `mcts_pw_plus_ph`: mean=87.24, median=88.0, std=8.636110235516913, p25=81.0, p75=94.0, min=72.0, max=102.0

## Pairwise Matchups
- `mcts_baseline__vs__mcts_progressive_history`: mcts_baseline>mcts_progressive_history=10, mcts_progressive_history>mcts_baseline=14, tie=1 (total=25)
- `mcts_baseline__vs__mcts_progressive_widening`: mcts_baseline>mcts_progressive_widening=3, mcts_progressive_widening>mcts_baseline=22, tie=0 (total=25)
- `mcts_baseline__vs__mcts_pw_plus_ph`: mcts_baseline>mcts_pw_plus_ph=3, mcts_pw_plus_ph>mcts_baseline=21, tie=1 (total=25)
- `mcts_progressive_history__vs__mcts_progressive_widening`: mcts_progressive_history>mcts_progressive_widening=0, mcts_progressive_widening>mcts_progressive_history=25, tie=0 (total=25)
- `mcts_progressive_history__vs__mcts_pw_plus_ph`: mcts_progressive_history>mcts_pw_plus_ph=6, mcts_pw_plus_ph>mcts_progressive_history=19, tie=0 (total=25)
- `mcts_progressive_widening__vs__mcts_pw_plus_ph`: mcts_progressive_widening>mcts_pw_plus_ph=17, mcts_pw_plus_ph>mcts_progressive_widening=8, tie=0 (total=25)

## Time and Simulation Efficiency
- `mcts_baseline`: avg_time_ms=574.9411366748569, avg_sims_per_move=25.0, sims_per_sec=43.48271223831058, win_rate_per_sec=0.06957233958129694, score_per_sec=132.11787286488288
- `mcts_progressive_history`: avg_time_ms=564.0296654160974, avg_sims_per_move=25.0, sims_per_sec=44.32390977442106, win_rate_per_sec=0.0, score_per_sec=135.73754129318706
- `mcts_progressive_widening`: avg_time_ms=553.5216411847747, avg_sims_per_move=25.0, sims_per_sec=45.165352426852245, win_rate_per_sec=1.1562330221274175, score_per_sec=166.9311425696459
- `mcts_pw_plus_ph`: avg_time_ms=587.4507524412599, avg_sims_per_move=25.0, sims_per_sec=42.55675883656271, win_rate_per_sec=0.5447265131080027, score_per_sec=148.50606563606922

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_progressive_widening` | 47.51 | 7.75 | **24.25** | 25 |
| 2 | `mcts_pw_plus_ph` | 32.70 | 7.60 | **9.90** | 25 |
| 3 | `mcts_baseline` | 10.88 | 7.43 | **-11.41** | 25 |
| 4 | `mcts_progressive_history` | 10.09 | 7.43 | **-12.21** | 25 |

## Score Margins (winner - last place)
- Mean: `24.48`, Median: `23.0`, Std: `8.29`, Range: `[13.0, 48.0]`

## Score by Seat Position
- `mcts_baseline`: P1: 72.43±1.02 (n=7), P2: 73.83±1.01 (n=6), P3: 87.33±5.55 (n=6), P4: 70.83±3.57 (n=6)
- `mcts_progressive_history`: P1: 74.33±3.11 (n=6), P2: 76.67±1.65 (n=6), P3: 82.0±1.84 (n=7), P4: 72.33±2.44 (n=6)
- `mcts_progressive_widening`: P1: 95.33±1.63 (n=6), P2: 92.14±2.06 (n=7), P3: 96.67±0.95 (n=6), P4: 85.5±2.39 (n=6)
- `mcts_pw_plus_ph`: P1: 92.17±1.96 (n=6), P2: 90.17±3.32 (n=6), P3: 89.83±3.52 (n=6), P4: 78.29±2.44 (n=7)
