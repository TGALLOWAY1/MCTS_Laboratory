/**
 * Breadth Over Time — shows tree size, root children count, and branching factor.
 */
import React from 'react';
import {
    LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, Legend
} from 'recharts';
import { BreadthTimePoint } from '../../types/mcts';

interface Props {
    data: BreadthTimePoint[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-charcoal-900 border border-charcoal-700 p-2 rounded shadow-xl text-xs">
                <p className="font-bold text-gray-200 mb-1">Iteration {label}</p>
                {payload.map((p: any, i: number) => (
                    <p key={i} style={{ color: p.color }}>
                        {p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
                    </p>
                ))}
            </div>
        );
    }
    return null;
};

export const BreadthOverTimeChart: React.FC<Props> = ({ data }) => {
    if (!data?.length) {
        return <div className="text-xs text-gray-500 p-4 text-center">No breadth data</div>;
    }

    return (
        <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                    <XAxis dataKey="iter" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                    <YAxis yAxisId="left" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                    <YAxis yAxisId="right" tick={{ fill: '#22c55e', fontSize: 10 }} orientation="right" />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Line yAxisId="left" type="monotone" dataKey="treeSize" name="Tree Size" stroke="#eab308" strokeWidth={2} dot={false} />
                    <Line yAxisId="right" type="monotone" dataKey="rootChildren" name="Root Children" stroke="#22c55e" strokeWidth={1.5} dot={false} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};
