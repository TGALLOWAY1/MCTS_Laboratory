# Arena Run Summary: 20260325_164033_3b30eeb2

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `alpha_0.0_d0_1000iter`: win_rate=0.240, win_points=6.00, outright=6, shared=0
- `alpha_0.1_d0_1000iter`: win_rate=0.280, win_points=7.00, outright=7, shared=0
- `alpha_0.25_d0_1000iter`: win_rate=0.240, win_points=6.00, outright=6, shared=0
- `alpha_0.5_d0_1000iter`: win_rate=0.240, win_points=6.00, outright=6, shared=0

## Win Rates by Seat
- `alpha_0.0_d0_1000iter`: seat0: 0.000 (7 games), seat1: 1.000 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (6 games)
- `alpha_0.1_d0_1000iter`: seat0: 0.000 (6 games), seat1: 1.000 (7 games), seat2: 0.000 (6 games), seat3: 0.000 (6 games)
- `alpha_0.25_d0_1000iter`: seat0: 0.000 (6 games), seat1: 1.000 (6 games), seat2: 0.000 (7 games), seat3: 0.000 (6 games)
- `alpha_0.5_d0_1000iter`: seat0: 0.000 (6 games), seat1: 1.000 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (7 games)

## Score Stats
- `alpha_0.0_d0_1000iter`: mean=69.32, median=71.0, std=2.9895819105687664, p25=68.0, p75=71.0, min=65.0, max=73.0
- `alpha_0.1_d0_1000iter`: mean=69.4, median=71.0, std=3.059411708155671, p25=68.0, p75=73.0, min=65.0, max=73.0
- `alpha_0.25_d0_1000iter`: mean=69.2, median=68.0, std=2.9799328851502676, p25=68.0, p75=71.0, min=65.0, max=73.0
- `alpha_0.5_d0_1000iter`: mean=69.08, median=68.0, std=3.0844124237851207, p25=65.0, p75=71.0, min=65.0, max=73.0

## Pairwise Matchups
- `alpha_0.0_d0_1000iter__vs__alpha_0.1_d0_1000iter`: alpha_0.0_d0_1000iter>alpha_0.1_d0_1000iter=12, alpha_0.1_d0_1000iter>alpha_0.0_d0_1000iter=13, tie=0 (total=25)
- `alpha_0.0_d0_1000iter__vs__alpha_0.25_d0_1000iter`: alpha_0.0_d0_1000iter>alpha_0.25_d0_1000iter=13, alpha_0.25_d0_1000iter>alpha_0.0_d0_1000iter=12, tie=0 (total=25)
- `alpha_0.0_d0_1000iter__vs__alpha_0.5_d0_1000iter`: alpha_0.0_d0_1000iter>alpha_0.5_d0_1000iter=13, alpha_0.5_d0_1000iter>alpha_0.0_d0_1000iter=12, tie=0 (total=25)
- `alpha_0.1_d0_1000iter__vs__alpha_0.25_d0_1000iter`: alpha_0.1_d0_1000iter>alpha_0.25_d0_1000iter=13, alpha_0.25_d0_1000iter>alpha_0.1_d0_1000iter=12, tie=0 (total=25)
- `alpha_0.1_d0_1000iter__vs__alpha_0.5_d0_1000iter`: alpha_0.1_d0_1000iter>alpha_0.5_d0_1000iter=13, alpha_0.5_d0_1000iter>alpha_0.1_d0_1000iter=12, tie=0 (total=25)
- `alpha_0.25_d0_1000iter__vs__alpha_0.5_d0_1000iter`: alpha_0.25_d0_1000iter>alpha_0.5_d0_1000iter=13, alpha_0.5_d0_1000iter>alpha_0.25_d0_1000iter=12, tie=0 (total=25)

## Time and Simulation Efficiency
- `alpha_0.0_d0_1000iter`: avg_time_ms=3642.6570196828898, avg_sims_per_move=1000.0, sims_per_sec=274.5248851584316, win_rate_per_sec=0.06588597243802358, score_per_sec=19.030065039182475
- `alpha_0.1_d0_1000iter`: avg_time_ms=3669.053903698216, avg_sims_per_move=1000.0, sims_per_sec=272.54982517211096, win_rate_per_sec=0.07631395104819108, score_per_sec=18.914957866944505
- `alpha_0.25_d0_1000iter`: avg_time_ms=3708.8194624299094, avg_sims_per_move=1000.0, sims_per_sec=269.62757560186805, win_rate_per_sec=0.06471061814444833, score_per_sec=18.658228231649268
- `alpha_0.5_d0_1000iter`: avg_time_ms=3692.0076474635557, avg_sims_per_move=1000.0, sims_per_sec=270.8553436196183, win_rate_per_sec=0.06500528246870839, score_per_sec=18.71068713724323

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `alpha_0.0_d0_1000iter` | 26.03 | 7.53 | **3.44** | 25 |
| 2 | `alpha_0.1_d0_1000iter` | 25.85 | 7.53 | **3.26** | 25 |
| 3 | `alpha_0.25_d0_1000iter` | 24.28 | 7.50 | **1.79** | 25 |
| 4 | `alpha_0.5_d0_1000iter` | 23.55 | 7.52 | **1.00** | 25 |

## Score Margins (winner - last place)
- Mean: `8.0`, Median: `8.0`, Std: `0.0`, Range: `[8.0, 8.0]`

## Score by Seat Position
- `alpha_0.0_d0_1000iter`: P1: 71.0±0.0 (n=7), P2: 73.0±0.0 (n=6), P3: 68.0±0.0 (n=6), P4: 65.0±0.0 (n=6)
- `alpha_0.1_d0_1000iter`: P1: 71.0±0.0 (n=6), P2: 73.0±0.0 (n=7), P3: 68.0±0.0 (n=6), P4: 65.0±0.0 (n=6)
- `alpha_0.25_d0_1000iter`: P1: 71.0±0.0 (n=6), P2: 73.0±0.0 (n=6), P3: 68.0±0.0 (n=7), P4: 65.0±0.0 (n=6)
- `alpha_0.5_d0_1000iter`: P1: 71.0±0.0 (n=6), P2: 73.0±0.0 (n=6), P3: 68.0±0.0 (n=6), P4: 65.0±0.0 (n=7)
