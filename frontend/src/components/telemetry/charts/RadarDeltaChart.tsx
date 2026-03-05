import React, { useMemo } from 'react';
import {
    Radar,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    ResponsiveContainer,
    Tooltip,
} from 'recharts';
import { MoveTelemetryDelta } from '../../../types/telemetry';

interface RadarDeltaChartProps {
    telemetry: MoveTelemetryDelta;
    showOpponents?: boolean;
}

const EXPANSION_METRICS: { key: string; label: string }[] = [
    { key: 'frontierSize', label: 'Frontier' },
    { key: 'mobility', label: 'Mobility' },
    { key: 'centerControl', label: 'Center' },
    { key: 'remainingArea', label: 'Open Area' },
    { key: 'effectiveFrontier', label: 'Eff. Frontier' },
];

const RISK_METRICS: { key: string; label: string }[] = [
    { key: 'deadSpace', label: 'Dead Space' },
    { key: 'pieceLockRisk', label: 'Lock Risk' },
    { key: 'mobilityDropRisk', label: 'Mob. Drop' },
    { key: 'bottleneckScore', label: 'Bottleneck' },
    { key: 'lockedArea', label: 'Locked Area' },
];

const PLAYER_COLORS: Record<string, string> = {
    RED: '#ef4444',
    BLUE: '#3b82f6',
    GREEN: '#22c55e',
    YELLOW: '#eab308',
};

/**
 * Normalise each metric independently to [0, 1] across all 4 data series
 * (Before/After for mover + optional Before/After for aggregate opponent).
 * Raw values are stored alongside so the tooltip can display them.
 */
function buildNormalisedRadarData(
    metrics: { key: string; label: string }[],
    moverBefore: any,
    moverAfter: any,
    telemetry: MoveTelemetryDelta,
    showOpponents: boolean,
) {
    return metrics.map(({ key, label }) => {
        const raw: Record<string, number> = {
            Before: moverBefore?.metrics?.[key] ?? 0,
            After: moverAfter?.metrics?.[key] ?? 0,
        };

        if (showOpponents) {
            let oppBefore = 0;
            let oppAfter = 0;
            telemetry.before?.forEach((p: any) => { if (p.playerId !== telemetry.moverId) oppBefore += p.metrics?.[key] ?? 0; });
            telemetry.after?.forEach((p: any) => { if (p.playerId !== telemetry.moverId) oppAfter += p.metrics?.[key] ?? 0; });
            raw.OppBefore = oppBefore;
            raw.OppAfter = oppAfter;
        }

        // Per-metric normalisation to [0, 1]
        const vals = Object.values(raw);
        const min = Math.min(...vals);
        const max = Math.max(...vals);
        const range = max - min;

        const norm = (v: number) => range > 0 ? (v - min) / range : 0.5;

        const entry: any = { metric: label };
        // Normalised values used for rendering
        Object.keys(raw).forEach(k => { entry[k] = norm(raw[k]); });
        // Raw values stored for tooltip
        Object.keys(raw).forEach(k => { entry[`raw_${k}`] = raw[k]; });
        return entry;
    });
}

/** Custom tooltip that shows raw (un-normalised) values */
const RadarTooltip: React.FC<any> = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const pt = payload[0]?.payload ?? {};
    const label = pt.metric ?? '';
    const keys = ['Before', 'After', 'OppBefore', 'OppAfter'].filter(k => `raw_${k}` in pt);
    const fmtRaw = (v: number) => Number.isInteger(v) ? String(v) : v.toFixed(2);

    return (
        <div style={{ background: '#111827', border: '1px solid #374151', padding: '6px 10px', borderRadius: 6, fontSize: 11, color: '#f3f4f6' }}>
            <div style={{ fontWeight: 700, marginBottom: 2 }}>{label}</div>
            {keys.map(k => (
                <div key={k} style={{ color: '#e5e7eb' }}>
                    {k.replace('Before', ' Before').replace('After', ' After').trim()}: {fmtRaw(pt[`raw_${k}`])}
                </div>
            ))}
        </div>
    );
};

