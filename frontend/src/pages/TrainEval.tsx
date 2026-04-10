import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE } from '../constants/gameConstants';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface ArenaRunSummary {
  run_id: string;
  notes: string;
  num_games: number;
  created_at: string;
  agent_names: string[];
}

interface TrueSkillEntry {
  agent_id: string;
  mu: number;
  sigma: number;
  conservative: number;
  rank: number;
}

interface RunDetail {
  run_id: string;
  num_games: number;
  run_config: {
    notes?: string;
    created_at?: string;
    agents: Array<{ name: string; params: Record<string, any> }>;
  };
  win_stats: Record<string, { win_rate: number; outright_wins: number; games_played: number }>;
  trueskill_ratings?: { leaderboard: TrueSkillEntry[] };
}

interface LayerGroup {
  layer: string;
  title: string;
  description: string;
  runs: ArenaRunSummary[];
}

const LAYER_COLORS = ['#00F0FF', '#00FF9D', '#FFE600', '#FF4D4D', '#A855F7', '#F97316'];

const LAYER_DESCRIPTIONS: Record<string, { title: string; description: string }> = {
  'Layer 3': {
    title: 'Action Reduction',
    description: 'Progressive widening limits branching factor; progressive history biases toward historically successful moves.',
  },
  'Layer 4': {
    title: 'Simulation Strategy',
    description: 'Heuristic/two-ply rollout policies, rollout cutoff with static evaluation, and minimax backup blending.',
  },
  'Layer 5': {
    title: 'RAVE & History',
    description: 'Rapid Action Value Estimation bootstraps cold-start nodes; NST biases rollouts using move-pair statistics.',
  },
  'Layer 6': {
    title: 'Evaluation Refinement',
    description: 'Regression-calibrated weights from 13K+ self-play states, phase-dependent evaluation (early/mid/late).',
  },
  'Layer 7': {
    title: 'Opponent Modeling',
    description: 'Blocking-rate tracking, alliance detection, king-maker awareness, and adaptive cross-game profiles.',
  },
  'Layer 9': {
    title: 'Meta-Optimization',
    description: 'Adaptive exploration constant, adaptive rollout depth, UCT sufficiency threshold, loss avoidance.',
  },
};

function classifyLayer(notes: string): string {
  const lower = notes.toLowerCase();
  if (lower.includes('layer 3')) return 'Layer 3';
  if (lower.includes('layer 4')) return 'Layer 4';
  if (lower.includes('layer 5')) return 'Layer 5';
  if (lower.includes('layer 6')) return 'Layer 6';
  if (lower.includes('layer 7')) return 'Layer 7';
  if (lower.includes('layer 8')) return 'Layer 8';
  if (lower.includes('layer 9')) return 'Layer 9';
  return 'Other';
}

function groupByLayer(runs: ArenaRunSummary[]): LayerGroup[] {
  const groups: Record<string, ArenaRunSummary[]> = {};
  for (const run of runs) {
    const layer = classifyLayer(run.notes || '');
    if (!groups[layer]) groups[layer] = [];
    groups[layer].push(run);
  }
  const order = ['Layer 3', 'Layer 4', 'Layer 5', 'Layer 6', 'Layer 7', 'Layer 8', 'Layer 9', 'Other'];
  return order
    .filter(l => groups[l]?.length)
    .map(layer => ({
      layer,
      title: LAYER_DESCRIPTIONS[layer]?.title || layer,
      description: LAYER_DESCRIPTIONS[layer]?.description || '',
      runs: groups[layer],
    }));
}

