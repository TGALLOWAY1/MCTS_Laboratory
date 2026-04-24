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
  BookOpen,
  FlaskConical,
  Search,
  Brain,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Small inline building blocks used across sections                  */
/* ------------------------------------------------------------------ */

type Accent = 'blue' | 'cyan' | 'violet' | 'red' | 'white';
const accentMap: Record<Accent, string> = {
  blue: 'text-neon-blue',
  cyan: 'text-neon-cyan',
  violet: 'text-neon-violet',
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

const EditorialFigure: React.FC<{
  src: string;
  alt: string;
  caption?: string;
  aspect?: string;
  accent?: 'blue' | 'cyan' | 'violet';
  className?: string;
}> = ({ src, alt, caption, aspect = 'aspect-[21/9]', accent = 'cyan', className = '' }) => {
  const glow = accent === 'blue'
    ? 'shadow-[0_0_40px_rgba(0,240,255,0.08)]'
    : accent === 'violet'
      ? 'shadow-[0_0_40px_rgba(139,92,246,0.10)]'
      : 'shadow-[0_0_40px_rgba(34,211,238,0.10)]';
  return (
    <figure className={`editorial-vignette relative overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/40 ${glow} ${className}`}>
      <div className={`${aspect} w-full`}>
        <img
          src={src}
          alt={alt}
          loading="lazy"
          className="h-full w-full object-cover object-center"
        />
      </div>
      {caption && (
        <figcaption className="relative z-10 border-t border-charcoal-700/80 bg-charcoal-900/60 px-4 py-3 text-xs uppercase tracking-widest text-gray-500 backdrop-blur-sm">
          {caption}
        </figcaption>
      )}
    </figure>
  );
};

const MediaPlaceholder: React.FC<{
  label: string;
  cmd?: string;
  aspect?: string;
  kind?: 'image' | 'video';
}> = ({ label, cmd, aspect = 'aspect-[16/9]', kind = 'image' }) => (
  <div
    className={`relative ${aspect} w-full rounded-2xl border-2 border-dashed border-charcoal-600 bg-charcoal-800/40 flex flex-col items-center justify-center p-6 text-center`}
  >
    <span className="inline-flex items-center gap-2 rounded-full border border-neon-violet/40 bg-neon-violet/10 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest text-neon-violet">
      <AlertTriangle size={12} />
      {kind === 'video' ? 'Video upload pending' : 'Placeholder'}
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
    ring: 'border-neon-cyan/40 hover:border-neon-cyan',
    badge: 'bg-neon-cyan/10 text-neon-cyan border-neon-cyan/30',
    icon: <CheckCircle2 size={12} />,
    text: 'Win',
  },
  mixed: {
    ring: 'border-neon-violet/40 hover:border-neon-violet',
    badge: 'bg-neon-violet/10 text-neon-violet border-neon-violet/30',
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

const PlaceholderBadge: React.FC<{ reason: string }> = ({ reason }) => (
  <span className="absolute top-3 right-3 z-20 inline-flex items-center gap-1 rounded-full border border-neon-violet/40 bg-charcoal-900/80 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-widest text-neon-violet backdrop-blur-sm">
    <AlertTriangle size={10} /> {reason}
  </span>
);

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
          className="absolute inset-0 z-0"
        >
          <img
            src="/assets/story/editorial/Project_purpose.png"
            alt=""
            aria-hidden="true"
            className="h-full w-full object-cover object-center opacity-55"
          />
          <img
            src="/assets/hero_search_tree_1776109554975.png"
            alt=""
            aria-hidden="true"
            className="absolute inset-0 h-full w-full object-cover object-center mix-blend-screen opacity-25"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-charcoal-900/80 via-transparent to-charcoal-900" />
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_50%,rgba(0,0,0,0.6)_100%)]" />
        </motion.div>

        <motion.div
          style={{ y: heroY }}
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="relative z-10 mx-auto max-w-5xl"
        >
          <span className="mb-4 inline-flex items-center gap-2 rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-4 py-1.5 text-xs font-semibold tracking-widest text-neon-cyan">
            <Cpu size={14} /> AI Systems Engineering for Multiplayer Search
          </span>
          <h1 className="mt-4 text-4xl font-extrabold tracking-tight text-white md:text-6xl lg:text-7xl">
            Building a Blokus Engine Was Step One.<br />
            <span className="bg-gradient-to-r from-neon-cyan via-neon-blue to-neon-violet bg-clip-text text-transparent">Building a Search Laboratory Was the Real Project.</span>
          </h1>
          <p className="mx-auto mt-8 max-w-3xl text-lg text-gray-300 md:text-xl">
            This project started as an AI agent for 4-player Blokus. It became something more valuable: a controlled experimentation system for testing how search quality changes when you optimize runtime, evaluation, rollout policy, parallelization, and exploration strategy inside a complex multiplayer game.
          </p>

          <div className="mt-12 flex flex-wrap justify-center gap-6">
            <MetricChip value="76%" label="Calibrated Eval Win Rate" accent="cyan" delay={0.2} />
            <MetricChip value="3.1x" label="Parallel Throughput Gain" accent="blue" delay={0.3} />
            <MetricChip value="13,332" label="Labeled Game States" accent="white" delay={0.4} />
          </div>

          <div className="mt-10 text-xs uppercase tracking-widest text-gray-500">
            Evidence-backed: 88 arena runs · 700 self-play games · controlled experimentation lab
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
              className="inline-flex items-center gap-2 rounded-full border border-charcoal-600 px-6 py-3 text-sm font-semibold tracking-widest text-gray-300 transition-colors hover:border-neon-violet hover:text-neon-violet"
            >
              <BarChart3 size={14} /> See the Arena
            </Link>
          </div>
        </motion.div>
      </section>

      {/* ================================================================== */}
      {/*  2. WHAT MAKES THIS HARD                                             */}
      {/* ================================================================== */}
      <section className="relative px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <SectionEyebrow color="red">The Challenge</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              4-player Blokus is not a clean minimax problem
            </h2>
            <p className="mx-auto mt-4 max-w-3xl text-gray-400">
              Two-player search has a simpler story: one opponent, stable incentives, cleaner backups, and more predictable convergence. 4-player Blokus breaks every one of those assumptions.
            </p>
          </div>

          <div className="grid gap-8 lg:grid-cols-5">
            <div className="lg:col-span-3 space-y-6">
              <motion.div
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true, margin: '-20%' }}
                variants={{ visible: { transition: { staggerChildren: 0.2 } } }}
                className="grid gap-6 md:grid-cols-2"
              >
                <motion.div
                  variants={{ hidden: { opacity: 0, x: -20 }, visible: { opacity: 1, x: 0 } }}
                  className="rounded-xl border border-charcoal-700 bg-charcoal-800/70 p-6"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-neon-blue/10 text-neon-blue">
                    <Activity />
                  </div>
                  <h3 className="text-lg font-bold text-white">2-Player Assumptions</h3>
                  <ul className="mt-3 space-y-2 text-sm text-gray-400">
                    <li>Stable minimax with one adversary</li>
                    <li>Fixed opponent model, clean backup</li>
                    <li>Narrow branching, known convergence</li>
                  </ul>
                </motion.div>

                <motion.div
                  variants={{ hidden: { opacity: 0, x: 20 }, visible: { opacity: 1, x: 0 } }}
                  className="rounded-xl border border-charcoal-700 bg-charcoal-800/70 p-6"
                >
                  <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-neon-red/10 text-neon-red">
                    <GitBranch />
                  </div>
                  <h3 className="text-lg font-bold text-white">4-Player Realities</h3>
                  <ul className="mt-3 space-y-2 text-sm text-gray-400">
                    <li>Peak branching <span className="text-neon-red font-semibold">534 moves</span> at turn 17</li>
                    <li>Three non-stationary opponents</li>
                    <li>King-making + tactical blocks dominate</li>
                    <li>Long-horizon mobility effects</li>
                  </ul>
                </motion.div>
              </motion.div>

              <div className="rounded-xl border border-charcoal-700 bg-charcoal-800/40 p-6">
                <p className="text-sm text-gray-400">
                  That combination makes this a useful laboratory for search research. The challenge is not just to build an agent that plays. The challenge is to determine, under controlled testing, <strong className="text-white">which optimizations actually improve decision quality</strong> in a noisy, multiplayer setting.
                </p>
              </div>
            </div>

            <div className="lg:col-span-2">
              <EditorialFigure
                src="/assets/story/editorial/Branching_factor.png"
                alt="Search branching visualization — legal moves fan out into a rapidly widening tree of possible futures"
                aspect="aspect-[3/4]"
                accent="violet"
                caption="534 legal moves at peak · search spreads thin"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  3. PROJECT STACK                                                     */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto grid max-w-6xl items-center gap-12 lg:grid-cols-2">
          <EditorialFigure
            src="/assets/story/editorial/Project_stack.png"
            alt="Full project stack — game engine, search and evaluation, benchmarking, explainability layers"
            aspect="aspect-[3/4]"
            accent="violet"
          />
          <div>
            <SectionEyebrow color="violet">Architecture</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              The full stack,<br />bottom to top
            </h2>
            <p className="mt-6 text-gray-400">
              The system factors cleanly across eight concerns, each exposing a measurable contract so wins, regressions, and stalemates can be attributed to a single knob instead of a black-box release.
            </p>
            <ul className="mt-6 space-y-3 text-sm text-gray-300">
              <li className="flex items-start gap-3"><Layers className="mt-0.5 shrink-0 text-neon-cyan" size={16} /><span><strong className="text-white">Representation</strong> — Bitboard encoding for O(1) legality checks</span></li>
              <li className="flex items-start gap-3"><Workflow className="mt-0.5 shrink-0 text-neon-cyan" size={16} /><span><strong className="text-white">Move generation</strong> — Frontier-first enumeration, 10-20x fewer candidates</span></li>
              <li className="flex items-start gap-3"><GitBranch className="mt-0.5 shrink-0 text-neon-blue" size={16} /><span><strong className="text-white">Rollout policy</strong> — How simulated games play out (random beat heuristic)</span></li>
              <li className="flex items-start gap-3"><Target className="mt-0.5 shrink-0 text-neon-blue" size={16} /><span><strong className="text-white">Evaluation</strong> — ML-calibrated feature weights for state scoring</span></li>
              <li className="flex items-start gap-3"><TrendingUp className="mt-0.5 shrink-0 text-neon-violet" size={16} /><span><strong className="text-white">Exploration</strong> — RAVE blending for 4x convergence speedup</span></li>
              <li className="flex items-start gap-3"><Cpu className="mt-0.5 shrink-0 text-neon-violet" size={16} /><span><strong className="text-white">Parallelization</strong> — Root-parallel multiprocessing (3.1x throughput)</span></li>
              <li className="flex items-start gap-3"><FlaskConical className="mt-0.5 shrink-0 text-neon-red" size={16} /><span><strong className="text-white">Experimentation</strong> — Arena framework, TrueSkill, seat-bias correction</span></li>
              <li className="flex items-start gap-3"><Eye className="mt-0.5 shrink-0 text-neon-red" size={16} /><span><strong className="text-white">Explainability</strong> — Real-time MCTS visualization and decision traces</span></li>
            </ul>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  4. PART I — THE ENGINE                                               */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="blue">Part I — The Engine</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Before I could study better search, I needed an engine fast enough to support real experiments
            </h2>
            <p className="mt-6 text-gray-400">
              A major early lesson was that runtime is not a secondary concern in search. It determines which ideas are even testable. The engine foundation focused on making the core game loop efficient enough to support repeated, measurable experimentation.
            </p>
          </div>

          {/* Throughput table */}
          <div className="mb-12 overflow-hidden rounded-2xl border border-charcoal-700 bg-charcoal-800/60">
            <div className="border-b border-charcoal-700 px-6 py-4">
              <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-400">Baseline Throughput by Game Phase</h3>
              <p className="mt-1 text-xs text-gray-500">
                An <strong className="text-gray-300">iteration</strong> is one full MCTS cycle: Select → Expand → Simulate → Backpropagate. Each adds one data point to the search tree.
              </p>
            </div>
            <table className="w-full text-left text-sm">
              <thead className="bg-charcoal-900/60 text-xs uppercase tracking-widest text-gray-500">
                <tr>
                  <th className="px-6 py-3">Phase</th>
                  <th className="px-6 py-3">Legal Moves</th>
                  <th className="px-6 py-3">Depth 0 (pure eval)</th>
                  <th className="px-6 py-3">Depth 5 (rollout)</th>
                  <th className="px-6 py-3">Slowdown</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-charcoal-700 text-gray-300">
                <tr>
                  <td className="px-6 py-3 font-semibold text-white">Early</td>
                  <td className="px-6 py-3">314</td>
                  <td className="px-6 py-3 font-mono text-neon-cyan">466 iter/s</td>
                  <td className="px-6 py-3 font-mono text-neon-red">3.5 iter/s</td>
                  <td className="px-6 py-3 font-semibold text-neon-red">133x</td>
                </tr>
                <tr>
                  <td className="px-6 py-3 font-semibold text-white">Mid</td>
                  <td className="px-6 py-3">362</td>
                  <td className="px-6 py-3 font-mono text-neon-cyan">139 iter/s</td>
                  <td className="px-6 py-3 font-mono text-neon-red">4.8 iter/s</td>
                  <td className="px-6 py-3 font-semibold text-neon-red">29x</td>
                </tr>
                <tr>
                  <td className="px-6 py-3 font-semibold text-white">Late</td>
                  <td className="px-6 py-3">31</td>
                  <td className="px-6 py-3 font-mono text-neon-cyan">368 iter/s</td>
                  <td className="px-6 py-3 font-mono">62.0 iter/s</td>
                  <td className="px-6 py-3">6x</td>
                </tr>
              </tbody>
            </table>
            <div className="border-t border-charcoal-700 px-6 py-3 text-xs text-gray-500">
              Source: <code>data/throughput_calibration.json</code> · 50 iterations per sample
            </div>
          </div>

          {/* Engine optimization image with placeholder badge */}
          <div className="relative mb-12">
            <PlaceholderBadge reason="Placeholder — text artifacts" />
            <EditorialFigure
              src="/assets/story/editorial/Engine_optimization.png"
              alt="Systems transformation — from fragmented computation to optimized engine pipeline"
              aspect="aspect-[21/9]"
              accent="blue"
              caption="Engine optimization · bitboard + frontier-first + instrumented loop"
            />
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
              <Workflow className="text-neon-cyan" />
              <h3 className="mt-4 text-lg font-bold text-white">Frontier-first enumeration</h3>
              <p className="mt-2 text-sm text-gray-400">
                Legal placements are scanned against the <span className="text-neon-cyan">20-30 active frontier cells</span>, not all 400 board squares. 10-20x fewer candidates, same correctness.
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
              <h3 className="mt-4 text-lg font-bold text-white">Instrumented search loop</h3>
              <p className="mt-2 text-sm text-gray-400">
                Every move decision is structured so diagnostics can be collected, compared, and surfaced later in analysis and UI. The search loop is both an engine and an instrument.
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
                Frontier halos · 10-20x fewer candidates
              </figcaption>
            </figure>
          </div>

          <div className="mt-10 rounded-2xl border border-charcoal-700 bg-charcoal-800/40 p-6">
            <div className="flex items-start gap-3">
              <Gauge className="mt-1 shrink-0 text-neon-blue" size={20} />
              <div>
                <h4 className="text-base font-bold text-white">Key engine insight</h4>
                <p className="mt-2 text-sm text-gray-400">
                  Search depth is far more expensive than it first appears. In the opening, depth-0 evaluation runs at <span className="font-mono text-neon-cyan">466 iter/s</span> while depth-5 rollouts drop to <span className="font-mono text-neon-red">3.5 iter/s</span>. That is not a tuning detail. The project stopped treating depth as "free strength" and started treating it as a <strong className="text-white">resource allocation problem</strong> inside a fixed wall-clock budget.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  5. PART II — THE LABORATORY                                          */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="cyan">Part II — The Laboratory</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              The more important system was the <span className="text-neon-cyan">experimentation framework</span>
            </h2>
            <p className="mt-6 text-gray-400">
              The engine made play possible. The laboratory made learning possible. I structured the project so each major improvement could be tested as its own layer, and each layer had to survive the same evaluation discipline.
            </p>
          </div>

          {/* Full pipeline header image */}
          <div className="mb-12">
            <EditorialFigure
              src="/assets/story/editorial/Full_pipeline.png"
              alt="Full pipeline — high throughput, analytics, intelligent search, and move selection working together"
              aspect="aspect-[21/9]"
              accent="cyan"
              caption="Throughput · analytics · intelligent search · move selection"
            />
          </div>

          {/* TrueSkill vs ELO callout */}
          <div className="mb-10 rounded-2xl border border-neon-blue/30 bg-charcoal-800/70 p-6">
            <div className="flex items-start gap-3">
              <TrendingUp className="mt-1 shrink-0 text-neon-blue" size={20} />
              <div>
                <h4 className="text-base font-bold text-white">Why TrueSkill instead of ELO?</h4>
                <p className="mt-2 text-sm text-gray-400">
                  <strong className="text-white">ELO is pairwise only</strong> — it requires decomposing a 4-player game into 6 pairs, losing the multiplayer structure. <strong className="text-white">TrueSkill</strong> (Herbrich et al., 2006) uses a Plackett-Luce model that natively handles multiplayer games. It models each agent's skill as a Gaussian distribution (<span className="font-mono text-gray-300">mu = estimated skill, sigma = uncertainty</span>). A "conservative rating" of <span className="font-mono text-gray-300">mu - 3*sigma</span> means an agent only gets a high rating if it's both strong <em>and</em> consistent. This was essential for ranking agents that play in 4-player round-robins.
                </p>
              </div>
            </div>
          </div>

          {/* Experimental discipline */}
          <div className="mb-10 grid gap-4 md:grid-cols-4">
            <MetricChip value="88" label="Archived Arena Runs" accent="blue" />
            <MetricChip value="700" label="Self-Play Games" accent="cyan" />
            <MetricChip value="13,332" label="Labeled States" accent="white" />
            <MetricChip value="p < 0.05" label="Seat-Bias Corrected" accent="violet" />
          </div>

          <div className="grid gap-8 lg:grid-cols-5">
            <div className="lg:col-span-2">
              <h3 className="mb-4 text-lg font-bold text-white">Experimental discipline</h3>
              <ul className="space-y-4 text-sm">
                <li className="flex items-start gap-3">
                  <Database className="mt-1 shrink-0 text-neon-blue" size={16} />
                  <span className="text-gray-300">
                    <strong className="text-white">Fixed seeds</strong> — every RNG initialized identically across experiments. Same seed = same game. Performance differences come from the algorithm, not luck.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <Target className="mt-1 shrink-0 text-neon-cyan" size={16} />
                  <span className="text-gray-300">
                    <strong className="text-white">4-player round-robin</strong> — every agent plays every seat position. Seat 1 scored ~78 avg vs. seat 4 at ~73; rotation ensures no unfair advantage.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <TrendingUp className="mt-1 shrink-0 text-neon-violet" size={16} />
                  <span className="text-gray-300">
                    <strong className="text-white">TrueSkill (mu, sigma)</strong> — Bayesian rating with uncertainty. Conservative estimate = mu - 3*sigma rewards consistency over lucky runs.
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <Workflow className="mt-1 shrink-0 text-neon-cyan" size={16} />
                  <span className="text-gray-300">
                    <strong className="text-white">Seat-bias correction</strong> — ANOVA detected significant positional advantage (p &lt; 0.000001). All configs rotate seat assignments and analysis accounts for it.
                  </span>
                </li>
              </ul>
            </div>
            <div className="grid gap-4 lg:col-span-3">
              <EditorialFigure
                src="/assets/story/editorial/Tournament_pipeline.png"
                alt="Tournament pipeline — benchmarking, parameter tuning, analytics, result comparison"
                aspect="aspect-[16/10]"
                accent="blue"
                caption="Arena · TrueSkill · seat-bias corrected · reproducible"
              />
              <EditorialFigure
                src="/assets/story/editorial/Arena_runs_for_evaluator_tuning.png"
                alt="Arena runs driving evaluator tuning — comparative performance, score distributions, matchup analysis"
                aspect="aspect-[16/10]"
                accent="violet"
                caption="88 arena runs driving evaluator calibration"
              />
            </div>
          </div>

          <div className="mt-10 rounded-2xl border border-charcoal-700 bg-charcoal-800/40 p-6">
            <p className="text-sm text-gray-400">
              This is not just "I made an AI for a board game." This is: <strong className="text-white">I built a repeatable AI experimentation setup for measuring search optimization in a complex multiplayer environment.</strong> That is the deeper systems-engineering story.
            </p>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  6. THE FIRST IMPORTANT RESULT                                        */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-2 lg:items-center">
          <div>
            <SectionEyebrow color="violet">The First Important Result</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold leading-tight text-white md:text-5xl">
              Naive MCTS <span className="text-neon-red">lost</span>
            </h2>
            <p className="mt-6 text-gray-400">
              One of the most valuable outcomes in the project was an early failure. A default MCTS agent with 1,000 iterations per move scored <strong className="text-white">-8.0 points</strong> below a heuristic-only agent. Iteration efficiency averaged just <strong className="text-white">11%</strong> — search budget spread across 534 children produces Q-estimates from 3-4 visits apiece. That's noise, not signal.
            </p>
            <ul className="mt-8 space-y-4">
              <li className="flex items-start gap-3">
                <Target className="mt-1 shrink-0 text-neon-violet" size={18} />
                <span className="text-sm text-gray-300">
                  <strong className="text-white">Iteration efficiency 11%</strong> across 80 turn indices; 78/80 turns below 50% utilization.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <Gauge className="mt-1 shrink-0 text-neon-violet" size={18} />
                <span className="text-sm text-gray-300">
                  <strong className="text-white">Q-values collapse</strong> when each child sees 3-4 visits — UCB1 can't discriminate.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <AlertTriangle className="mt-1 shrink-0 text-neon-violet" size={18} />
                <span className="text-sm text-gray-300">
                  <strong className="text-white">Takeaway:</strong> search quality depends on how efficiently the budget is used, not just how much budget is thrown at the problem.
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
              className="relative flex aspect-square items-center justify-center overflow-hidden rounded-full border border-charcoal-700 bg-charcoal-800 p-12 shadow-2xl shadow-neon-violet/10"
            >
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-neon-red/10 via-charcoal-800/20 to-transparent blur-md" />
              <div className="relative z-10 text-center">
                <div className="text-7xl font-black tracking-tighter text-neon-red">-8.0</div>
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

        <div className="mx-auto mt-12 max-w-6xl rounded-2xl border border-neon-violet/30 bg-charcoal-800/40 p-8 text-center">
          <blockquote className="text-lg font-semibold text-gray-200 italic">
            "In 4-player Blokus, stronger play comes from improving search efficiency, evaluation quality, and experimental rigor — not from blindly scaling vanilla MCTS."
          </blockquote>
          <p className="mt-3 text-xs uppercase tracking-widest text-gray-500">Central thesis of the laboratory</p>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  7. RESEARCH APPROACH (Placeholder)                                   */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="blue">Research Process</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Approaches determined via systematic literature review
            </h2>
            <p className="mt-6 text-gray-400">
              Before building each optimization layer, I surveyed the relevant literature using multiple AI research tools, then selected techniques with evidence of success in similar high-branching-factor or multiplayer settings.
            </p>
          </div>

          <div className="mb-10 grid gap-4 md:grid-cols-4">
            {[
              { icon: <BookOpen size={20} />, name: 'NotebookLM', desc: 'Structured analysis of MCTS survey papers' },
              { icon: <Search size={20} />, name: 'ChatGPT Deep Research', desc: 'Broad literature search across multiplayer game AI' },
              { icon: <Brain size={20} />, name: 'Gemini Deep Research', desc: 'Cross-referencing technique applicability' },
              { icon: <FlaskConical size={20} />, name: 'Claude Research', desc: 'Implementation-focused technique evaluation' },
            ].map((tool, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="rounded-xl border border-charcoal-700 bg-charcoal-800/70 p-5 text-center"
              >
                <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-neon-blue/10 text-neon-blue">
                  {tool.icon}
                </div>
                <h4 className="text-sm font-bold text-white">{tool.name}</h4>
                <p className="mt-1 text-xs text-gray-500">{tool.desc}</p>
              </motion.div>
            ))}
          </div>

          <div className="rounded-2xl border border-charcoal-700 bg-charcoal-800/60 p-6">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-widest text-gray-400">Key Papers & References</h3>
            <ul className="space-y-3 text-sm text-gray-300">
              <li className="flex items-start gap-3">
                <BookOpen className="mt-0.5 shrink-0 text-gray-500" size={14} />
                <span><strong className="text-white">Nijssen (Thesis, Ch. 6)</strong> — Two-ply search-based playouts in multiplayer MCTS</span>
              </li>
              <li className="flex items-start gap-3">
                <BookOpen className="mt-0.5 shrink-0 text-gray-500" size={14} />
                <span><strong className="text-white">Lanctot et al. (2014)</strong> — Implicit minimax backups for multiplayer games</span>
              </li>
              <li className="flex items-start gap-3">
                <BookOpen className="mt-0.5 shrink-0 text-gray-500" size={14} />
                <span><strong className="text-white">Herbrich et al. (2006)</strong> — TrueSkill: Bayesian skill rating for multiplayer games</span>
              </li>
              <li className="flex items-start gap-3">
                <BookOpen className="mt-0.5 shrink-0 text-gray-500" size={14} />
                <span><strong className="text-white">Soemers et al.</strong> — Loss avoidance and MCTS configuration prediction</span>
              </li>
              <li className="flex items-start gap-3">
                <BookOpen className="mt-0.5 shrink-0 text-gray-500" size={14} />
                <span><strong className="text-white">AutoMCTS (Survey S3.2)</strong> — Self-adaptation mechanisms for MCTS hyperparameters</span>
              </li>
              <li className="flex items-start gap-3">
                <BookOpen className="mt-0.5 shrink-0 text-gray-500" size={14} />
                <span><strong className="text-white">ColosseumRL (2019)</strong> — Emergent alliances in multiplayer game environments</span>
              </li>
            </ul>
          </div>

          <div className="mt-6">
            <MediaPlaceholder
              label="Detailed research methodology and paper-to-layer mapping — content forthcoming"
              aspect="aspect-[21/6]"
            />
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  8. WHAT THE LAB DISCOVERED                                           */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="cyan">Findings</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Not every search optimization helped —<br />and that was the point
            </h2>
            <p className="mt-6 text-gray-400">
              The strongest message here is that the lab produced <strong className="text-white">insight</strong>, not just incremental code changes. Some layers won big, some taught us that less is more, and a few lost outright. Shipping the losses alongside the wins is the whole point of the lab.
            </p>
          </div>

          <div className="mb-8">
            <EditorialFigure
              src="/assets/story/editorial/MCTS_approaches.png"
              alt="MCTS search optimization approaches — branching, pruning, selective exploration, prioritization"
              aspect="aspect-[21/9]"
              accent="cyan"
              caption="Search optimization landscape · which approaches survived controlled testing"
            />
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
              id="01"
              title="Constraining the Search Tree"
              headline="+64% win rate"
              body="Progressive widening reduced effective branching without sacrificing move quality. Mean score 92.4 vs. 76.0 baseline."
              verdict="win"
            />
            <LayerCard
              id="02"
              title="Faster Rollout Beats Smarter Rollout"
              headline="Random > heuristic > two-ply"
              body="Random rollout at depth 5 is 10x faster than two-ply and outscores heuristic. In this environment, extra bias hurt more than extra speed helped."
              verdict="win"
              delay={0.05}
            />
            <LayerCard
              id="03"
              title="RAVE Was a Major Win"
              headline="50ms RAVE > 200ms vanilla"
              body="RAVE (Rapid Action Value Estimation) shares information across sibling nodes, accelerating convergence 4x. Better information sharing dominated raw compute."
              verdict="win"
              delay={0.1}
            />
            <LayerCard
              id="04"
              title="Evaluation Quality Dominated"
              headline="76% WR vs. 12% defaults"
              body="ML-calibrated weights from regression on 13,332 states fixed three miscalibrations including a sign error. The headline moment of the project."
              verdict="win"
              delay={0.15}
            />
            <LayerCard
              id="05"
              title="Sophisticated Ideas Failed in Practice"
              headline="Opponent modeling: no lift, 2.4x slower"
              body="Alliance detection activated correctly, but compute cost exceeded benefit at real budgets. Phase-aware eval collapsed to 0% WR. Adaptive C + RAVE cratered to 8%."
              verdict="loss"
              delay={0.2}
            />
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  9. THE BIGGEST INSIGHT — EVALUATOR CALIBRATION                       */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="cyan">The Biggest Insight</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Better evaluation beat more blind search
            </h2>
            <p className="mt-6 text-gray-400">
              The most revealing result in the entire project was not a search trick. It was evaluator calibration. Regression on 13,332 labeled states didn't just refine the evaluator — it surfaced three misspecifications that no amount of MCTS iteration could have fixed. The biggest: <code className="text-gray-200">largest_remaining_piece_size</code> carried the <span className="text-neon-red font-semibold">wrong sign</span>. After ML calibration: <strong className="text-neon-cyan">76% arena win rate vs. 12% for the defaults</strong>.
            </p>
          </div>

          {/* Regression methodology callout */}
          <div className="mb-10 rounded-2xl border border-neon-cyan/30 bg-charcoal-800/70 p-6">
            <div className="flex items-start gap-3">
              <FlaskConical className="mt-1 shrink-0 text-neon-cyan" size={20} />
              <div>
                <h4 className="text-base font-bold text-white">How the regression was done</h4>
                <p className="mt-2 text-sm text-gray-400">
                  Data was collected via checkpoint snapshots every 4 plies during 700 self-play games, producing <strong className="text-white">13,332 labeled states</strong> (3,216 early / 5,608 mid / 4,508 late). <strong className="text-white">Linear regression</strong> (R&sup2; = 0.136, 7 features) identified directional miscalibrations — which weights had the wrong sign or magnitude. <strong className="text-white">Random Forest</strong> (R&sup2; = 0.535, 34 features) ranked feature importance, revealing <code className="text-gray-300">center_proximity</code> as the dominant predictor at 36.1%. Bootstrap CIs and SHAP values confirmed feature directions.
                </p>
              </div>
            </div>
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
                    <td className="px-4 py-3 font-semibold text-neon-red">-0.23</td>
                    <td className="px-4 py-3 text-xs text-neon-red">Wrong sign</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-mono text-xs">opponent_avg_mobility</td>
                    <td className="px-4 py-3 text-gray-400">-0.10</td>
                    <td className="px-4 py-3 font-semibold text-neon-violet">-0.30</td>
                    <td className="px-4 py-3 text-xs text-neon-violet">3x underweighted</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-mono text-xs">squares_placed</td>
                    <td className="px-4 py-3 text-gray-400">+0.30</td>
                    <td className="px-4 py-3 font-semibold text-neon-violet">+0.03</td>
                    <td className="px-4 py-3 text-xs text-neon-violet">10x overweighted</td>
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
                  Evaluation R&sup2; varies sharply with board occupancy: early <span className="font-mono text-white">0.006</span> &rarr; mid <span className="font-mono text-white">0.080</span> &rarr; late <span className="font-mono text-white">0.435</span>. Static features are nearly useless in the opening. A phase-dependent weight vector was trained — and cratered to <strong className="text-neon-red">0% win rate</strong>. Inverted early-game signs and hard transitions made it worse than a single globally-calibrated vector. <em>Simpler, not smarter.</em>
                </p>
              </div>
            </div>
          </div>

          <div className="mt-8 rounded-2xl border border-neon-violet/30 bg-charcoal-800/40 p-8 text-center">
            <blockquote className="text-lg font-semibold text-gray-200 italic">
              "If your evaluator is wrong, more MCTS will often just explore the wrong landscape more efficiently."
            </blockquote>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  10. SYSTEMS INSIGHT                                                  */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="blue">Systems Insight</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              Parallelization helped, but only in the right form
            </h2>
            <p className="mt-6 text-gray-400">
              The project tested systems-level optimization, not just search-policy ideas. Optimization is not additive by default. A good experimentation setup has to detect when "more advanced" actually means "worse together."
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl border border-neon-cyan/30 bg-charcoal-800/70 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-white">Root Parallelization</h3>
                <span className="inline-flex items-center gap-1 rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-neon-cyan">
                  <CheckCircle2 size={12} /> Win
                </span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-gray-400">
                <li><strong className="text-white">3.1x throughput</strong> at 4 workers (near-linear scaling)</li>
                <li><strong className="text-white">46% win rate</strong> at 2 workers, TrueSkill #1</li>
                <li>Tree-parallel + virtual loss: <strong className="text-neon-red">&lt;10% WR</strong> — Python GIL kills threads</li>
              </ul>
              <div className="mt-4 rounded-lg bg-charcoal-900/60 p-3 text-xs text-gray-500">
                Lesson: for CPU-bound Python search, multiprocessing beats clever concurrency.
              </div>
            </div>

            <div className="rounded-2xl border border-neon-violet/30 bg-charcoal-800/70 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-white">Adaptive Meta-Control</h3>
                <span className="inline-flex items-center gap-1 rounded-full border border-neon-violet/30 bg-neon-violet/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-neon-violet">
                  <AlertTriangle size={12} /> Mixed
                </span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-gray-400">
                <li>Adaptive rollout depth: <strong className="text-white">36% WR + 1.64x faster</strong></li>
                <li><code className="text-xs text-gray-300">depth = 5 x (80 / branching_factor)</code></li>
                <li>Adaptive exploration C + RAVE: <strong className="text-neon-red">8% WR</strong> — double-exploration</li>
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
      {/*  11. EXPLAINABILITY & INSTRUMENTATION                                 */}
      {/* ================================================================== */}
      <section className="story-divider bg-charcoal-900 px-6 py-24 md:px-12 lg:px-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 max-w-3xl">
            <SectionEyebrow color="violet">Explainability</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">
              The frontend is also<br />a research surface
            </h2>
            <p className="mt-6 text-gray-400">
              This project does not stop at backend search code. The system exposes its reasoning. During play, the frontend surfaces top candidate moves, visit counts, Q-values, rollout distributions, exploration vs. exploitation balance, and board-level search heatmaps. That makes the system useful in two ways: as an agent you can play against, and as an instrument for understanding how the search process behaves under different configurations.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="flex flex-col gap-4">
              <div className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-6">
                <div className="flex items-center gap-3">
                  <Eye className="text-neon-violet" size={20} />
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
                  <li>Rollout histogram</li>
                  <li>UCT breakdown</li>
                  <li>Exploration vs. exploitation</li>
                  <li>Root policy</li>
                  <li>Board heatmap</li>
                  <li>Depth over time</li>
                  <li>Breadth over time</li>
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
              <EditorialFigure
                src="/assets/story/editorial/08-explainability.png"
                alt="AI decision explainability — a chosen move emerges from candidates with surrounding evaluation signals"
                aspect="aspect-[4/5]"
                accent="violet"
                caption="Explain This Move · why one decision was preferred"
              />
              <EditorialFigure
                src="/assets/story/editorial/09-analytics-instrumentation.png"
                alt="Deep instrumentation — layered analytic signals across throughput, search depth, branching, and evaluation"
                aspect="aspect-[4/5]"
                accent="blue"
                caption="MCTS viz · throughput · depth · rollout distributions"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================== */}
      {/*  12. FINAL TAKEAWAY                                                   */}
      {/* ================================================================== */}
      <section className="story-divider relative overflow-hidden bg-gradient-to-b from-charcoal-900 to-charcoal-800 px-6 py-24 md:px-12 lg:px-24">
        <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-0">
          <img
            src="/assets/story/editorial/10-results-takeaway.png"
            alt=""
            className="h-full w-full object-cover object-center opacity-20"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-charcoal-900/90 via-charcoal-900/70 to-charcoal-900" />
        </div>

        <div className="relative z-10 mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <SectionEyebrow color="blue">What This Project Demonstrates</SectionEyebrow>
            <h2 className="mt-4 text-3xl font-bold text-white md:text-5xl">Two deliverables came out of this work</h2>
          </div>

          <div className="mb-12 grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl border border-charcoal-700 bg-charcoal-800/70 p-8">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-neon-blue/10 text-neon-blue">
                <Cpu size={24} />
              </div>
              <h3 className="text-xl font-bold text-white">1. A Performant AI Game Engine</h3>
              <p className="mt-3 text-sm text-gray-400">
                A custom Blokus engine with efficient bitboard state representation, frontier-first move generation, and live decision instrumentation designed specifically to support iterative search research.
              </p>
            </div>
            <div className="rounded-2xl border border-neon-cyan/40 bg-charcoal-800/70 p-8 shadow-[0_0_30px_rgba(34,211,238,0.08)]">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-neon-cyan/10 text-neon-cyan">
                <FlaskConical size={24} />
              </div>
              <h3 className="text-xl font-bold text-white">2. A Search Experimentation Platform</h3>
              <p className="mt-3 text-sm text-gray-400">
                A reproducible lab for testing search, evaluation, and systems optimizations in a complex 4-player environment. 88 arena runs, TrueSkill-rated, seat-bias corrected, with preserved configs and logs.
              </p>
            </div>
          </div>

          <div className="mb-12 grid gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-charcoal-700 bg-charcoal-800/60 p-4 text-center">
              <span className="text-xs font-bold uppercase tracking-widest text-gray-500">Systems Engineering</span>
              <p className="mt-1 text-xs text-gray-400">Engine, bitboard, parallelization</p>
            </div>
            <div className="rounded-xl border border-charcoal-700 bg-charcoal-800/60 p-4 text-center">
              <span className="text-xs font-bold uppercase tracking-widest text-gray-500">ML Pipeline</span>
              <p className="mt-1 text-xs text-gray-400">Regression, feature engineering, calibration</p>
            </div>
            <div className="rounded-xl border border-charcoal-700 bg-charcoal-800/60 p-4 text-center">
              <span className="text-xs font-bold uppercase tracking-widest text-gray-500">Experiment Design</span>
              <p className="mt-1 text-xs text-gray-400">Arena, TrueSkill, reproducibility</p>
            </div>
            <div className="rounded-xl border border-charcoal-700 bg-charcoal-800/60 p-4 text-center">
              <span className="text-xs font-bold uppercase tracking-widest text-gray-500">Product Thinking</span>
              <p className="mt-1 text-xs text-gray-400">Explainability, frontend instrumentation</p>
            </div>
          </div>

          <div className="mb-10 rounded-2xl border border-neon-violet/30 bg-charcoal-800/40 p-8 text-center">
            <blockquote className="text-lg font-semibold text-gray-200 italic">
              "I built the engine, then built the lab needed to discover what actually makes search work in that engine."
            </blockquote>
          </div>

          <div className="mb-10 grid gap-4 md:grid-cols-3">
            <MetricChip value="76%" label="Calibrated Eval WR" accent="cyan" />
            <MetricChip value="54% vs 0%" label="Quality > Quantity" accent="blue" />
            <MetricChip value="3.1x" label="Parallel Throughput" accent="violet" />
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
                  Source: <code>KEY_FINDINGS.md</code> · the synthesis of Layers 3-9.
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
              className="inline-flex items-center gap-2 rounded-full border border-charcoal-600 px-8 py-4 font-bold tracking-widest text-gray-300 transition-colors hover:border-neon-violet hover:text-neon-violet"
            >
              <Activity size={16} /> Play a Game
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
