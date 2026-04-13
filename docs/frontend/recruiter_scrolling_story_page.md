# Recruiter Scrolling Story Page Spec — MCTS Laboratory (Blokus RL)

This document is a production-ready narrative + UX specification for a recruiter-facing scrolling page. It is designed for direct implementation in React + Framer Motion (or equivalent scroll animation stack).

## 1) HERO SECTION

### Final polished copy
- **Project name:** MCTS Laboratory — Strategic AI for 4-Player Blokus
- **One-line value proposition:** *Built a high-performance multi-agent decision engine that converts extreme search complexity into measurable competitive advantage and explainable move quality.*

### Visual direction
- **Background concept:** dark, high-contrast board-grid texture with soft player-color gradients (red/blue/green/yellow) and a glowing “search trunk” that branches as scroll progresses.
- **Motion behavior:**
  - Initial parallax drift on gradient layers (subtle, <8px).
  - Search trunk grows from center-bottom to upper-right while hero metrics counters fade in.
  - Scroll cue arrow pulses until first scroll.

### UI structure (React-style)
```tsx
<HeroSection>
  <Eyebrow>MCTS Laboratory</Eyebrow>
  <Headline>Engineering Strategic Intelligence for 4-Player Blokus</Headline>
  <ValueProp>Built a high-performance multi-agent decision engine...</ValueProp>
  <MetricChipRow>
    <MetricChip label="Win-rate Lift" value="+18.4 pp" />
    <MetricChip label="Throughput Gain" value="3.1x" />
    <MetricChip label="Explainability" value="100% traced moves" />
  </MetricChipRow>
  <PrimaryCTA href="#how-it-works">Explore Architecture</PrimaryCTA>
</HeroSection>
```

### Animation spec
- **Scroll behavior:**
  - `progress 0.00 → 0.20`: headline scale `0.96→1.0`, opacity `0.7→1.0`.
  - `progress 0.05 → 0.25`: branch depth visual `2→8` nodes.
  - `progress 0.10 → 0.22`: metric chips stagger in (`60ms` each).
- **Timing / transitions:**
  - Primary transitions: `spring(stiffness:180, damping:24)`.
  - Secondary text: `easeOut` 260ms.

---

## 2) PROBLEM SECTION

### Recruiter-facing narrative
Standard game AI assumptions fail in this domain. In 2-player, zero-sum systems, opponent behavior is relatively stable and minimax framing is straightforward. In 4-player Blokus, each move is affected by shifting incentives across multiple opponents, tactical blocking, and long-horizon mobility trade-offs. The result is a rapidly changing decision landscape where naive search burns compute without reliably improving policy quality.

### Contrast vs simpler systems
- **2-player systems:** lower strategic volatility, cleaner adversarial objective.
- **4-player Blokus:** non-stationary opponent dynamics, tactical coalition effects, and high move-space branching each turn.

### Visual + animation concept
- Split-panel visual:
  - Left: single stable minimax tree.
  - Right: branching explosion with four color channels and dynamic interference lines.
- On scroll, right panel branch count accelerates while left panel remains mostly linear.

### Suggested implementation approach
- Use `position: sticky` container with two synchronized SVG canvases.
- Drive branch density from `useScroll` + `useTransform` values.
- Keep branch rendering lightweight: pre-generated polyline sets, opacity interpolation by scroll.

---

## 3) TECHNICAL INTEREST SECTION

### Deep but readable explanation
- **Branching factor:** legal candidate moves often expand into high double digits, and quality differences among top moves are subtle.
- **Multi-agent complexity:** with 4 players, optimal action depends on anticipating multiple strategic responses, not a single adversary.
- **Optimization challenge:** compute budget is fixed per turn, so strength gains require better move generation, compact state ops, and smarter evaluation—not just “more rollouts.”

### Visual metaphors
- **Tree bloom metaphor:** ring-based branch expansion where each ring doubles visible candidate trajectories.
- **Compute pressure meter:** side gauge showing “candidate growth vs rollout throughput.”
- **Constraint badges:** latency, memory locality, and explainability all shown as simultaneous requirements.

