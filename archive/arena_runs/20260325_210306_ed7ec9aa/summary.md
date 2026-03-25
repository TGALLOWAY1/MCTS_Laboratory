# Arena Run Summary: 20260325_210306_ed7ec9aa

## Overview
- Seed: `20260323`
- Seat policy: `round_robin`
- Games: `25/25` completed
- Error games: `0`

## Win Rates by Agent
- `mcts_baseline`: win_rate=0.147, win_points=3.67, outright=2, shared=4
- `mcts_ph_only`: win_rate=0.140, win_points=3.50, outright=2, shared=3
- `mcts_ph_plus_rave`: win_rate=0.267, win_points=6.67, outright=5, shared=4
- `mcts_rave_only`: win_rate=0.447, win_points=11.17, outright=9, shared=5

## Win Rates by Seat
- `mcts_baseline`: seat0: 0.000 (7 games), seat1: 0.167 (6 games), seat2: 0.444 (6 games), seat3: 0.000 (6 games)
- `mcts_ph_only`: seat0: 0.000 (6 games), seat1: 0.071 (7 games), seat2: 0.500 (6 games), seat3: 0.000 (6 games)
- `mcts_ph_plus_rave`: seat0: 0.333 (6 games), seat1: 0.278 (6 games), seat2: 0.500 (6 games), seat3: 0.000 (7 games)
- `mcts_rave_only`: seat0: 0.278 (6 games), seat1: 0.500 (6 games), seat2: 0.929 (7 games), seat3: 0.000 (6 games)

## Score Stats
- `mcts_baseline`: mean=69.28, median=69.0, std=2.9054431675735803, p25=69.0, p75=71.0, min=62.0, max=73.0
- `mcts_ph_only`: mean=69.84, median=71.0, std=3.1199999999999997, p25=69.0, p75=72.0, min=62.0, max=73.0
- `mcts_ph_plus_rave`: mean=70.64, median=71.0, std=4.906159394067828, p25=66.0, p75=73.0, min=62.0, max=83.0
- `mcts_rave_only`: mean=71.12, median=72.0, std=5.217815634918506, p25=69.0, p75=73.0, min=62.0, max=90.0

## Pairwise Matchups
- `mcts_baseline__vs__mcts_ph_only`: mcts_baseline>mcts_ph_only=6, mcts_ph_only>mcts_baseline=17, tie=2 (total=25)
- `mcts_baseline__vs__mcts_ph_plus_rave`: mcts_baseline>mcts_ph_plus_rave=12, mcts_ph_plus_rave>mcts_baseline=11, tie=2 (total=25)
- `mcts_baseline__vs__mcts_rave_only`: mcts_baseline>mcts_rave_only=9, mcts_rave_only>mcts_baseline=14, tie=2 (total=25)
- `mcts_ph_only__vs__mcts_ph_plus_rave`: mcts_ph_only>mcts_ph_plus_rave=12, mcts_ph_plus_rave>mcts_ph_only=13, tie=0 (total=25)
- `mcts_ph_only__vs__mcts_rave_only`: mcts_ph_only>mcts_rave_only=6, mcts_rave_only>mcts_ph_only=18, tie=1 (total=25)
- `mcts_ph_plus_rave__vs__mcts_rave_only`: mcts_ph_plus_rave>mcts_rave_only=11, mcts_rave_only>mcts_ph_plus_rave=10, tie=4 (total=25)

## Time and Simulation Efficiency
- `mcts_baseline`: avg_time_ms=457.99974447188106, avg_sims_per_move=25.0, sims_per_sec=54.58518329268386, win_rate_per_sec=0.3202330753170787, score_per_sec=151.2664599406855
- `mcts_ph_only`: avg_time_ms=452.3112975473654, avg_sims_per_move=25.0, sims_per_sec=55.27166828589338, win_rate_per_sec=0.30952134240100293, score_per_sec=154.40693252347174
- `mcts_ph_plus_rave`: avg_time_ms=439.2527531493794, avg_sims_per_move=25.0, sims_per_sec=56.91483962423361, win_rate_per_sec=0.6070916226584918, score_per_sec=160.81857084223446
- `mcts_rave_only`: avg_time_ms=440.48999381540847, avg_sims_per_move=25.0, sims_per_sec=56.7549782083733, win_rate_per_sec=1.0140222773229364, score_per_sec=161.4565620071804

## TrueSkill Ratings
- Converged: `False`

| Rank | Agent | mu | sigma | Conservative (mu-3sigma) | Games |
|------|-------|----|-------|-------------------------|-------|
| 1 | `mcts_rave_only` | 30.03 | 7.63 | **7.14** | 25 |
| 2 | `mcts_ph_only` | 24.78 | 7.50 | **2.28** | 25 |
| 3 | `mcts_ph_plus_rave` | 24.33 | 7.53 | **1.74** | 25 |
| 4 | `mcts_baseline` | 20.76 | 7.43 | **-1.52** | 25 |

## Score Margins (winner - last place)
- Mean: `9.56`, Median: `8.0`, Std: `4.3`, Range: `[5.0, 24.0]`

## Score by Seat Position
- `mcts_baseline`: P1: 69.0±0.0 (n=7), P2: 71.17±0.75 (n=6), P3: 72.0±0.45 (n=6), P4: 65.0±0.63 (n=6)
- `mcts_ph_only`: P1: 69.33±0.33 (n=6), P2: 71.86±0.26 (n=7), P3: 72.83±0.17 (n=6), P4: 65.0±0.63 (n=6)
- `mcts_ph_plus_rave`: P1: 74.0±2.86 (n=6), P2: 72.0±0.68 (n=6), P3: 72.5±0.5 (n=6), P4: 65.0±0.53 (n=7)
- `mcts_rave_only`: P1: 73.17±3.39 (n=6), P2: 73.17±0.6 (n=6), P3: 73.0±0.0 (n=7), P4: 64.83±0.65 (n=6)
