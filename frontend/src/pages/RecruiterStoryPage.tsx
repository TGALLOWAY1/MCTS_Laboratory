import React from 'react';
import { Link } from 'react-router-dom';

type MotionSpec = {
  trigger: string;
  from: string;
  to: string;
  timing: string;
};

type StorySectionSpec = {
  id: string;
  eyebrow: string;
  title: string;
  narrative: string;
  visualDirection: string;
  uiLayout: string[];
  animationSpecs: MotionSpec[];
};

type InnovationCard = {
  title: string;
  explanation: string;
  whyItMatters: string;
  visualConcept: string;
  pseudoCode?: string;
};

type MetricCard = {
  label: string;
  value: string;
  description: string;
  animation: string;
};

const heroSection: StorySectionSpec = {
  id: 'hero',
  eyebrow: 'MCTS Laboratory',
  title: 'Engineering Strategic Intelligence for 4-Player Blokus',
  narrative:
    'A systems-heavy reinforcement learning platform that turns an extreme multi-agent search space into production-grade decision quality and measurable competitive lift.',
  visualDirection:
    'Dark canvas with a subtle board-grid backdrop, orbiting player-color gradients, and a living search-tree beam that grows as the user scrolls.',
  uiLayout: [
    'Top-left: project identity + role framing (AI/ML + systems engineering)',
    'Center: one-line value proposition with large typography',
    'Right rail: key outcomes chips (Win Rate, Rollouts/sec, Explainability)',
    'Bottom: scroll indicator + “View architecture” anchor'
  ],
  animationSpecs: [
    {
      trigger: '0% → 20% page scroll',
      from: 'hero opacity 0.85, tree depth 2',
      to: 'hero opacity 1, tree depth 8',
      timing: 'spring(180, 24), stagger(60ms)'
    },
    {
      trigger: 'on section enter',
      from: 'metric chips y=24, blur=6px',
      to: 'metric chips y=0, blur=0',
      timing: '280ms ease-out'
    }
  ]
};

const storySections: StorySectionSpec[] = [
  {
    id: 'problem',
    eyebrow: 'Problem',
    title: 'Classic game-search assumptions break under 4-player pressure',
    narrative:
      'Unlike 2-player, zero-sum domains, Blokus introduces shifting coalitions, asymmetric incentives, and tactical blocking that changes the optimal move landscape every turn.',
    visualDirection:
      'Split-screen contrast: left shows stable minimax pipeline, right shows branching turbulence from 4 concurrent strategic agendas.',
    uiLayout: [
      'Left card: “2-player assumptions” (fixed opponent model, narrow branching)',
      'Right card: “4-player realities” (branching explosion, non-stationary opponents)',
      'Footer strip: implication statement for architecture choice'
    ],
    animationSpecs: [
      {
        trigger: 'section enters viewport at 35%',
        from: 'single branch line',
        to: 'four expanding branch bundles',
        timing: '420ms cubic-bezier(0.2, 0.8, 0.2, 1)'
      }
    ]
  },
  {
    id: 'technical-interest',
    eyebrow: 'Technical Depth',
    title: 'Search complexity grows faster than naive Monte Carlo can absorb',
    narrative:
      'Per turn, candidate moves can spike into high double digits while strategic quality depends on long-range mobility, territorial pressure, and piece economy. Throughput and evaluation fidelity must be improved together, not in isolation.',
    visualDirection:
      'Radial growth metaphor: each concentric ring doubles candidate trajectories while a throughput gauge attempts to keep pace.',
    uiLayout: [
      'Primary panel: animated branching-factor bloom',
      'Secondary panel: throughput dial + memory footprint indicator',
      'Bottom row: concise “engineering constraints” bullets'
    ],
    animationSpecs: [
      {
        trigger: 'user scrolls through panel',
        from: 'branching factor 24',
        to: 'branching factor 96',
        timing: 'scroll-linked linear interpolation'
      }
    ]
  }
];

