# Arena Run Summary: 20260325_033805_9b3944b6

## Overview
- Seed: `20260325`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_calibrated_d0`: win_rate=0.520, win_points=13.00, outright=13, shared=0
- `mcts_default_eval_d0`: win_rate=0.480, win_points=12.00, outright=12, shared=0
- `mcts_phase_eval_d0`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `mcts_phase_eval_rave_d0`: win_rate=0.000, win_points=0.00, outright=0, shared=0

## Win Rates by Seat
- `mcts_calibrated_d0`: seat0: 1.000 (7 games), seat1: 1.000 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (6 games)
- `mcts_default_eval_d0`: seat0: 1.000 (6 games), seat1: 1.000 (6 games), seat2: 0.000 (7 games), seat3: 0.000 (6 games)
- `mcts_phase_eval_d0`: seat0: 0.000 (6 games), seat1: 0.000 (7 games), seat2: 0.000 (6 games), seat3: 0.000 (6 games)
- `mcts_phase_eval_rave_d0`: seat0: 0.000 (6 games), seat1: 0.000 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (7 games)

## Score Stats
- `mcts_calibrated_d0`: mean=90.92, median=95.0, std=9.367689149411396, p25=90.0, p75=95.0, min=76.0, max=102.0
- `mcts_default_eval_d0`: mean=95.68, median=94.0, std=2.0341091416145787, p25=94.0, p75=96.0, min=94.0, max=99.0
- `mcts_phase_eval_d0`: mean=69.04, median=66.0, std=8.430800673720142, p25=58.0, p75=74.0, min=58.0, max=80.0
- `mcts_phase_eval_rave_d0`: mean=60.84, median=61.0, std=5.640425515863143, p25=58.0, p75=69.0, min=54.0, max=69.0

## Pairwise Matchups
- `mcts_calibrated_d0__vs__mcts_default_eval_d0`: mcts_calibrated_d0>mcts_default_eval_d0=13, mcts_default_eval_d0>mcts_calibrated_d0=12, tie=0 (total=25)
- `mcts_calibrated_d0__vs__mcts_phase_eval_d0`: mcts_calibrated_d0>mcts_phase_eval_d0=19, mcts_phase_eval_d0>mcts_calibrated_d0=6, tie=0 (total=25)
- `mcts_calibrated_d0__vs__mcts_phase_eval_rave_d0`: mcts_calibrated_d0>mcts_phase_eval_rave_d0=25, mcts_phase_eval_rave_d0>mcts_calibrated_d0=0, tie=0 (total=25)
- `mcts_default_eval_d0__vs__mcts_phase_eval_d0`: mcts_default_eval_d0>mcts_phase_eval_d0=25, mcts_phase_eval_d0>mcts_default_eval_d0=0, tie=0 (total=25)
- `mcts_default_eval_d0__vs__mcts_phase_eval_rave_d0`: mcts_default_eval_d0>mcts_phase_eval_rave_d0=25, mcts_phase_eval_rave_d0>mcts_default_eval_d0=0, tie=0 (total=25)
- `mcts_phase_eval_d0__vs__mcts_phase_eval_rave_d0`: mcts_phase_eval_d0>mcts_phase_eval_rave_d0=18, mcts_phase_eval_rave_d0>mcts_phase_eval_d0=7, tie=0 (total=25)

## Time and Simulation Efficiency
- `mcts_calibrated_d0`: avg_time_ms=2627.0137241441907, avg_sims_per_move=1000.0, sims_per_sec=380.6603638227176, win_rate_per_sec=0.19794338918781318, score_per_sec=34.60964027876149
- `mcts_default_eval_d0`: avg_time_ms=2433.3216924952644, avg_sims_per_move=1000.0, sims_per_sec=410.9608701077842, win_rate_per_sec=0.1972612176517364, score_per_sec=39.320736051912796
- `mcts_phase_eval_d0`: avg_time_ms=2425.2612449355042, avg_sims_per_move=1000.0, sims_per_sec=412.3267141171809, win_rate_per_sec=0.0, score_per_sec=28.467036342650175
- `mcts_phase_eval_rave_d0`: avg_time_ms=2737.0423520465506, avg_sims_per_move=1000.0, sims_per_sec=365.3578832100558, win_rate_per_sec=0.0, score_per_sec=22.228373614499795

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_default_eval_d0` | 45.97 | 7.72 | **22.80** | 25 |
| 2 | `mcts_calibrated_d0` | 41.19 | 7.68 | **18.16** | 25 |
| 3 | `mcts_phase_eval_d0` | 14.36 | 7.43 | **-7.93** | 25 |
| 4 | `mcts_phase_eval_rave_d0` | -0.16 | 7.46 | **-22.54** | 25 |

## Score Margins (winner - last place)
- Mean: `40.12`, Median: `38.0`, Std: `2.87`, Range: `[37.0, 44.0]`

## Score by Seat Position
- `mcts_calibrated_d0`: P1: 95.0±0.0 (n=7), P2: 102.0±0.0 (n=6), P3: 90.0±0.0 (n=6), P4: 76.0±0.0 (n=6)
- `mcts_default_eval_d0`: P1: 99.0±0.0 (n=6), P2: 96.0±0.0 (n=6), P3: 94.0±0.0 (n=7), P4: 94.0±0.0 (n=6)
- `mcts_phase_eval_d0`: P1: 80.0±0.0 (n=6), P2: 58.0±0.0 (n=7), P3: 74.0±0.0 (n=6), P4: 66.0±0.0 (n=6)
- `mcts_phase_eval_rave_d0`: P1: 58.0±0.0 (n=6), P2: 61.0±0.0 (n=6), P3: 54.0±0.0 (n=6), P4: 69.0±0.0 (n=7)
