import React, { useMemo } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    ReferenceLine,
} from 'recharts';
import { MoveTelemetryDelta } from '../../../types/telemetry';

interface OpponentSuppressionProps {
    allMoves: MoveTelemetryDelta[];
    currentPly: number;
    moverId: string;
}

const PLAYER_COLORS: Record<string, string> = {
    RED: '#ef4444',
    BLUE: '#3b82f6',
    GREEN: '#22c55e',
    YELLOW: '#eab308',
};

// Known metrics to try, in priority order
const CANDIDATE_METRICS: { key: string; label: string }[] = [
    { key: 'mobility', label: 'Mobility' },
    { key: 'frontierSize', label: 'Frontier' },
    { key: 'deadSpace', label: 'Dead Space' },
    { key: 'centerControl', label: 'Center Ctrl' },
    { key: 'effectiveFrontier', label: 'Eff. Frontier' },
    { key: 'remainingArea', label: 'Open Area' },
];

/**
 * Shows each opponent's absolute metric trajectories over the whole game,
 * from the perspective of `moverId` (i.e., shows only the opponents of moverId).
 *
 * Bug fixes vs previous version:
 * 1. Opponents are derived from `after` snapshots where playerId != moverId,
 *    so the selector actually changes what's displayed.
 * 2. Metrics are auto-detected: only metrics that have non-zero variation
 *    across the game are shown, preventing flat lines for missing data.
 */
export const OpponentSuppressionMultiples: React.FC<OpponentSuppressionProps> = ({
    allMoves,
    currentPly,
    moverId,
}) => {
    const { opponents, timeseriesPerOpponent, activeMetrics } = useMemo(() => {
        if (!allMoves?.length) return { opponents: [], timeseriesPerOpponent: {}, activeMetrics: [] };

        // Collect all opponent IDs as players who are not the mover.
        // Use the `after` array from any move to get all 4 players, then exclude moverId.
        const allPlayerIds = new Set<string>();
        for (const m of allMoves) {
            if (!m.after) continue;
            for (const snap of m.after) {
                allPlayerIds.add(snap.playerId);
            }
            if (allPlayerIds.size >= 4) break;         // have all players, stop
        }
        const opponentIds = Array.from(allPlayerIds).filter(id => id !== moverId);

        // Build time series from `after` snapshots at every ply
        const series: Record<string, { ply: number;[k: string]: number }[]> = {};
        opponentIds.forEach(id => { series[id] = []; });

        for (const m of allMoves) {
            if (!m.after) continue;
            for (const oppId of opponentIds) {
                const snap = m.after.find(s => s.playerId === oppId);
                if (!snap?.metrics) continue;
                const point: any = { ply: m.ply };
                CANDIDATE_METRICS.forEach(({ key }) => {
                    point[key] = snap.metrics[key] ?? null;
                });
                series[oppId].push(point);
            }
        }

        // Auto-detect which metrics actually vary (avoid flat lines from missing data)
        const activeMetrics = CANDIDATE_METRICS.filter(({ key }) => {
            // Check across all opponents and all time points
            const vals = opponentIds.flatMap(id =>
                series[id].map(p => p[key]).filter(v => v !== null && v !== undefined)
            );
            if (vals.length < 2) return false;
            const min = Math.min(...vals);
            const max = Math.max(...vals);
            return max - min > 0.01;  // has meaningful variation
        });

        return { opponents: opponentIds, timeseriesPerOpponent: series, activeMetrics };
    }, [allMoves, moverId]);

    if (opponents.length === 0) {
        return (
            <div className="text-gray-500 text-xs text-center py-4">
                No opponent snapshot data available.
            </div>
        );
    }

    if (activeMetrics.length === 0) {
        return (
            <div className="text-gray-500 text-xs text-center py-4">
                Opponent metrics are constant or unavailable for this game.
            </div>
        );
    }

    // Assign fixed colors to active metrics
    const metricPalette = ['#60a5fa', '#34d399', '#f87171', '#a78bfa', '#fbbf24', '#67e8f9'];

    return (
        <div className="flex flex-col gap-4">
            {opponents.map(opp => {
                const playerColor = PLAYER_COLORS[opp] || '#9ca3af';
                const data = timeseriesPerOpponent[opp] || [];

                return (
                    <div key={opp} className="bg-charcoal-900 rounded-lg border border-charcoal-700 p-3">
                        {/* Opponent header */}
                        <div className="flex items-center gap-2 mb-2">
                            <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: playerColor }} />
                            <span className="text-xs font-bold" style={{ color: playerColor }}>{opp}</span>
                            <span className="text-[10px] text-gray-500 ml-auto">{data.length} plies</span>
                        </div>

                        <div style={{ height: 110 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={data} margin={{ top: 2, right: 8, left: -10, bottom: 2 }}>
                                    <CartesianGrid strokeDasharray="2 2" stroke="#374151" />
                                    <XAxis
                                        dataKey="ply"
                                        type="number"
                                        stroke="#6b7280"
                                        fontSize={9}
                                        domain={['dataMin', 'dataMax']}
                                        tickCount={5}
                                    />
                                    <YAxis stroke="#6b7280" fontSize={9} width={28} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', color: '#f3f4f6', fontSize: 11 }}
                                        labelFormatter={(l) => `Ply ${l}`}
                                        formatter={(v: any, name: any) => {
                                            const m = activeMetrics.find(m => m.key === name);
                                            const label = m?.label || name;
                                            const allInt = Number.isInteger(Number(v));
                                            return [allInt ? String(Math.round(v)) : Number(v).toFixed(1), label];
                                        }}
                                    />
                                    {currentPly > 0 && (
                                        <ReferenceLine x={currentPly} stroke="#eab308" strokeDasharray="3 3" />
                                    )}
                                    {activeMetrics.map(({ key }, i) => (
                                        <Line
                                            key={key}
                                            type="monotone"
                                            dataKey={key}
                                            stroke={metricPalette[i % metricPalette.length]}
                                            strokeWidth={1.5}
                                            dot={false}
                                            connectNulls
                                            name={key}
                                        />
                                    ))}
                                </LineChart>
                            </ResponsiveContainer>
                        </div>

                        {/* Mini legend */}
                        <div className="flex flex-wrap gap-3 mt-1">
                            {activeMetrics.map(({ key, label }, i) => (
                                <div key={key} className="flex items-center gap-1">
                                    <span className="w-3 h-0.5 rounded inline-block" style={{ backgroundColor: metricPalette[i % metricPalette.length] }} />
                                    <span className="text-[9px] text-gray-400">{label}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};
