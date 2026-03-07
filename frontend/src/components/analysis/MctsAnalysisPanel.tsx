
import React, { useMemo, useState } from 'react';
import { useGameStore } from '../../store/gameStore';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    LineChart, Line, CartesianGrid, Legend
} from 'recharts';
import { MctsDiagnosticsV1 } from '../../types/mcts';

const PLAYER_COLORS: Record<string, string> = {
    RED: '#ef4444',
    BLUE: '#3b82f6',
    GREEN: '#22c55e',
    YELLOW: '#eab308',
};

const Collapsible: React.FC<{ title: string; defaultOpen?: boolean; children: React.ReactNode }> = ({
    title, defaultOpen = true, children,
}) => {
    const [open, setOpen] = useState(defaultOpen);
    return (
        <div className="bg-charcoal-800 rounded-lg border border-charcoal-700 overflow-hidden">
            <button
                onClick={() => setOpen(!open)}
                className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-charcoal-700 transition-colors"
            >
                <span className="text-xs font-bold text-gray-300 uppercase tracking-widest">{title}</span>
                <span className="text-neon-blue text-sm">{open ? '−' : '+'}</span>
            </button>
            {open && <div className="border-t border-charcoal-700">{children}</div>}
        </div>
    );
};

export const MctsAnalysisPanel: React.FC = () => {
    const gameState = useGameStore((s) => s.gameState);
    const currentSliderTurn = useGameStore((s) => s.currentSliderTurn);
    const setCurrentSliderTurn = useGameStore((s) => s.setCurrentSliderTurn);

    if (!gameState) {
        return <div className="p-6 text-center text-gray-500">No game active.</div>;
    }

    const gameHistory = gameState.game_history || [];
    const totalTurns = gameHistory.length;
    const actualPly = currentSliderTurn ?? (totalTurns > 0 ? totalTurns : 0);

    // Filter history to just moves with MCTS Diagnostics
    const movesWithMcts = useMemo(() =>
        gameHistory
            .map((entry: any, index: number) => ({ ...entry, originalIndex: index }))
            .filter((entry: any) => entry.mcts_diagnostics),
        [gameHistory]
    );

    // Find the nearest MCTS move
    const safeIndex = useMemo(() => {
        if (!movesWithMcts.length) return -1;
        // Prefer exact match by turn_number or ply
        const targetTurn = actualPly;
        const exact = movesWithMcts.findIndex((m: any) => m.turn_number === targetTurn || m.turn_number === targetTurn - 1);
        if (exact >= 0) return exact;
        // Fall back to last entry <= actualPly
        for (let i = movesWithMcts.length - 1; i >= 0; i--) {
            if ((movesWithMcts[i].turn_number || 0) <= targetTurn) return i;
        }
        return 0;
    }, [movesWithMcts, actualPly]);

    const selectedMove = movesWithMcts[safeIndex];

    const handlePrev = () => { if (safeIndex > 0) setCurrentSliderTurn(movesWithMcts[safeIndex - 1].turn_number || 0); };
    const handleNext = () => { if (safeIndex < movesWithMcts.length - 1) setCurrentSliderTurn(movesWithMcts[safeIndex + 1].turn_number || 0); };

    const handleExportTrace = () => {
        const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(movesWithMcts, null, 2));
        const downloadAnchorNode = document.createElement('a');
        downloadAnchorNode.setAttribute("href", dataStr);
        downloadAnchorNode.setAttribute("download", `mcts_trace_${Date.now()}.json`);
        document.body.appendChild(downloadAnchorNode); // required for firefox
        downloadAnchorNode.click();
        downloadAnchorNode.remove();
    };

    // Data for Entropy Over Time Chart
    const entropyHistoryData = useMemo(() => {
        return movesWithMcts.map((m: any) => ({
            turn: m.turn_number || 0,
            player: m.player_to_move,
            entropy: m.mcts_diagnostics.policyEntropy || 0,
            simulations: m.mcts_diagnostics.simulations || 0,
        }));
    }, [movesWithMcts]);

    // Data for Agent Comparison
    const comparisonData = useMemo(() => {
        const stats: Record<string, { sims: number; entropy: number; count: number; simsPerSec: number }> = {};
        movesWithMcts.forEach((m: any) => {
            const p = m.player_to_move;
            const d = m.mcts_diagnostics;
            if (!stats[p]) stats[p] = { sims: 0, entropy: 0, count: 0, simsPerSec: 0 };
            stats[p].sims += d.simulations || 0;
            stats[p].entropy += d.policyEntropy || 0;
            stats[p].simsPerSec += d.simsPerSec || 0;
            stats[p].count += 1;
        });

        return Object.entries(stats).map(([player, s]) => ({
            player,
            avgSims: Math.round(s.sims / s.count),
            avgEntropy: parseFloat((s.entropy / s.count).toFixed(3)),
            avgSimsPerSec: Math.round(s.simsPerSec / s.count),
        }));
    }, [movesWithMcts]);

    if (movesWithMcts.length === 0) {
        return (
            <div className="h-full flex items-center justify-center p-6 text-center text-gray-500">
                <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-6">
                    <p>No MCTS Diagnostics tracked yet.</p>
                    <p className="text-xs mt-2 text-gray-400">Ensure "Enable MCTS Diagnostics" is checked.</p>
                </div>
            </div>
        );
    }

    const diag: MctsDiagnosticsV1 | null = selectedMove?.mcts_diagnostics || null;
    const playerColor = PLAYER_COLORS[selectedMove?.player_to_move] || '#9ca3af';

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-charcoal-900 border border-charcoal-700 p-2 rounded shadow-xl text-xs">
                    <p className="font-bold text-gray-200 mb-1">{label}</p>
                    {payload.map((p: any, i: number) => (
                        <p key={i} style={{ color: p.color }}>
                            {p.name}: {typeof p.value === 'number' ? p.value.toFixed(4).replace(/\.?0+$/, '') : p.value}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    return (
        <div className="h-full overflow-y-auto custom-scrollbar p-4 space-y-4 bg-charcoal-900">

            {/* ─── MCTS MOVES NAVIGATOR ─── */}
            <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-neon-blue uppercase tracking-widest">MCTS Step Explorer</span>
                    <button
                        onClick={handleExportTrace}
                        className="px-2 py-1 bg-charcoal-700 hover:bg-charcoal-600 text-gray-300 text-[10px] rounded uppercase font-bold tracking-wider transition-colors"
                    >
                        Export Trace JSON
                    </button>
                </div>
                <div className="flex items-center gap-3 mb-3">
                    <span className="text-[10px] font-mono text-slate-500">1</span>
                    <input
                        type="range"
                        min={1}
                        max={totalTurns || 1}
                        value={currentSliderTurn || totalTurns}
                        onChange={(e) => setCurrentSliderTurn(parseInt(e.target.value, 10))}
                        className="flex-1 accent-neon-blue h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer"
                    />
                    <span className="text-[10px] font-mono text-slate-500">{totalTurns}</span>
                </div>
                <div className="flex items-center justify-between">
                    <button onClick={handlePrev} disabled={safeIndex <= 0} className="px-3 py-1 text-xs bg-charcoal-700 rounded hover:bg-charcoal-600 disabled:opacity-30 text-gray-200">← Prev</button>
                    <div className="text-center">
                        <div className="text-sm font-bold" style={{ color: playerColor }}>
                            {selectedMove?.player_to_move}
                        </div>
                        <div className="text-xs text-gray-400">
                            Turn {selectedMove?.turn_number}
                            <span className="ml-1 text-gray-500">({safeIndex + 1}/{movesWithMcts.length})</span>
                        </div>
                    </div>
                    <button onClick={handleNext} disabled={safeIndex >= movesWithMcts.length - 1} className="px-3 py-1 text-xs bg-charcoal-700 rounded hover:bg-charcoal-600 disabled:opacity-30 text-gray-200">Next →</button>
                </div>
            </div>

            <Collapsible title="ℹ️ Metrics Explained" defaultOpen={false}>
                <div className="p-4 text-xs text-gray-300 space-y-3 bg-charcoal-700/30">
                    <p><strong>Simulations & Speed:</strong> How many times the agent traversed its decision tree and evaluated an outcome. `FastMCTSAgent` does ultra-fast 1-ply rollouts in the browser to maintain 60 FPS, while full MCTS simulates deeper.</p>
                    <p><strong>Entropy:</strong> Measures uncertainty. High entropy means the AI is unsure between many viable moves. Low entropy means it is highly confident in one specific line.</p>
                    <p><strong>Root Policy & Q-Values:</strong> The Visits bar shows how many times a move was explored. The Q-Mean line shows the estimated win-rate [0, 1] of that move.</p>
                    <p><strong>Search Tree Depth:</strong> Shows how deep the agent looked ahead. <em>Note: The browser `FastMCTSAgent` optimizes for speed by evaluating immediate children without full deep cloning, so maximum depth is typically 1 or 2.</em></p>
                    <p><strong>Convergence Trace:</strong> Shows how the AI's opinion of the best move (Q-Mean) and its overall uncertainty (Entropy) evolved over the course of thinking about this single turn.</p>
                </div>
            </Collapsible>

            {diag && (
                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-3 col-span-2 shadow flex gap-4 text-center justify-around items-center mt-2">
                        <div>
                            <div className="text-gray-400 text-[10px] uppercase font-bold">Simulations</div>
                            <div className="text-gray-200 font-mono">{diag.simulations}</div>
                        </div>
                        <div>
                            <div className="text-gray-400 text-[10px] uppercase font-bold">Time Spent</div>
                            <div className="text-gray-200 font-mono">{diag.timeSpentMs.toFixed(0)} ms</div>
                        </div>
                        <div>
                            <div className="text-gray-400 text-[10px] uppercase font-bold">Speed</div>
                            <div className="text-gray-200 font-mono">{diag.simsPerSec} sim/s</div>
                        </div>
                        <div>
                            <div className="text-neon-purple text-[10px] uppercase font-bold">Entropy</div>
                            <div className="text-neon-purple font-mono">{diag.policyEntropy.toFixed(3)}</div>
                        </div>
                        <div>
                            <div className="text-gray-400 text-[10px] uppercase font-bold">Max Depth</div>
                            <div className="text-gray-200 font-mono">{diag.maxDepthReached}</div>
                        </div>
                    </div>

                    {/* ─── POLICY HISTOGRAM ─── */}
                    <div className="col-span-2">
                        <Collapsible title="Root Policy & Q-Values">
                            <div className="p-3 h-[250px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={diag.rootPolicy.slice(0, 20)} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                                        <XAxis
                                            dataKey={(d) => `${d.piece_id} (R${d.anchor_row}C${d.anchor_col})`}
                                            tick={{ fill: '#9ca3af', fontSize: 10 }}
                                            tickFormatter={(val) => val.split(' ')[0]}
                                        />
                                        <YAxis yAxisId="left" tick={{ fill: '#64748b', fontSize: 10 }} orientation="left" />
                                        <YAxis yAxisId="right" tick={{ fill: '#3b82f6', fontSize: 10 }} orientation="right" domain={[0, 1]} />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Legend wrapperStyle={{ fontSize: 10 }} />
                                        <Bar yAxisId="left" dataKey="visits" name="Visits" fill="#64748b" radius={[4, 4, 0, 0]} />
                                        <Bar yAxisId="right" dataKey="q_value" name="Q-Mean" fill="#3b82f6" radius={[4, 4, 0, 0]} barSize={10} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </Collapsible>
                    </div>

                    {/* ─── CONVERGENCE TRACE ─── */}
                    <div className="col-span-2">
                        <Collapsible title="Convergence & Entropy Trace">
                            <div className="p-3 h-[220px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={diag.bestMoveTrace} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                                        <XAxis dataKey="sim" tick={{ fill: '#9ca3af', fontSize: 10 }} type="number" domain={['dataMin', 'dataMax']} />
                                        <YAxis yAxisId="left" domain={[0, 1]} tick={{ fill: '#3b82f6', fontSize: 10 }} orientation="left" />
                                        <YAxis yAxisId="right" tick={{ fill: '#a855f7', fontSize: 10 }} orientation="right" />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Legend wrapperStyle={{ fontSize: 10 }} />
                                        <Line yAxisId="left" type="monotone" dataKey="bestQMean" name="Best Move Q-Mean" stroke="#3b82f6" strokeWidth={2} dot={false} />
                                        <Line yAxisId="right" type="stepAfter" dataKey="entropy" name="Policy Entropy" stroke="#a855f7" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </Collapsible>
                    </div>

                    {/* ─── DEPTH BREADTH HISTOGRAM ─── */}
                    <div className="col-span-2">
                        <Collapsible title="Search Tree Depth">
                            <div className="p-3 h-[200px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={diag.nodesByDepth} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                                        <XAxis dataKey="depth" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                                        <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                                        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                                        <Bar dataKey="nodes" name="Nodes Expanded at Depth" fill="#10b981" radius={[2, 2, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </Collapsible>
                    </div>
                </div>
            )}

            {/* ─── ENTROPY HISTORY (ALL MOVES) ─── */}
            <Collapsible title="Game Flow (Entropy)">
                <div className="p-3 h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={entropyHistoryData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                            <XAxis dataKey="turn" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                            <YAxis tick={{ fill: '#a855f7', fontSize: 10 }} />
                            <Tooltip content={<CustomTooltip />} />
                            <Line type="monotone" dataKey="entropy" name="Policy Entropy" stroke="#a855f7" strokeWidth={2} dot={{ r: 3, fill: '#charcoal-900', strokeWidth: 2 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </Collapsible>

            {/* ─── AGENT COMPARISON ─── */}
            <Collapsible title="Agent Performance Comparison" defaultOpen={false}>
                <div className="p-3">
                    <div className="overflow-x-auto">
                        <table className="w-full text-[10px] text-left">
                            <thead className="text-gray-500 uppercase">
                                <tr className="border-b border-charcoal-700">
                                    <th className="py-2">Player</th>
                                    <th className="py-2 text-right">Avg Sims</th>
                                    <th className="py-2 text-right">Avg Sims/s</th>
                                    <th className="py-2 text-right">Avg Entropy</th>
                                </tr>
                            </thead>
                            <tbody className="text-gray-300">
                                {comparisonData.map((row) => (
                                    <tr key={row.player} className="border-b border-charcoal-700/50">
                                        <td className="py-2 font-bold" style={{ color: PLAYER_COLORS[row.player] }}>{row.player}</td>
                                        <td className="py-2 text-right font-mono">{row.avgSims}</td>
                                        <td className="py-2 text-right font-mono">{row.avgSimsPerSec}</td>
                                        <td className="py-2 text-right font-mono text-neon-purple">{row.avgEntropy}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </Collapsible>
        </div>
    );
};
