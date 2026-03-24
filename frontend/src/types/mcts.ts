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
    searchTrace?: SearchTraceV1;
}

// --- Search Trace types for MCTS Visualization Platform ---

export interface DepthTimePoint {
    iter: number;
    maxDepth: number;
    avgDepth: number;
    selectedDepth: number;
}

export interface BreadthTimePoint {
    iter: number;
    treeSize: number;
    rootChildren: number;
    avgBranching: number;
}

export interface ExplorationTimePoint {
    iter: number;
    avgExploitation: number;
    avgExploration: number;
    ratio: number;
}

export interface RootChildSnapshotEntry {
    actionId: string;
    pieceId: number;
    orientation: number;
    anchorRow: number;
    anchorCol: number;
    visits: number;
    qValue: number;
    prob: number;
}

export interface RootSnapshotCheckpoint {
    checkpoint: number;
    children: RootChildSnapshotEntry[];
}

export interface UctChildBreakdown {
    actionId: string;
    pieceId: number;
    orientation: number;
    anchorRow: number;
    anchorCol: number;
    visits: number;
    parentVisits: number;
    exploitation: number;
    exploration: number;
    raveQ: number;
    raveBeta: number;
    total: number;
}

export interface SearchTraceV1 {
    depthOverTime: DepthTimePoint[];
    breadthOverTime: BreadthTimePoint[];
    explorationOverTime: ExplorationTimePoint[];
    rolloutResults: number[];
    rootChildrenSnapshots: RootSnapshotCheckpoint[];
    uctBreakdown: UctChildBreakdown[];
    explorationGrid: number[][] | null;
    totalIterations: number;
    sampleRate: number;
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