### Optional lightweight diagram (renderable structure)
```json
{
  "visual": "branching_explosion",
  "layers": [
    { "name": "candidate_moves", "range": [24, 96] },
    { "name": "multi_agent_responses", "players": 4 },
    { "name": "throughput_budget", "ms_per_move": 200 }
  ]
}
```

---

## 4) HOW IT WORKS (STICKY SCROLL)

### Section architecture
- Left rail (sticky): persistent visual scene.
- Right rail (scroll): step cards with narrative and technical details.
- Trigger model: each step owns an interval of normalized progress (`0.0-1.0`).

### Step 1 — Game Representation
- **Narrative:** game state is encoded using compact board representations (bitboard-style), enabling fast legality and occupancy checks.
- **Visual:** 20x20 grid transitions into layered bit masks by player.
- **Animation:** tiles collapse into bit lanes during entry; re-expand on exit.
- **Implementation:**
  - `RepresentationScene.tsx`
  - SVG board + mask layers
  - Motion values mapped to lane separation and opacity

### Step 2 — Move Generation
- **Narrative:** frontier-based move generation prioritizes actionable regions and avoids full-board brute-force scans.
- **Visual:** frontier cells glow; legal placements appear in bursts.
- **Animation:** pulsing frontier rings, accepted vs rejected placement colors.
- **Implementation:**
  - `MoveGenerationScene.tsx`
  - Canvas overlay with candidate density map
  - Candidate stream from pre-recorded telemetry payload

### Step 3 — MCTS Loop
- **Narrative:** selection → expansion → rollout → backprop runs under time constraints, continuously refining move estimates.
- **Visual:** four-lane pipeline with counters for visits, value, and uncertainty.
- **Animation:** active lane highlight cycles; counters increment live.
- **Implementation:**
  - `MctsLoopScene.tsx`
  - Data model: snapshots per 20 iterations
  - `requestAnimationFrame` interpolation between snapshots

### Step 4 — Evaluation + Explainability
- **Narrative:** move scores combine immediate outcomes with mobility, territory, and blocking pressure, then expose a human-readable rationale.
- **Visual:** top moves list + weighted contribution bars + text rationale panel.
- **Animation:** score bars tween from 0; rationale lines reveal with stagger.
- **Implementation:**
  - `EvaluationExplainScene.tsx`
  - Factor bars via `recharts` horizontal bars
  - Explanation template + weight/value substitution

---

## 5) KEY INNOVATIONS / ARCHITECTURE

Use 4 cards in a responsive 2x2 grid.

### Card A — Frontier-First Move Generation
- **Explanation:** legal move discovery starts from tactical frontier zones, not from exhaustive board scans.
- **Why it matters:** higher useful rollout density under identical time budgets.
- **Visual concept:** before/after density heatmap with highlighted frontier ring.
- **Pseudo-code:**
```py
for anchor in frontier_cells:
    for t in piece_transforms:
        if is_legal(anchor, t):
            candidates.append((anchor, t))
```

### Card B — Bitboard-Centric Operations
- **Explanation:** board occupancy and constraints represented in compact, bit-aligned structures.
- **Why it matters:** lower per-operation overhead and predictable runtime behavior.
- **Visual concept:** stack of bit layers with AND/OR legality pipeline.

### Card C — Equal-Time Tournament Harness
- **Explanation:** evaluation framework compares agents with identical decision budgets.
- **Why it matters:** fair, recruiter-credible performance claims.
- **Visual concept:** matchup matrix with equal-time badges and confidence intervals.

### Card D — Explain This Move
- **Explanation:** maps model internals into factor-level rationale per recommendation.
- **Why it matters:** demonstrates explainable AI product thinking, not just algorithmic strength.
- **Visual concept:** top move card with contribution bars + generated explanation summary.

