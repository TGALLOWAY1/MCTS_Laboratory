import React, { useState, useMemo, useEffect } from 'react';
import { useGameStore } from '../../store/gameStore';
import { DivergingBarChart } from './charts/DivergingBarChart';
import { RadarDeltaChart } from './charts/RadarDeltaChart';
import { CumulativeTimelineChart } from './charts/CumulativeTimelineChart';
import { MoveImpactWaterfall } from './charts/MoveImpactWaterfall';
import { TopMovesLeaderboard } from './charts/TopMovesLeaderboard';
import { WeightPreset, NormalizationMethod } from '../../utils/moveImpactScore';
import { MoveTelemetryDelta } from '../../types/telemetry';
import { OpponentSuppressionMultiples } from './charts/OpponentSuppressionMultiples';
import { StrategyMixPanel } from './StrategyMixPanel';

const PRESETS: { label: string; value: WeightPreset }[] = [
    { label: 'Balanced', value: 'balanced' },
    { label: 'Aggressive Blocking', value: 'blocking' },
    { label: 'Expansion', value: 'expansion' },
    { label: 'Late-game', value: 'late-game' },
];

const MetricDefinitions: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="bg-charcoal-800 rounded-lg border border-charcoal-700 overflow-hidden">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-3 text-left hover:bg-charcoal-700 transition-colors"
            >
                <span className="text-sm font-semibold text-gray-300">
                    ℹ️ How are these metrics calculated?
                </span>
                <span className="text-gray-400 text-xs">
                    {isOpen ? 'Collapse ▲' : 'Expand ▼'}
                </span>
            </button>
            {isOpen && (
                <div className="p-4 pt-0 border-t border-charcoal-700 text-xs text-gray-300 space-y-3 mt-2">
                    <div>
                        <strong className="text-blue-400">Frontier Size:</strong> The number of open corners your pieces currently touch.
                    </div>
                    <div>
                        <strong className="text-purple-400">Effective Frontier Adv:</strong> Similar to Frontier Size, but weighted by the amount of open space nearby and penalized if opponents are threatening the corner. Shows how much stronger your frontier is relative to opponents.
                    </div>
                    <div>
                        <strong className="text-blue-400">Mobility:</strong> An estimation of your total legal moves. Higher mobility means you have more options and are harder to block.
                    </div>
                    <div>
                        <strong className="text-purple-400">Stability (P10) Adv:</strong> Simulates possible opponent moves to find the 10th percentile worst-case scenario. High stability means your mobility cannot be easily crushed next turn.
                    </div>
                    <div>
                        <strong className="text-blue-400">Center Control:</strong> A continuous measure of how close your pieces are to the absolute center of the board. Max score is 9 per piece placed.
                    </div>
                    <div>
                        <strong className="text-blue-400">Dead Space:</strong> Unreachable empty squares on the board adjacent to your pieces.
                    </div>
                    <div>
                        <strong className="text-blue-400">Piece Lock Risk:</strong> The number of pieces remaining in your hand that currently have <em>zero legal placements anywhere on the board</em>.
                    </div>
                    <div>
                        <strong className="text-purple-400">Win Proxy Score:</strong> A composite predictive score combining core expansion, material, and stability advantages into a single "win probability proxy."
                    </div>
                </div>
            )}
        </div>
    );
};

