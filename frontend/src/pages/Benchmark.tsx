import React from 'react';
import { useNavigate } from 'react-router-dom';

export const Benchmark: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen bg-charcoal-900 text-gray-200 p-8">
            <div className="max-w-4xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                            <svg className="w-8 h-8 text-neon-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                            AI Comparison Scoreboard
                        </h1>
                        <p className="text-gray-400 mt-2">Historical benchmark results between agent configurations.</p>
                    </div>
                    <button
                        onClick={() => navigate('/')}
                        className="px-4 py-2 bg-charcoal-800 border border-charcoal-700 hover:bg-charcoal-700 rounded transition-colors"
                    >
                        ← Back to Game
                    </button>
                </div>

                {/* High Level Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                    <div className="bg-charcoal-800 border border-charcoal-700 p-6 rounded-lg shadow-lg">
                        <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-2">Strongest Agent</h3>
                        <div className="text-2xl font-bold text-neon-blue">MCTS (800ms)</div>
                        <div className="text-sm text-green-400 mt-1">↑ 24% Edge over 400ms</div>
                    </div>
                    <div className="bg-charcoal-800 border border-charcoal-700 p-6 rounded-lg shadow-lg">
                        <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-2">Avg Match Length</h3>
                        <div className="text-2xl font-bold text-white">82 Moves</div>
                        <div className="text-sm text-gray-500 mt-1">Highly contested boards</div>
                    </div>
                    <div className="bg-charcoal-800 border border-charcoal-700 p-6 rounded-lg shadow-lg">
                        <h3 className="text-gray-400 text-sm font-semibold uppercase tracking-wider mb-2">Search Efficiency</h3>
                        <div className="text-2xl font-bold text-neon-yellow">~45k nodes/sec</div>
                        <div className="text-sm text-gray-500 mt-1">C++ optimized rollouts</div>
                    </div>
                </div>

                {/* Win Rates Table */}
                <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg shadow-lg overflow-hidden mb-8">
                    <div className="p-6 border-b border-charcoal-700">
                        <h2 className="text-xl font-bold text-white">Win Rate Pairwise Matrix (N=200 games)</h2>
                    </div>
                    <div className="overflow-x-auto p-4">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="text-gray-500 text-sm border-b border-charcoal-700">
                                    <th className="py-3 px-4">Agent</th>
                                    <th className="py-3 px-4">vs Random</th>
                                    <th className="py-3 px-4">vs Heuristic</th>
                                    <th className="py-3 px-4">vs MCTS (50ms)</th>
                                    <th className="py-3 px-4">vs MCTS (200ms)</th>
                                    <th className="py-3 px-4">vs MCTS (400ms)</th>
                                </tr>
                            </thead>
                            <tbody className="text-sm">
                                <tr className="border-b border-charcoal-700/50 hover:bg-charcoal-700/30">
                                    <td className="py-3 px-4 font-semibold text-gray-300">Random</td>
                                    <td className="py-3 px-4 text-gray-600">—</td>
                                    <td className="py-3 px-4 text-red-400">0%</td>
                                    <td className="py-3 px-4 text-red-400">0%</td>
                                    <td className="py-3 px-4 text-red-400">0%</td>
                                    <td className="py-3 px-4 text-red-400">0%</td>
                                </tr>
                                <tr className="border-b border-charcoal-700/50 hover:bg-charcoal-700/30">
                                    <td className="py-3 px-4 font-semibold text-gray-300">Heuristic</td>
                                    <td className="py-3 px-4 text-green-400">100%</td>
                                    <td className="py-3 px-4 text-gray-600">—</td>
                                    <td className="py-3 px-4 text-red-400">15%</td>
                                    <td className="py-3 px-4 text-red-400">2%</td>
                                    <td className="py-3 px-4 text-red-400">0%</td>
                                </tr>
                                <tr className="border-b border-charcoal-700/50 hover:bg-charcoal-700/30">
                                    <td className="py-3 px-4 font-semibold text-neon-blue">MCTS (50ms)</td>
                                    <td className="py-3 px-4 text-green-400">100%</td>
                                    <td className="py-3 px-4 text-green-400">85%</td>
                                    <td className="py-3 px-4 text-gray-600">—</td>
                                    <td className="py-3 px-4 text-red-400">24%</td>
                                    <td className="py-3 px-4 text-red-400">12%</td>
                                </tr>
                                <tr className="border-b border-charcoal-700/50 hover:bg-charcoal-700/30">
                                    <td className="py-3 px-4 font-semibold text-neon-blue">MCTS (200ms)</td>
                                    <td className="py-3 px-4 text-green-400">100%</td>
                                    <td className="py-3 px-4 text-green-400">98%</td>
                                    <td className="py-3 px-4 text-green-400">76%</td>
                                    <td className="py-3 px-4 text-gray-600">—</td>
                                    <td className="py-3 px-4 text-red-400">35%</td>
                                </tr>
                                <tr className="hover:bg-charcoal-700/30">
                                    <td className="py-3 px-4 font-semibold text-neon-blue">MCTS (400ms)</td>
                                    <td className="py-3 px-4 text-green-400">100%</td>
                                    <td className="py-3 px-4 text-green-400">100%</td>
                                    <td className="py-3 px-4 text-green-400">88%</td>
                                    <td className="py-3 px-4 text-green-400">65%</td>
                                    <td className="py-3 px-4 text-gray-600">—</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* Elo Rating Board */}
                <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg shadow-lg overflow-hidden">
                    <div className="p-6 border-b border-charcoal-700 flex justify-between items-center">
                        <h2 className="text-xl font-bold text-white">Estimated Elo Ratings</h2>
                        <span className="text-xs text-gray-500 bg-charcoal-900 px-2 py-1 rounded">Baseline: Random = 1000</span>
                    </div>
                    <div className="p-4">
                        <div className="space-y-4 max-w-2xl mx-auto">
                            {/* Bars */}
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="font-semibold text-gray-300">MCTS (800ms)</span>
                                    <span className="text-neon-blue font-mono">~2450</span>
                                </div>
                                <div className="w-full bg-charcoal-900 rounded-full h-2.5">
                                    <div className="bg-neon-blue h-2.5 rounded-full" style={{ width: '95%' }}></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="font-semibold text-gray-300">MCTS (400ms)</span>
                                    <span className="text-neon-blue font-mono">2210</span>
                                </div>
                                <div className="w-full bg-charcoal-900 rounded-full h-2.5">
                                    <div className="bg-neon-blue h-2.5 rounded-full" style={{ width: '85%' }}></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="font-semibold text-gray-300">MCTS (200ms)</span>
                                    <span className="text-neon-blue font-mono">1980</span>
                                </div>
                                <div className="w-full bg-charcoal-900 rounded-full h-2.5">
                                    <div className="bg-neon-blue h-2.5 rounded-full" style={{ width: '75%' }}></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="font-semibold text-gray-300">MCTS (50ms)</span>
                                    <span className="text-neon-blue font-mono">1650</span>
                                </div>
                                <div className="w-full bg-charcoal-900 rounded-full h-2.5">
                                    <div className="bg-neon-blue/70 h-2.5 rounded-full" style={{ width: '55%' }}></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="font-semibold text-gray-300">Heuristic</span>
                                    <span className="text-neon-yellow font-mono">1300</span>
                                </div>
                                <div className="w-full bg-charcoal-900 rounded-full h-2.5">
                                    <div className="bg-neon-yellow h-2.5 rounded-full" style={{ width: '35%' }}></div>
                                </div>
                            </div>
                            <div>
                                <div className="flex justify-between text-sm mb-1">
                                    <span className="font-semibold text-gray-300">Random</span>
                                    <span className="text-gray-500 font-mono">1000</span>
                                </div>
                                <div className="w-full bg-charcoal-900 rounded-full h-2.5">
                                    <div className="bg-gray-600 h-2.5 rounded-full" style={{ width: '15%' }}></div>
                                </div>
                            </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-6 text-center">
                            Note: Ratings are estimated locally based on N=200 tournament matches between each pair using Bradley-Terry model semantics.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};
