/**
 * Root Move Probability Chart — shows visit distribution and Q-values
 * for root children at a selected iteration checkpoint.
 */
import React, { useMemo, useState } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
    CartesianGrid, Legend, Cell
} from 'recharts';
import { RootSnapshotCheckpoint } from '../../types/mcts';
import { PIECE_NAMES } from '../../constants/gameConstants';

interface Props {
    snapshots: RootSnapshotCheckpoint[];
    selectedCheckpoint?: number; // index into snapshots
}

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

export const RootPolicyChart: React.FC<Props> = ({ snapshots, selectedCheckpoint }) => {
    const [showProb, setShowProb] = useState(false);
    const [cpIdx, setCpIdx] = useState<number>(selectedCheckpoint ?? (snapshots.length - 1));

    const snapshot = snapshots[Math.min(cpIdx, snapshots.length - 1)];
    if (!snapshot?.children?.length) {
        return <div className="text-xs text-gray-500 p-4 text-center">No root policy data</div>;
    }

    const data = useMemo(() =>
        snapshot.children.slice(0, 15).map(c => ({
            label: `${PIECE_NAMES?.[c.pieceId] ?? `P${c.pieceId}`}`,
            fullLabel: `${PIECE_NAMES?.[c.pieceId] ?? `P${c.pieceId}`} @(${c.anchorRow},${c.anchorCol})`,
            visits: c.visits,
            prob: c.prob,
            qValue: c.qValue,
        })),
    [snapshot]);

    return (
        <div>
            <div className="flex items-center justify-between mb-2 px-1">
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowProb(!showProb)}
                        className={`text-[10px] px-2 py-0.5 rounded ${showProb ? 'bg-neon-blue/20 text-neon-blue' : 'bg-charcoal-700 text-gray-400'}`}
                    >
                        {showProb ? 'Probabilities' : 'Visits'}
                    </button>
                </div>
                {snapshots.length > 1 && (
                    <div className="flex items-center gap-1">
                        <span className="text-[10px] text-gray-500">Checkpoint:</span>
                        <select
                            value={cpIdx}
                            onChange={e => setCpIdx(Number(e.target.value))}
                            className="text-[10px] bg-charcoal-700 text-gray-300 rounded px-1 py-0.5 border border-charcoal-600"
                        >
                            {snapshots.map((s, i) => (
                                <option key={i} value={i}>iter {s.checkpoint}</option>
                            ))}
                        </select>
                    </div>
                )}
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
                        <YAxis yAxisId="left" tick={{ fill: '#64748b', fontSize: 10 }} />
                        <YAxis yAxisId="right" tick={{ fill: '#3b82f6', fontSize: 10 }} orientation="right" domain={[0, 1]} />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 10 }} />
                        <Bar
                            yAxisId="left"
                            dataKey={showProb ? "prob" : "visits"}
                            name={showProb ? "Probability" : "Visits"}
                            fill="#64748b"
                            radius={[3, 3, 0, 0]}
                        >
                            {data.map((_, i) => (
                                <Cell key={i} fill={i === 0 ? '#22c55e' : '#64748b'} />
                            ))}
                        </Bar>
                        <Bar
                            yAxisId="right"
                            dataKey="qValue"
                            name="Q-Value"
                            fill="#3b82f6"
                            radius={[3, 3, 0, 0]}
                            barSize={8}
                        />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
