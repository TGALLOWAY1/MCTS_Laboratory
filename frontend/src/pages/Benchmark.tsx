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
    agent_count: number;
}

interface TrueSkillEntry {
    agent_id: string;
    mu: number;
    sigma: number;
    conservative: number;
    rank: number;
    games_played: number;
}

interface WinStats {
    [agent: string]: {
        games_played: number;
        outright_wins: number;
        win_rate: number;
    };
}

interface PairwiseMatchup {
    agent_a: string;
    agent_b: string;
    a_beats_b: number;
    b_beats_a: number;
    tie: number;
    total: number;
}

interface ArenaRunDetail {
    run_id: string;
    num_games: number;
    run_config: {
        notes?: string;
        created_at?: string;
        agents: Array<{
            name: string;
            type: string;
            thinking_time_ms?: number;
            params: Record<string, any>;
        }>;
    };
    pairwise_matchups: Record<string, PairwiseMatchup>;
    trueskill_ratings?: {
        leaderboard: TrueSkillEntry[];
    };
    win_stats: WinStats;
    game_duration_sec?: {
        mean: number;
        median: number;
        min: number;
        max: number;
    };
}

const CHART_COLORS = ['#00F0FF', '#00FF9D', '#FFE600', '#FF4D4D', '#A855F7', '#F97316'];

function getActiveLayers(params: Record<string, any>): string[] {
    const layers: string[] = [];
    if (params.progressive_widening_enabled || params.progressive_history_enabled) layers.push('L3');
    if (params.rollout_policy && params.rollout_policy !== 'random') layers.push('L4');
    if (params.rollout_cutoff_depth != null) layers.push('L4');
    if (params.rave_enabled) layers.push('L5');
    if (params.nst_enabled) layers.push('L5');
    if (params.state_eval_phase_weights) layers.push('L6');
    if (params.opponent_modeling_enabled) layers.push('L7');
    if (params.num_workers && params.num_workers > 1) layers.push('L8');
    if (params.adaptive_exploration_enabled || params.sufficiency_threshold_enabled) layers.push('L9');
    return [...new Set(layers)];
}