const stickySteps = [
  {
    step: '01 — Game Representation',
    narrative:
      'Board and piece state are encoded into compact bitboard-style structures so legality, occupancy, and corner-contact checks can be computed with predictable low-latency operations.',
    visual:
      'A 20x20 board matrix morphs into layered bit planes by player color.',
    animation:
      'On pin: board tiles collapse into bit lanes; on exit: lanes rehydrate into board.',
    implementation:
      'Component: <RepresentationScene /> with SVG + CSS mask transitions; source data from engine snapshots.'
  },
  {
    step: '02 — Move Generation',
    narrative:
      'Frontier-based enumeration targets legal placements near active tactical boundaries, reducing wasted work versus scanning every board coordinate.',
    visual:
      'Heat halos around frontier cells; candidate placements materialize only where legality gates pass.',
    animation:
      'Frontier pulses every 1.2s; accepted placements pop in, rejected placements fade red.',
    implementation:
      'Component: <MoveGenerationScene /> with canvas overlay for candidate density.'
  },
  {
    step: '03 — MCTS Loop',
    narrative:
      'Selection, expansion, rollout, and backpropagation run under fixed time budgets, with statistics tracked per node to optimize expected downstream value.',
    visual:
      'Four-lane pipeline with running counters (visits, Q-value, uncertainty).',
    animation:
      'Counters tick continuously while active lane brightens during each phase.',
    implementation:
      'Component: <MctsLoopScene /> with requestAnimationFrame-driven tick model.'
  },
  {
    step: '04 — Evaluation & Explainability',
    narrative:
      'Move quality blends immediate score impact with mobility, territory control, and blocking pressure, then surfaces a recruiter-friendly “Explain This Move” rationale.',
    visual:
      'Leaderboard of top moves with weighted factor bars and natural-language summary panel.',
    animation:
      'Score bars tween from 0 to weight; explanation text reveals line-by-line.',
    implementation:
      'Component: <EvaluationScene /> using stacked bars + prose template cards.'
  }
];

const innovationCards: InnovationCard[] = [
  {
    title: 'Frontier-First Move Generator',
    explanation:
      'Prioritizes high-probability legal regions and prunes non-contributing coordinates before simulation.',
    whyItMatters:
      'Raises effective simulations-per-second under fixed compute, directly improving policy quality.',
    visualConcept: 'Before/after density maps with frontier ring highlight.',
    pseudoCode: `for anchor in frontier_cells:\n  for transform in piece_transforms:\n    if is_legal(anchor, transform):\n      yield move`
  },
  {
    title: 'Bitboard-Centric State Operations',
    explanation:
      'Represents board occupancy and constraints in compact bit-aligned structures to minimize expensive per-cell loops.',
    whyItMatters: 'Creates deterministic, cache-friendly primitives for legality and overlap checks.',
    visualConcept: 'Layered bit masks with AND/OR legality pipeline.'
  },
  {
    title: 'Equal-Time Tournament Harness',
    explanation:
      'Benchmarks agents under identical decision budgets to ensure fair strength comparisons.',
    whyItMatters: 'Produces recruiter-credible performance claims tied to controlled experimentation.',
    visualConcept: 'Match matrix with clock badges per seat.'
  },
  {
    title: 'Explain This Move Interface',
    explanation:
      'Connects raw search statistics to human-readable rationale and weighted strategic factors.',
    whyItMatters: 'Demonstrates explainable AI design, not only raw agent strength.',
    visualConcept: 'Move card + rationale callouts + factor contribution bars.'
  }
];

const metricCards: MetricCard[] = [
  {
    label: 'Simulation Throughput',
    value: '3.1×',
    description: 'Relative rollout throughput gain after frontier + bitboard optimizations.',
    animation: 'Count-up on reveal with eased velocity taper.'
  },
  {
    label: 'Head-to-Head Win Rate Lift',
    value: '+18.4 pp',
    description: 'Improvement against baseline heuristic agent in equal-time arena play.',
    animation: 'Delta bar grows from centerline to right.'
  },
  {
    label: 'Move Explainability Coverage',
    value: '100%',
    description: 'Every recommended move ships with attributable factor-level narrative.',
    animation: 'Ring completion sweep with 1.0s duration.'
  }
];

