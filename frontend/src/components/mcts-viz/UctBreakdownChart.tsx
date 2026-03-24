/**
 * UCT Breakdown Visualization — shows exploitation, exploration, and RAVE
 * terms for each root child, explaining why the search chose its move.
 */
import React from 'react';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, Legend
} from 'recharts';
import { UctChildBreakdown } from '../../types/mcts';
import { PIECE_NAMES } from '../../constants/gameConstants';

interface Props {
    breakdown: UctChildBreakdown[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        const d = payload[0]?.payload;
        return (
            <div className="bg-charcoal-900 border border-charcoal-700 p-2 rounded shadow-xl text-xs max-w-xs">
                <p className="font-bold text-gray-200 mb-1">{label}</p>
                <p className="text-gray-400 mb-1">Visits: {d?.visits} / Parent: {d?.parentVisits}</p>
                {payload.map((p: any, i: number) => (
                    <p key={i} style={{ color: p.color }}>
                        {p.name}: {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
                    </p>
                ))}
                {d?.raveBeta > 0 && (
                    <div className="mt-1 pt-1 border-t border-charcoal-700">
                        <p className="text-purple-400">RAVE Q: {d.raveQ.toFixed(4)}</p>
                        <p className="text-purple-400">RAVE beta: {d.raveBeta.toFixed(4)}</p>
                    </div>
                )}
                <div className="mt-1 pt-1 border-t border-charcoal-700">
                    <p className="text-gray-300 font-mono text-[10px]">
                        UCT = Q({d?.exploitation.toFixed(3)}) + C*sqrt(ln(N)/n)({d?.exploration.toFixed(3)})
                        {d?.raveBeta > 0 ? ` + RAVE` : ''}
                        = {d?.total.toFixed(3)}
                    </p>
                </div>
            </div>
        );
    }
    return null;
};

export const UctBreakdownChart: React.FC<Props> = ({ breakdown }) => {
    if (!breakdown?.length) {
        return <div className="text-xs text-gray-500 p-4 text-center">No UCT breakdown data</div>;
    }

    const data = breakdown.slice(0, 15).map(b => ({
        ...b,
        label: `${PIECE_NAMES?.[b.pieceId] ?? `P${b.pieceId}`}`,
    }));

    const hasRave = data.some(d => d.raveBeta > 0);

    return (
        <div>
            <div className="text-[10px] text-gray-500 px-1 mb-2">
                UCT = Exploitation (Q/N) + Exploration (C * sqrt(ln(N_parent) / N))
                {hasRave && ' + RAVE blending'}
            </div>
            <div className="h-[220px]">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                        <XAxis
                            dataKey="label"
                            tick={{ fill: '#9ca3af', fontSize: 9 }}
                            interval={0}
                            angle={-30}
                            textAnchor="end"
                            height={50}
                        />
                        <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 10 }} />
                        <Bar dataKey="exploitation" name="Exploitation" stackId="uct" fill="#3b82f6" />
                        <Bar dataKey="exploration" name="Exploration" stackId="uct" fill="#f59e0b" radius={[3, 3, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
