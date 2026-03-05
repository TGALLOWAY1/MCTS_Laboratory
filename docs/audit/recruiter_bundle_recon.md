# Recruiter Bundle Recon

## Inventory

### Routes / Navigation
- Frontend uses React Router (`react-router-dom`).
- Important routes/pages:
  - `Home.tsx` (`/`) - Game configuration and start.
  - `Play.tsx` (`/play`) - Main board and gameplay UI.
  - `TrainingHistory.tsx` / `TrainingRunDetail.tsx` - Existing analytics dashboards.
- Navigation logic is handled by `useNavigate()` post game creation.

### Game Start and Reset Logic
- `Home.tsx` has `handleCreateGame` which configures a `gameConfig` payload (players, agent types, auto-start).
- It calls `createGame` in `gameStore.ts`, which bridges to `BlokusWorker` (local Pyodide worker) using `init_game`.
- After local creation, it connects the store state and navigates to `/play`.
- There are already "Quick Start" presets in `Home.tsx` (e.g., 4 Players, vs Random, vs MCTS).

### AI Configuration
- Agents are currently defined by `agent_type` (e.g. `human`, `mcts`, `random`, `heuristic`).
- Backend MCTS agent configuration is mapped in `webapi/app.py` and `webapi/gameplay_agent_factory.py`. There's an existing `deploy_validation.py` which enforces 1 Human + 3 MCTS of varying difficulties under deployment scenarios.
- MCTS time budgets and seeds can be passed into the game config (e.g. `agent_config`).

### Telemetry and Explainability
- **Excellent news**: The game engine already produces complex telemetry.
- `GameState` object contains `advanced_metrics`, `frontier_metrics`, `piece_lock_risk`, `self_block_risk`.
- MCTS is already returning top alternative moves: `mcts_top_moves` (with `visits` and `q_value`) and `mcts_stats` (time spent, nodes evaluated, max depth). 
- History logs are tracked via `game_history` and `GameHistoryEntry`.

### UI State and Store
- Leverages `zustand` in `frontend/src/store/gameStore.ts`.
- `GameState` represents the single source of truth inside the store.
- Component updates listen directly to `useGameStore`.

---

## Existing Components We Can Reuse

- **Home.tsx (Quick Start section)**: We can easily add a "Run Demo Game" shortcut here that constructs a pre-determined, fully automated, deterministic MCTS v MCTS game.
- **useGameStore() & BlokusWorker**: We will use these to start the demo game in the local worker without needing a server component.
- **GameStore's `mcts_top_moves` & `mcts_stats`**: These variables exactly match the "Explain-This-Move" data requirement. We just need to build a UI panel in `Play.tsx` (or a dedicated component) to render them.
- **ResearchSidebar.tsx / DebugLogsPanel.tsx**: Provide structural templates for injecting our Explain-This-Move side panel.