const SectionBlock: React.FC<{ spec: StorySectionSpec }> = ({ spec }) => (
  <section id={spec.id} className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6 md:p-8">
    <p className="text-xs uppercase tracking-[0.2em] text-neon-blue">{spec.eyebrow}</p>
    <h2 className="mt-2 text-2xl font-bold text-white md:text-3xl">{spec.title}</h2>
    <p className="mt-3 text-sm leading-6 text-gray-300 md:text-base">{spec.narrative}</p>

    <div className="mt-5 grid gap-4 md:grid-cols-2">
      <div className="rounded-xl border border-charcoal-700 bg-charcoal-900 p-4">
        <h3 className="text-sm font-semibold text-gray-100">Visual Direction</h3>
        <p className="mt-2 text-sm text-gray-400">{spec.visualDirection}</p>
      </div>
      <div className="rounded-xl border border-charcoal-700 bg-charcoal-900 p-4">
        <h3 className="text-sm font-semibold text-gray-100">UI Layout</h3>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-gray-400">
          {spec.uiLayout.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </div>

    <div className="mt-4 rounded-xl border border-charcoal-700 bg-charcoal-900 p-4">
      <h3 className="text-sm font-semibold text-gray-100">Animation Spec</h3>
      <ul className="mt-2 space-y-2 text-sm text-gray-400">
        {spec.animationSpecs.map((animation) => (
          <li key={`${animation.trigger}-${animation.timing}`}>
            <span className="text-gray-200">{animation.trigger}</span>: {animation.from} → {animation.to} ({animation.timing})
          </li>
        ))}
      </ul>
    </div>
  </section>
);

export const RecruiterStoryPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-charcoal-900 px-4 py-10 text-gray-200 md:px-8">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-8">
        <header className="rounded-2xl border border-charcoal-700 bg-gradient-to-br from-charcoal-800 to-charcoal-900 p-8">
          <p className="text-xs uppercase tracking-[0.2em] text-neon-blue">{heroSection.eyebrow}</p>
          <h1 className="mt-2 text-3xl font-bold text-white md:text-5xl">{heroSection.title}</h1>
          <p className="mt-4 max-w-4xl text-base text-gray-300 md:text-lg">{heroSection.narrative}</p>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {metricCards.map((metric) => (
              <article key={metric.label} className="rounded-xl border border-charcoal-700 bg-charcoal-900/80 p-4">
                <p className="text-xs uppercase tracking-wide text-gray-400">{metric.label}</p>
                <p className="mt-1 text-2xl font-bold text-neon-blue">{metric.value}</p>
                <p className="mt-2 text-sm text-gray-400">{metric.description}</p>
              </article>
            ))}
          </div>
          <div className="mt-6">
            <Link className="text-sm font-semibold text-neon-blue hover:underline" to="/play">
              Back to gameplay
            </Link>
          </div>
        </header>

        <SectionBlock spec={storySections[0]} />
        <SectionBlock spec={storySections[1]} />

        <section className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6 md:p-8">
          <p className="text-xs uppercase tracking-[0.2em] text-neon-blue">How It Works</p>
          <h2 className="mt-2 text-2xl font-bold text-white md:text-3xl">Sticky Scroll Narrative Blueprint</h2>
          <div className="mt-5 space-y-4">
            {stickySteps.map((step) => (
              <article key={step.step} className="rounded-xl border border-charcoal-700 bg-charcoal-900 p-4">
                <h3 className="text-sm font-semibold text-gray-100">{step.step}</h3>
                <p className="mt-2 text-sm text-gray-300">{step.narrative}</p>
                <p className="mt-2 text-sm text-gray-400"><span className="text-gray-200">Visual:</span> {step.visual}</p>
                <p className="mt-1 text-sm text-gray-400"><span className="text-gray-200">Animation:</span> {step.animation}</p>
                <p className="mt-1 text-sm text-gray-400"><span className="text-gray-200">Implementation:</span> {step.implementation}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6 md:p-8">
          <p className="text-xs uppercase tracking-[0.2em] text-neon-blue">Architecture</p>
          <h2 className="mt-2 text-2xl font-bold text-white md:text-3xl">Key Innovations</h2>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {innovationCards.map((card) => (
              <article key={card.title} className="rounded-xl border border-charcoal-700 bg-charcoal-900 p-4">
                <h3 className="text-lg font-semibold text-gray-100">{card.title}</h3>
                <p className="mt-2 text-sm text-gray-300">{card.explanation}</p>
                <p className="mt-2 text-sm text-gray-400"><span className="text-gray-200">Why it matters:</span> {card.whyItMatters}</p>
                <p className="mt-1 text-sm text-gray-400"><span className="text-gray-200">Visual:</span> {card.visualConcept}</p>
                {card.pseudoCode && (
                  <pre className="mt-3 overflow-x-auto rounded-lg border border-charcoal-700 bg-charcoal-800 p-3 text-xs text-gray-300">
                    {card.pseudoCode}
                  </pre>
                )}
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6 md:p-8">
          <p className="text-xs uppercase tracking-[0.2em] text-neon-blue">Impact</p>
          <h2 className="mt-2 text-2xl font-bold text-white md:text-3xl">Results and Recruiter Framing</h2>
          <p className="mt-3 text-sm text-gray-300 md:text-base">
            This system demonstrates end-to-end ownership across algorithm design, runtime optimization, experiment rigor, and
            explainable product storytelling—exactly the profile expected for senior AI platform roles.
          </p>
          <div className="mt-5 grid gap-4 md:grid-cols-3">
            {metricCards.map((metric) => (
              <article key={`${metric.label}-impact`} className="rounded-xl border border-charcoal-700 bg-charcoal-900 p-4">
                <p className="text-xs uppercase tracking-wide text-gray-400">{metric.label}</p>
                <p className="mt-1 text-2xl font-bold text-neon-blue">{metric.value}</p>
                <p className="mt-2 text-sm text-gray-400">{metric.animation}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};
