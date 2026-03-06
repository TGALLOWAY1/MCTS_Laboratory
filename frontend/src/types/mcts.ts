/**
 * MCTS Diagnostics Contract V1
 * Defines the telemetry payload emitted by the Monte Carlo Tree Search agent per move.
 */

import { MctsTopMove } from '../store/gameStore';

export interface MctsBestMoveTracePoint {
    sim: number;
    bestActionId: string;
    bestQMean: number;
    entropy: number;
}

export interface MctsDiagnosticsV1 {
    version: "v1";
    timeBudgetMs: number;
    timeSpentMs: number;
    simulations: number;
    simsPerSec: number;
    rootLegalMoves: number;
    rootChildrenExpanded: number;
    rootPolicy: MctsTopMove[];    // Borrowing the existing store type
    policyEntropy: number;
    maxDepthReached: number;
    nodesExpanded: number;
    nodesByDepth: { depth: number; nodes: number }[];
    bestMoveTrace: MctsBestMoveTracePoint[];
}

/**
 * Compute the Shannon entropy of the visit distribution.
 */
export function computePolicyEntropy(visits: number[]): number {
    if (!visits || visits.length === 0) return 0;

    const total = visits.reduce((a, b) => a + b, 0);
    if (total <= 0) return 0;

    let entropy = 0;
    for (const v of visits) {
        if (v > 0) {
            const p = v / total;
            entropy -= p * Math.log(p);
        }
    }
    return entropy;
}

/**
 * Normalize visits to probabilities summing to 1.
 */
export function normalizeVisitsToProbabilities(visits: number[]): number[] {
    if (!visits || visits.length === 0) return [];
    const total = visits.reduce((a, b) => a + b, 0);
    if (total <= 0) return visits.map(() => 0);
    return visits.map(v => v / total);
}
