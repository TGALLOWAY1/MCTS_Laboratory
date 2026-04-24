import React, { useState } from 'react';
import { useGameStore } from '../store/gameStore';
import {
  API_BASE,
  CHALLENGE_CHAMPION_BUDGET_MS,
  CHALLENGE_CHAMPION_PROFILE,
  DEPLOY_MCTS_PRESETS,
  IS_DEPLOY_PROFILE,
} from '../constants/gameConstants';

interface GameConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGameCreated: () => void;
  /** When false (e.g. initial view), hide close button - user must start a game */
  canClose?: boolean;
}

export const GameConfigModal: React.FC<GameConfigModalProps> = ({
  isOpen,
  onClose,
  onGameCreated,
  canClose = true
}) => {
  const deployConfig = {
    players: [
      { player: 'RED', agent_type: 'human', agent_config: {} },
      { player: 'BLUE', agent_type: 'mcts', agent_config: { difficulty: 'easy', time_budget_ms: DEPLOY_MCTS_PRESETS.easy } },
      { player: 'GREEN', agent_type: 'mcts', agent_config: { difficulty: 'medium', time_budget_ms: DEPLOY_MCTS_PRESETS.medium } },
      { player: 'YELLOW', agent_type: 'mcts', agent_config: { difficulty: 'hard', time_budget_ms: DEPLOY_MCTS_PRESETS.hard } }
    ],
    auto_start: true
  };

  const challengeChampionConfig = {
    players: [
      { player: 'RED', agent_type: 'human', agent_config: {} },
      { player: 'BLUE', agent_type: 'mcts', agent_config: { profile: CHALLENGE_CHAMPION_PROFILE, time_budget_ms: CHALLENGE_CHAMPION_BUDGET_MS } },
      { player: 'GREEN', agent_type: 'mcts', agent_config: { profile: CHALLENGE_CHAMPION_PROFILE, time_budget_ms: CHALLENGE_CHAMPION_BUDGET_MS } },
      { player: 'YELLOW', agent_type: 'mcts', agent_config: { profile: CHALLENGE_CHAMPION_PROFILE, time_budget_ms: CHALLENGE_CHAMPION_BUDGET_MS } }
    ],
    auto_start: true
  };

  const researchDefaultConfig = {
    players: [
      { player: 'RED', agent_type: 'human', agent_config: {} },
      { player: 'BLUE', agent_type: 'mcts', agent_config: { difficulty: 'easy', time_budget_ms: DEPLOY_MCTS_PRESETS.easy } },
      { player: 'GREEN', agent_type: 'mcts', agent_config: { difficulty: 'medium', time_budget_ms: DEPLOY_MCTS_PRESETS.medium } },
      { player: 'YELLOW', agent_type: 'mcts', agent_config: { difficulty: 'hard', time_budget_ms: DEPLOY_MCTS_PRESETS.hard } }
    ],
    auto_start: true
  };

  const { createGame, connect, loadGame } = useGameStore();
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [maxTime, setMaxTime] = useState<number>(DEPLOY_MCTS_PRESETS.hard);

  const [gameConfig, setGameConfig] = useState<any>(IS_DEPLOY_PROFILE ? deployConfig : researchDefaultConfig);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleCreateGame = async () => {
    console.log('🎮 Starting game creation...');
    setIsCreating(true);
    setError(null);

    try {
      console.log('📋 Creating game with config:', gameConfig);
      const gameId = await createGame(gameConfig);
      console.log('🎯 Game created with ID:', gameId);

      console.log('Connecting to WebSocket...');
      await connect(gameId);
      console.log('WebSocket connected');

      // Check store state
      const storeState = useGameStore.getState();
      console.log('Store state after connection:', {
        gameState: storeState.gameState,
        connectionStatus: storeState.connectionStatus,
        error: storeState.error
      });

      // If no game state, try to fetch it via REST API as fallback
      if (!storeState.gameState) {
        console.log('No game state from WebSocket, fetching via REST API...');
        try {
          const response = await fetch(`${API_BASE}/api/games/${gameId}`);
          if (response.ok) {
            const gameState = await response.json();
            console.log('Game state from REST API:', gameState);
            useGameStore.getState().setGameState(gameState);
          }
        } catch (err) {
          console.error('Failed to fetch game state via REST API:', err);
        }
      }

      onGameCreated();
      onClose();
    } catch (err) {
      console.error('Error creating game:', err);
      setError(err instanceof Error ? err.message : 'Failed to create game');
    } finally {
      setIsCreating(false);
    }
  };

  const updatePlayer = (index: number, field: string, value: string) => {
    if (IS_DEPLOY_PROFILE) {
      return;
    }
    setGameConfig((prev: any) => ({
      ...prev,
      players: prev.players.map((player: any, i: number) =>
        i === index ? { ...player, [field]: value } : player
      )
    }));
  };

  const addPlayer = () => {
    if (IS_DEPLOY_PROFILE) {
      return;
    }
    if (gameConfig.players.length < 4) {
      const playerColors = ['RED', 'BLUE', 'GREEN', 'YELLOW'];
      const nextColor = playerColors[gameConfig.players.length];
      setGameConfig((prev: any) => ({
        ...prev,
        players: [...prev.players, { player: nextColor, agent_type: 'random', agent_config: {} }]
      }));
    }
  };

  const removePlayer = (index: number) => {
    if (IS_DEPLOY_PROFILE) {
      return;
    }
    if (gameConfig.players.length > 2) {
      setGameConfig((prev: any) => ({
        ...prev,
        players: prev.players.filter((_: any, i: number) => i !== index)
      }));
    }
  };

  const [expandedAdvanced, setExpandedAdvanced] = useState<number | null>(null);

  const MCTS_LAYER_PRESETS: Record<string, { label: string; description: string; config: Record<string, any> }> = {
    'baseline': {
      label: 'Baseline',
      description: 'Vanilla MCTS (no layers)',
      config: { time_budget_ms: 1000 },
    },
    'layer3': {
      label: 'L3: Action Reduction',
      description: 'Progressive widening + history',
      config: { time_budget_ms: 1000, progressive_widening_enabled: true, pw_c: 2.0, pw_alpha: 0.5, progressive_history_enabled: true },
    },
    'layer4': {
      label: 'L4: Simulation',
      description: 'Heuristic rollouts + cutoff',
      config: { time_budget_ms: 1000, progressive_widening_enabled: true, progressive_history_enabled: true, rollout_policy: 'heuristic', rollout_cutoff_depth: 10, minimax_backup_alpha: 0.25 },
    },
    'layer5': {
      label: 'L5: RAVE',
      description: 'RAVE value estimation',
      config: { time_budget_ms: 1000, progressive_widening_enabled: true, progressive_history_enabled: true, rollout_policy: 'heuristic', rollout_cutoff_depth: 10, rave_enabled: true, rave_k: 1000 },
    },
    'layer7': {
      label: 'L7: Opponents',
      description: 'Opponent modeling + alliances',
      config: { time_budget_ms: 1000, progressive_widening_enabled: true, progressive_history_enabled: true, rollout_policy: 'heuristic', rollout_cutoff_depth: 10, rave_enabled: true, rave_k: 1000, opponent_modeling_enabled: true, alliance_detection_enabled: true, kingmaker_detection_enabled: true },
    },
    'layer9': {
      label: 'L9: Full Stack',
      description: 'All layers + meta-optimization',
      config: { time_budget_ms: 1500, progressive_widening_enabled: true, progressive_history_enabled: true, rollout_policy: 'heuristic', rollout_cutoff_depth: 10, minimax_backup_alpha: 0.25, rave_enabled: true, rave_k: 1000, opponent_modeling_enabled: true, alliance_detection_enabled: true, kingmaker_detection_enabled: true, adaptive_exploration_enabled: true, sufficiency_threshold_enabled: true },
    },
  };

  const updateAdvancedConfig = (playerIndex: number, key: string, value: any) => {
    setGameConfig((prev: any) => ({
      ...prev,
      players: prev.players.map((p: any, i: number) =>
        i === playerIndex
          ? { ...p, agent_config: { ...p.agent_config, [key]: value } }
          : p
      ),
    }));
  };

  const applyMctsPreset = (playerIndex: number, presetKey: string) => {
    const preset = MCTS_LAYER_PRESETS[presetKey];
    if (!preset) return;
    setGameConfig((prev: any) => ({
      ...prev,
      players: prev.players.map((p: any, i: number) =>
        i === playerIndex
          ? { ...p, agent_type: 'mcts', agent_config: { ...preset.config } }
          : p
      ),
    }));
  };

  const researchQuickStartPresets = [
    {
      name: 'Challenge Champion',
      description: 'Human vs adaptive arena-tested champion profile',
      config: challengeChampionConfig
    },
    {
      name: '4 Players',
      description: `Human vs MCTS Easy/Medium/Hard (${DEPLOY_MCTS_PRESETS.easy}/${DEPLOY_MCTS_PRESETS.medium}/${DEPLOY_MCTS_PRESETS.hard}ms)`,
      config: {
        players: [
          { player: 'RED', agent_type: 'human', agent_config: {} },
          { player: 'BLUE', agent_type: 'mcts', agent_config: { difficulty: 'easy', time_budget_ms: DEPLOY_MCTS_PRESETS.easy } },
          { player: 'GREEN', agent_type: 'mcts', agent_config: { difficulty: 'medium', time_budget_ms: DEPLOY_MCTS_PRESETS.medium } },
          { player: 'YELLOW', agent_type: 'mcts', agent_config: { difficulty: 'hard', time_budget_ms: DEPLOY_MCTS_PRESETS.hard } }
        ],
        auto_start: true
      }
    },
    {
      name: 'vs Random',
      description: 'Easy opponent',
      config: {
        players: [
          { player: 'RED', agent_type: 'human', agent_config: {} },
          { player: 'BLUE', agent_type: 'random', agent_config: {} }
        ],
        auto_start: true
      }
    },
    {
      name: 'vs Heuristic',
      description: 'Medium opponent',
      config: {
        players: [
          { player: 'RED', agent_type: 'human', agent_config: {} },
          { player: 'BLUE', agent_type: 'heuristic', agent_config: {} }
        ],
        auto_start: true
      }
    },
    {
      name: 'vs MCTS 1s',
      description: 'Fast opponent',
      config: {
        players: [
          { player: 'RED', agent_type: 'human', agent_config: {} },
          { player: 'BLUE', agent_type: 'mcts', agent_config: { time_budget_ms: 1000 } }
        ],
        auto_start: true
      }
    },
    {
      name: 'vs MCTS 3s',
      description: 'Balanced opponent',
      config: {
        players: [
          { player: 'RED', agent_type: 'human', agent_config: {} },
          { player: 'BLUE', agent_type: 'mcts', agent_config: { time_budget_ms: 3000 } }
        ],
        auto_start: true
      }
    },
    {
      name: 'vs MCTS 5s',
      description: 'Deep-thinking opponent',
      config: {
        players: [
          { player: 'RED', agent_type: 'human', agent_config: {} },
          { player: 'BLUE', agent_type: 'mcts', agent_config: { time_budget_ms: 5000 } }
        ],
        auto_start: true
      }
    },
    {
      name: 'Layer Battle',
      description: 'Baseline vs L3 vs L5 vs L9',
      config: {
        players: [
          { player: 'RED', agent_type: 'mcts', agent_config: { ...MCTS_LAYER_PRESETS.baseline.config } },
          { player: 'BLUE', agent_type: 'mcts', agent_config: { ...MCTS_LAYER_PRESETS.layer3.config } },
          { player: 'GREEN', agent_type: 'mcts', agent_config: { ...MCTS_LAYER_PRESETS.layer5.config } },
          { player: 'YELLOW', agent_type: 'mcts', agent_config: { ...MCTS_LAYER_PRESETS.layer9.config } }
        ],
        auto_start: true
      }
    },
    {
      name: 'MCTS Arena',
      description: '4-way AI Battle (Easy/Med/Hard/Pro)',
      config: {
        players: [
          { player: 'RED', agent_type: 'mcts', agent_config: { difficulty: 'easy', time_budget_ms: 100 } },
          { player: 'BLUE', agent_type: 'mcts', agent_config: { difficulty: 'medium', time_budget_ms: 450 } },
          { player: 'GREEN', agent_type: 'mcts', agent_config: { difficulty: 'hard', time_budget_ms: 1000 } },
          { player: 'YELLOW', agent_type: 'mcts', agent_config: { difficulty: 'pro', time_budget_ms: 2500 } }
        ],
        auto_start: true
      }
    }
  ];

  const deployQuickStartPresets = [
    {
      name: 'Challenge Champion',
      description: 'Human vs adaptive arena-tested champion profile',
      config: challengeChampionConfig
    },
    {
      name: 'Deploy Preset',
      description: `Human vs MCTS Easy/Medium/Hard (${DEPLOY_MCTS_PRESETS.easy}/${DEPLOY_MCTS_PRESETS.medium}/${DEPLOY_MCTS_PRESETS.hard}ms)`,
      config: deployConfig
    }
  ];

  const quickStartPresets = IS_DEPLOY_PROFILE ? deployQuickStartPresets : researchQuickStartPresets;

  const applyQuickStart = async (preset: typeof quickStartPresets[0]) => {
    setGameConfig(preset.config);
    setIsCreating(true);
    setError(null);

    try {
      const gameId = await createGame(preset.config);
      await connect(gameId);

      const storeState = useGameStore.getState();
      if (!storeState.gameState) {
        try {
          const response = await fetch(`${API_BASE}/api/games/${gameId}`);
          if (response.ok) {
            const gameState = await response.json();
            useGameStore.getState().setGameState(gameState);
          }
        } catch (err) {
          console.error('Failed to fetch game state via REST API:', err);
        }
      }

      onGameCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create game');
    } finally {
      setIsCreating(false);
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsCreating(true);
    setError(null);

    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const content = e.target?.result as string;
        const history = JSON.parse(content);

        if (!Array.isArray(history)) {
          throw new Error("Invalid save file format (expected array)");
        }

        await loadGame(history);
        onGameCreated();
        onClose();
      } catch (err) {
        console.error("Failed to load game:", err);
        setError(err instanceof Error ? err.message : "Failed to load game file");
      } finally {
        setIsCreating(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = ''; // Reset input
        }
      }
    };
    reader.onerror = () => {
      setError("Failed to read the file");
      setIsCreating(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    };
    reader.readAsText(file);
  };

  if (!isOpen) return null;

  // Deploy profile: minimal first-page UI — Human vs MCTS (easy/medium/hard) only, no config
  if (IS_DEPLOY_PROFILE) {
    const arenaConfig = {
      players: [
        { player: 'RED', agent_type: 'mcts', agent_config: { difficulty: 'easy', time_budget_ms: 100 } },
        { player: 'BLUE', agent_type: 'mcts', agent_config: { difficulty: 'medium', time_budget_ms: 450 } },
        { player: 'GREEN', agent_type: 'mcts', agent_config: { difficulty: 'hard', time_budget_ms: 1000 } },
        { player: 'YELLOW', agent_type: 'mcts', agent_config: { difficulty: 'pro', time_budget_ms: 2500 } }
      ],
      auto_start: true
    };

    return (
      <div className="fixed inset-0 bg-charcoal-900 flex items-center justify-center z-50 p-4">
        <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg max-w-md w-full p-8 text-center relative">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="absolute top-4 left-4 text-gray-400 hover:text-neon-blue transition-colors"
            title="Advanced Settings"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
          {canClose && (
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-gray-400 hover:text-gray-200 transition-colors"
              aria-label="Close"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
          <h1 className="text-3xl font-bold text-gray-200 mb-2">Blokus</h1>

          {showSettings && (
            <div className="mb-6 bg-charcoal-900 p-4 rounded-lg border border-charcoal-700 text-left">
              <label className="block text-sm text-gray-300 font-medium mb-2">
                Max AI Thinking Time: {maxTime / 1000}s
              </label>
              <input
                type="range"
                min="400"
                max="9000"
                step="100"
                value={maxTime}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                  const val = parseInt(e.target.value);
                  setMaxTime(val);
                  setGameConfig((prev: any) => ({
                    ...prev,
                    players: prev.players.map((p: any) => {
                      if (p.agent_type === 'mcts') {
                        let budget = val;
                        if (p.agent_config.difficulty === 'easy') budget = Math.floor(val / 4.5);
                        else if (p.agent_config.difficulty === 'medium') budget = Math.floor(val / 2);
                        return {
                          ...p,
                          agent_config: { ...p.agent_config, time_budget_ms: budget }
                        };
                      }
                      return p;
                    })
                  }));
                }}
                className="w-full accent-neon-blue h-2 bg-charcoal-700 rounded-lg appearance-none cursor-pointer"
              />
              <p className="text-xs text-gray-500 mt-2">
                Adjusts the maximum time the Hard AI will think. Easy and Medium scale proportionally.
              </p>
            </div>
          )}

          {error && (
            <div className="bg-red-900 border border-red-700 rounded-lg p-4 mb-6 text-red-200 text-sm">
              {error}
            </div>
          )}

          {/* Mode Selector */}
          <div className="flex flex-col gap-3 mb-4">
            {/* Human vs AI */}
            <div className="text-left">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-bold">Play vs AI</p>
              <button
                onClick={handleCreateGame}
                disabled={isCreating}
                className={`w-full py-3 px-6 rounded-lg font-medium transition-colors duration-200 text-left flex items-center justify-between ${isCreating ? 'bg-gray-600 cursor-not-allowed text-gray-400' : 'bg-neon-blue hover:bg-neon-blue/80 text-black'
                  }`}
              >
                <span>{isCreating ? 'Starting...' : 'Start Game'}</span>
                <span className="text-xs opacity-70">You (Red) vs Easy · Med · Hard</span>
              </button>
            </div>

            {/* MCTS Arena */}
            <div className="text-left">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-bold">Watch AI Battle</p>
              <button
                onClick={() => applyQuickStart({ name: 'MCTS Arena', description: '', config: arenaConfig })}
                disabled={isCreating}
                className={`w-full py-3 px-6 rounded-lg font-medium border transition-colors duration-200 text-left flex items-center justify-between ${isCreating
                    ? 'border-charcoal-600 bg-charcoal-700 text-gray-500 cursor-not-allowed'
                    : 'border-neon-blue bg-neon-blue/5 hover:bg-neon-blue/10 text-neon-blue'
                  }`}
              >
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  {isCreating ? 'Starting...' : 'MCTS Arena'}
                </span>
                <span className="text-xs opacity-70">Easy · Med · Hard · Pro (full auto)</span>
              </button>
            </div>
          </div>

          {/* Load game */}
          <input
            type="file"
            accept=".json"
            ref={fileInputRef}
            onChange={handleFileUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isCreating}
            className={`w-full py-2 px-6 rounded-lg font-medium border transition-colors duration-200 text-sm ${isCreating
                ? 'bg-charcoal-700 border-charcoal-600 text-gray-500 cursor-not-allowed'
                : 'bg-charcoal-800 border-charcoal-600 text-gray-400 hover:bg-charcoal-700 hover:text-white'
              }`}
          >
            Load Saved Game
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-charcoal-800 border border-charcoal-700 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-200">Game Configuration</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-200 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {error && (
            <div className="bg-red-900 border border-red-700 rounded-lg p-4 mb-6">
              <div className="text-red-200">{error}</div>
            </div>
          )}

          <div className="mb-6">
            <h3 className="text-lg font-semibold text-gray-200 mb-3">Quick Start</h3>
            <div className="grid grid-cols-2 gap-3">
              {quickStartPresets.map((preset, idx) => {
                const isArena = preset.name === 'MCTS Arena';
                return (
                  <button
                    key={idx}
                    onClick={() => applyQuickStart(preset)}
                    disabled={isCreating}
                    className={`p-4 border rounded-lg transition-colors text-left disabled:opacity-50 disabled:cursor-not-allowed ${isArena
                      ? 'border-neon-blue bg-neon-blue/5 hover:bg-neon-blue/10 col-span-2'
                      : 'border-charcoal-700 hover:border-neon-blue hover:bg-charcoal-700'
                      }`}
                  >
                    <div className={`text-sm font-medium flex items-center gap-2 ${isArena ? 'text-neon-blue' : 'text-gray-200'}`}>
                      {isArena && (
                        <svg className="w-4 h-4 flex-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      )}
                      {preset.name}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">{preset.description}</div>
                    {isArena && (
                      <div className="flex gap-2 mt-2">
                        {['Easy·100ms', 'Med·450ms', 'Hard·1s', 'Pro·2.5s'].map((label, i) => (
                          <span key={i} className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-charcoal-700 text-gray-400 tracking-wider">{label}</span>
                        ))}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="border-t border-charcoal-700 pt-6">
            <h3 className="text-lg font-semibold text-gray-200 mb-4">Custom Configuration</h3>

            {/* Players */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Players ({gameConfig.players.length}/4)
              </label>
              <div className="space-y-3">
                {gameConfig.players.map((player: any, index: number) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center space-x-3">
                      <div className="w-24">
                        <select
                          value={player.player}
                          onChange={(e) => updatePlayer(index, 'player', e.target.value)}
                          className="w-full bg-charcoal-900 border border-charcoal-700 text-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-neon-blue"
                        >
                          <option value="RED">Red</option>
                          <option value="BLUE">Blue</option>
                          <option value="GREEN">Green</option>
                          <option value="YELLOW">Yellow</option>
                        </select>
                      </div>
                      <div className="flex-1">
                        <select
                          value={player.agent_type}
                          onChange={(e) => updatePlayer(index, 'agent_type', e.target.value)}
                          className="w-full bg-charcoal-900 border border-charcoal-700 text-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-neon-blue"
                        >
                          <option value="human">Human</option>
                          <option value="random">Random Agent</option>
                          <option value="heuristic">Heuristic Agent</option>
                          <option value="mcts">MCTS Agent</option>
                        </select>
                      </div>
                      {player.agent_type === 'mcts' && (
                        <button
                          onClick={() => setExpandedAdvanced(expandedAdvanced === index ? null : index)}
                          className={`text-xs px-2 py-1 rounded border transition-colors ${expandedAdvanced === index ? 'border-neon-blue text-neon-blue bg-neon-blue/10' : 'border-charcoal-600 text-gray-400 hover:text-neon-blue hover:border-neon-blue'}`}
                          title="Advanced MCTS Settings"
                        >
                          Layers
                        </button>
                      )}
                      {gameConfig.players.length > 2 && (
                        <button
                          onClick={() => removePlayer(index)}
                          className="text-red-400 hover:text-red-300 text-sm px-2"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                    {/* Advanced MCTS Configuration */}
                    {player.agent_type === 'mcts' && expandedAdvanced === index && (
                      <div className="ml-4 p-3 bg-charcoal-900 border border-charcoal-700 rounded-lg text-xs space-y-3">
                        {/* Layer Presets */}
                        <div>
                          <label className="block text-gray-400 font-semibold mb-1 uppercase tracking-wider" style={{ fontSize: '10px' }}>Layer Preset</label>
                          <div className="flex flex-wrap gap-1">
                            {Object.entries(MCTS_LAYER_PRESETS).map(([key, preset]) => (
                              <button
                                key={key}
                                onClick={() => applyMctsPreset(index, key)}
                                className="px-2 py-0.5 rounded border border-charcoal-600 text-gray-300 hover:border-neon-blue hover:text-neon-blue transition-colors"
                                title={preset.description}
                              >
                                {preset.label}
                              </button>
                            ))}
                          </div>
                        </div>
                        {/* Time Budget */}
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block text-gray-500 mb-0.5">Time Budget (ms)</label>
                            <input type="number" min={50} max={10000} step={50}
                              value={player.agent_config?.time_budget_ms ?? 1000}
                              onChange={(e) => updateAdvancedConfig(index, 'time_budget_ms', parseInt(e.target.value) || 1000)}
                              className="w-full bg-charcoal-800 border border-charcoal-600 text-gray-200 rounded px-2 py-1 text-xs" />
                          </div>
                          <div>
                            <label className="block text-gray-500 mb-0.5">Exploration C</label>
                            <input type="number" min={0} max={5} step={0.1}
                              value={player.agent_config?.exploration_constant ?? 1.414}
                              onChange={(e) => updateAdvancedConfig(index, 'exploration_constant', parseFloat(e.target.value) || 1.414)}
                              className="w-full bg-charcoal-800 border border-charcoal-600 text-gray-200 rounded px-2 py-1 text-xs" />
                          </div>
                        </div>
                        {/* Layer 3: Action Reduction */}
                        <div>
                          <div className="text-gray-400 font-semibold uppercase tracking-wider mb-1" style={{ fontSize: '10px' }}>L3: Action Reduction</div>
                          <div className="flex gap-4">
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.progressive_widening_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'progressive_widening_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              Prog. Widening
                            </label>
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.progressive_history_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'progressive_history_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              Prog. History
                            </label>
                          </div>
                        </div>
                        {/* Layer 4: Simulation */}
                        <div>
                          <div className="text-gray-400 font-semibold uppercase tracking-wider mb-1" style={{ fontSize: '10px' }}>L4: Simulation Strategy</div>
                          <div className="grid grid-cols-3 gap-2">
                            <div>
                              <label className="block text-gray-500 mb-0.5">Rollout Policy</label>
                              <select
                                value={player.agent_config?.rollout_policy ?? 'heuristic'}
                                onChange={(e) => updateAdvancedConfig(index, 'rollout_policy', e.target.value)}
                                className="w-full bg-charcoal-800 border border-charcoal-600 text-gray-200 rounded px-2 py-1 text-xs"
                              >
                                <option value="random">Random</option>
                                <option value="heuristic">Heuristic</option>
                                <option value="two_ply">Two-Ply</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-gray-500 mb-0.5">Cutoff Depth</label>
                              <input type="number" min={0} max={100} step={5}
                                value={player.agent_config?.rollout_cutoff_depth ?? ''}
                                placeholder="None"
                                onChange={(e) => updateAdvancedConfig(index, 'rollout_cutoff_depth', e.target.value ? parseInt(e.target.value) : null)}
                                className="w-full bg-charcoal-800 border border-charcoal-600 text-gray-200 rounded px-2 py-1 text-xs" />
                            </div>
                            <div>
                              <label className="block text-gray-500 mb-0.5">Minimax Alpha</label>
                              <input type="number" min={0} max={1} step={0.05}
                                value={player.agent_config?.minimax_backup_alpha ?? 0}
                                onChange={(e) => updateAdvancedConfig(index, 'minimax_backup_alpha', parseFloat(e.target.value) || 0)}
                                className="w-full bg-charcoal-800 border border-charcoal-600 text-gray-200 rounded px-2 py-1 text-xs" />
                            </div>
                          </div>
                        </div>
                        {/* Layer 5: RAVE & NST */}
                        <div>
                          <div className="text-gray-400 font-semibold uppercase tracking-wider mb-1" style={{ fontSize: '10px' }}>L5: RAVE & History</div>
                          <div className="flex gap-4 items-end">
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.rave_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'rave_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              RAVE
                            </label>
                            {player.agent_config?.rave_enabled && (
                              <div>
                                <label className="block text-gray-500 mb-0.5">RAVE k</label>
                                <input type="number" min={100} max={10000} step={100}
                                  value={player.agent_config?.rave_k ?? 1000}
                                  onChange={(e) => updateAdvancedConfig(index, 'rave_k', parseFloat(e.target.value) || 1000)}
                                  className="w-24 bg-charcoal-800 border border-charcoal-600 text-gray-200 rounded px-2 py-1 text-xs" />
                              </div>
                            )}
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.nst_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'nst_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              NST
                            </label>
                          </div>
                        </div>
                        {/* Layer 7: Opponent Modeling */}
                        <div>
                          <div className="text-gray-400 font-semibold uppercase tracking-wider mb-1" style={{ fontSize: '10px' }}>L7: Opponent Modeling</div>
                          <div className="flex flex-wrap gap-3">
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.opponent_modeling_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'opponent_modeling_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              Enabled
                            </label>
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.alliance_detection_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'alliance_detection_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              Alliances
                            </label>
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.kingmaker_detection_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'kingmaker_detection_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              King-maker
                            </label>
                          </div>
                        </div>
                        {/* Layer 9: Meta-Optimization */}
                        <div>
                          <div className="text-gray-400 font-semibold uppercase tracking-wider mb-1" style={{ fontSize: '10px' }}>L9: Meta-Optimization</div>
                          <div className="flex flex-wrap gap-3">
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.adaptive_exploration_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'adaptive_exploration_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              Adaptive C
                            </label>
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.sufficiency_threshold_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'sufficiency_threshold_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              Sufficiency
                            </label>
                            <label className="flex items-center gap-1 text-gray-300">
                              <input type="checkbox" checked={!!player.agent_config?.loss_avoidance_enabled}
                                onChange={(e) => updateAdvancedConfig(index, 'loss_avoidance_enabled', e.target.checked)}
                                className="accent-neon-blue" />
                              Loss Avoidance
                            </label>
                          </div>
                        </div>
                        {/* Search Trace */}
                        <div>
                          <label className="flex items-center gap-1 text-gray-300">
                            <input type="checkbox" checked={!!player.agent_config?.enable_search_trace}
                              onChange={(e) => updateAdvancedConfig(index, 'enable_search_trace', e.target.checked)}
                              className="accent-neon-blue" />
                            Enable Search Trace (for MCTS visualization)
                          </label>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {gameConfig.players.length < 4 && (
                <button
                  onClick={addPlayer}
                  className="mt-2 text-neon-blue hover:text-neon-blue/80 text-sm"
                >
                  + Add Player
                </button>
              )}
            </div>

            {/* Game Settings */}
            <div className="flex items-center mb-6">
              <input
                type="checkbox"
                id="auto_start"
                checked={gameConfig.auto_start}
                onChange={(e) => setGameConfig((prev: any) => ({
                  ...prev,
                  auto_start: e.target.checked
                }))}
                className="mr-2"
              />
              <label htmlFor="auto_start" className="text-sm text-gray-300">
                Auto-start game
              </label>
            </div>

            {/* Create Game Button */}
            <div className="flex space-x-3">
              <button
                onClick={handleCreateGame}
                disabled={isCreating}
                className={`
                  flex-1 py-3 px-6 rounded-lg font-medium text-white transition-colors duration-200
                  ${isCreating
                    ? 'bg-gray-600 cursor-not-allowed'
                    : 'bg-neon-blue hover:bg-neon-blue/80'
                  }
                `}
              >
                {isCreating ? 'Creating Game...' : 'Start New Game'}
              </button>

              <input
                type="file"
                accept=".json"
                ref={fileInputRef}
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isCreating}
                className={`
                  py-3 px-6 rounded-lg font-medium border transition-colors duration-200
                  ${isCreating
                    ? 'bg-charcoal-700 border-charcoal-600 text-gray-500 cursor-not-allowed'
                    : 'bg-charcoal-800 border-charcoal-600 text-gray-300 hover:bg-charcoal-700 hover:text-white'
                  }
                `}
              >
                Load From File
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
