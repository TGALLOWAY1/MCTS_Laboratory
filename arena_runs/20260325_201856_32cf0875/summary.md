# Arena Run Summary: 20260325_201856_32cf0875

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `15/15` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_baseline`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `mcts_progressive_history`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `mcts_progressive_widening`: win_rate=0.667, win_points=10.00, outright=10, shared=0
- `mcts_pw_plus_ph`: win_rate=0.333, win_points=5.00, outright=5, shared=0

## Win Rates by Seat
- `mcts_baseline`: seat0: 0.000 (4 games), seat1: 0.000 (3 games), seat2: 0.000 (4 games), seat3: 0.000 (4 games)
- `mcts_progressive_history`: seat0: 0.000 (4 games), seat1: 0.000 (4 games), seat2: 0.000 (4 games), seat3: 0.000 (3 games)
- `mcts_progressive_widening`: seat0: 0.750 (4 games), seat1: 1.000 (4 games), seat2: 0.667 (3 games), seat3: 0.250 (4 games)
- `mcts_pw_plus_ph`: seat0: 0.333 (3 games), seat1: 0.750 (4 games), seat2: 0.250 (4 games), seat3: 0.000 (4 games)

## Score Stats
- `mcts_baseline`: mean=73.86666666666666, median=73.0, std=7.6756469144662685, p25=70.5, p75=75.0, min=61.0, max=88.0
- `mcts_progressive_history`: mean=77.53333333333333, median=78.0, std=6.042810236599818, p25=75.5, p75=80.5, min=64.0, max=89.0
- `mcts_progressive_widening`: mean=92.4, median=94.0, std=6.9550940563973205, p25=88.0, p75=97.0, min=79.0, max=103.0
- `mcts_pw_plus_ph`: mean=86.86666666666666, median=91.0, std=9.076465293396005, p25=77.5, p75=94.0, min=73.0, max=99.0

## Pairwise Matchups
- `mcts_baseline__vs__mcts_progressive_history`: mcts_baseline>mcts_progressive_history=5, mcts_progressive_history>mcts_baseline=10, tie=0 (total=15)
- `mcts_baseline__vs__mcts_progressive_widening`: mcts_baseline>mcts_progressive_widening=2, mcts_progressive_widening>mcts_baseline=13, tie=0 (total=15)
- `mcts_baseline__vs__mcts_pw_plus_ph`: mcts_baseline>mcts_pw_plus_ph=1, mcts_pw_plus_ph>mcts_baseline=13, tie=1 (total=15)
- `mcts_progressive_history__vs__mcts_progressive_widening`: mcts_progressive_history>mcts_progressive_widening=0, mcts_progressive_widening>mcts_progressive_history=15, tie=0 (total=15)
- `mcts_progressive_history__vs__mcts_pw_plus_ph`: mcts_progressive_history>mcts_pw_plus_ph=4, mcts_pw_plus_ph>mcts_progressive_history=11, tie=0 (total=15)
- `mcts_progressive_widening__vs__mcts_pw_plus_ph`: mcts_progressive_widening>mcts_pw_plus_ph=10, mcts_pw_plus_ph>mcts_progressive_widening=5, tie=0 (total=15)

## Time and Simulation Efficiency
- `mcts_baseline`: avg_time_ms=593.9609724542369, avg_sims_per_move=25.0, sims_per_sec=42.090307544450965, win_rate_per_sec=0.0, score_per_sec=124.36282869133778
- `mcts_progressive_history`: avg_time_ms=553.2853949454523, avg_sims_per_move=25.0, sims_per_sec=45.18463749158735, win_rate_per_sec=0.0, score_per_sec=140.1326224072429
- `mcts_progressive_widening`: avg_time_ms=560.2432781795286, avg_sims_per_move=25.0, sims_per_sec=44.62347157691165, win_rate_per_sec=1.1899592420509773, score_per_sec=164.92835094826546
- `mcts_pw_plus_ph`: avg_time_ms=588.6147098847662, avg_sims_per_move=25.0, sims_per_sec=42.47260488086389, win_rate_per_sec=0.5663013984115185, score_per_sec=147.57814442604172

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_progressive_widening` | 40.13 | 7.97 | **16.21** | 15 |
| 2 | `mcts_pw_plus_ph` | 31.38 | 7.88 | **7.75** | 15 |
| 3 | `mcts_progressive_history` | 17.78 | 7.72 | **-5.39** | 15 |
| 4 | `mcts_baseline` | 11.34 | 7.71 | **-11.78** | 15 |

## Score Margins (winner - last place)
- Mean: `24.0`, Median: `25.0`, Std: `7.75`, Range: `[13.0, 37.0]`

## Score by Seat Position
- `mcts_baseline`: P1: 73.5±1.26 (n=4), P2: 72.0±0.58 (n=3), P3: 83.75±3.61 (n=4), P4: 65.75±1.84 (n=4)
- `mcts_progressive_history`: P1: 78.5±2.47 (n=4), P2: 78.5±1.66 (n=4), P3: 81.25±3.2 (n=4), P4: 70.0±3.79 (n=3)
- `mcts_progressive_widening`: P1: 96.5±2.25 (n=4), P2: 93.75±3.07 (n=4), P3: 97.0±1.53 (n=3), P4: 83.5±2.63 (n=4)
- `mcts_pw_plus_ph`: P1: 92.33±2.96 (n=3), P2: 88.5±3.57 (n=4), P3: 92.0±5.12 (n=4), P4: 76.0±1.78 (n=4)
