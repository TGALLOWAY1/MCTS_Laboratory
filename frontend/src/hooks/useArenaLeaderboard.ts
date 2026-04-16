import { useEffect, useState } from 'react';
import { API_BASE } from '../constants/gameConstants';

/**
 * Single agent entry from the latest arena run, joined across the TrueSkill
 * leaderboard and the run_config agents list. `params` is the full MCTS
 * agent_config dict that was used in the arena run and can be forwarded
 * verbatim to /api/games.
 */
export interface LeaderboardAgent {
  agent_id: string;
  type: string;              // 'mcts' | 'random' | 'heuristic' | ...
  mu: number;
  sigma: number;
  conservative: number;      // mu - 3*sigma (used for ranking)
  rank: number;              // 1-indexed, rank 1 = best
  games_played: number;
  params: Record<string, any>;
  thinking_time_ms: number;
}

export interface ArenaLeaderboardState {
  isLoading: boolean;
  error: string | null;
  runId: string | null;
  createdAt: string | null;
  agents: LeaderboardAgent[];
}

interface ArenaRunListItem {
  run_id: string;
  created_at?: string;
  notes?: string;
  num_games?: number;
  agent_names?: string[];
  agent_count?: number;
}

/**
 * Fetches the latest arena run and returns a ranked list of its agents.
 *
 * Flow:
 *   1. GET /api/arena-runs -> list sorted newest first (server sorts reverse-lex by id)
 *   2. GET /api/arena-runs/{latest.run_id} -> summary with trueskill_ratings + run_config
 *   3. Join leaderboard entries to run_config.agents by name/agent_id
 *
 * Returns an empty agents list (no error) when no arena runs exist yet.
 */
export const useArenaLeaderboard = (): ArenaLeaderboardState => {
  const [state, setState] = useState<ArenaLeaderboardState>({
    isLoading: true,
    error: null,
    runId: null,
    createdAt: null,
    agents: [],
  });

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const listResp = await fetch(`${API_BASE}/api/arena-runs`);
        if (!listResp.ok) {
          throw new Error(`Failed to list arena runs (${listResp.status})`);
        }
        const listJson = await listResp.json();
        const runs: ArenaRunListItem[] = Array.isArray(listJson?.runs) ? listJson.runs : [];

        if (runs.length === 0) {
          if (!cancelled) {
            setState({
              isLoading: false,
              error: null,
              runId: null,
              createdAt: null,
              agents: [],
            });
          }
          return;
        }

        const latest = runs[0];
        const detailResp = await fetch(`${API_BASE}/api/arena-runs/${latest.run_id}`);
        if (!detailResp.ok) {
          throw new Error(`Failed to load arena run '${latest.run_id}' (${detailResp.status})`);
        }
        const summary = await detailResp.json();

        const leaderboard: any[] = summary?.trueskill_ratings?.leaderboard ?? [];
        const configAgents: any[] = summary?.run_config?.agents ?? [];
        const configByName = new Map<string, any>(
          configAgents.map((a) => [a?.name, a])
        );

        const agents: LeaderboardAgent[] = leaderboard
          .map((entry) => {
            const name = entry?.agent_id;
            const cfg = configByName.get(name);
            if (!cfg) return null;
            return {
              agent_id: name,
              type: String(cfg?.type ?? 'mcts'),
              mu: Number(entry?.mu ?? 0),
              sigma: Number(entry?.sigma ?? 0),
              conservative: Number(entry?.conservative ?? 0),
              rank: Number(entry?.rank ?? 0),
              games_played: Number(entry?.games_played ?? 0),
              params: (cfg?.params ?? {}) as Record<string, any>,
              thinking_time_ms: Number(cfg?.thinking_time_ms ?? cfg?.params?.time_budget_ms ?? 0),
            } as LeaderboardAgent;
          })
          .filter((a): a is LeaderboardAgent => a !== null)
          .sort((a, b) => a.rank - b.rank);

        if (!cancelled) {
          setState({
            isLoading: false,
            error: null,
            runId: summary?.run_id ?? latest.run_id,
            createdAt: latest.created_at ?? null,
            agents,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setState({
            isLoading: false,
            error: err instanceof Error ? err.message : 'Failed to load arena leaderboard',
            runId: null,
            createdAt: null,
            agents: [],
          });
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
};

/**
 * Pick bottom / middle / top MCTS agents for the deploy "Current Best" tab,
 * matching easy / medium / hard slots respectively. Falls back to duplicating
 * the top agent when the leaderboard is too thin.
 *
 * Returns null when the leaderboard contains zero MCTS agents.
 */
export const pickDeployCurrentBestTrio = (
  agents: LeaderboardAgent[],
): { easy: LeaderboardAgent; medium: LeaderboardAgent; hard: LeaderboardAgent } | null => {
  const mcts = agents.filter((a) => a.type === 'mcts');
  if (mcts.length === 0) return null;

  // mcts is already sorted by rank ascending (rank 1 = best).
  const top = mcts[0];                              // hard = best
  const bottom = mcts[mcts.length - 1];             // easy = weakest
  // medium = middle of leaderboard by index
  const middleIdx = Math.floor(mcts.length / 2);
  const middle = mcts[Math.min(middleIdx, mcts.length - 1)];

  // Guarantee 3 distinct slots even with tiny leaderboards.
  return {
    easy: bottom,
    medium: mcts.length >= 3 ? middle : mcts[Math.min(1, mcts.length - 1)],
    hard: top,
  };
};

/**
 * Deploy mode caps MCTS time budgets at 9000ms (see webapi/deploy_validation.py).
 * This helper clamps a stored arena agent config to that cap without mutating
 * the source object, preserving all other MCTS parameters.
 */
export const DEPLOY_TIME_BUDGET_CAP_MS = 9000;

export const clampAgentConfigForDeploy = (
  params: Record<string, any>,
): { config: Record<string, any>; wasClamped: boolean } => {
  const next = { ...params };
  const raw = Number(next.time_budget_ms ?? 0);
  if (raw > DEPLOY_TIME_BUDGET_CAP_MS) {
    next.time_budget_ms = DEPLOY_TIME_BUDGET_CAP_MS;
    return { config: next, wasClamped: true };
  }
  if (!raw || raw < 1) {
    // Fall back to a safe default if the arena run didn't record a budget.
    next.time_budget_ms = 1000;
  }
  return { config: next, wasClamped: false };
};