export const Benchmark: React.FC = () => {
    const navigate = useNavigate();
    const [runs, setRuns] = useState<ArenaRunSummary[]>([]);
    const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
    const [runDetail, setRunDetail] = useState<ArenaRunDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadRuns = async () => {
            try {
                const resp = await fetch(`${API_BASE}/api/arena-runs`);
                if (!resp.ok) return;
                const data = await resp.json();
                setRuns(data.runs || []);
                if (data.runs?.length > 0) {
                    setSelectedRunId(data.runs[0].run_id);
                }
            } catch {
                // API not available
            } finally {
                setLoading(false);
            }
        };
        loadRuns();
    }, []);

    useEffect(() => {
        if (!selectedRunId) return;
        const loadDetail = async () => {
            try {
                const resp = await fetch(`${API_BASE}/api/arena-runs/${selectedRunId}`);
                if (!resp.ok) return;
                setRunDetail(await resp.json());
            } catch {
                // API not available
            }
        };
        loadDetail();
    }, [selectedRunId]);

    const leaderboard = runDetail?.trueskill_ratings?.leaderboard || [];
    const winStats = runDetail?.win_stats || {};
    const matchups = runDetail?.pairwise_matchups || {};
    const agents = runDetail?.run_config?.agents || [];
    const agentNames = agents.map(a => a.name);

    // Build pairwise matrix
    const buildMatrix = () => {
        const matrix: Record<string, Record<string, number | null>> = {};
        for (const name of agentNames) {
            matrix[name] = {};
            for (const other of agentNames) {
                matrix[name][other] = null;
            }
        }
        for (const m of Object.values(matchups)) {
            if (m.total > 0) {
                matrix[m.agent_a][m.agent_b] = Math.round((m.a_beats_b / m.total) * 100);
                matrix[m.agent_b][m.agent_a] = Math.round((m.b_beats_a / m.total) * 100);
            }
        }
        return matrix;
    };

    const winRateColor = (pct: number | null) => {
        if (pct === null) return 'text-gray-600';
        if (pct >= 70) return 'text-green-400';
        if (pct >= 50) return 'text-neon-blue';
        if (pct >= 30) return 'text-yellow-400';
        return 'text-red-400';
    };

    const tsData = leaderboard.map((entry, i) => ({
        name: entry.agent_id.replace(/^mcts_/, ''),
        mu: Math.round(entry.mu * 10) / 10,
        conservative: Math.round(entry.conservative * 10) / 10,
        sigma: Math.round(entry.sigma * 10) / 10,
        color: CHART_COLORS[i % CHART_COLORS.length],
    }));

    const winData = Object.entries(winStats).map(([agent, stats], i) => ({
        name: agent.replace(/^mcts_/, ''),
        winRate: Math.round(stats.win_rate * 100),
        wins: stats.outright_wins,
        games: stats.games_played,
        color: CHART_COLORS[i % CHART_COLORS.length],
    })).sort((a, b) => b.winRate - a.winRate);

    return (
        <div className="min-h-screen bg-charcoal-900 text-gray-200 p-8">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                            <svg className="w-8 h-8 text-neon-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                            Arena Results
                        </h1>
                        <p className="text-gray-400 mt-2">Tournament results from arena experiments</p>
                    </div>
                    <button
                        onClick={() => navigate('/')}
                        className="px-4 py-2 bg-charcoal-800 border border-charcoal-700 hover:bg-charcoal-700 rounded transition-colors"
                    >
                        Back to Game
                    </button>
                </div>

                {loading && <div className="text-gray-400 text-center py-12">Loading arena runs...</div>}

                {!loading && runs.length === 0 && (
                    <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-12 text-center">
                        <div className="text-gray-400 text-lg mb-2">No arena runs found</div>
                        <div className="text-gray-500 text-sm">Run <code className="text-neon-blue">python scripts/arena.py --config scripts/arena_config.json</code> to generate results</div>
                    </div>
                )}

                {runs.length > 0 && (
                    <>
                        {/* Run Selector */}
                        <div className="mb-6">
                            <select
                                value={selectedRunId || ''}
                                onChange={(e) => setSelectedRunId(e.target.value)}
                                className="bg-charcoal-800 border border-charcoal-700 text-gray-200 rounded-lg px-4 py-2 focus:outline-none focus:border-neon-blue"
                            >
                                {runs.map(run => (
                                    <option key={run.run_id} value={run.run_id}>
                                        {run.run_id} — {run.notes || `${run.agent_count} agents, ${run.num_games} games`}
                                    </option>
                                ))}
                            </select>
                        </div>

                        {runDetail && (
                            <>
                                {/* Run Info */}
                                <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-4 mb-6">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            {runDetail.run_config.notes && (
                                                <p className="text-neon-blue font-medium">{runDetail.run_config.notes}</p>
                                            )}
                                            <p className="text-gray-500 text-sm mt-1">
                                                {runDetail.num_games} games | {agents.length} agents | {runDetail.run_config.created_at?.slice(0, 10)}
                                                {runDetail.game_duration_sec && ` | Avg ${runDetail.game_duration_sec.mean.toFixed(1)}s/game`}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Top Stats */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                                    <div className="bg-charcoal-800 border border-charcoal-700 p-6 rounded-lg">
                                        <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-2">Top Agent</h3>
                                        <div className="text-2xl font-bold text-neon-blue">
                                            {leaderboard[0]?.agent_id.replace(/^mcts_/, '') || '-'}
                                        </div>
                                        {leaderboard[0] && (
                                            <div className="text-sm text-green-400 mt-1">
                                                TrueSkill {leaderboard[0].mu.toFixed(1)} ({leaderboard[0].conservative.toFixed(1)} conservative)
                                            </div>
                                        )}
                                    </div>
                                    <div className="bg-charcoal-800 border border-charcoal-700 p-6 rounded-lg">
                                        <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-2">Games Played</h3>
                                        <div className="text-2xl font-bold text-white">{runDetail.num_games}</div>
                                        <div className="text-sm text-gray-500 mt-1">{Object.keys(matchups).length} matchup pairs</div>
                                    </div>
                                    <div className="bg-charcoal-800 border border-charcoal-700 p-6 rounded-lg">
                                        <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-2">Highest Win Rate</h3>
                                        <div className="text-2xl font-bold text-neon-yellow">
                                            {winData[0] ? `${winData[0].winRate}%` : '-'}
                                        </div>
                                        <div className="text-sm text-gray-500 mt-1">
                                            {winData[0]?.name || '-'} ({winData[0]?.wins || 0}/{winData[0]?.games || 0} wins)
                                        </div>
                                    </div>
                                </div>

                                {/* TrueSkill Chart + Win Rate Chart side by side */}
                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                                    {/* TrueSkill Ratings */}
                                    <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-6">
                                        <h2 className="text-lg font-bold text-white mb-4">TrueSkill Ratings</h2>
                                        {tsData.length > 0 ? (
                                            <ResponsiveContainer width="100%" height={250}>
                                                <BarChart data={tsData} layout="vertical" margin={{ left: 20 }}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                                    <XAxis type="number" stroke="#666" />
                                                    <YAxis type="category" dataKey="name" stroke="#999" width={120} tick={{ fontSize: 12 }} />
                                                    <Tooltip
                                                        contentStyle={{ backgroundColor: '#252526', border: '1px solid #333', borderRadius: '8px' }}
                                                        formatter={(value: any, name: any) => [(value ?? 0).toFixed(1), name === 'mu' ? 'Rating (mu)' : 'Conservative']}
                                                    />
                                                    <Bar dataKey="mu" name="mu" radius={[0, 4, 4, 0]}>
                                                        {tsData.map((entry, i) => (
                                                            <Cell key={i} fill={entry.color} fillOpacity={0.8} />
                                                        ))}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        ) : (
                                            <div className="text-gray-500 text-center py-8">No TrueSkill data</div>
                                        )}
                                    </div>

                                    {/* Win Rates */}
                                    <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-6">
                                        <h2 className="text-lg font-bold text-white mb-4">Win Rates</h2>
                                        {winData.length > 0 ? (
                                            <ResponsiveContainer width="100%" height={250}>
                                                <BarChart data={winData} layout="vertical" margin={{ left: 20 }}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                                    <XAxis type="number" domain={[0, 100]} stroke="#666" tickFormatter={(v) => `${v}%`} />
                                                    <YAxis type="category" dataKey="name" stroke="#999" width={120} tick={{ fontSize: 12 }} />
                                                    <Tooltip
                                                        contentStyle={{ backgroundColor: '#252526', border: '1px solid #333', borderRadius: '8px' }}
                                                        formatter={(value: any) => [`${value ?? 0}%`, 'Win Rate']}
                                                    />
                                                    <Bar dataKey="winRate" name="Win Rate" radius={[0, 4, 4, 0]}>
                                                        {winData.map((entry, i) => (
                                                            <Cell key={i} fill={entry.color} fillOpacity={0.8} />
                                                        ))}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        ) : (
                                            <div className="text-gray-500 text-center py-8">No win rate data</div>
                                        )}
                                    </div>
                                </div>

                                {/* Pairwise Win Rate Matrix */}
                                <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg overflow-hidden mb-8">
                                    <div className="p-6 border-b border-charcoal-700">
                                        <h2 className="text-xl font-bold text-white">
                                            Pairwise Win Rate Matrix (N={runDetail.num_games})
                                        </h2>
                                    </div>
                                    <div className="overflow-x-auto p-4">
                                        <table className="w-full text-left text-sm">
                                            <thead>
                                                <tr className="text-gray-500 border-b border-charcoal-700">
                                                    <th className="py-3 px-4">Agent</th>
                                                    {agentNames.map(name => (
                                                        <th key={name} className="py-3 px-4 font-normal">
                                                            vs {name.replace(/^mcts_/, '')}
                                                        </th>
                                                    ))}
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {agentNames.map(rowAgent => {
                                                    const matrix = buildMatrix();
                                                    return (
                                                        <tr key={rowAgent} className="border-b border-charcoal-700/50 hover:bg-charcoal-700/30">
                                                            <td className="py-3 px-4 font-semibold text-gray-300">
                                                                {rowAgent.replace(/^mcts_/, '')}
                                                            </td>
                                                            {agentNames.map(colAgent => {
                                                                const pct = rowAgent === colAgent ? null : matrix[rowAgent]?.[colAgent];
                                                                return (
                                                                    <td key={colAgent} className={`py-3 px-4 ${rowAgent === colAgent ? 'text-gray-600' : winRateColor(pct)}`}>
                                                                        {rowAgent === colAgent ? '—' : pct !== null ? `${pct}%` : '-'}
                                                                    </td>
                                                                );
                                                            })}
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                {/* Agent Configurations */}
                                <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg overflow-hidden">
                                    <div className="p-6 border-b border-charcoal-700">
                                        <h2 className="text-xl font-bold text-white">Agent Configurations</h2>
                                    </div>
                                    <div className="p-4 space-y-3">
                                        {agents.map((agent) => {
                                            const layers = getActiveLayers(agent.params || {});
                                            return (
                                                <div key={agent.name} className="bg-charcoal-900 rounded-lg p-4 border border-charcoal-700/50">
                                                    <div className="flex items-center justify-between mb-2">
                                                        <span className="font-semibold text-gray-200">{agent.name}</span>
                                                        <div className="flex gap-1">
                                                            {layers.length > 0 ? layers.map(l => (
                                                                <span key={l} className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-neon-blue/10 text-neon-blue border border-neon-blue/20">
                                                                    {l}
                                                                </span>
                                                            )) : (
                                                                <span className="text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-charcoal-700 text-gray-400">
                                                                    Baseline
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <div className="text-xs text-gray-500 space-x-4">
                                                        <span>type: {agent.type}</span>
                                                        {agent.thinking_time_ms && <span>think: {agent.thinking_time_ms}ms</span>}
                                                        {Object.entries(agent.params || {}).filter(([k, v]) => v !== false && v !== null && k !== 'deterministic_time_budget' && k !== 'iterations_per_ms').map(([k, v]) => (
                                                            <span key={k}>{k}: {String(v)}</span>
                                                        ))}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};
