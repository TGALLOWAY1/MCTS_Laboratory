Here's the result from the Coding Agent's analysis 

# Portfolio Impact Upgrade Plan

## Prioritization Framework

Each recommendation is ranked by:
- **Recruiter Impact** (High / Medium / Low)
- **Implementation Effort** (S / M / L)

---

## Tier 1: High Impact, Low-Medium Effort (Do First)

## 1) Recruiter Demo Mode (one-click)
- **Impact**: High
- **Effort**: M
- **What to add**:
  - “Run Demo Game” CTA on landing.
  - Preconfigured board seeds + AI difficulty presets.
  - Auto-play and pause/step controls.
- **Why it matters**: instantly demonstrates value without setup friction.

## 2) Explain-This-Move panel
- **Impact**: High
- **Effort**: M
- **What to show**:
  - top candidate moves,
  - visit counts / Q-values,
  - heuristic contributors (center/frontier/piece economy).
- **Why**: converts raw telemetry into interview-friendly reasoning.

## 3) AI Comparison scoreboard
- **Impact**: High
- **Effort**: M
- **What to include**:
  - win rates by opponent,
  - average score margin,
  - average think time,
  - Elo-style ranking.
- **Why**: recruiters can assess performance maturity quickly.

## 4) README recruiter section
- **Impact**: High
- **Effort**: S
- **Add**:
  - 60-second architecture summary,
  - quick demo URL flow,
  - “What this demonstrates” bullets (RL, search, systems).

---

## Tier 2: High Impact, Medium-High Effort

## 5) Live MCTS tree viewer
- **Impact**: High
- **Effort**: L
- **Features**:
  - node expansion timeline,
  - branch visits,
  - principal variation highlight.

## 6) Win probability timeline
- **Impact**: High
- **Effort**: M
- **Features**:
  - turn-by-turn win prob for each player,
  - key turning-point annotations.

## 7) Search depth and frontier heatmaps
- **Impact**: High
- **Effort**: M-L
- **Features**:
  - per-cell move pressure,
  - depth/intensity overlays.

---

## Tier 3: Medium Impact, Medium Effort

## 8) Step-through decision debugger
- **Impact**: Medium-High
- **Effort**: M
- **Features**:
  - frame-by-frame replay,
  - candidate-set evolution,
  - chosen-vs-rejected rationale.

## 9) Algorithm toggle mode
- **Impact**: Medium-High
- **Effort**: M
- **Features**:
  - MCTS vs heuristic vs random switch,
  - immediate side-by-side move differences.

## 10) Piece usage analytics dashboard
- **Impact**: Medium
- **Effort**: M
- **Features**:
  - piece timing histograms,
  - unused-piece penalties,
  - endgame lock patterns.

---

## Tier 4: Infrastructure Upgrades (Credibility Multipliers)

## 11) Persistent game sessions + replay links
- **Impact**: High for production credibility
- **Effort**: M-L
- **Recommendation**:
  - store sessions/events in Redis + Postgres/Mongo,
  - generate shareable replay URLs.

## 12) Auth + role-aware views
- **Impact**: Medium-High
- **Effort**: M
- **Recommendation**:
  - anonymous guest session for instant use,
  - optional login for saved experiments.

## 13) Observability stack
- **Impact**: Medium
- **Effort**: M
- **Recommendation**:
  - structured logs,
  - request latency p95,
  - move think-time distributions,
  - error budgets.

---

## Implementation Roadmap (Suggested)

## Phase A (1–2 weeks)
- Recruiter Demo Mode
- Explain-This-Move
- README recruiter section
- Basic AI comparison table

## Phase B (2–4 weeks)
- Win probability timeline
- Step-through decision debugger
- Algorithm toggle mode

## Phase C (4+ weeks)
- Live MCTS tree viewer
- Persistent sessions + replay links
- Auth + observability hardening

---

## Highest ROI Upgrade Bundle

If you only do 3 things:
1. One-click Demo Mode
2. Explain-This-Move + top alternatives
3. AI comparison dashboard with benchmark metrics

This bundle gives the strongest immediate recruiter impact per unit effort.