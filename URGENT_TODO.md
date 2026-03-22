# URGENT TODO — Layer 0: Measurement Infrastructure

## Status: IMPLEMENTED — Manual Verification Required

Layer 0 establishes the measurement foundation that all subsequent optimization
layers depend on. Without rigorous measurement, every change is guesswork.

---

## Checklist

- [x] **Game logger** captures all listed metrics and writes to structured JSONL
- [x] **TrueSkill rating system** implemented and tested with 3+ dummy agents
- [x] **Tournament harness** runs N games with seat rotation and produces TrueSkill ratings + convergence detection
- [x] **Profiler** has been run on the current agent and time breakdown is documented
- [ ] **All infrastructure automated** — verify the single-command tournament runner works end-to-end

---

## Manual Verification Instructions

### 0.1 — Game Logger

The game logger captures per-move MCTS diagnostics including: wall-clock time,
iterations, branching factor, tree depth (max/mean), tree size, visit entropy,
Q-values, regret gap, piece info, and per-player score deltas.

**Verify MCTS tree diagnostics are captured:**

```bash
python -c "
from engine.board import Board, Player
from engine.move_generator import get_shared_generator
from mcts.mcts_agent import MCTSAgent

board = Board()
agent = MCTSAgent(iterations=50)
move_gen = get_shared_generator()
legal_moves = move_gen.get_legal_moves(board, Player.RED)
move = agent.select_action(board, Player.RED, legal_moves)
info = agent.get_action_info()
stats = info['stats']
print('Iterations:', stats['iterations_run'])
print('Tree size:', stats['tree_size'])
print('Tree depth max:', stats['tree_depth_max'])
print('Tree depth mean:', stats['tree_depth_mean'])
print('Visit entropy:', stats['visit_entropy'])
print('Best move Q:', stats['best_move_q'])
print('Best move visits:', stats['best_move_visits'])
print('Second best Q:', stats['second_best_q'])
print('Regret gap:', stats['regret_gap'])
print('Branching factor:', stats['branching_factor'])
"
```

**Expected:** All fields should have numeric values (not None).

**Verify schema includes new fields:**

```bash
python -c "
from analytics.logging.schemas import StepLog, MCTSStepDiagnostics
import json
diag = MCTSStepDiagnostics(
    decision_time_ms=150.0, iterations=100, branching_factor=300,
    tree_depth_max=3, tree_depth_mean=1.5, tree_size=150,
    visit_entropy=2.3, best_move_q=45.0, best_move_visits=30,
    second_best_q=42.0, regret_gap=3.0,
    piece_id=15, piece_size=5, piece_anchor_row=8, piece_anchor_col=10,
)
print(json.dumps(json.loads(diag.model_dump_json()), indent=2))
"
```

**Verify logger can write MCTS data to JSONL:**

```bash
python -c "
from analytics.logging.logger import StrategyLogger
print('StrategyLogger constructor OK')
logger = StrategyLogger(log_dir='/tmp/test_game_logs')
print('Logger created at /tmp/test_game_logs')
print('Methods: on_reset, on_step (with mcts_stats param), on_game_end')
"
```

### 0.2 — Tournament Harness with TrueSkill

**Run TrueSkill tests (18 tests):**

```bash
python -m pytest tests/test_trueskill_rating.py -v
```

**Expected:** 18 passed, 0 failed.

**Verify TrueSkill tracker directly:**

```bash
python -c "
from analytics.tournament.trueskill_rating import TrueSkillTracker
import random
random.seed(42)

tracker = TrueSkillTracker()
agents = ['mcts_strong', 'mcts_medium', 'heuristic', 'random']
for i in range(50):
    scores = {
        'mcts_strong': 70 + random.randint(-10, 10),
        'mcts_medium': 55 + random.randint(-10, 10),
        'heuristic': 40 + random.randint(-10, 10),
        'random': 25 + random.randint(-10, 10),
    }
    tracker.update_game(scores)

print('=== TrueSkill Leaderboard ===')
for e in tracker.get_leaderboard():
    print(f'  #{e[\"rank\"]} {e[\"agent_id\"]}: mu={e[\"mu\"]:.2f}, sigma={e[\"sigma\"]:.2f}, conservative={e[\"conservative\"]:.2f}')
print(f'Converged: {tracker.is_converged()}')
"
```

