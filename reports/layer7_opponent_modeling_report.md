# Layer 7: Opponent Modeling in 4-Player Blokus

> **Status**: IMPLEMENTED — Asymmetric rollout policies, blocking-rate tracking, alliance detection, king-maker awareness, and adaptive opponent profiles integrated. Arena experiment configs ready for benchmarking.

**Branch:** `claude/opponent-modeling-layer-7-lrY1A`

## 7.0 — Motivation

Layers 3-6 optimized the MCTS agent's search efficiency, simulation quality, and evaluation accuracy — but all treated the four players symmetrically during rollout simulations. In a 4-player game like Blokus, this symmetry assumption ignores three critical dynamics:

1. **Asymmetric importance**: Baier & Kaisers (2020) demonstrate that in multiplayer games, the agent's own actions have significantly greater impact on final score than opponent prediction. Their Opponent Move Abstractions (OMA) approach achieves better win rates by focusing computation on self-modeling.

2. **Emergent alliances**: The ColosseumRL paper (2019) highlights that players can form implicit alliances by focusing blocking on a single opponent. Standard symmetric rollouts cannot capture these targeting dynamics.

3. **King-maker scenarios**: A player far behind the leader can determine the final ranking through strategic blocking. Modeling these players as self-maximizing (the symmetric default) produces unrealistic simulations.

### The Research Question

How much computational budget should the agent invest in modeling opponents vs. modeling itself? This layer implements three levels of opponent modeling and provides arena configurations to measure the impact of each.

## 7.1 — Asymmetric Rollout Policies

### Design

The core change is in `_rollout()` (mcts/mcts_agent.py): when `opponent_rollout_policy != "same"`, the rollout loop selects different move policies for the root player vs. opponents.

| Config | Self Policy | Opponent Policy | Hypothesis |
|--------|-------------|-----------------|------------|
| Symmetric (baseline) | heuristic | heuristic | Balanced simulation |
| Self-focused | heuristic | random | "Focus on yourself" saves computation |
| Balanced | two_ply (top-k=10) | heuristic | Self gets stronger search, opponents stay realistic |

### New Parameter: `opponent_rollout_policy`

| Value | Behavior |
|-------|----------|
| `"same"` (default) | Use same policy as `rollout_policy` — backward compatible |
| `"random"` | Opponents use uniform random move selection |
| `"heuristic"` | Opponents use the heuristic rollout agent |

When `opponent_rollout_policy="same"`, the rollout behavior is identical to the Layer 6 baseline. No existing behavior changes.

### Implementation

The rollout loop (line ~952) now checks `current_player == root_player`:
- **Root player**: Uses the configured `rollout_policy` (heuristic, random, or two_ply) plus NST bias
- **Opponents**: Uses `_select_opponent_rollout_move()` which consults the opponent model for per-player policy decisions

### Arena Config

**`scripts/arena_config_layer7_rollout_asymmetry.json`**

Four agents:
1. `L6_baseline_symmetric` — heuristic rollout, cutoff 8, phase weights, `opponent_rollout_policy="same"`
2. `L7_self_focused` — heuristic self, random opponents
3. `L7_balanced` — two_ply (top-k=10) self, heuristic opponents
4. `L6_baseline_default` — heuristic rollout, phase weights, no cutoff

100 games, round-robin seating, seed 20260323.

### Expected Outcomes

- If **self-focused beats symmetric**: The "focus on yourself" finding generalizes to Blokus. Random opponent rollouts produce noisier simulations, but the agent compensates by getting better self-modeling from saved computation.
- If **balanced beats self-focused**: Opponent behavior matters enough that completely random opponents create blind spots. The heuristic opponent policy provides useful signal about blocking and territorial denial.
- If **symmetric beats both**: The default symmetric approach is already near-optimal for Blokus. Don't invest in rollout asymmetry.

## 7.2 — Alliance Detection and Exploitation

### Blocking Rate Tracking

The `BlockingTracker` class (mcts/opponent_model.py) records per-opponent blocking statistics during actual gameplay:

- After each move, compares the opponent's frontier before and after
- Records `blocking_counts[(blocker, victim)]` = total frontier cells eliminated
- Computes `blocking_rate(blocker, victim)` = blocked_cells / moves_made

### Alliance Detection Threshold

A player is flagged as "targeting" when:
```
blocking_rate(opponent, root_player) > threshold × avg_blocking_rate(opponent)
```

Default threshold = 2.0×. Requires at least 3 moves to avoid early-game false positives.

### Exploitation During Simulation

When an opponent is flagged as targeting:
1. **Rollout policy upgrade**: Their moves are simulated with the heuristic agent (not random), producing more realistic pessimistic simulations
2. **Defensive evaluation shift**: The state evaluator increases weight on `accessible_corners` (+0.15) and `reachable_empty_squares` (+0.075), while decreasing `squares_placed` (-0.075) and `opponent_avg_mobility` (-0.075)

### King-Maker Detection

The `KingMakerDetector` class identifies players in king-maker positions:

