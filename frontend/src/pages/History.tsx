import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE } from '../constants/gameConstants';

function getActiveLayers(cfg: Record<string, any>): string[] {
  const layers: string[] = [];
  if (cfg.progressive_widening_enabled || cfg.progressive_history_enabled) layers.push('L3');
  if ((cfg.rollout_policy && cfg.rollout_policy !== 'random') || cfg.rollout_cutoff_depth != null) layers.push('L4');
  if (cfg.rave_enabled || cfg.nst_enabled) layers.push('L5');
  if (cfg.state_eval_phase_weights) layers.push('L6');
  if (cfg.opponent_modeling_enabled) layers.push('L7');
  if (cfg.num_workers && cfg.num_workers > 1) layers.push('L8');
  if (cfg.adaptive_exploration_enabled || cfg.sufficiency_threshold_enabled) layers.push('L9');
  return [...new Set(layers)];
}

function AgentBadge({ agentType, agentConfig }: { agentType: string; agentConfig: Record<string, any> }) {
  if (agentType === 'human') return <span className="text-gray-400">Human</span>;
  if (agentType === 'random') return <span className="text-gray-500">Random</span>;
  if (agentType === 'heuristic') return <span className="text-neon-yellow">Heuristic</span>;

  const layers = getActiveLayers(agentConfig || {});
  const budget = agentConfig?.time_budget_ms;

  return (
    <span className="inline-flex items-center gap-1">
      <span className="text-neon-blue">MCTS</span>
      {budget && <span className="text-gray-500 text-[10px]">{budget}ms</span>}
      {layers.map(l => (
        <span key={l} className="text-[9px] font-bold px-1 py-0 rounded bg-neon-blue/10 text-neon-blue border border-neon-blue/20">
          {l}
        </span>
      ))}
    </span>
  );
}

export const History: React.FC = () => {
  const [games, setGames] = useState<any[]>([]);

  useEffect(() => {
    const load = async () => {
      const resp = await fetch(`${API_BASE}/api/history?limit=50`);
      if (!resp.ok) return;
      const data = await resp.json();
      setGames(data.games || []);
    };
    load();
  }, []);

  return (
    <div className="min-h-screen bg-charcoal-900 text-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Game History</h1>
        <Link to="/play" className="text-neon-blue">Back to Play</Link>
      </div>
      <div className="bg-charcoal-800 border border-charcoal-700 rounded p-4">
        {games.length === 0 ? (
          <div className="text-gray-400">No finished games yet.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-charcoal-700">
                <th className="py-2">Game</th>
                <th>Winner</th>
                <th>Players</th>
                <th>Moves</th>
                <th>Duration</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {games.map((g) => (
                <tr key={g.game_id} className="border-b border-charcoal-700/40">
                  <td className="py-2 font-mono text-xs">{g.game_id.slice(0, 8)}</td>
                  <td>{g.winner || 'NONE'}</td>
                  <td className="py-2">
                    {g.players ? (
                      <div className="flex flex-wrap gap-1">
                        {g.players.map((p: any, i: number) => (
                          <span key={i} className="text-xs">
                            <AgentBadge agentType={p.agent_type} agentConfig={p.agent_config || {}} />
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-500 text-xs">-</span>
                    )}
                  </td>
                  <td>{g.move_count}</td>
                  <td>{g.gameDurationMs ? `${(g.gameDurationMs / 1000).toFixed(1)}s` : '-'}</td>
                  <td>
                    <Link className="text-neon-blue" to={`/analysis/${g.game_id}`}>Analyze</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
