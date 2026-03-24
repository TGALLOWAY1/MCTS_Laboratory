/**
 * MCTS Visualization Platform — dedicated analysis page with tabbed layout.
 *
 * Tabs:
 * 1. Search Overview — root policy, depth/breadth over time, rollout histogram
 * 2. Decision Analysis — UCT breakdown, exploration vs exploitation, convergence
 * 3. Spatial Analysis — board exploration heatmap
 */
import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useGameStore } from '../store/gameStore';
import { SearchTraceV1 } from '../types/mcts';
import {
    RootPolicyChart,
    DepthOverTimeChart,
    BreadthOverTimeChart,
    RolloutHistogram,
    ExplorationExploitationChart,
    UctBreakdownChart,
    BoardExplorationHeatmap,
} from '../components/mcts-viz';

type Tab = 'overview' | 'decision' | 'spatial';

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
            {open && <div className="border-t border-charcoal-700 p-3">{children}</div>}
        </div>
    );
};

const TabButton: React.FC<{ active: boolean; onClick: () => void; children: React.ReactNode }> = ({
    active, onClick, children,
}) => (
    <button
        onClick={onClick}
        className={`px-4 py-2 text-xs font-bold uppercase tracking-wider transition-colors rounded-t-lg ${
            active
                ? 'bg-charcoal-800 text-neon-blue border border-charcoal-700 border-b-charcoal-800'
                : 'bg-charcoal-900 text-gray-500 hover:text-gray-300 border border-transparent'
        }`}
    >
        {children}
    </button>
);

export const MctsVisualization: React.FC = () => {
    const gameState = useGameStore((s) => s.gameState);
    const [activeTab, setActiveTab] = useState<Tab>('overview');

    // Get search trace from current game state or from game history
    const trace: SearchTraceV1 | null = useMemo(() => {
        // First check current state
        if (gameState?.search_trace) return gameState.search_trace;

        // Check game history for MCTS diagnostics with search trace
        const history = gameState?.game_history;
        if (history?.length) {
            for (let i = history.length - 1; i >= 0; i--) {
                const entry = history[i] as any;
                if (entry?.mcts_diagnostics?.searchTrace) {
                    return entry.mcts_diagnostics.searchTrace;
                }
            }
        }
        return null;
    }, [gameState]);

    const board = gameState?.board as number[][] | undefined;

    if (!trace) {
        return (
            <div className="min-h-screen bg-charcoal-900 text-gray-200 p-6">
                <div className="flex justify-between items-center mb-6">
                    <h1 className="text-2xl font-bold">MCTS Visualization</h1>
                    <Link to="/play" className="text-neon-blue text-sm hover:underline">Back to Play</Link>
                </div>
                <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg p-8 text-center">
                    <p className="text-gray-400">No MCTS search trace available.</p>
                    <p className="text-xs text-gray-500 mt-2">
                        Play a game with a full MCTS agent (not FastMCTS) with search trace enabled to see visualizations.
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-charcoal-900 text-gray-200 p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-4">
                <div>
                    <h1 className="text-2xl font-bold">MCTS Visualization</h1>
                    <p className="text-xs text-gray-500 mt-1">
                        {trace.totalIterations} iterations | {trace.sampleRate}x sample rate |{' '}
                        {trace.rolloutResults.length} rollouts
                    </p>
                </div>
                <Link to="/play" className="text-neon-blue text-sm hover:underline">Back to Play</Link>
            </div>

            {/* Tab bar */}
            <div className="flex gap-1 mb-0">
                <TabButton active={activeTab === 'overview'} onClick={() => setActiveTab('overview')}>
                    Search Overview
                </TabButton>
                <TabButton active={activeTab === 'decision'} onClick={() => setActiveTab('decision')}>
                    Decision Analysis
                </TabButton>
                <TabButton active={activeTab === 'spatial'} onClick={() => setActiveTab('spatial')}>
                    Spatial Analysis
                </TabButton>
            </div>

            {/* Tab content */}
            <div className="bg-charcoal-800 border border-charcoal-700 rounded-b-lg rounded-tr-lg p-4 space-y-4">

                {/* === SEARCH OVERVIEW === */}
                {activeTab === 'overview' && (
                    <>
                        <Collapsible title="Root Move Distribution">
                            <RootPolicyChart snapshots={trace.rootChildrenSnapshots} />
                        </Collapsible>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <Collapsible title="Tree Depth Over Time">
                                <DepthOverTimeChart data={trace.depthOverTime} />
                            </Collapsible>
                            <Collapsible title="Tree Breadth Over Time">
                                <BreadthOverTimeChart data={trace.breadthOverTime} />
                            </Collapsible>
                        </div>

                        <Collapsible title="Rollout Result Distribution">
                            <RolloutHistogram results={trace.rolloutResults} />
                        </Collapsible>
                    </>
                )}

                {/* === DECISION ANALYSIS === */}
                {activeTab === 'decision' && (
                    <>
                        <Collapsible title="UCT Score Breakdown (Root Children)">
                            <UctBreakdownChart breakdown={trace.uctBreakdown} />
                        </Collapsible>

                        <Collapsible title="Exploration vs Exploitation Over Time">
                            <ExplorationExploitationChart data={trace.explorationOverTime} />
                        </Collapsible>

                        {trace.rootChildrenSnapshots.length > 1 && (
                            <Collapsible title="Policy Convergence" defaultOpen={false}>
                                <div className="text-xs text-gray-400 mb-2">
                                    Root move distribution at different search checkpoints:
                                </div>
                                <div className="space-y-3">
                                    {trace.rootChildrenSnapshots.map((snap, i) => (
                                        <div key={i}>
                                            <div className="text-[10px] text-gray-500 mb-1">
                                                Iteration {snap.checkpoint}
                                            </div>
                                            <div className="flex gap-1 flex-wrap">
                                                {snap.children.slice(0, 8).map((c, j) => (
                                                    <div
                                                        key={j}
                                                        className="bg-charcoal-700 rounded px-1.5 py-0.5 text-[10px]"
                                                        style={{ opacity: 0.3 + c.prob * 0.7 }}
                                                    >
                                                        <span className="text-gray-300">P{c.pieceId}</span>
                                                        <span className="text-neon-blue ml-1">{(c.prob * 100).toFixed(1)}%</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </Collapsible>
                        )}
                    </>
                )}

                {/* === SPATIAL ANALYSIS === */}
                {activeTab === 'spatial' && (
                    <>
                        <Collapsible title="Board Exploration Heatmap">
                            <BoardExplorationHeatmap grid={trace.explorationGrid} board={board} />
                        </Collapsible>

                        <Collapsible title="Exploration Statistics" defaultOpen={false}>
                            <div className="text-xs text-gray-400 space-y-1">
                                {trace.explorationGrid && (() => {
                                    let totalCells = 0;
                                    let totalCount = 0;
                                    let maxCount = 0;
                                    for (const row of trace.explorationGrid) {
                                        for (const v of row) {
                                            if (v > 0) totalCells++;
                                            totalCount += v;
                                            if (v > maxCount) maxCount = v;
                                        }
                                    }
                                    return (
                                        <>
                                            <p>Cells explored: {totalCells} / 400 ({(totalCells / 4).toFixed(1)}%)</p>
                                            <p>Total exploration count: {totalCount.toLocaleString()}</p>
                                            <p>Max cell count: {maxCount}</p>
                                            <p>Avg per explored cell: {totalCells > 0 ? (totalCount / totalCells).toFixed(1) : '0'}</p>
                                        </>
                                    );
                                })()}
                            </div>
                        </Collapsible>
                    </>
                )}
            </div>
        </div>
    );
};
