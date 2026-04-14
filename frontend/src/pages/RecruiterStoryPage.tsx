import React, { useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import {
  Target,
  GitBranch,
  Cpu,
  Activity,
  Zap,
  TrendingUp,
  Workflow,
  Eye,
  Database,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Layers,
  Gauge,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Small inline building blocks used across sections                  */
/* ------------------------------------------------------------------ */

type Accent = 'blue' | 'green' | 'yellow' | 'red' | 'white';
const accentMap: Record<Accent, string> = {
  blue: 'text-neon-blue',
  green: 'text-neon-green',
  yellow: 'text-neon-yellow',
  red: 'text-neon-red',
  white: 'text-white',
};

const MetricChip: React.FC<{ value: string; label: string; accent?: Accent; delay?: number }> = ({
  value,
  label,
  accent = 'white',
  delay = 0,
}) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ delay }}
    className="flex flex-col items-center rounded-xl border border-charcoal-700 bg-charcoal-800/80 px-8 py-4 backdrop-blur-sm"
  >
    <span className={`text-3xl font-bold ${accentMap[accent]}`}>{value}</span>
    <span className="mt-1 text-xs uppercase tracking-widest text-gray-400">{label}</span>
  </motion.div>
);

const SectionEyebrow: React.FC<{ color: Accent; children: React.ReactNode }> = ({ color, children }) => (
  <span className={`text-xs font-bold uppercase tracking-widest ${accentMap[color]}`}>{children}</span>
);

const CapturePlaceholder: React.FC<{ label: string; cmd?: string; aspect?: string }> = ({
  label,
  cmd,
  aspect = 'aspect-[16/9]',
}) => (
  <div
    className={`relative ${aspect} w-full rounded-2xl border-2 border-dashed border-charcoal-600 bg-charcoal-800/40 flex flex-col items-center justify-center p-6 text-center`}
  >
    <span className="inline-flex items-center gap-2 rounded-full border border-neon-yellow/40 bg-neon-yellow/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-neon-yellow">
      <AlertTriangle size={12} /> Capture TODO
    </span>
    <div className="mt-4 max-w-md text-sm text-charcoal-500">{label}</div>
    {cmd && (
      <pre className="mt-3 max-w-md whitespace-pre-wrap break-words rounded bg-charcoal-900/60 px-3 py-2 text-left text-[10px] leading-snug text-charcoal-500">
        {cmd}
      </pre>
    )}
  </div>
);

type LayerVerdict = 'win' | 'mixed' | 'loss';
const verdictStyle: Record<LayerVerdict, { ring: string; badge: string; icon: JSX.Element; text: string }> = {
  win: {
    ring: 'border-neon-green/40 hover:border-neon-green',
    badge: 'bg-neon-green/10 text-neon-green border-neon-green/30',
    icon: <CheckCircle2 size={12} />,
    text: 'Win',
  },
  mixed: {
    ring: 'border-neon-yellow/40 hover:border-neon-yellow',
    badge: 'bg-neon-yellow/10 text-neon-yellow border-neon-yellow/30',
    icon: <AlertTriangle size={12} />,
    text: 'Mixed',
  },
  loss: {
    ring: 'border-neon-red/40 hover:border-neon-red',
    badge: 'bg-neon-red/10 text-neon-red border-neon-red/30',
    icon: <XCircle size={12} />,
    text: 'No lift',
  },
};

