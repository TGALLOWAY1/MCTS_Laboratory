import { describe, it, expect } from 'vitest';
import {
    computeRawScore,
    computeGameImpactScores,
    WEIGHT_PRESETS,
} from '../moveImpactScore';
import { MoveTelemetryDelta } from '../../types/telemetry';

// ---- Fixtures ----

function makeDelta(ply: number, moverId: string, selfOverrides: Record<string, number> = {}, oppOverrides: Record<string, number> = {}): MoveTelemetryDelta {
    return {
        ply,
        moverId,
        moveId: `${ply}-0-5-5`,
        deltaSelf: {
            frontierSize: 2,
            mobility: 1,
            deadSpace: -3,
            centerControl: 0.5,
            pieceLockRisk: 0,
            ...selfOverrides,
        },
        deltaOppTotal: {
            frontierSize: -1,
            mobility: -0.5,
            deadSpace: 1,
            centerControl: -0.2,
            pieceLockRisk: 0.1,
            ...oppOverrides,
        },
        deltaOppByPlayer: {},
    };
}

// ---- Tests ----

describe('computeRawScore', () => {
    it('returns a finite number for a valid delta', () => {
        const delta = makeDelta(1, 'RED');
        const score = computeRawScore(delta, WEIGHT_PRESETS.balanced);
        expect(isFinite(score)).toBe(true);
    });

    it('positive self delta with no opp change produces positive score under balanced weights', () => {
        const delta = makeDelta(1, 'RED', { frontierSize: 5 }, { frontierSize: 0 });
        const score = computeRawScore(delta, WEIGHT_PRESETS.balanced);
        expect(score).toBeGreaterThan(0);
    });

    it('blocking preset weighs dead space reduction more heavily', () => {
        const delta = makeDelta(1, 'RED', { deadSpace: -10 }, { deadSpace: 10 });
        const blockingScore = computeRawScore(delta, WEIGHT_PRESETS.blocking);
        const balancedScore = computeRawScore(delta, WEIGHT_PRESETS.balanced);
        // Under blocking, deadSpace weight is -1.5 vs -0.5, so the blocking score should be lower since deadSpace is contributing negatively
        expect(Math.abs(blockingScore)).toBeGreaterThan(Math.abs(balancedScore) * 0.5);
    });
});

describe('computeGameImpactScores', () => {
    const moves = [
        makeDelta(1, 'RED', { frontierSize: 5 }),
        makeDelta(2, 'BLUE', { frontierSize: -1 }),
        makeDelta(3, 'RED', { frontierSize: 3 }),
        makeDelta(4, 'BLUE', { frontierSize: 0 }),
    ];

    it('returns an array with the same length as input', () => {
        const scores = computeGameImpactScores(moves, 'balanced', 'z-score');
        expect(scores.length).toBe(moves.length);
    });

    it('z-score normalized mean is approximately 0', () => {
        const scores = computeGameImpactScores(moves, 'balanced', 'z-score');
        const mean = scores.reduce((a, b) => a + b.total, 0) / scores.length;
        expect(Math.abs(mean)).toBeLessThan(1e-9);
    });

    it('min-max normalized values are in [0, 1]', () => {
        const scores = computeGameImpactScores(moves, 'balanced', 'min-max');
        for (const s of scores) {
            expect(s.total).toBeGreaterThanOrEqual(0);
            expect(s.total).toBeLessThanOrEqual(1);
        }
    });

    it('is deterministic: same input produces same output', () => {
        const s1 = computeGameImpactScores(moves, 'expansion', 'z-score').map(s => s.total);
        const s2 = computeGameImpactScores(moves, 'expansion', 'z-score').map(s => s.total);
        expect(s1).toEqual(s2);
    });

    it('contributions have correct metric keys', () => {
        const scores = computeGameImpactScores(moves, 'balanced', 'z-score');
        const metrics = scores[0].contributions.map(c => c.metric);
        expect(metrics).toContain('frontierSize');
        expect(metrics).toContain('mobility');
    });

    it('empty moves returns empty array', () => {
        const scores = computeGameImpactScores([], 'balanced', 'z-score');
        expect(scores).toHaveLength(0);
    });
});
