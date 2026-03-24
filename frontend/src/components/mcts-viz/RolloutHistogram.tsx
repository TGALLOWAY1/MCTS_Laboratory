/**
 * Rollout Result Histogram — shows the distribution of rollout outcomes.
 */
import React, { useMemo } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, ReferenceLine
} from 'recharts';

interface Props {
    results: number[];
    bins?: number;
}

export const RolloutHistogram: React.FC<Props> = ({ results, bins = 20 }) => {
    const { histogram, stats } = useMemo(() => {
        if (!results?.length) return { histogram: [], stats: null };

        const sorted = [...results].sort((a, b) => a - b);
        const min = sorted[0];
        const max = sorted[sorted.length - 1];
        const mean = results.reduce((a, b) => a + b, 0) / results.length;
        const variance = results.reduce((a, b) => a + (b - mean) ** 2, 0) / results.length;
        const std = Math.sqrt(variance);
        const median = sorted[Math.floor(sorted.length / 2)];

        const range = max - min || 1;
        const binWidth = range / bins;
        const counts = new Array(bins).fill(0);

        for (const v of results) {
            const idx = Math.min(Math.floor((v - min) / binWidth), bins - 1);
            counts[idx]++;
        }

        const histogram = counts.map((count, i) => ({
            bin: `${(min + i * binWidth).toFixed(1)}`,
            binCenter: min + (i + 0.5) * binWidth,
            count,
        }));

        return {
            histogram,
            stats: { mean, median, std, min, max, n: results.length },
        };
    }, [results, bins]);

    if (!histogram.length || !stats) {
        return <div className="text-xs text-gray-500 p-4 text-center">No rollout data</div>;
    }

    return (
        <div>
            <div className="flex gap-3 mb-2 text-[10px] text-gray-400 px-1">
                <span>n={stats.n}</span>
                <span>mean={stats.mean.toFixed(2)}</span>
                <span>median={stats.median.toFixed(2)}</span>
                <span>std={stats.std.toFixed(2)}</span>
                <span>range=[{stats.min.toFixed(1)}, {stats.max.toFixed(1)}]</span>
            </div>
            <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={histogram} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                        <XAxis
                            dataKey="bin"
                            tick={{ fill: '#9ca3af', fontSize: 9 }}
                            interval={Math.max(0, Math.floor(bins / 8) - 1)}
                        />
                        <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                        <Tooltip
                            content={({ active, payload }) => {
                                if (active && payload && payload.length) {
                                    const d = payload[0].payload;
                                    return (
                                        <div className="bg-charcoal-900 border border-charcoal-700 p-2 rounded shadow-xl text-xs">
                                            <p className="text-gray-200">Value: ~{d.binCenter.toFixed(2)}</p>
                                            <p className="text-neon-blue">Count: {d.count}</p>
                                        </div>
                                    );
                                }
                                return null;
                            }}
                        />
                        <ReferenceLine
                            x={histogram.reduce((best, h) =>
                                Math.abs(h.binCenter - stats.mean) < Math.abs(best.binCenter - stats.mean) ? h : best
                            ).bin}
                            stroke="#ef4444"
                            strokeDasharray="3 3"
                            label={{ value: 'mean', fill: '#ef4444', fontSize: 9, position: 'top' }}
                        />
                        <Bar dataKey="count" name="Frequency" fill="#6366f1" radius={[2, 2, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
