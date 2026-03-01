# Move vs Round (Game Turn) — Definitions & Sampling

This document defines the terminology used for tracking game progress and how x-axis alignment works in the telemetry and analysis layers.

## 1. Core Definitions

| Term | Domain | Definition | Implementation Detail |
|---|---|---|---|
| **Move** | Player Action | A single placement or pass by one player. | `board.move_count`, `turn_index`, `move_index` |
| **Round** | Rotation | A full cycle where all 4 players (R→B→Y→G) have had 1 move opportunity. | `round_index = move_index // 4` |
| **Position** | Seat | The slot (0–3) within a specific round. | `position_in_round = move_index % 4` |
| **Seat** | Player | The static assigned order index (0: RED, 1: BLUE, 2: YELLOW, 3: GREEN). | `seat_index = player_id - 1` |

## 2. Global Indexing Rules

- **0-based (Internal)**: All counters in code and JSON data (`move_index`, `round_index`, `seat_index`) are 0-based to match standard array/Python indexing.
- **1-based (User-facing)**: The UI labels ("Move 1", "Round 1") are consistently 1-based for human readability.
- **Move Counter**: The counter `turn_number` in `game_history` is retained as a legacy/stable 1-based indicator.

## 3. Sampling: End-of-Round Snapshots

When aligning metrics by **Round**, the dashboard and telemetry analyzers use **end-of-round snapshots**.

Instead of plotting every individual move (which causes a visual skew where RED's data point precedes others), the "Round X" data point represents the board state **after all 4 players have moved** (or had the chance to move) in that round.

- For each Round $R$:
  - The snapshot index is $(R \times 4) + 3$.
  - In the chart, the Y-value for player $P$ at Round $R$ is $P$'s metric value at or immediately before that snapshot.
  - If the game ends mid-round, the latest available value for that player is used.

## 4. Derived Data Logic

The following derivation is canonical across the engine and webapi:

```python
seat_index = player_id - 1
round_index = internal_move_counter // 4
position_in_round = internal_move_counter % 4
```

In the `AnalysisDashboard` frontend:
```typescript
const roundEndIdx = (r * 4) + 3;
// Snapshot state at or before roundEndIdx represents the round results.
```
