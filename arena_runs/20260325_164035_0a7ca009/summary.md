# Arena Run Summary: 20260325_164035_0a7ca009

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `cutoff_0_1000iter`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `cutoff_0_25iter`: win_rate=0.180, win_points=4.50, outright=2, shared=5
- `cutoff_10_25iter`: win_rate=0.280, win_points=7.00, outright=7, shared=0
- `cutoff_5_25iter`: win_rate=0.540, win_points=13.50, outright=11, shared=5

## Win Rates by Seat
- `cutoff_0_1000iter`: seat0: 0.000 (7 games), seat1: 0.000 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (6 games)
- `cutoff_0_25iter`: seat0: 0.000 (6 games), seat1: 0.643 (7 games), seat2: 0.000 (6 games), seat3: 0.000 (6 games)
- `cutoff_10_25iter`: seat0: 1.000 (6 games), seat1: 0.167 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (7 games)
- `cutoff_5_25iter`: seat0: 0.833 (6 games), seat1: 1.000 (6 games), seat2: 0.357 (7 games), seat3: 0.000 (6 games)

## Score Stats
- `cutoff_0_1000iter`: mean=70.76, median=71.0, std=1.449965516831349, p25=70.0, p75=71.0, min=69.0, max=73.0
- `cutoff_0_25iter`: mean=70.84, median=73.0, std=2.8380274840106816, p25=71.0, p75=73.0, min=66.0, max=73.0
- `cutoff_10_25iter`: mean=73.4, median=68.0, std=11.579291860904101, p25=66.0, p75=76.0, min=62.0, max=94.0
- `cutoff_5_25iter`: mean=75.2, median=73.0, std=9.842763839491425, p25=71.0, p75=73.0, min=64.0, max=94.0

## Pairwise Matchups
- `cutoff_0_1000iter__vs__cutoff_0_25iter`: cutoff_0_1000iter>cutoff_0_25iter=6, cutoff_0_25iter>cutoff_0_1000iter=19, tie=0 (total=25)
- `cutoff_0_1000iter__vs__cutoff_10_25iter`: cutoff_0_1000iter>cutoff_10_25iter=18, cutoff_10_25iter>cutoff_0_1000iter=7, tie=0 (total=25)
- `cutoff_0_1000iter__vs__cutoff_5_25iter`: cutoff_0_1000iter>cutoff_5_25iter=7, cutoff_5_25iter>cutoff_0_1000iter=16, tie=2 (total=25)
- `cutoff_0_25iter__vs__cutoff_10_25iter`: cutoff_0_25iter>cutoff_10_25iter=13, cutoff_10_25iter>cutoff_0_25iter=12, tie=0 (total=25)
- `cutoff_0_25iter__vs__cutoff_5_25iter`: cutoff_0_25iter>cutoff_5_25iter=8, cutoff_5_25iter>cutoff_0_25iter=12, tie=5 (total=25)
- `cutoff_10_25iter__vs__cutoff_5_25iter`: cutoff_10_25iter>cutoff_5_25iter=7, cutoff_5_25iter>cutoff_10_25iter=18, tie=0 (total=25)

## Time and Simulation Efficiency
- `cutoff_0_1000iter`: avg_time_ms=3519.1521099635534, avg_sims_per_move=1000.0, sims_per_sec=284.1593567861881, win_rate_per_sec=0.0, score_per_sec=20.107116086190672
- `cutoff_0_25iter`: avg_time_ms=94.86057485852923, avg_sims_per_move=25.0, sims_per_sec=263.5446816265226, win_rate_per_sec=1.8975217077109625, score_per_sec=746.7802098569144
- `cutoff_10_25iter`: avg_time_ms=6407.323567421881, avg_sims_per_move=25.0, sims_per_sec=3.9017851583323835, win_rate_per_sec=0.043699993773322704, score_per_sec=11.45564122486388
- `cutoff_5_25iter`: avg_time_ms=3254.014787521768, avg_sims_per_move=25.0, sims_per_sec=7.682816960718179, win_rate_per_sec=0.16594884635151266, score_per_sec=23.109913417840282

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `cutoff_0_25iter` | 29.72 | 7.61 | **6.89** | 25 |
| 2 | `cutoff_5_25iter` | 29.43 | 7.61 | **6.61** | 25 |
| 3 | `cutoff_0_1000iter` | 27.20 | 7.37 | **5.10** | 25 |
| 4 | `cutoff_10_25iter` | 13.46 | 7.53 | **-9.14** | 25 |

## Score Margins (winner - last place)
- Mean: `16.44`, Median: `11.0`, Std: `10.29`, Range: `[5.0, 30.0]`

## Score by Seat Position
- `cutoff_0_1000iter`: P1: 71.0±0.0 (n=7), P2: 69.0±0.0 (n=6), P3: 73.0±0.0 (n=6), P4: 70.0±0.0 (n=6)
- `cutoff_0_25iter`: P1: 71.0±0.0 (n=6), P2: 73.0±0.0 (n=7), P3: 73.0±0.0 (n=6), P4: 66.0±0.0 (n=6)
- `cutoff_10_25iter`: P1: 93.33±0.67 (n=6), P2: 70.17±1.17 (n=6), P3: 68.0±0.0 (n=6), P4: 63.71±0.68 (n=7)
- `cutoff_5_25iter`: P1: 90.17±3.83 (n=6), P2: 73.0±0.0 (n=6), P3: 72.43±0.37 (n=7), P4: 65.67±0.33 (n=6)