export const MoveDeltaPanel: React.FC = () => {
    const gameState = useGameStore((s) => s.gameState);

    const currentSliderTurn = useGameStore((s) => s.currentSliderTurn);
    const setCurrentSliderTurn = useGameStore((s) => s.setCurrentSliderTurn);

    const [showRaw, setShowRaw] = useState<boolean>(false);
    const [showAdvantage, setShowAdvantage] = useState<boolean>(true);
    const [perOpponent, setPerOpponent] = useState<boolean>(false);
    const [preset, setPreset] = useState<WeightPreset>('balanced');
    const [normalization] = useState<NormalizationMethod>('z-score');
    const [strategyPlayer, setStrategyPlayer] = useState<string>('');
    const [showOverlay, setShowOverlay] = useState<boolean>(false);
    const setBoardOverlay = useGameStore((s) => s.setBoardOverlay);

    if (!gameState) {
        return (
            <div className="h-full flex items-center justify-center p-6 text-center text-gray-500">
                <p>No game active.</p>
            </div>
        );
    }

    const gameHistory = gameState.game_history || [];
    const winner: string = (gameState as any).winner ?? '';

    const movesWithTelemetry = useMemo(() => {
        const withTel = gameHistory
            .map((entry: any, index: number) => ({ ...entry, originalIndex: index }))
            .filter((entry: any) => entry.telemetry);
        // Debug: if history exists but telemetry is always missing, log the first entry
        if (gameHistory.length > 0 && withTel.length === 0) {
            const sample = gameHistory[0] as any;
            console.warn('[MoveDelta] game_history exists but no telemetry found. First entry keys:', Object.keys(sample), 'telemetry value:', sample?.telemetry);
        }
        return withTel;
    }, [gameHistory]);

    // Flat array of just the telemetry objects for scoring computations
    const allTelemetry: MoveTelemetryDelta[] = useMemo(
        () => movesWithTelemetry.map((m: any) => m.telemetry),
        [movesWithTelemetry]
    );

    if (movesWithTelemetry.length === 0) {
        return (
            <div className="h-full flex items-center justify-center p-6 text-center text-gray-500">
                <p>Play some moves to see Move Delta Telemetry.</p>
            </div>
        );
    }

    // Default to the latest move
    const actualPly = currentSliderTurn === null && movesWithTelemetry.length > 0
        ? movesWithTelemetry[movesWithTelemetry.length - 1].telemetry.ply
        : currentSliderTurn || 0;

    const currentIndex = movesWithTelemetry.findIndex((m: any) => m.telemetry.ply === actualPly);
    const safeIndex = currentIndex >= 0 ? currentIndex : movesWithTelemetry.length - 1;
    const selectedMove = movesWithTelemetry[safeIndex];

    const handlePrev = () => {
        if (safeIndex > 0) setCurrentSliderTurn(movesWithTelemetry[safeIndex - 1].telemetry.ply);
    };
    const handleNext = () => {
        if (safeIndex < movesWithTelemetry.length - 1) setCurrentSliderTurn(movesWithTelemetry[safeIndex + 1].telemetry.ply);
    };
    const handleSlider = (e: React.ChangeEvent<HTMLInputElement>) => {
        setCurrentSliderTurn(movesWithTelemetry[parseInt(e.target.value, 10)].telemetry.ply);
    };

    const handleCopySummary = () => {
        if (!selectedMove?.telemetry) return;
        const t = selectedMove.telemetry;
        let summary = `Ply ${t.ply} - ${t.moverId}'s Move\n`;
        if (t.impactScore !== undefined) {
            summary += `Impact Score: ${t.impactScore.toFixed(2)} (${preset} preset)\n`;
        }
        summary += `Self Delta:\n`;
        Object.entries(t.deltaSelf).forEach(([k, v]) => {
            const val = v as number;
            if (val !== 0) summary += `  ${k}: ${val > 0 ? '+' : ''}${val}\n`;
        });

        navigator.clipboard.writeText(summary).then(() => {
            alert('Copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy: ', err);
        });
    };

    // Board overlay: compute cells that changed between before/after board states
    useEffect(() => {
        if (!showOverlay || !selectedMove) {
            setBoardOverlay(null);
            return;
        }
        const moveIdx = selectedMove.originalIndex;
        const current = gameHistory[moveIdx];
        const prev = moveIdx > 0 ? gameHistory[moveIdx - 1] : null;
        const boardAfter: number[][] = current?.board_state;
        const boardBefore: number[][] = prev?.board_state ?? Array(20).fill(0).map(() => Array(20).fill(0));
        if (!boardAfter || !boardBefore) { setBoardOverlay(null); return; }

        const overlay: Record<string, { color: string; opacity: number }> = {};
        const MOVER_COLOR = '#ffffff';
        for (let r = 0; r < boardAfter.length; r++) {
            for (let c = 0; c < (boardAfter[r]?.length ?? 0); c++) {
                const before = boardBefore[r]?.[c] ?? 0;
                const after = boardAfter[r]?.[c] ?? 0;
                if (after !== before && after !== 0) {
                    overlay[`${r}-${c}`] = { color: MOVER_COLOR, opacity: 0.5 };
                }
            }
        }
        setBoardOverlay(Object.keys(overlay).length > 0 ? overlay : null);
        return () => setBoardOverlay(null);
    }, [showOverlay, selectedMove, gameHistory, setBoardOverlay]);

    return (
        <div className="h-full flex flex-col p-4 space-y-4 overflow-y-auto">
            {/* Header + Controls */}
            <div className="flex items-center justify-between border-b border-charcoal-700 pb-3 flex-wrap gap-2">
                <h2 className="text-xl font-bold text-gray-200">Move Impact Delta</h2>
                <div className="flex items-center gap-2 flex-wrap">
                    <select
                        value={preset}
                        onChange={(e) => setPreset(e.target.value as WeightPreset)}
                        className="px-2 py-1 text-xs rounded bg-charcoal-700 text-gray-300 border border-charcoal-600 cursor-pointer"
                    >
                        {PRESETS.map(p => (
                            <option key={p.value} value={p.value}>{p.label}</option>
                        ))}
                    </select>
                    <button
                        onClick={() => setShowRaw(!showRaw)}
                        className={`px-3 py-1 text-xs rounded-full transition-colors ${showRaw ? 'bg-blue-500 text-white font-bold' : 'bg-charcoal-700 text-gray-300 hover:bg-charcoal-600'}`}
                    >
                        {showRaw ? 'Raw' : 'Normalized'}
                    </button>
                    <button
                        onClick={() => setShowAdvantage(!showAdvantage)}
                        className={`px-3 py-1 text-xs rounded-full transition-colors ${showAdvantage ? 'bg-purple-500 text-white font-bold' : 'bg-charcoal-700 text-gray-300 hover:bg-charcoal-600'}`}
                        title="Toggle predictive Advantage Deltas vs. Raw Metric Deltas"
                    >
                        {showAdvantage ? 'Advantage (V2)' : 'Raw Deltas'}
                    </button>
                    {!showAdvantage && (
                        <button
                            onClick={() => setPerOpponent(!perOpponent)}
                            className={`px-3 py-1 text-xs rounded-full transition-colors ${perOpponent ? 'bg-yellow-500 text-charcoal-900 font-bold' : 'bg-charcoal-700 text-gray-300 hover:bg-charcoal-600'}`}
                        >
                            {perOpponent ? 'Per Opponent' : 'Agg. Opp'}
                        </button>
                    )}
                    <button
                        onClick={() => setShowOverlay(!showOverlay)}
                        className={`px-3 py-1 text-xs rounded-full transition-colors ${showOverlay ? 'bg-emerald-500 text-white font-bold' : 'bg-charcoal-700 text-gray-300 hover:bg-charcoal-600'}`}
                        title="Highlight cells changed by this move on the board"
                    >
                        🗺 Overlay
                    </button>
                    <button
                        onClick={handleCopySummary}
                        className="px-3 py-1 text-xs rounded-full transition-colors bg-charcoal-700 text-gray-300 hover:bg-charcoal-600"
                        title="Copy text summary of this move to clipboard"
                    >
                        📋 Copy Summary
                    </button>
                </div>
            </div>

            {/* Move Selector */}
            <div className="bg-charcoal-800 rounded-lg p-3 border border-charcoal-700">
                <div className="flex items-center justify-between mb-3">
                    <button
                        onClick={handlePrev}
                        disabled={safeIndex === 0}
                        className="p-1 px-3 bg-charcoal-700 rounded hover:bg-charcoal-600 disabled:opacity-30 text-gray-200"
                    >
                        &larr; Prev
                    </button>
                    <div className="text-center">
                        <div className="text-sm font-bold text-blue-400">
                            {selectedMove?.player_to_move}'s Move
                        </div>
                        <div className="text-xs text-gray-400">
                            Ply {selectedMove?.telemetry?.ply}
                            {selectedMove?.action ? ` · Piece ${selectedMove.action.piece_id}` : ' · Pass'}
                        </div>
                    </div>
                    <button
                        onClick={handleNext}
                        disabled={safeIndex === movesWithTelemetry.length - 1}
                        className="p-1 px-3 bg-charcoal-700 rounded hover:bg-charcoal-600 disabled:opacity-30 text-gray-200"
                    >
                        Next &rarr;
                    </button>
                </div>
                <input
                    type="range"
                    min="0"
                    max={movesWithTelemetry.length - 1}
                    value={safeIndex}
                    onChange={handleSlider}
                    className="w-full accent-blue-500 cursor-pointer"
                />
            </div>

            {/* Charts */}
            {selectedMove?.telemetry && (
                <div className="space-y-4">
                    <MetricDefinitions />

                    <div className="bg-charcoal-800 rounded-lg border border-charcoal-700 p-3 h-[280px]" title="Shows how this move changed metrics for the mover and opponents">
                        <DivergingBarChart
                            telemetry={selectedMove.telemetry}
                            showRaw={showRaw}
                            perOpponent={perOpponent}
                            isAdvantageMode={showAdvantage}
                            advantageKeys={['winProxy', 'mobilityNextP10Adv', 'effectiveFrontierAdv', 'lockedAreaAdv', 'remainingAreaAdv']}
                        />
                    </div>

                    <div className="bg-charcoal-800 rounded-lg border border-charcoal-700 p-3 h-[280px]" title="Breaks down the Move Impact Score into contributions from individual metrics">
                        <MoveImpactWaterfall
                            telemetry={selectedMove.telemetry}
                            preset={preset}
                            normalization={normalization}
                            allMoves={allTelemetry}
                        />
                    </div>

                    <div className="flex gap-3 h-[280px]">
                        <div className="flex-1 bg-charcoal-800 rounded-lg border border-charcoal-700 p-3" title="Visualizes the shape of your position before vs after the move">
                            <RadarDeltaChart
                                telemetry={selectedMove.telemetry}
                                showOpponents={!perOpponent}
                            />
                        </div>
                        <div className="flex-1 bg-charcoal-800 rounded-lg border border-charcoal-700 p-3" title="Tracks the accumulated impact points over the course of the game">
                            <CumulativeTimelineChart
                                gameHistory={gameHistory}
                                currentPly={selectedMove.telemetry.ply}
                            />
                        </div>
                    </div>

                    <div className="bg-charcoal-800 rounded-lg border border-charcoal-700 p-3" title="Ranks all moves in the game by their Impact Score">
                        <TopMovesLeaderboard
                            allMoves={allTelemetry}
                            preset={preset}
                            normalization={normalization}
                            winnerId={winner}
                            selectedPly={selectedMove.telemetry.ply}
                            onSelectPly={setCurrentSliderTurn}
                        />
                    </div>

                    <div className="bg-charcoal-800 rounded-lg border border-charcoal-700 p-3" title="Shows what metrics contributed most to this player's overall score across the game">
                        {/* Strategy Mix — player selector */}
                        <div className="flex items-center gap-2 mb-3">
                            <span className="text-xs text-gray-400 shrink-0">Strategy for:</span>
                            {Array.from(new Set(allTelemetry.map(m => m.moverId))).map(pid => (
                                <button
                                    key={pid}
                                    onClick={() => setStrategyPlayer(pid)}
                                    className={`px-2 py-0.5 text-xs rounded-full transition-colors ${(strategyPlayer || winner || allTelemetry[0]?.moverId) === pid
                                        ? 'bg-blue-500 text-white font-bold'
                                        : 'bg-charcoal-700 text-gray-300 hover:bg-charcoal-600'
                                        }`}
                                >
                                    {pid}
                                </button>
                            ))}
                        </div>
                        <StrategyMixPanel
                            allMoves={allTelemetry}
                            playerId={strategyPlayer || winner || selectedMove.telemetry.moverId}
                            preset={preset}
                            normalization={normalization}
                            onSelectPly={setCurrentSliderTurn}
                        />
                    </div>

                    <div className="bg-charcoal-800 rounded-lg border border-charcoal-700 p-3" title="Highlights how drastically opponents were suppressed by the selected player's moves">
                        <OpponentSuppressionMultiples
                            allMoves={allTelemetry}
                            currentPly={selectedMove.telemetry.ply}
                            moverId={selectedMove.telemetry.moverId}
                        />
                    </div>
                </div>
            )}
        </div>
    );
};
