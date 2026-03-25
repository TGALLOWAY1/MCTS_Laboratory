# Arena Run Summary: 20260325_182815_f28a2209

## Overview
- Seed: `20260325`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `baseline_d0_1000iter`: win_rate=0.040, win_points=1.00, outright=1, shared=0
- `random_d5_25iter`: win_rate=0.240, win_points=6.00, outright=6, shared=0
- `random_d5_25iter_alpha0.25`: win_rate=0.360, win_points=9.00, outright=9, shared=0
- `two_ply_all_d8_25iter`: win_rate=0.360, win_points=9.00, outright=9, shared=0

## Win Rates by Seat
- `baseline_d0_1000iter`: seat0: 0.000 (7 games), seat1: 0.167 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (6 games)
- `random_d5_25iter`: seat0: 0.667 (6 games), seat1: 0.000 (7 games), seat2: 0.333 (6 games), seat3: 0.000 (6 games)
- `random_d5_25iter_alpha0.25`: seat0: 0.000 (6 games), seat1: 0.333 (6 games), seat2: 1.000 (7 games), seat3: 0.000 (6 games)
- `two_ply_all_d8_25iter`: seat0: 0.500 (6 games), seat1: 1.000 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (7 games)

## Score Stats
- `baseline_d0_1000iter`: mean=70.92, median=71.0, std=1.4675149062275312, p25=70.0, p75=73.0, min=69.0, max=73.0
- `random_d5_25iter`: mean=72.2, median=69.0, std=7.4565407529229, p25=69.0, p75=73.0, min=62.0, max=90.0
- `random_d5_25iter_alpha0.25`: mean=70.88, median=73.0, std=3.1281943673627435, p25=71.0, p75=73.0, min=65.0, max=76.0
- `two_ply_all_d8_25iter`: mean=72.84, median=68.0, std=8.674929394525353, p25=66.0, p75=76.0, min=66.0, max=94.0

## Pairwise Matchups
- `baseline_d0_1000iter__vs__random_d5_25iter`: baseline_d0_1000iter>random_d5_25iter=14, random_d5_25iter>baseline_d0_1000iter=11, tie=0 (total=25)
- `baseline_d0_1000iter__vs__random_d5_25iter_alpha0.25`: baseline_d0_1000iter>random_d5_25iter_alpha0.25=12, random_d5_25iter_alpha0.25>baseline_d0_1000iter=13, tie=0 (total=25)
- `baseline_d0_1000iter__vs__two_ply_all_d8_25iter`: baseline_d0_1000iter>two_ply_all_d8_25iter=14, two_ply_all_d8_25iter>baseline_d0_1000iter=11, tie=0 (total=25)
- `random_d5_25iter__vs__random_d5_25iter_alpha0.25`: random_d5_25iter>random_d5_25iter_alpha0.25=10, random_d5_25iter_alpha0.25>random_d5_25iter=15, tie=0 (total=25)
- `random_d5_25iter__vs__two_ply_all_d8_25iter`: random_d5_25iter>two_ply_all_d8_25iter=15, two_ply_all_d8_25iter>random_d5_25iter=9, tie=1 (total=25)
- `random_d5_25iter_alpha0.25__vs__two_ply_all_d8_25iter`: random_d5_25iter_alpha0.25>two_ply_all_d8_25iter=13, two_ply_all_d8_25iter>random_d5_25iter_alpha0.25=12, tie=0 (total=25)

## Time and Simulation Efficiency
- `baseline_d0_1000iter`: avg_time_ms=3503.828806075615, avg_sims_per_move=1000.0, sims_per_sec=285.40207166115164, win_rate_per_sec=0.011416082866446065, score_per_sec=20.240714922208873
- `random_d5_25iter`: avg_time_ms=432.55521398682833, avg_sims_per_move=25.0, sims_per_sec=57.79608982071193, win_rate_per_sec=0.5548424622788345, score_per_sec=166.91510740221605
- `random_d5_25iter_alpha0.25`: avg_time_ms=440.8527761265851, avg_sims_per_move=25.0, sims_per_sec=56.70827394953633, win_rate_per_sec=0.8165991448733232, score_per_sec=160.7792983017254
- `two_ply_all_d8_25iter`: avg_time_ms=6294.832693937734, avg_sims_per_move=25.0, sims_per_sec=3.9715114309672375, win_rate_per_sec=0.05718976460592822, score_per_sec=11.571395705266145

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `baseline_d0_1000iter` | 31.22 | 7.43 | **8.92** | 25 |
| 2 | `random_d5_25iter_alpha0.25` | 26.89 | 7.55 | **4.25** | 25 |
| 3 | `random_d5_25iter` | 24.63 | 7.51 | **2.11** | 25 |
| 4 | `two_ply_all_d8_25iter` | 16.98 | 7.61 | **-5.84** | 25 |

## Score Margins (winner - last place)
- Mean: `12.52`, Median: `10.0`, Std: `7.58`, Range: `[5.0, 29.0]`

## Score by Seat Position
- `baseline_d0_1000iter`: P1: 71.0±0.0 (n=7), P2: 69.67±0.67 (n=6), P3: 73.0±0.0 (n=6), P4: 70.0±0.0 (n=6)
- `random_d5_25iter`: P1: 82.67±3.46 (n=6), P2: 69.0±0.0 (n=7), P3: 72.33±0.42 (n=6), P4: 65.33±0.67 (n=6)
- `random_d5_25iter_alpha0.25`: P1: 71.0±0.0 (n=6), P2: 73.5±0.5 (n=6), P3: 73.0±0.0 (n=7), P4: 65.67±0.21 (n=6)
- `two_ply_all_d8_25iter`: P1: 82.5±5.14 (n=6), P2: 76.0±0.0 (n=6), P3: 68.0±0.0 (n=6), P4: 66.0±0.0 (n=7)
