import React from 'react';
import { useGameStore } from '../../store/gameStore';

export const MoveDeltaPanel: React.FC = () => {
    const gameState = useGameStore((s) => s.gameState);

    // Check if we are connected
    if (!gameState) {
        return (
            <div className="h-full flex items-center justify-center p-6 text-center text-gray-500">
                <p>No game active.</p>
            </div>
        );
    }

    // Make sure we have move deltas
    const gameHistory = gameState.game_history || [];
    const movesWithTelemetry = gameHistory.filter((entry: any) => entry.telemetry);

    if (movesWithTelemetry.length === 0) {
        return (
            <div className="h-full flex items-center justify-center p-6 text-center text-gray-500">
                <p>Play some moves to see Move Delta Telemetry.</p>
            </div>
        );
    }

    return (
        <div className="h-full flex flex-col p-4 space-y-4">
            <h2 className="text-xl font-bold text-gray-200">Move Impact Delta</h2>
            <p className="text-gray-400">Placeholders for charts to go here</p>
        </div>
    );
};
