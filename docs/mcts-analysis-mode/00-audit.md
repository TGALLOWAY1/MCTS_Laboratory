# MCTS Analysis Mode Audit

## 1. Files Involved

### Engine / Setup
- `mcts/mcts_agent.py` & `browser_python/mcts/mcts_agent.py`: Contains the `MCTSAgent` and `MCTSNode` classes.
- `engine/board.py`, `engine/game.py`: Handle game state.

### Frontend / Telemetry
- `frontend/src/store/gameStore.ts`: Manages the game state, including `game_history` and `telemetry`. This is where `MctsTrace` will be plumbed.
- `frontend/src/pages/Analysis.tsx`: Existing analysis page. Can house the new "Analysis Mode" or be adapted.
- `frontend/src/components/AnalysisDashboard.tsx`: Existing dashboard for spatial analysis and mobility.
- `frontend/src/components/telemetry/MergedAnalysisPanel.tsx`: Existing telemetry components.
- `frontend/src/types/telemetry.ts`: Types for telemetry.

## 2. Where to Hook Diagnostics

- **MCTS Instrumentation**: Inside `mcts_agent.py` in the `select_action` and `_mcts_iteration` methods. We need to collect metadata at the root node (children visits, Q-values) after iterations complete, and optionally sample metrics during the `_run_mcts_with_iterations` loop.
- **Frontend Plumbing**: Pyodide worker (`BlokusWorker.ts`) sends `state_update` messages. We should attach the `MctsDiagnosticsV1` payload to the move telemetry or game state history.

## 3. Current Telemetry Data Model

- `GameState` includes `game_history` of type `GameHistoryEntry[]`.
- `GameHistoryEntry` contains `telemetry?: MoveTelemetryDelta` and `metrics`.
- We can add `mcts_trace?: MctsDiagnosticsV1` to `GameHistoryEntry` or store an array of traces in `GameState`.

## 4. Performance Risks

- **Deep copies / Tree traversal**: Collecting metrics must not traverse the entire tree on every simulation. We should only aggregate at the root, and track depth as we go down.
- **Payload size**: Sending large traces across the Pyodide/WebWorker boundary could cause jank. We must sample `bestMoveTrace` sparingly (e.g. every 100-200 sims) and only return aggregate arrays for histograms.
- **Disabled state overhead**: When `enableDiagnostics` is false, the tracking logic must be completely bypassed to preserve pure MCTS playouts speed.