const LayerCard: React.FC<{
  id: string;
  title: string;
  headline: string;
  body: string;
  verdict: LayerVerdict;
  delay?: number;
}> = ({ id, title, headline, body, verdict, delay = 0 }) => {
  const v = verdictStyle[verdict];
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-10%' }}
      transition={{ duration: 0.5, delay }}
      className={`group relative flex flex-col rounded-xl border bg-charcoal-800/70 p-6 transition-colors ${v.ring}`}
    >
      <div className="flex items-center justify-between">
        <span className="font-mono text-xs tracking-widest text-gray-500">{id}</span>
        <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${v.badge}`}>
          {v.icon}
          {v.text}
        </span>
      </div>
      <h4 className="mt-3 text-lg font-bold text-white">{title}</h4>
      <div className="mt-2 text-sm font-semibold text-gray-200">{headline}</div>
      <p className="mt-2 text-sm leading-relaxed text-gray-400">{body}</p>
    </motion.div>
  );
};

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

export const RecruiterStoryPage: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end start'],
  });

  const heroOpacity = useTransform(scrollYProgress, [0, 0.2], [1, 0]);
  const heroY = useTransform(scrollYProgress, [0, 0.2], [0, -50]);
  const treeScale = useTransform(scrollYProgress, [0, 0.3], [1, 1.4]);

  return (
    <div ref={containerRef} className="min-h-screen bg-charcoal-900 text-gray-200">

      {/* ================================================================== */}
      {/*  1. HERO                                                             */}
      {/* ================================================================== */}
      <section className="relative flex min-h-[90vh] flex-col items-center justify-center overflow-hidden border-b border-charcoal-700 bg-gradient-to-b from-charcoal-800 to-charcoal-900 px-6 py-20 text-center">
        <motion.div
          style={{ opacity: heroOpacity, scale: treeScale }}
          className="absolute inset-0 z-0 flex items-center justify-center opacity-30"
        >
          <img
            src="/assets/hero_search_tree_1776109554975.png"
            alt=""
            aria-hidden="true"
            className="h-full w-full object-cover object-center opacity-70"
          />
          <div className="absolute inset-0 bg-charcoal-900/50" />
        </motion.div>

        <motion.div
          style={{ y: heroY }}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="relative z-10 mx-auto max-w-5xl"
        >
          <span className="mb-4 inline-flex items-center gap-2 rounded-full border border-neon-blue/30 bg-neon-blue/10 px-4 py-1.5 text-xs font-semibold tracking-widest text-neon-blue">
            <Cpu size={14} /> AI / ML Systems Engineering
          </span>
          <h1 className="mt-4 text-5xl font-extrabold tracking-tight text-white md:text-7xl">
            Engineering Strategic Intelligence for <br />
            <span className="bg-gradient-to-r from-neon-blue to-neon-green bg-clip-text text-transparent">4-Player Blokus</span>
          </h1>
          <p className="mx-auto mt-8 max-w-3xl text-lg text-gray-300 md:text-xl">
            A nine-layer optimization program that turns a 534-move branching factor and four non-stationary opponents into measurable, explainable decision quality.
          </p>

          <div className="mt-12 flex flex-wrap justify-center gap-6">
            <MetricChip value="76%" label="Calibrated Eval Win Rate" accent="green" delay={0.2} />
            <MetricChip value="3.1×" label="Parallel Throughput Gain" accent="blue" delay={0.3} />
            <MetricChip value="13,332" label="Labeled Game States" accent="white" delay={0.4} />
          </div>

          <div className="mt-10 text-xs uppercase tracking-widest text-gray-500">
            Evidence-backed: 88 arena runs · 700 self-play games · 9 optimization layers
          </div>

          <div className="mt-14 flex flex-wrap items-center justify-center gap-6">
            <Link
              to="/play"
              className="inline-flex items-center gap-2 rounded-full border border-neon-blue bg-neon-blue/10 px-6 py-3 text-sm font-semibold tracking-widest text-white transition-all hover:bg-neon-blue/20 hover:scale-105 active:scale-95"
            >
              <Activity size={14} /> Play a Game
            </Link>
            <Link
              to="/benchmark"
              className="inline-flex items-center gap-2 rounded-full border border-charcoal-600 px-6 py-3 text-sm font-semibold tracking-widest text-gray-300 transition-colors hover:border-neon-green hover:text-neon-green"
            >
              <BarChart3 size={14} /> See the Arena
            </Link>
          </div>
        </motion.div>
      </section>

      {/* ================================================================== */}
      {/*  2. WHY THE GAME IS HARD                                             */}
      {/* ================================================================== */}
      <section className="relative px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <SectionEyebrow color="red">The Challenge</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Four agents, 534 legal moves,<br />no stable minimax
            </h2>
            <p className="mx-auto mt-4 max-w-3xl text-gray-400">
              Two-player zero-sum search assumes one adversary with stable incentives. 4-player Blokus breaks every one of those assumptions — shifting coalitions, long-horizon mobility, and king-making all reshape the optimal move landscape every turn.
            </p>
          </div>

          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-20%' }}
            variants={{ visible: { transition: { staggerChildren: 0.2 } } }}
            className="grid gap-8 overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800 lg:grid-cols-2"
          >
            <motion.div
              variants={{ hidden: { opacity: 0, x: -20 }, visible: { opacity: 1, x: 0 } }}
              className="flex flex-col border-b border-charcoal-700 lg:border-b-0 lg:border-r"
            >
              <div className="flex-1 p-8">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-neon-blue/10 text-neon-blue">
                  <Activity />
                </div>
                <h3 className="text-xl font-bold text-white">2-Player Assumptions</h3>
                <ul className="mt-3 space-y-2 text-sm text-gray-400">
                  <li>• Stable minimax with one adversary</li>
                  <li>• Fixed opponent model, clean backup</li>
                  <li>• Narrow branching, known convergence</li>
                </ul>
              </div>
            </motion.div>

            <motion.div
              variants={{ hidden: { opacity: 0, x: 20 }, visible: { opacity: 1, x: 0 } }}
              className="flex flex-col"
            >
              <div className="flex-1 p-8">
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-neon-red/10 text-neon-red">
                  <GitBranch />
                </div>
                <h3 className="text-xl font-bold text-white">4-Player Realities</h3>
                <ul className="mt-3 space-y-2 text-sm text-gray-400">
                  <li>• Peak branching <span className="text-neon-red font-semibold">534 moves</span> at turn 17</li>
                  <li>• Three non-stationary opponents, no minimax</li>
                  <li>• King-making + tactical blocks dominate</li>
                </ul>
              </div>
            </motion.div>

            <div className="col-span-1 lg:col-span-2 overflow-hidden border-t border-charcoal-700 bg-charcoal-800/60">
              {/* TODO capture: 2P-vs-4P split-tree graphic → frontend/public/assets/story/split_tree.png
                  Candidates: NB3 prompt in plan doc §Remaining, or render with matplotlib
                  (nx.DiGraph tree with 2 vs 534 children). */}
              <CapturePlaceholder
                label="Split-screen 2P vs 4P tree bloom. Left: tidy binary tree. Right: radial 534-branch explosion."
                cmd={'# generate via matplotlib or NB3 prompt (see plan)\n# → frontend/public/assets/story/split_tree.png'}
                aspect="aspect-[21/9]"
              />
            </div>
          </motion.div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  3. WHY NAÏVE MCTS FAILS                                             */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <SectionEyebrow color="yellow">The First Failure</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold leading-tight text-white md:text-5xl">
              The first MCTS implementation <span className="text-neon-red">lost to heuristic rollouts</span>
            </h2>
            <p className="mt-6 text-gray-400">
              A default MCTS agent with 1,000 iterations per move scored <strong className="text-white">-8.0 points</strong> below a heuristic-only agent. Iteration efficiency averaged just <strong className="text-white">11%</strong> — search budget spread across 534 children produces Q-estimates from 3–4 visits apiece. That's noise, not signal.
            </p>
            <ul className="mt-8 space-y-4">
              <li className="flex items-start gap-3">
                <Target className="mt-1 shrink-0 text-neon-yellow" size={18} />
                <span className="text-sm text-gray-300">
                  <strong className="text-white">Iteration efficiency 11%</strong> across 80 turn indices; 78/80 turns below 50% utilization.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <Gauge className="mt-1 shrink-0 text-neon-yellow" size={18} />
                <span className="text-sm text-gray-300">
                  <strong className="text-white">Q-values collapse</strong> when each child sees 3–4 visits — UCB1 can't discriminate.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <AlertTriangle className="mt-1 shrink-0 text-neon-yellow" size={18} />
                <span className="text-sm text-gray-300">
                  <strong className="text-white">Takeaway:</strong> Throwing more iterations at a broken baseline will never close the gap. Every layer that followed was shaped by this result.
                </span>
              </li>
            </ul>
          </div>

          <div className="relative">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8 }}
              className="relative flex aspect-square items-center justify-center overflow-hidden rounded-full border border-charcoal-700 bg-charcoal-800 p-12 shadow-2xl shadow-neon-yellow/5"
            >
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-neon-red/10 via-charcoal-800/20 to-transparent blur-md" />
              <div className="relative z-10 text-center">
                <div className="text-7xl font-black tracking-tighter text-neon-red">−8.0</div>
                <div className="mt-2 text-sm font-semibold uppercase tracking-widest text-gray-400">
                  Point deficit<br />vs. heuristic-only
                </div>
                <div className="mt-6 text-xs text-gray-500">
                  Source: <code>archive/reports/layer1_baseline_report.md</code>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  4. ENGINE PERFORMANCE FOUNDATION                                     */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="blue">Engine Foundation</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Rollout depth is <span className="text-neon-blue">100× more expensive</span> than it looks
            </h2>
            <p className="mt-6 text-gray-400">
              Before search quality could improve, the engine had to be fast enough to run real experiments. Bitboard state with O(1) legality checks and frontier-based move generation cut candidate placements 10–20×. Even so, rollout depth carries a brutal cliff — in the opening, depth-0 evaluation runs at 466 iter/s while depth-5 rollouts crawl at 3.5 iter/s.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6"
            >
              <Layers className="text-neon-blue" />
              <h3 className="mt-4 text-lg font-bold text-white">Bitboard representation</h3>
              <p className="mt-2 text-sm text-gray-400">
                Board, per-player occupancy, and piece masks as 64-bit integer layers. Overlap + adjacency checks become single bitwise ops.
              </p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6"
            >
              <Workflow className="text-neon-green" />
              <h3 className="mt-4 text-lg font-bold text-white">Frontier-first enumeration</h3>
              <p className="mt-2 text-sm text-gray-400">
                Legal placements are scanned against the <span className="text-neon-green">20–30 active frontier cells</span>, not all 400 board squares. 10–20× fewer candidates, same correctness.
              </p>
            </motion.div>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.2 }}
              className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6"
            >
              <Zap className="text-neon-red" />
              <h3 className="mt-4 text-lg font-bold text-white">The rollout cliff</h3>
              <p className="mt-2 text-sm text-gray-400">
                Depth 0 → 5 in the opening: <span className="font-mono text-neon-red">466 → 3.5</span> iter/s. <strong className="text-white">133× slowdown</strong>. Every depth choice is a time-budget decision, not a hyperparameter.
              </p>
            </motion.div>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-2">
            <figure className="overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
              <img
                src="/assets/bitboard_layers_1776109582947.png"
                alt="Bitboard layer representation of the Blokus board"
                className="w-full object-cover"
              />
              <figcaption className="px-4 py-3 text-xs uppercase tracking-widest text-gray-500">
                Bitboard layers · O(1) legality
              </figcaption>
            </figure>
            <figure className="overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
              <img
                src="/assets/move_gen_halos_1776109596022.png"
                alt="Frontier-based move generation with placement halos"
                className="w-full object-cover"
              />
              <figcaption className="px-4 py-3 text-xs uppercase tracking-widest text-gray-500">
                Frontier halos · 10–20× fewer candidates
              </figcaption>
            </figure>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  5. THE PIPELINE (sticky scroll — aesthetic preserved)                */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-charcoal-900">
        <div className="mx-auto max-w-7xl px-6 md:px-12 lg:px-24">
          <div className="pt-24">
            <SectionEyebrow color="green">How It Works</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">The Search Pipeline</h2>
            <p className="mt-4 max-w-2xl text-gray-400">
              Four stages run every turn, under a fixed wall-clock budget. Every stage is instrumented — diagnostics flow straight through to the frontend.
            </p>
          </div>

          <div className="relative flex flex-col lg:flex-row">
            <div className="pb-[30vh] pt-12 lg:w-1/2">
              <div className="space-y-[40vh]">
                {[
                  {
                    step: '01',
                    title: 'Game Representation',
                    desc: 'Board, piece, and per-player state encoded as bitboard layers so legality, occupancy, and corner-contact checks are predictable single-cycle operations.',
                    img: '/assets/bitboard_layers_1776109582947.png',
                  },
                  {
                    step: '02',
                    title: 'Move Generation',
                    desc: 'Frontier-first enumeration targets only the 20–30 cells adjacent to active tactical boundaries — skipping the rest of the 400-cell board entirely.',
                    img: '/assets/move_gen_halos_1776109596022.png',
                  },
                  {
                    step: '03',
                    title: 'MCTS Loop',
                    desc: 'Selection (UCB1 + RAVE blend), expansion, rollout (random policy, depth-5 cutoff, minimax backup α=0.25), backpropagation. Per-node diagnostics streamed to the frontend trace.',
                    img: '/assets/innovation_split_screen_1776109569579.png',
                  },
                  {
                    step: '04',
                    title: 'Evaluation & Explainability',
                    desc: 'ML-calibrated weights score terminal states. Every decision surfaces top-k candidate moves, visit counts, and Q-values to the Explain panel.',
                    img: '/assets/hero_search_tree_1776109554975.png',
                  },
                ].map((item, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0.2 }}
                    whileInView={{ opacity: 1 }}
                    viewport={{ margin: '-40% 0px -40% 0px' }}
                    className="prose prose-invert max-w-md"
                  >
                    <span className="text-5xl font-black text-charcoal-700">{item.step}</span>
                    <h3 className="mt-4 text-2xl font-bold text-white">{item.title}</h3>
                    <p className="mt-4 text-lg leading-relaxed text-gray-400">{item.desc}</p>
                  </motion.div>
                ))}
              </div>
            </div>

            <div className="sticky top-0 hidden h-screen py-24 lg:block lg:w-1/2">
              <div className="flex h-full w-full items-center justify-center overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/50 p-6">
                <img
                  src="/assets/innovation_split_screen_1776109569579.png"
                  alt="MCTS loop and evaluation split-screen"
                  className="max-h-full max-w-full object-contain"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  6. EXPERIMENTATION INFRASTRUCTURE                                    */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="blue">Infrastructure</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              <span className="text-neon-blue">88 tournaments.</span> Deterministic seeds. TrueSkill-rated.
            </h2>
            <p className="mt-6 text-gray-400">
              Every optimization claim on this page survives the same 4-player round-robin arena with fixed seeds, per-agent TrueSkill ratings, and seat-bias correction. Without that discipline, layer-over-layer results are noise.
            </p>
          </div>

          <div className="mb-10 grid gap-4 md:grid-cols-4">
            <MetricChip value="88" label="Archived Arena Runs" accent="blue" />
            <MetricChip value="700" label="Self-Play Games" accent="green" />
            <MetricChip value="13,332" label="Labeled States" accent="white" />
            <MetricChip value="p < 0.05" label="Seat-Bias Corrected" accent="yellow" />
          </div>

          <div className="grid gap-8 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <ul className="space-y-4 text-sm">
                <li className="flex items-start gap-3">
                  <Database className="mt-1 shrink-0 text-neon-blue" size={16} />
                  <span className="text-gray-300">
                    <strong className="text-white">4-player round-robin</strong>, 25 games per experiment, identical seeds across agents.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <TrendingUp className="mt-1 shrink-0 text-neon-green" size={16} />
                  <span className="text-gray-300">
                    <strong className="text-white">TrueSkill (μ, σ)</strong> per agent with pairwise head-to-head records.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <Target className="mt-1 shrink-0 text-neon-yellow" size={16} />
                  <span className="text-gray-300">
                    <strong className="text-white">Seat-position bias</strong> detected at p &lt; 0.05 and corrected across configs.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <Workflow className="mt-1 shrink-0 text-neon-red" size={16} />
                  <span className="text-gray-300">
                    <strong className="text-white">Full reproducibility</strong>: configs, seeds, summaries, game logs preserved in <code className="text-xs">arena_runs/</code>.
                  </span>
                </li>
              </ul>
            </div>
            <div className="lg:col-span-3">
              {/* TODO capture: run benchmark page → frontend/public/assets/story/capture_benchmark.png */}
              <CapturePlaceholder
                label="Benchmark page · TrueSkill leaderboard + pairwise win matrix for a layer-comparison tournament."
                cmd={'cd frontend && npm run dev\n# open http://localhost:3000/benchmark\n# capture 1920×1080 → frontend/public/assets/story/capture_benchmark.png'}
                aspect="aspect-[16/10]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  7. GAMEPLAY OPTIMIZATION LAYERS (L3 → L9)                            */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="green">Layers 3 → 9</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Seven layers of search quality,<br />each isolated and measured
            </h2>
            <p className="mt-6 text-gray-400">
              Each enhancement was added as its own layer with an isolated arena evaluation. The honest result: some layers won big, some taught us that <em>less is more</em>, and a few lost outright. Shipping the losses alongside the wins is the whole point of the lab.
            </p>
          </div>

          <figure className="mb-12 overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
            <img
              src="/assets/story/layer_progression.png"
              alt="Layer-by-layer win-rate progression chart"
              className="w-full object-contain"
            />
            <figcaption className="px-4 py-3 text-xs uppercase tracking-widest text-gray-500">
              Cumulative win-rate by layer · source: <code>arena_visuals/01_layer_progression.png</code>
            </figcaption>
          </figure>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <LayerCard
              id="L3"
              title="Progressive Widening"
              headline="+64% win rate"
              body="Caps tree width as a function of visits. Branching factor drops without move-quality loss. Mean score 92.4 vs. 76.0 baseline."
              verdict="win"
            />
            <LayerCard
              id="L4"
              title="Rollout Policy"
              headline="54% WR vs. 0% (pure eval)"
              body="Random rollout at depth 5 beats 1000-iter pure static eval outright. Random is 10× faster than two-ply and outscores heuristic — bias hurts more than speed helps."
              verdict="win"
              delay={0.05}
            />
            <LayerCard
              id="L5"
              title="RAVE (k=1000)"
              headline="4× convergence speedup"
              body="50ms RAVE budget beats 200ms vanilla budget. 44.7% WR vs. 14.7% baseline. Progressive history *hurts* when combined (redundant exploration)."
              verdict="win"
              delay={0.1}
            />
            <LayerCard
              id="L6"
              title="ML-Calibrated Eval"
              headline="76% WR vs. 12% defaults"
              body="Regression on 13,332 states fixed three miscalibrations in hand-tuned weights, including one sign error. The headline moment of the project."
              verdict="win"
              delay={0.15}
            />
            <LayerCard
              id="L7"
              title="Opponent Modeling"
              headline="No reliable lift, 2.4× slower"
              body="Alliance detection, king-maker awareness, asymmetric rollouts. Activates correctly, but compute cost exceeds marginal benefit at real iteration budgets."
              verdict="loss"
              delay={0.2}
            />
            <LayerCard
              id="L8"
              title="Root Parallelization"
              headline="3.1× throughput, 46% WR"
              body="Multiprocessing root-parallel scales near-linearly through 4 workers. Tree-parallel with virtual loss is slower than single-threaded (Python GIL)."
              verdict="win"
              delay={0.25}
            />
            <LayerCard
              id="L9"
              title="Adaptive Rollout Depth"
              headline="36% WR + 1.64× faster"
              body="Shallow eval in high-BF early game, deep rollouts when BF collapses late. Stacking adaptive exploration constant on top of RAVE cratered to 8% — less is more."
              verdict="mixed"
              delay={0.3}
            />
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  8. ML-DRIVEN EVALUATION (Layer 6 headline)                           */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="green">The Headline Finding</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              The hand-tuned weights<br />had a <span className="text-neon-red">sign bug</span>
            </h2>
            <p className="mt-6 text-gray-400">
              Regression on 13,332 labeled states didn't just refine the evaluator — it surfaced three misspecifications that no amount of MCTS iteration could have fixed. The biggest: <code className="text-gray-200">largest_remaining_piece_size</code> carried the wrong sign. After ML calibration: <strong className="text-neon-green">76% arena win rate vs. 12% for the defaults</strong>.
            </p>
          </div>

          <div className="grid gap-8 lg:grid-cols-2">
            <div className="overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
              <table className="w-full text-left text-sm">
                <thead className="bg-charcoal-900/60 text-xs uppercase tracking-widest text-gray-500">
                  <tr>
                    <th className="px-4 py-3">Feature</th>
                    <th className="px-4 py-3">Default</th>
                    <th className="px-4 py-3">Calibrated</th>
                    <th className="px-4 py-3">Issue</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-charcoal-700 text-gray-300">
                  <tr>
                    <td className="px-4 py-3 font-mono text-xs">largest_remaining_piece_size</td>
                    <td className="px-4 py-3 text-gray-400">+0.10</td>
                    <td className="px-4 py-3 font-semibold text-neon-red">−0.23</td>
                    <td className="px-4 py-3 text-xs text-neon-red">Wrong sign</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-mono text-xs">opponent_avg_mobility</td>
                    <td className="px-4 py-3 text-gray-400">−0.10</td>
                    <td className="px-4 py-3 font-semibold text-neon-yellow">−0.30</td>
                    <td className="px-4 py-3 text-xs text-neon-yellow">3× underweighted</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-mono text-xs">squares_placed</td>
                    <td className="px-4 py-3 text-gray-400">+0.30</td>
                    <td className="px-4 py-3 font-semibold text-neon-yellow">+0.03</td>
                    <td className="px-4 py-3 text-xs text-neon-yellow">10× overweighted</td>
                  </tr>
                </tbody>
              </table>
              <div className="border-t border-charcoal-700 p-4 text-xs text-gray-500">
                Linear regression, bootstrap CIs, 34-feature win-probability model.
              </div>
            </div>

            <div className="grid gap-4">
              <figure className="overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
                <img
                  src="/assets/story/lr_coefs.png"
                  alt="Linear regression coefficients with confidence intervals"
                  className="w-full object-contain"
                />
                <figcaption className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500">
                  LR coefficients · win probability model
                </figcaption>
              </figure>
              <figure className="overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
                <img
                  src="/assets/story/rf_importance.png"
                  alt="Random Forest feature importance"
                  className="w-full object-contain"
                />
                <figcaption className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500">
                  RF feature importance · <span className="text-gray-300">center_proximity dominates at 36.1%</span>
                </figcaption>
              </figure>
            </div>
          </div>

          <div className="mt-10 rounded-2xl border border-charcoal-700 bg-charcoal-800/40 p-6">
            <div className="flex items-start gap-3">
              <Eye className="mt-1 shrink-0 text-neon-blue" size={20} />
              <div>
                <h4 className="text-base font-bold text-white">Phase-aware nuance</h4>
                <p className="mt-2 text-sm text-gray-400">
                  Evaluation R² varies sharply with board occupancy: early <span className="font-mono text-white">0.006</span> → mid <span className="font-mono text-white">0.080</span> → late <span className="font-mono text-white">0.435</span>. Static features are nearly useless in the opening. A phase-dependent weight vector was trained — and cratered to <strong className="text-neon-red">0% win rate</strong>. Inverted early-game signs and hard transitions made it worse than a single globally-calibrated vector. <em>Simpler, not smarter.</em>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  9. PARALLELIZATION & ADAPTIVE CONTROL                                */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="blue">Systems Leverage</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Root parallelization wins.<br />
              <span className="text-neon-red">Adding more knobs loses.</span>
            </h2>
            <p className="mt-6 text-gray-400">
              Two systems-level moves drove the biggest compute wins. Root-parallel multiprocessing delivered near-linear scaling; tree-parallel threading was slower than single-threaded. Adaptive rollout depth reshaped the budget at runtime — but layering an adaptive exploration constant on top of RAVE caused double-exploration and cratered win rate.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl border border-neon-green/30 bg-charcoal-800/70 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-white">Root Parallelization</h3>
                <span className="inline-flex items-center gap-1 rounded-full border border-neon-green/30 bg-neon-green/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-neon-green">
                  <CheckCircle2 size={12} /> Win
                </span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-gray-400">
                <li>• <strong className="text-white">3.1× throughput</strong> at 4 workers (near-linear scaling)</li>
                <li>• <strong className="text-white">46% win rate</strong> at 2 workers, TrueSkill #1</li>
                <li>• Tree-parallel + virtual loss: <strong className="text-neon-red">&lt;10% WR</strong> — GIL kills threads</li>
              </ul>
              <div className="mt-4 rounded-lg bg-charcoal-900/60 p-3 text-xs text-gray-500">
                Lesson: for CPU-bound Python search, multiprocessing beats clever concurrency.
              </div>
            </div>

            <div className="rounded-2xl border border-neon-yellow/30 bg-charcoal-800/70 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-white">Adaptive Meta-Control</h3>
                <span className="inline-flex items-center gap-1 rounded-full border border-neon-yellow/30 bg-neon-yellow/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-neon-yellow">
                  <AlertTriangle size={12} /> Mixed
                </span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-gray-400">
                <li>• Adaptive rollout depth: <strong className="text-white">36% WR + 1.64× faster</strong></li>
                <li>• <code className="text-xs text-gray-300">depth = 5 × (80 / branching_factor)</code></li>
                <li>• Adaptive exploration C + RAVE: <strong className="text-neon-red">8% WR</strong> — double-exploration</li>
              </ul>
              <div className="mt-4 rounded-lg bg-charcoal-900/60 p-3 text-xs text-gray-500">
                Lesson: meta-controllers must respect the signals already in the stack.
              </div>
            </div>
          </div>

          <figure className="mt-10 overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
            <img
              src="/assets/story/meta_optimization.png"
              alt="Meta-optimization results chart"
              className="w-full object-contain"
            />
            <figcaption className="px-4 py-3 text-xs uppercase tracking-widest text-gray-500">
              Layer 9 · adaptive depth wins, stacked adaptive C harms
            </figcaption>
          </figure>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  10. ANALYTICS & EXPLAINABILITY                                       */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="yellow">Analytics & Explainability</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Every move carries<br />its own rationale
            </h2>
            <p className="mt-6 text-gray-400">
              The frontend doubles as a research instrument. During a live game the <strong className="text-white">Explain panel</strong> surfaces top candidate moves with visit counts and Q-values; the MCTS viz suite streams depth, breadth, exploration/exploitation mix, rollout distributions, and per-board exploration heatmaps in real time.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="flex flex-col gap-4">
              <div className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6">
                <div className="flex items-center gap-3">
                  <Eye className="text-neon-yellow" size={20} />
                  <h3 className="text-lg font-bold text-white">Explain This Move</h3>
                </div>
                <p className="mt-2 text-sm text-gray-400">
                  Top-k candidate moves surfaced with visit counts, Q-values, and an embedded MCTS-phase diagram. The black box opens up mid-game, not in retrospective.
                </p>
                <div className="mt-3 font-mono text-[10px] tracking-widest text-gray-500">
                  frontend/src/components/ExplainMovePanel.tsx
                </div>
              </div>
              <div className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6">
                <div className="flex items-center gap-3">
                  <BarChart3 className="text-neon-blue" size={20} />
                  <h3 className="text-lg font-bold text-white">Real-time MCTS viz (7 charts)</h3>
                </div>
                <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-400">
                  <li>• Rollout histogram</li>
                  <li>• UCT breakdown</li>
                  <li>• Exploration vs. exploitation</li>
                  <li>• Root policy</li>
                  <li>• Board heatmap</li>
                  <li>• Depth over time</li>
                  <li>• Breadth over time</li>
                </ul>
                <div className="mt-3 font-mono text-[10px] tracking-widest text-gray-500">
                  frontend/src/components/mcts-viz/
                </div>
              </div>
              <figure className="overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
                <img
                  src="/images/mcts_diagram.png"
                  alt="MCTS phases diagram"
                  className="w-full object-contain"
                />
                <figcaption className="px-4 py-2 text-[10px] uppercase tracking-widest text-gray-500">
                  Embedded in the Explain panel · 100% of AI moves get a diagram + trace
                </figcaption>
              </figure>
            </div>

            <div className="grid gap-4">
              {/* TODO capture: Explain panel screenshot → frontend/public/assets/story/capture_explain.png */}
              <CapturePlaceholder
                label="Explain This Move panel · top-k moves, visit counts, Q-values, rationale text."
                cmd={'cd frontend && npm run dev\n# open /play, start MCTS vs MCTS, let run to ~turn 12\n# capture ExplainMovePanel → frontend/public/assets/story/capture_explain.png'}
                aspect="aspect-[4/5]"
              />
              {/* TODO capture: MCTS viz right panel → frontend/public/assets/story/capture_mcts_viz.png */}
              <CapturePlaceholder
                label="MCTS viz panel · UCT breakdown + board exploration heatmap during live search."
                cmd={'# from the same game, open the MCTS viz tab on the right panel\n# capture → frontend/public/assets/story/capture_mcts_viz.png'}
                aspect="aspect-[4/5]"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  11. RESULTS & RECRUITER TAKEAWAY                                     */}
      {/* ================================================================== */}
      <section className="border-t border-charcoal-800 bg-gradient-to-b from-charcoal-900 to-charcoal-800 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <SectionEyebrow color="blue">What Ships</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">Ready for Production</h2>
            <p className="mx-auto mt-6 max-w-3xl text-gray-400">
              End-to-end ownership across algorithm design, runtime optimization, ML pipeline work, experiment rigor, and explainable product surfaces. The final configuration is a synthesis of everything that survived arena evaluation.
            </p>
          </div>

          <div className="mb-10 grid gap-4 md:grid-cols-3">
            <MetricChip value="76%" label="Calibrated Eval WR" accent="green" />
            <MetricChip value="54% vs 0%" label="Quality > Quantity" accent="blue" />
            <MetricChip value="3.1×" label="Parallel Throughput" accent="yellow" />
          </div>

          <div className="grid gap-8 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <figure className="overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
                <img
                  src="/assets/story/grand_summary.png"
                  alt="Grand summary of layer contributions"
                  className="w-full object-contain"
                />
                <figcaption className="px-4 py-3 text-xs uppercase tracking-widest text-gray-500">
                  Grand summary · layer contributions ranked
                </figcaption>
              </figure>
            </div>
            <div className="lg:col-span-2">
              <div className="rounded-2xl border border-charcoal-700 bg-charcoal-800/60 p-6">
                <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-400">Best configuration</h3>
                <pre className="mt-4 overflow-x-auto rounded-lg bg-charcoal-900/70 p-4 text-xs leading-relaxed text-gray-300">
{`{
  "rollout_policy": "random",
  "rollout_cutoff_depth": 5,
  "minimax_backup_alpha": 0.25,
  "state_eval_weights": "calibrated",
  "rave_enabled": true,
  "rave_k": 1000,
  "num_workers": 2,
  "parallel_strategy": "root",
  "adaptive_rollout_depth_enabled": true
}`}
                </pre>
                <div className="mt-3 text-xs text-gray-500">
                  Source: <code>KEY_FINDINGS.md</code> · the synthesis of Layers 3–9.
                </div>
              </div>
            </div>
          </div>

          <div className="mt-16 flex flex-wrap items-center justify-center gap-6">
            <Link
              to="/benchmark"
              className="inline-flex items-center gap-2 rounded-full border border-neon-blue bg-neon-blue/10 px-8 py-4 font-bold tracking-widest text-white shadow-[0_0_20px_rgba(0,240,255,0.2)] transition-all hover:scale-105 hover:bg-neon-blue/20 active:scale-95"
            >
              <BarChart3 size={16} /> Proceed to Arena
            </Link>
            <Link
              to="/play"
              className="inline-flex items-center gap-2 rounded-full border border-charcoal-600 px-8 py-4 font-bold tracking-widest text-gray-300 transition-colors hover:border-neon-green hover:text-neon-green"
            >
              <Activity size={16} /> Play a Game
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
