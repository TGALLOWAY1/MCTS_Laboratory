/**
 * Tree Depth Over Time — shows how deep the search goes as iterations accumulate.
 */
import React from 'react';
import {
    LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, Legend
} from 'recharts';
import { DepthTimePoint } from '../../types/mcts';

interface Props {
    data: DepthTimePoint[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-charcoal-900 border border-charcoal-700 p-2 rounded shadow-xl text-xs">
                <p className="font-bold text-gray-200 mb-1">Iteration {label}</p>
                {payload.map((p: any, i: number) => (
                    <p key={i} style={{ color: p.color }}>
                        {p.name}: {p.value}
                    </p>
                ))}
            </div>
        );
    }
    return null;
};

export const DepthOverTimeChart: React.FC<Props> = ({ data }) => {
    if (!data?.length) {
        return <div className="text-xs text-gray-500 p-4 text-center">No depth data</div>;
    }

    return (
        <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                    <XAxis dataKey="iter" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Line type="monotone" dataKey="maxDepth" name="Max Depth" stroke="#ef4444" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="selectedDepth" name="Selected Depth" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
};