**Expected:** Agents ranked mcts_strong > mcts_medium > heuristic > random.

**Verify statistical utilities:**

```bash
python -c "
from analytics.tournament.statistics import bootstrap_score_ci, score_margin_stats

# Agent A consistently 10 points better
ci = bootstrap_score_ci([70,75,65,80,72], [60,65,55,70,62], seed=42)
print(f'Bootstrap CI for score diff: {ci[\"mean_diff\"]:.1f} [{ci[\"ci_lower\"]:.1f}, {ci[\"ci_upper\"]:.1f}]')

margins = score_margin_stats([
    {'final_scores': {'1': 70, '2': 55, '3': 40, '4': 25}},
    {'final_scores': {'1': 60, '2': 58, '3': 55, '4': 50}},
])
print(f'Score margins: mean={margins[\"mean_margin\"]}, range=[{margins[\"min_margin\"]}, {margins[\"max_margin\"]}]')
"
```

### 0.3 — The Profiler

**Run the profiler (quick test):**

```bash
python scripts/profile_mcts.py --iterations 20 --game-phase mid
```

**Expected output:** Phase breakdown table showing simulation at ~99% of time.

**Run full profile with JSON output:**

```bash
python scripts/profile_mcts.py --iterations 50 --game-phase all --output /tmp/profile_report.json
```

**Review documented baseline:**

```bash
cat docs/profiler_baseline.md
```

### End-to-End: Tournament Runner

**Run a small tournament with game logging and TrueSkill:**

```bash
python scripts/run_tournament.py --num-games 5 --verbose
```

**Expected:** Completes N games, produces:
- `arena_runs/<run_id>/summary.json` with `trueskill_ratings` key
- `arena_runs/<run_id>/summary.md` with TrueSkill leaderboard table
- `arena_runs/<run_id>/game_logs/steps.jsonl` (if logging enabled)
- Score margins and seat-position analysis in summary

---

## Key Files Added/Modified

### New Files
| File | Description |
|------|-------------|
| `mcts/utils.py` | Shared `compute_policy_entropy()` function |
| `analytics/tournament/trueskill_rating.py` | TrueSkill-style rating tracker (openskill) |
| `analytics/tournament/statistics.py` | Bootstrap CI, permutation test, seat/margin analysis |
| `scripts/profile_mcts.py` | Structured MCTS profiler |
| `scripts/run_tournament.py` | Single-command tournament runner |
| `tests/test_trueskill_rating.py` | 18 integration tests |
| `docs/profiler_baseline.md` | Profiler baseline documentation |

### Modified Files
| File | Changes |
|------|---------|
| `mcts/mcts_agent.py` | Added `_collect_tree_diagnostics()` — captures depth, size, entropy, Q-values, regret gap |
| `agents/fast_mcts_agent.py` | Imports `compute_policy_entropy` from shared `mcts/utils.py` |
| `analytics/logging/schemas.py` | Added `MCTSStepDiagnostics`, `score_deltas`, `running_scores` |
| `analytics/logging/logger.py` | Extended `on_step()` to accept MCTS stats and compute score deltas |
| `analytics/tournament/arena_runner.py` | Integrated game logger, passes MCTS stats through adapters |
| `analytics/tournament/arena_stats.py` | Integrated TrueSkill, score margins, seat analysis into summary |
| `pyproject.toml` | Added `openskill` dependency |

---

## Architecture Notes

- **TrueSkill uses openskill's Plackett-Luce model** (not the `trueskill` package, which fails to build). The Plackett-Luce model provides equivalent μ/σ Gaussian skill distributions and is designed for >2 player games.
- **Game logger is opt-in** — pass `enable_game_logging=True` to `run_experiment()`. Adds ~3μs overhead per move for board copy.
- **Profiler baseline shows simulation (rollout) at 99%+ of time** — this should inform which layers to prioritize next.
