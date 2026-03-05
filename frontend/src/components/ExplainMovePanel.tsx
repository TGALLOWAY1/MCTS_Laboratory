import React from 'react';
import { useGameStore } from '../store/gameStore';
import { MctsTopMovesTable } from './MctsTopMovesTable';

export const ExplainMovePanel: React.FC = () => {
    const gameState = useGameStore((s) => s.gameState);
    const mctsStats = gameState?.mcts_stats;

    // Only show explanation if there are MCTS stats/moves available
    if (!gameState?.mcts_top_moves?.length && !mctsStats) {
        return (
            <div className="p-4 border-b border-charcoal-700 bg-charcoal-900 h-full flex items-center justify-center">
                <div className="text-center">
                    <svg className="w-12 h-12 text-charcoal-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <p className="text-gray-400 text-sm">Waiting for AI move...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col bg-charcoal-900 overflow-hidden">
            <div className="p-4 bg-charcoal-800 border-b border-charcoal-700 shrink-0">
                <h2 className="text-lg font-bold text-gray-200 flex items-center gap-2">
                    <svg className="w-5 h-5 text-neon-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Explain This Move
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                    Review the AI's internal decision making process and alternative candidates.
                </p>
            </div>

            <div className="flex-1 overflow-auto flex flex-col">
                <div className="px-4 py-3 bg-charcoal-800/50 border-b border-charcoal-700 text-[11px] text-gray-300">
                    <p className="mb-2"><strong className="text-neon-blue">Visits:</strong> The number of times the Monte Carlo Tree Search algorithm simulated this specific move branching path. Higher visits mean the AI spent more time exploring this option because it looked promising.</p>
                    <p className="mb-3"><strong className="text-neon-blue">Q-Value:</strong> The expected utility or score if this move is chosen. Since this is a fast agent, this is a heuristic score based on piece size (larger pieces score higher) and center proximity, rather than a pure 0.0 to 1.0 win rate. A higher Q-value means the AI evaluates the position more favorably.</p>
                    <details className="cursor-pointer group">
                        <summary className="font-semibold text-gray-200 hover:text-neon-blue transition-colors outline-none select-none">
                            View MCTS Diagram
                        </summary>
                        <div className="mt-2 text-gray-300 cursor-default">
                            <img src="/images/mcts_diagram.png" alt="MCTS Phases Diagram" className="w-full h-auto rounded border border-charcoal-600 shadow-md" />
                        </div>
                    </details>
                </div>

                <MctsTopMovesTable />
            </div>
        </div>
    );
};