- **Trigger**: Board occupancy >= 55% (late phase) AND score gap > 15 behind the leader
- **Role classification**: Each player is labeled `"contender"`, `"kingmaker"`, or `"eliminated"`
- **Impact on simulation**: King-maker players use heuristic rollout (models strategic anti-leader behavior) instead of random

### Arena Config

**`scripts/arena_config_layer7_alliance.json`**

Three agents:
1. `L7_alliance_kingmaker` — Full opponent modeling (alliance + king-maker detection)
2. `L7_alliance_only` — Alliance detection only (no king-maker)
3. `L6_baseline` — Layer 6 baseline (no opponent modeling)

## 7.3 — Adaptive Opponent Modeling (Repeated Play)

### Design

The `OpponentProfile` class maintains a persistent model of each opponent across games:

| Feature | Description | Update Method |
|---------|-------------|---------------|
| `avg_piece_size_preference` | Large vs small piece preference | EMA (α=0.3) |
| `blocking_tendency` | Fraction of moves that block others | EMA (α=0.3) |
| `center_preference` | Tendency toward center positions | EMA (α=0.3) |

First game initializes values directly. Subsequent games use exponential moving average (EMA) with α=0.3, giving recent games ~30% influence on the profile.

### Integration

The `OpponentModelManager` coordinates all components:
- `on_move_made()`: Called after each game move to update blocking tracker
- `get_opponent_rollout_policy()`: Returns per-player rollout policy based on current flags
- `get_defensive_eval_adjustment()`: Returns weight deltas when under threat
- `reset_game()`: Clears per-game state while preserving cross-game profiles

## Integration Points

| Component | File | Change |
|-----------|------|--------|
| Opponent model module | `mcts/opponent_model.py` | NEW: BlockingTracker, KingMakerDetector, OpponentProfile, OpponentModelManager |
| MCTS agent | `mcts/mcts_agent.py` | 8 new constructor params, asymmetric rollout logic, notify_move() |
| Arena runner | `analytics/tournament/arena_runner.py` | Wire Layer 7 params, board_before capture, move notification |
| Rollout asymmetry config | `scripts/arena_config_layer7_rollout_asymmetry.json` | NEW: 4-agent experiment |
| Alliance detection config | `scripts/arena_config_layer7_alliance.json` | NEW: 3-agent experiment |
| Unit tests | `tests/test_layer7_opponent_modeling.py` | NEW: 31 tests |

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `opponent_rollout_policy` | `"same"` | Opponent rollout policy: `"same"`, `"random"`, `"heuristic"` |
| `opponent_modeling_enabled` | `false` | Master switch for opponent tracking |
| `alliance_detection_enabled` | `false` | Enable blocking-rate targeting detection |
| `alliance_threshold` | `2.0` | Blocking rate multiplier for targeting flag |
| `kingmaker_detection_enabled` | `false` | Enable late-game king-maker detection |
| `kingmaker_score_gap` | `15` | Score gap threshold for king-maker classification |
| `adaptive_opponent_enabled` | `false` | Build cross-game opponent profiles |
| `defensive_weight_shift` | `0.15` | Evaluation weight shift magnitude when under threat |

## Backward Compatibility

All new parameters default to values that preserve existing behavior:
- `opponent_rollout_policy="same"` means rollouts are identical to pre-Layer 7
- `opponent_modeling_enabled=false` disables all tracking and detection
- No `board.copy()` overhead in the arena game loop unless an agent enables opponent modeling

## Running the Experiments

```bash
# Rollout asymmetry experiment (symmetric vs self-focused vs balanced)
python scripts/arena.py --config scripts/arena_config_layer7_rollout_asymmetry.json

# Alliance detection experiment
python scripts/arena.py --config scripts/arena_config_layer7_alliance.json

# Smoke test with reduced games
python scripts/arena.py --config scripts/arena_config_layer7_rollout_asymmetry.json --num-games 4
```

## Checklist

- [x] Three rollout configurations (symmetric, self-focused, balanced) — arena config ready
- [x] Blocking rate tracking implemented per opponent (`BlockingTracker`)
- [x] Alliance detection threshold calibrated (default 2.0×, min 3 moves)
- [x] King-maker detection implemented (late-game, occupancy >= 0.55, gap > 15)
- [x] Adaptive opponent model structure defined (`OpponentProfile` with EMA updates)
- [ ] Arena experiments run and TrueSkill ratings documented vs Layer 6 baseline
- [x] 31 unit tests passing

## Key Decisions This Layer Informs

| Finding | Decision | Layer Affected |
|---------|----------|----------------|
| Self-focused wins | Simplify opponent rollout modeling; save computation | Architecture efficiency |
| Balanced wins | Maintain heuristic opponent modeling; worth the cost | Permanent architecture |
| Alliance detection helps | Keep blocking-rate tracking in production agent | Evaluation function design |
| King-maker modeling helps | Add late-game opponent behavior switching | Layer 9 phase-dependent parameters |