const MiniRadar: React.FC<{
    title: string;
    data: any[];
    moverColor: string;
    moverId: string;
    showOpponents: boolean;
}> = ({ title, data, moverColor, moverId, showOpponents }) => (
    <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest text-center mb-1 shrink-0">
            {title}
        </p>
        <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="65%" data={data}>
                    <PolarGrid stroke="#374151" />
                    <PolarAngleAxis
                        dataKey="metric"
                        tick={{ fill: '#9ca3af', fontSize: 9 }}
                    />
                    {/* Radius axis hidden — values are per-metric normalised */}
                    <PolarRadiusAxis
                        angle={30}
                        domain={[0, 1]}
                        tick={false}
                        axisLine={false}
                    />
                    <Tooltip content={<RadarTooltip />} />
                    {showOpponents && (
                        <>
                            <Radar name="OppBefore" dataKey="OppBefore" stroke="#6b7280" fill="#6b7280" fillOpacity={0.08} strokeDasharray="3 3" dot={false} />
                            <Radar name="OppAfter" dataKey="OppAfter" stroke="#9ca3af" fill="#9ca3af" fillOpacity={0.2} dot={false} />
                        </>
                    )}
                    <Radar name="Before" dataKey="Before" stroke={moverColor} fill={moverColor} fillOpacity={0.08} strokeDasharray="4 2" dot={false} />
                    <Radar name="After" dataKey="After" stroke={moverColor} fill={moverColor} fillOpacity={0.45} dot={false} />
                </RadarChart>
            </ResponsiveContainer>
        </div>
    </div>
);

export const RadarDeltaChart: React.FC<RadarDeltaChartProps> = ({ telemetry, showOpponents = false }) => {
    const { expansionData, riskData, moverColor } = useMemo(() => {
        if (!telemetry?.before || !telemetry?.after) {
            return { expansionData: [], riskData: [], moverColor: '#8884d8' };
        }
        const moverBefore = telemetry.before.find((p: any) => p.playerId === telemetry.moverId);
        const moverAfter = telemetry.after.find((p: any) => p.playerId === telemetry.moverId);
        return {
            expansionData: buildNormalisedRadarData(EXPANSION_METRICS, moverBefore, moverAfter, telemetry, showOpponents),
            riskData: buildNormalisedRadarData(RISK_METRICS, moverBefore, moverAfter, telemetry, showOpponents),
            moverColor: PLAYER_COLORS[telemetry.moverId] || '#8884d8',
        };
    }, [telemetry, showOpponents]);

    if (!expansionData.length) return null;

    return (
        <div className="w-full h-full flex flex-col min-h-0">
            <h3 className="text-sm font-semibold text-gray-300 mb-1 shrink-0">
                Move Shape <span className="text-[10px] text-gray-500 font-normal">(each axis normalised independently)</span>
            </h3>

            <div className="flex-1 flex gap-2 min-h-0">
                <MiniRadar title="Expansion" data={expansionData} moverColor={moverColor} moverId={telemetry.moverId} showOpponents={showOpponents} />
                <div className="w-px bg-charcoal-700 shrink-0" />
                <MiniRadar title="Risk" data={riskData} moverColor={moverColor} moverId={telemetry.moverId} showOpponents={showOpponents} />
            </div>

            {/* Shared legend */}
            <div className="shrink-0 flex items-center justify-center gap-4 pt-1 flex-wrap">
                <span className="flex items-center gap-1 text-[10px] text-gray-400">
                    <span className="inline-block w-5 h-0.5 rounded" style={{ borderTop: `1.5px dashed ${moverColor}` }} />
                    {telemetry.moverId} Before
                </span>
                <span className="flex items-center gap-1 text-[10px] text-gray-400">
                    <span className="inline-block w-5 h-1.5 rounded" style={{ backgroundColor: moverColor, opacity: 0.7 }} />
                    {telemetry.moverId} After
                </span>
                {showOpponents && (
                    <>
                        <span className="flex items-center gap-1 text-[10px] text-gray-400">
                            <span className="inline-block w-5 h-0.5 border-t border-dashed border-gray-500" />
                            Opp Before
                        </span>
                        <span className="flex items-center gap-1 text-[10px] text-gray-400">
                            <span className="inline-block w-5 h-1.5 rounded bg-gray-400 opacity-60" />
                            Opp After
                        </span>
                    </>
                )}
            </div>
        </div>
    );
};
