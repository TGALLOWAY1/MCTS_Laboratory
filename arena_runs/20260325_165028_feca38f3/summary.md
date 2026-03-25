# Arena Run Summary: 20260325_165028_feca38f3

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `heuristic_cutoff8_25iter`: win_rate=0.140, win_points=3.50, outright=3, shared=1
- `random_cutoff8_25iter`: win_rate=0.360, win_points=9.00, outright=7, shared=4
- `two_ply_all_cutoff8_25iter`: win_rate=0.340, win_points=8.50, outright=8, shared=1
- `two_ply_k10_cutoff8_25iter`: win_rate=0.160, win_points=4.00, outright=2, shared=4

## Win Rates by Seat
- `heuristic_cutoff8_25iter`: seat0: 0.500 (7 games), seat1: 0.000 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (6 games)
- `random_cutoff8_25iter`: seat0: 0.667 (6 games), seat1: 0.429 (7 games), seat2: 0.333 (6 games), seat3: 0.000 (6 games)
- `two_ply_all_cutoff8_25iter`: seat0: 1.000 (6 games), seat1: 0.333 (6 games), seat2: 0.071 (7 games), seat3: 0.000 (6 games)
- `two_ply_k10_cutoff8_25iter`: seat0: 0.667 (6 games), seat1: 0.000 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (7 games)

## Score Stats
- `heuristic_cutoff8_25iter`: mean=71.6, median=72.0, std=7.889233169326408, p25=70.0, p75=73.0, min=62.0, max=94.0
- `random_cutoff8_25iter`: mean=73.4, median=73.0, std=6.3999999999999995, p25=70.0, p75=75.0, min=65.0, max=86.0
- `two_ply_all_cutoff8_25iter`: mean=74.92, median=73.0, std=7.177297541554203, p25=70.0, p75=76.0, min=66.0, max=86.0
- `two_ply_k10_cutoff8_25iter`: mean=73.0, median=73.0, std=5.966573556070519, p25=66.0, p75=76.0, min=66.0, max=91.0

## Pairwise Matchups
- `heuristic_cutoff8_25iter__vs__random_cutoff8_25iter`: heuristic_cutoff8_25iter>random_cutoff8_25iter=11, random_cutoff8_25iter>heuristic_cutoff8_25iter=14, tie=0 (total=25)
- `heuristic_cutoff8_25iter__vs__two_ply_all_cutoff8_25iter`: heuristic_cutoff8_25iter>two_ply_all_cutoff8_25iter=9, two_ply_all_cutoff8_25iter>heuristic_cutoff8_25iter=12, tie=4 (total=25)
- `heuristic_cutoff8_25iter__vs__two_ply_k10_cutoff8_25iter`: heuristic_cutoff8_25iter>two_ply_k10_cutoff8_25iter=7, two_ply_k10_cutoff8_25iter>heuristic_cutoff8_25iter=18, tie=0 (total=25)
- `random_cutoff8_25iter__vs__two_ply_all_cutoff8_25iter`: random_cutoff8_25iter>two_ply_all_cutoff8_25iter=15, two_ply_all_cutoff8_25iter>random_cutoff8_25iter=10, tie=0 (total=25)
- `random_cutoff8_25iter__vs__two_ply_k10_cutoff8_25iter`: random_cutoff8_25iter>two_ply_k10_cutoff8_25iter=11, two_ply_k10_cutoff8_25iter>random_cutoff8_25iter=8, tie=6 (total=25)
- `two_ply_all_cutoff8_25iter__vs__two_ply_k10_cutoff8_25iter`: two_ply_all_cutoff8_25iter>two_ply_k10_cutoff8_25iter=19, two_ply_k10_cutoff8_25iter>two_ply_all_cutoff8_25iter=6, tie=0 (total=25)

## Time and Simulation Efficiency
- `heuristic_cutoff8_25iter`: avg_time_ms=5354.491398832893, avg_sims_per_move=25.0, sims_per_sec=4.668977525194867, win_rate_per_sec=0.026146274141091257, score_per_sec=13.371951632158098
- `random_cutoff8_25iter`: avg_time_ms=603.6876675882313, avg_sims_per_move=25.0, sims_per_sec=41.412142971011, win_rate_per_sec=0.5963348587825584, score_per_sec=121.5860517628883
- `two_ply_all_cutoff8_25iter`: avg_time_ms=6075.100329187181, avg_sims_per_move=25.0, sims_per_sec=4.115158375227176, win_rate_per_sec=0.05596615390308959, score_per_sec=12.3323066188808
- `two_ply_k10_cutoff8_25iter`: avg_time_ms=1815.5555333176703, avg_sims_per_move=25.0, sims_per_sec=13.769890009542172, win_rate_per_sec=0.0881272960610699, score_per_sec=40.20807882786315

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `random_cutoff8_25iter` | 27.16 | 7.56 | **4.48** | 25 |
| 2 | `two_ply_all_cutoff8_25iter` | 26.67 | 7.55 | **4.01** | 25 |
| 3 | `two_ply_k10_cutoff8_25iter` | 23.62 | 7.52 | **1.06** | 25 |
| 4 | `heuristic_cutoff8_25iter` | 22.24 | 7.45 | **-0.11** | 25 |

## Score Margins (winner - last place)
- Mean: `16.84`, Median: `20.0`, Std: `6.96`, Range: `[7.0, 28.0]`

## Score by Seat Position
- `heuristic_cutoff8_25iter`: P1: 79.86±3.45 (n=7), P2: 72.5±0.5 (n=6), P3: 70.67±0.49 (n=6), P4: 62.0±0.0 (n=6)
- `random_cutoff8_25iter`: P1: 81.67±2.74 (n=6), P2: 73.57±0.87 (n=7), P3: 72.5±0.5 (n=6), P4: 65.83±0.17 (n=6)
- `two_ply_all_cutoff8_25iter`: P1: 86.0±0.0 (n=6), P2: 76.0±0.0 (n=6), P3: 72.14±0.55 (n=7), P4: 66.0±0.0 (n=6)
- `two_ply_k10_cutoff8_25iter`: P1: 78.17±3.33 (n=6), P2: 76.0±0.0 (n=6), P3: 73.0±0.0 (n=6), P4: 66.0±0.0 (n=7)
