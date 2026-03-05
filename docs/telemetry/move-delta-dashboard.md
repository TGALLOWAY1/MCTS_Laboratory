# Move Delta Dashboard Plan

## Findings
- **Metrics plumbing**: `engine/advanced_metrics.py` defines `compute_dead_zones`. `webapi/app.py` calculates mobility, corner control, and frontier size and attaches them to `GameState`. `engine/game.py` maintains `game_history` which logs basic metrics per move via `BlokusGame.make_move()`.
- **Telemetry charts**: Frontend components live in `frontend/src/components/AnalysisDashboard.tsx` (renders `DeadZoneMap`, `ModuleE_FrontierChart`, etc.) and `frontend/src/components/TelemetryPanel.tsx`.
- **Game history & logs**: In the backend, `webapi/app.py` maintains `move_records` on the active `game_data` dict and writes to MongoDB (`db.move_records`).
- **State advancement**: `engine/game.py` -> `BlokusGame.make_move()` handles state transitions and populates `game_history`. `webapi/app.py` contains endpoints that advance the turn and push moves.

## Implementation Plan (Milestones)
See `task.md` for the full breakdown.
1. **Types & Validation** (Commit: "chore: add move delta telemetry types")
2. **Data Production** (Commit: "feat(engine): compute per-move metric snapshots")
3. **Data Transport** (Commit: "feat(api): include move delta telemetry in game payload")
4. **UI Foundation** (Commit: "feat(ui): add Move Delta tab with selector and controls")
5. **Charts MVP** (Commit: "feat(charts): add diverging delta bar chart")
6. **Advanced Charts & Overlays** (Commits: radar, cumulative timeline, opponent suppression)
7. **Scoring & Leaderboard** (Commits: impact score, waterfall, top moves list)
8. **Polish & Docs** (Commits: perf optimization, documentation)

## Schema Definitions

```typescript
export type MetricKey = 'frontierSize' | 'mobility' | 'deadSpace' | 'frontierUtility' | string;

export interface PlayerMetricSnapshot {
  playerId: string; // e.g., 'RED', 'BLUE'
  metrics: Record<MetricKey, number>;
}

export interface MoveTelemetrySnapshot {
  ply: number;
  moverId: string;
  moveId: string; // e.g., '14-0-3-4'
  before: PlayerMetricSnapshot[];
  after: PlayerMetricSnapshot[];
}

export interface MoveTelemetryDelta {
  ply: number;
  moverId: string;
  moveId: string;
  deltaSelf: Record<MetricKey, number>;
  deltaOppTotal: Record<MetricKey, number>;
  deltaOppByPlayer: Record<string, Record<MetricKey, number>>;
  impactScore?: number;
}

export interface GameTelemetry {
  gameId: string;
  players: string[];
  moves: MoveTelemetryDelta[];
  normalization: 'z-score' | 'min-max' | 'none';
  weights?: Record<MetricKey, number>;
}
```

## Data Flow Diagram
```text
[Engine: make_move()]
       |
       v
Compute Metrics (Before) -> Place Piece -> Compute Metrics (After)
       |
       v
Calculate Deltas -> Append to GameHistory/MoveRecord
       |
       v
[WebAPI: /api/games/{id}/replay or /api/games/{id}]
       |
       v
[Frontend: API Slice / Store] -> Parse & Validate Schema
       |
       v
[Move Delta UI Components: Charts, Overlays, Leaderboards]
```

## Metric Definitions and Approximations
- **frontierSize**: Number of unique frontier cells available to the player. (Existing: `board.get_frontier(player)`)
- **mobility**: Number of legal moves. (Existing: Cached legal moves list, fallback to fast approximation if legal move generation is too slow mid-game)
- **deadSpace**: Number of dead zone cells. (Existing: `compute_dead_zones` BFS)
- **frontierUtility**: Value of frontier cells. (MVP approximation: Count of adjacent open cells or overlap with influence map)

## Performance Considerations
- `compute_dead_zones` is a BFS and can be expensive. We should gate parsing the full deadzone diff behind an analytical toggle if it bottlenecks the game loop per move.
- Fast mobility proxy: If full legal move counting across all orientations is too slow for all opponents every move, we can use the size of the frontier as a proxy or just count piece/anchor pairs.
- Frontend rendering: Memoize chart datapoints to avoid re-calculating diverging bars on every render. Virtualize the move list to handle 80+ ply games smoothly.
- Payload size: Delta vectors add O(P * M) data per move. This is small enough for JSON delivery but may require `/api/games/:id/telemetry` separation if it blows up the initial game load size.

## UI Components List (MVP + Stretch)
1. **Move Delta Route/Tab**: Main container.
2. **Move Selector**: Slider + Virtualized list.
3. **Controls Sidebar**: Weight presets, normalization toggles, player visibility.
4. **Diverging Bar Chart**: Component for `deltaSelf` vs `deltaOppTotal`.
5. **Radar Chart**: Before vs After shape comparison.
6. **Cumulative Timeline**: Line chart tracking cumulative move impact.
7. **Move Impact Waterfall**: Breakdown of a single move's components.
8. **Top Moves Leaderboard**: Ranked list with jump-to-move action.
9. **Opponent Suppression**: Small multiples of opponent metric timelines.
10. **Board Overlay**: Cell-level heatmap delta styling on the grid.
11. **Strategy Mix Summary**: Phase tabs with aggregate stats.