const LayerRunCard: React.FC<{ run: ArenaRunSummary }> = ({ run }) => {
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!expanded) return;
    const load = async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/arena-runs/${run.run_id}`);
        if (resp.ok) setDetail(await resp.json());
      } catch { /* ignore */ }
    };
    load();
  }, [expanded, run.run_id]);

  const leaderboard = detail?.trueskill_ratings?.leaderboard || [];
  const winStats = detail?.win_stats || {};
  const winData = Object.entries(winStats)
    .map(([agent, stats], i) => ({
      name: agent.replace(/^mcts_/, ''),
      winRate: Math.round(stats.win_rate * 100),
      color: LAYER_COLORS[i % LAYER_COLORS.length],
    }))
    .sort((a, b) => b.winRate - a.winRate);

  return (
    <div className="bg-charcoal-900 border border-charcoal-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 text-left flex items-center justify-between hover:bg-charcoal-800/50 transition-colors"
      >
        <div>
          <span className="text-gray-200 font-medium text-sm">{run.notes || run.run_id}</span>
          <span className="text-gray-500 text-xs ml-3">{run.num_games} games | {run.agent_names.length} agents</span>
        </div>
        <svg className={`w-4 h-4 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {expanded && detail && (
        <div className="px-4 pb-4 space-y-4">
          {/* Win Rate Chart */}
          {winData.length > 0 && (
            <ResponsiveContainer width="100%" height={Math.max(120, winData.length * 40)}>
              <BarChart data={winData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis type="number" domain={[0, 100]} stroke="#666" tickFormatter={(v) => `${v}%`} />
                <YAxis type="category" dataKey="name" stroke="#999" width={140} tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#252526', border: '1px solid #333', borderRadius: '8px' }}
                  formatter={(value: any) => [`${value ?? 0}%`, 'Win Rate']}
                />
                <Bar dataKey="winRate" radius={[0, 4, 4, 0]}>
                  {winData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          {/* TrueSkill Leaderboard */}
          {leaderboard.length > 0 && (
            <div className="text-xs">
              <div className="text-gray-400 font-semibold uppercase tracking-wider mb-2" style={{ fontSize: '10px' }}>
                TrueSkill Ranking
              </div>
              <div className="space-y-1">
                {leaderboard.map((entry, i) => (
                  <div key={entry.agent_id} className="flex items-center gap-3">
                    <span className={`w-5 text-right font-mono ${i === 0 ? 'text-neon-blue' : 'text-gray-500'}`}>#{entry.rank}</span>
                    <span className="text-gray-300 flex-1">{entry.agent_id.replace(/^mcts_/, '')}</span>
                    <span className="text-gray-400 font-mono">{entry.mu.toFixed(1)}</span>
                    <span className="text-gray-600 font-mono text-[10px]">(+/-{entry.sigma.toFixed(1)})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export const TrainEval: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<ArenaRunSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const resp = await fetch(`${API_BASE}/api/arena-runs`);
        if (resp.ok) {
          const data = await resp.json();
          setRuns(data.runs || []);
        }
      } catch { /* ignore */ }
      setLoading(false);
    };
    load();
  }, []);

  const layerGroups = groupByLayer(runs);

  return (
    <div className="min-h-screen bg-charcoal-900 text-gray-200">
      {/* Header */}
      <div className="bg-charcoal-800 border-b border-charcoal-700">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-white">Layer Progression</h1>
            <p className="text-sm text-gray-400">
              How each MCTS improvement layer impacts performance
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => navigate('/benchmark')}
              className="px-4 py-2 text-sm bg-charcoal-700 border border-charcoal-600 hover:bg-charcoal-600 rounded transition-colors"
            >
              Full Benchmark
            </button>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 text-sm bg-charcoal-700 border border-charcoal-600 hover:bg-charcoal-600 rounded transition-colors"
            >
              Back to Game
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        {loading && <div className="text-gray-400 text-center py-12">Loading layer experiments...</div>}

        {!loading && layerGroups.length === 0 && (
          <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-12 text-center">
            <div className="text-gray-400 text-lg mb-2">No arena experiments found</div>
            <div className="text-gray-500 text-sm">
              Run arena experiments to see layer-by-layer progression.
              <br />
              <code className="text-neon-blue">python scripts/arena.py --config scripts/arena_config.json</code>
            </div>
          </div>
        )}

        {/* Layer Narrative */}
        {layerGroups.length > 0 && (
          <div className="space-y-8">
            {/* Overview */}
            <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-6">
              <h2 className="text-lg font-bold text-white mb-2">The MCTS Improvement Story</h2>
              <p className="text-gray-400 text-sm">
                This project builds a competitive Blokus AI through progressive MCTS enhancements.
                Each layer addresses a specific weakness: Layer 3 tames the branching factor,
                Layer 4 improves simulation quality, Layer 5 bootstraps cold-start evaluation,
                Layer 6 calibrates the evaluation function from data, Layer 7 models opponents,
                and Layer 9 self-tunes parameters at runtime. Below, arena experiments validate
                each layer's contribution.
              </p>
              <div className="flex gap-2 mt-4">
                {layerGroups.map(g => (
                  <a key={g.layer} href={`#${g.layer.replace(' ', '-')}`} className="text-xs px-2 py-1 rounded bg-neon-blue/10 text-neon-blue border border-neon-blue/20 hover:bg-neon-blue/20 transition-colors">
                    {g.layer}: {g.title}
                  </a>
                ))}
              </div>
            </div>

            {/* Layer Sections */}
            {layerGroups.map(group => (
              <div key={group.layer} id={group.layer.replace(' ', '-')} className="bg-charcoal-800 border border-charcoal-700 rounded-lg overflow-hidden">
                <div className="p-6 border-b border-charcoal-700">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs font-bold uppercase px-2 py-0.5 rounded bg-neon-blue/10 text-neon-blue border border-neon-blue/20">
                      {group.layer}
                    </span>
                    <h2 className="text-xl font-bold text-white">{group.title}</h2>
                  </div>
                  <p className="text-gray-400 text-sm">{group.description}</p>
                </div>
                <div className="p-4 space-y-2">
                  {group.runs.map(run => (
                    <LayerRunCard key={run.run_id} run={run} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
