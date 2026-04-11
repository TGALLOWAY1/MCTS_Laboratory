# Deployment

This project deploys as a two-part application:

1. **Frontend** — Vite/React SPA built from `frontend/`, served as static assets.
2. **Backend** — FastAPI app exposed through `api-runtime/app.py`, which wraps `webapi/create_app(profile="deploy")` and registers only the gameplay routes.

The canonical Vercel config is [`vercel.json`](../vercel.json).

## Runtime profiles

`webapi/app.py` supports two profiles controlled by `APP_PROFILE`:

| Profile | Routes enabled | Notes |
|---------|---------------|-------|
| `research` (default) | All routes — gameplay, analysis, history, training, DB debug | Used for local development and arena work. |
| `deploy` | Gameplay-only (`/api/games`, `/api/games/{id}`, `/api/games/{id}/move`, `/api/agents`, `/health`, `/ws/games/{id}`) | Used on Vercel. Time budgets are capped by `webapi/deploy_validation.py`. |

`api-runtime/app.py` is the entry point that forces `profile="deploy"`.

## Environment variables

### Backend (Vercel project)

| Variable | Required | Purpose |
|----------|----------|---------|
| `APP_PROFILE` | yes | Set to `deploy` on Vercel. |
| `MONGODB_URI` | research profile only | MongoDB connection string for analysis/history routes. |
| `MONGODB_DB_NAME` | research profile only | Database name (defaults to `blokusdb`). |

### Frontend (Vercel project)

| Variable | Required | Purpose |
|----------|----------|---------|
| `VITE_APP_PROFILE` | yes | `deploy` or `research`. Gates research-only UI. |
| `VITE_API_URL` | yes | Public base URL of the deployed backend. |
| `VITE_WS_URL` | no | WebSocket base URL. Derived from `VITE_API_URL` if omitted. |

Copy `.env.example` to `.env` for local development.

## Local smoke test

Start the deploy-profile backend:

```bash
APP_PROFILE=deploy PYTHONPATH=. python3 api-runtime/app.py
# Serves on http://localhost:8000
```

Create a valid deploy game (1 human vs 3 MCTS):

```bash
curl -sS -X POST http://localhost:8000/api/games \
  -H 'Content-Type: application/json' \
  -d '{
    "players": [
      {"player":"RED","agent_type":"human","agent_config":{}},
      {"player":"BLUE","agent_type":"mcts","agent_config":{"difficulty":"easy"}},
      {"player":"GREEN","agent_type":"mcts","agent_config":{"difficulty":"medium"}},
      {"player":"YELLOW","agent_type":"mcts","agent_config":{"difficulty":"hard"}}
    ],
    "auto_start": true
  }'
```

Verify health and that invalid configs are rejected:

```bash
curl -sS http://localhost:8000/health
curl -sS -X POST http://localhost:8000/api/games \
  -H 'Content-Type: application/json' \
  -d '{"players":[{"player":"RED","agent_type":"human"},{"player":"BLUE","agent_type":"random"}]}'
# Expected: HTTP 400 with validation message
```

## Vercel routing

`vercel.json` routes:

- `/api/*`, `/health`, `/docs`, `/openapi.json` → `api-runtime/app.py` (Python serverless).
- Everything else → `index.html` (SPA fallback).

Keep `APP_PROFILE=deploy` set in the Vercel project so the backend never registers research/training routes.

## In-browser gameplay (no backend)

The demo game on the landing page runs entirely in the browser via Pyodide —
`browser_python/` mirrors the engine and MCTS and is loaded in a WebWorker.
This path requires no backend and is the recommended zero-cost demo mode.
Build the browser bundle with `scripts/build_browser_core.sh` before deploying
the frontend.

## Historical notes

Earlier iterations deployed an external `engine-service/` FastAPI microservice
that exposed `POST /think` and was called from the web API via `ENGINE_URL`.
That service has been archived to `archive/engine-service/` because it
depended on the archived `FastMCTSAgent` (see `CLAUDE.md`). The `ENGINE_URL`
fallback path in `webapi/app.py` is left in place but inert when the variable
is unset.
