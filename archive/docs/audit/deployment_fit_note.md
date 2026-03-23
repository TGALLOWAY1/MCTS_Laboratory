# Deployment Fit Assessment: Vercel vs. Fly.io

**Date:** March 2026
**Context:** The Blokus RL project has evolved to support a dual-execution topology for the core game engine (`engine/`). It can run either on a traditional backend (FastAPI) or entirely in the browser (Pyodide WebWorkers).

This document evaluates the fit for deploying the recruiter-ready demonstration version to the public internet.

---

## 1. The Pyodide (In-Browser) Topology
The current frontend (`frontend/src/store/blokusWorker.ts`) bundles a WASM-compiled Python environment (`Pyodide`) which downloads the `engine/` and `agents/` Python source files to the client's browser and executes MCTS locally.

### Pros
* **Zero Backend Costs:** Compute is entirely offloaded to the client. We do not pay for the heavy CPU cycles required by Monte Carlo Tree Search.
* **Infinite Scalability:** We can handle 1 user or 10,000 users concurrently without provisioning servers.
* **Low Latency Perception:** Since UI updates happen locally, interactions feel instantaneous despite the AI "thinking" for hundreds of milliseconds.
* **Perfect for Vercel:** This architecture turns the application into a pure Static Site Generation (SSG) / Single Page Application (SPA). Vercel's global CDN is the ideal candidate for this, offering fast delivery of the initial WASM payload and React bundles.

### Cons
* **Heavy Initial Payload:** Users must download the Pyodide runtime (~10-20MB depending on caching) on their first visit.
* **Mobile Constraint:** Deep MCTS budgets (e.g., 400ms+) might struggle on older mobile devices or severely drain battery.
* **Browser Limitations:** No shared memory multiprocessing or native C++ add-ons without specific WASM compilation toolchains.

---

## 2. The Traditional Backend Topology
The project contains a FastAPI server (`webapi/app.py`) which manages state in MongoDB and runs agents server-side.

### Pros
* **Predictable Performance:** Agent AI think time is deterministic and unaffected by the user's hardware.
* **Data Collection:** Enables server-side tracking of user interactions, telemetry gathering, and game record capturing for further ML/RL training datasets.
* **Lightweight Client:** Solves the Pyodide initial loading threshold.

### Cons
* **Scaling Costs:** Each MCTS agent requires heavy CPU locking. Running 10 concurrent users with 4 agents playing at 400ms per turn would easily saturate a standard VPS.
* **Complex Infrastructure:** Requires container orchestration (Docker), persistent volume routing (MongoDB), and load balancers. Fly.io or AWS ECS would be required.

---

## Conclusion & Recommendation

**Target Platform:** Vercel (Pure Frontend)

For the purpose of a Recruiter/Portfolio Demonstration, **Vercel is the optimal choice**.

By relying on the Pyodide WebWorker topology implemented in the Recruiter Bundle, we achieve:
1. **Free Hosting:** Vercel's free tier comfortably covers the static payload delivery.
2. **Zero Maintenance:** No servers to wake up (cold starts), no databases to monitor, and no security patches to manage.
3. **Instant Demonstrability:** A recruiter can immediately interact with the UI, pause the MCTS, explore the Explain-This-Move panel, and benchmark the AI purely from their laptop browser without us footing a massive cloud compute bill.

**Next Steps:**
- Configure a `vercel.json` and a build script that simply copies the raw Python `engine/` and `agents/` files into Vercel's public directory so Pyodide can fetch them.
- Strip or conditionalize MongoDB and FastAPI logic from the Vercel deploy phase (since we only use Local Pyodide).
- Set `IS_DEPLOY_PROFILE = true` to restrict certain heavy research dashboard features.