### Suggested UI layout
```tsx
<InnovationGrid>
  {cards.map(card => (
    <InnovationCard key={card.title}>
      <CardTitle />
      <CardBody />
      <WhyItMatters />
      <VisualHint />
      <OptionalCodeSnippet />
    </InnovationCard>
  ))}
</InnovationGrid>
```

---

## 6) RESULTS / IMPACT

### Concrete metrics to display (with mock values)
- **Rollout throughput gain:** `3.1x` (optimized vs baseline configuration)
- **Head-to-head win-rate lift:** `+18.4 percentage points`
- **Decision quality stability:** `-27% variance in top-move confidence`
- **Explainability coverage:** `100%` of recommended moves have rationale payload

### Suggested charts/visualizations
- **Throughput chart:** baseline vs optimized bars (`rollouts/sec`).
- **Win-rate chart:** grouped bars by opponent type (random, heuristic, older MCTS).
- **Confidence chart:** line plot of top-1 policy confidence over game phases.
- **Rationale composition:** stacked bars for mobility/territory/blocking contributions.

### Data shape for frontend charts
```ts
export type RecruiterMetricPoint = {
  label: string;
  baseline: number;
  optimized: number;
  unit: 'rollouts_per_sec' | 'win_rate' | 'confidence';
};

export type ExplainabilityBreakdown = {
  moveId: string;
  mobility: number;
  territory: number;
  blocking: number;
  pieceEconomy: number;
};
```

### Animation behavior for metrics
- Number counters animate from 0 on visibility (`duration: 900ms`).
- Bars rise with slight stagger (`80ms`) and decelerating ease.
- Confidence line draws left-to-right as phase labels fade in.

---

## 7) WHY IT MATTERS (Recruiter Positioning)

This project shows full-stack AI engineering capability across algorithm design, systems optimization, instrumentation, and productized explainability. The work demonstrates ability to:

- Build high-performance decision systems under hard runtime constraints.
- Design fair evaluation harnesses and communicate statistically credible outcomes.
- Translate complex model internals into interfaces that non-specialists can trust.
- Deliver end-to-end ownership from core engine decisions to polished UI storytelling.

**Role framing:** strong fit for senior AI engineer, ML systems engineer, or applied research engineering roles where technical depth and product communication must coexist.

---

## Implementation-ready scaffolding

### Route + page composition
```tsx
<Route path="/story" element={<RecruiterStoryPage />} />

<RecruiterStoryPage>
  <HeroSection />
  <ProblemSection />
  <TechnicalInterestSection />
  <StickyHowItWorksSection />
  <InnovationGridSection />
  <ResultsSection />
  <WhyItMattersSection />
</RecruiterStoryPage>
```

### Section config object (for content-driven rendering)
```ts
export type RecruiterStorySection = {
  id: string;
  eyebrow: string;
  title: string;
  narrative: string;
  visualDirection: string;
  animation: {
    trigger: string;
    from: string;
    to: string;
    timing: string;
  }[];
};
```

### Motion stack recommendation
- **Primary:** Framer Motion (`useScroll`, `useTransform`, `AnimatePresence`)
- **Fallback:** CSS scroll timelines + IntersectionObserver
- **Performance:** precompute heavy geometry, avoid reflow-heavy DOM updates, prefer canvas/SVG for branch scenes

---

## Implementation Summary

### Fully generated and ready to use
- Complete recruiter-grade narrative copy for all required sections.
- UI structure and component hierarchy for direct React implementation.
- Detailed animation behavior and transition timing guidance.
- Chart/data contracts and mock metric payload shapes.
- Sticky-scroll step-by-step scene plan for “How It Works.”

### Should be reviewed by a human
- Exact metric values before public publishing.
- Brand tone calibration (more technical vs more executive voice).
- Final visual style tokens (color, typography, spacing) aligned to portfolio brand.

### Still needs implementation
- Hooking live backend telemetry and arena metrics into chart data.
- Framer Motion scene implementation for branch-growth visuals.
- Responsive QA, accessibility pass, and cross-browser performance tuning.
