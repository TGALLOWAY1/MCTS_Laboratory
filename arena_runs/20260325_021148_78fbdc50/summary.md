# Arena Run Summary: 20260325_021148_78fbdc50

## Overview
- Seed: `20260325`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_baseline_d0`: win_rate=0.120, win_points=3.00, outright=0, shared=6
- `mcts_calibrated_eval_d0`: win_rate=0.760, win_points=19.00, outright=19, shared=0
- `mcts_calibrated_eval_d5`: win_rate=0.000, win_points=0.00, outright=0, shared=0
- `mcts_default_eval_d0`: win_rate=0.120, win_points=3.00, outright=0, shared=6

## Win Rates by Seat
- `mcts_baseline_d0`: seat0: 0.000 (6 games), seat1: 0.500 (6 games), seat2: 0.000 (6 games), seat3: 0.000 (7 games)
- `mcts_calibrated_eval_d0`: seat0: 1.000 (6 games), seat1: 1.000 (7 games), seat2: 1.000 (6 games), seat3: 0.000 (6 games)
- `mcts_calibrated_eval_d5`: seat0: 0.000 (6 games), seat1: 0.000 (6 games), seat2: 0.000 (7 games), seat3: 0.000 (6 games)
- `mcts_default_eval_d0`: seat0: 0.000 (7 games), seat1: 0.000 (6 games), seat2: 0.500 (6 games), seat3: 0.000 (6 games)

## Score Stats
- `mcts_baseline_d0`: mean=70.48, median=70.0, std=1.7690675509996785, p25=70.0, p75=71.0, min=68.0, max=73.0
- `mcts_calibrated_eval_d0`: mean=75.4, median=73.0, std=8.68101376568428, p25=73.0, p75=73.0, min=66.0, max=90.0
- `mcts_calibrated_eval_d5`: mean=68.96, median=68.0, std=2.5056735621385315, p25=68.0, p75=69.0, min=66.0, max=73.0
- `mcts_default_eval_d0`: mean=69.56, median=71.0, std=2.9131426329653003, p25=69.0, p75=71.0, min=65.0, max=73.0

## Pairwise Matchups
- `mcts_baseline_d0__vs__mcts_calibrated_eval_d0`: mcts_baseline_d0>mcts_calibrated_eval_d0=6, mcts_calibrated_eval_d0>mcts_baseline_d0=19, tie=0 (total=25)
- `mcts_baseline_d0__vs__mcts_calibrated_eval_d5`: mcts_baseline_d0>mcts_calibrated_eval_d5=19, mcts_calibrated_eval_d5>mcts_baseline_d0=6, tie=0 (total=25)
- `mcts_baseline_d0__vs__mcts_default_eval_d0`: mcts_baseline_d0>mcts_default_eval_d0=12, mcts_default_eval_d0>mcts_baseline_d0=7, tie=6 (total=25)
- `mcts_calibrated_eval_d0__vs__mcts_calibrated_eval_d5`: mcts_calibrated_eval_d0>mcts_calibrated_eval_d5=19, mcts_calibrated_eval_d5>mcts_calibrated_eval_d0=6, tie=0 (total=25)
- `mcts_calibrated_eval_d0__vs__mcts_default_eval_d0`: mcts_calibrated_eval_d0>mcts_default_eval_d0=19, mcts_default_eval_d0>mcts_calibrated_eval_d0=6, tie=0 (total=25)
- `mcts_calibrated_eval_d5__vs__mcts_default_eval_d0`: mcts_calibrated_eval_d5>mcts_default_eval_d0=6, mcts_default_eval_d0>mcts_calibrated_eval_d5=19, tie=0 (total=25)

## Time and Simulation Efficiency
- `mcts_baseline_d0`: avg_time_ms=3350.5543957585874, avg_sims_per_move=1000.0, sims_per_sec=298.45807048107736, win_rate_per_sec=0.03581496845772928, score_per_sec=21.03532480750633
- `mcts_calibrated_eval_d0`: avg_time_ms=3036.556697519202, avg_sims_per_move=1000.0, sims_per_sec=329.3203781826229, win_rate_per_sec=0.2502834874187934, score_per_sec=24.830756514969767
- `mcts_calibrated_eval_d5`: avg_time_ms=3532.8121416496506, avg_sims_per_move=25.0, sims_per_sec=7.0765155342582755, win_rate_per_sec=0.0, score_per_sec=19.519860449698026
- `mcts_default_eval_d0`: avg_time_ms=3362.933044516763, avg_sims_per_move=1000.0, sims_per_sec=297.3594736387905, win_rate_per_sec=0.03568313683665486, score_per_sec=20.68432498631427

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_calibrated_eval_d0` | 36.02 | 7.77 | **12.72** | 25 |
| 2 | `mcts_baseline_d0` | 31.32 | 7.47 | **8.90** | 25 |
| 3 | `mcts_default_eval_d0` | 22.80 | 7.46 | **0.40** | 25 |
| 4 | `mcts_calibrated_eval_d5` | 10.15 | 7.45 | **-12.20** | 25 |

## Score Margins (winner - last place)
- Mean: `10.76`, Median: `7.0`, Std: `8.05`, Range: `[5.0, 25.0]`

## Score by Seat Position
- `mcts_baseline_d0`: P1: 71.0±0.0 (n=6), P2: 73.0±0.0 (n=6), P3: 68.0±0.0 (n=6), P4: 70.0±0.0 (n=7)
- `mcts_calibrated_eval_d0`: P1: 90.0±0.0 (n=6), P2: 73.0±0.0 (n=7), P3: 73.0±0.0 (n=6), P4: 66.0±0.0 (n=6)
- `mcts_calibrated_eval_d5`: P1: 69.0±0.0 (n=6), P2: 73.0±0.0 (n=6), P3: 68.0±0.0 (n=7), P4: 66.0±0.0 (n=6)
- `mcts_default_eval_d0`: P1: 71.0±0.0 (n=7), P2: 69.0±0.0 (n=6), P3: 73.0±0.0 (n=6), P4: 65.0±0.0 (n=6)
