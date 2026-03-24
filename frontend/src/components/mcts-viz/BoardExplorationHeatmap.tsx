/**
 * Board Exploration Heatmap — shows which board regions the search pays attention to.
 * Colors cells by how often they appeared in expanded moves during MCTS.
 */
import React, { useMemo } from 'react';

interface Props {
    grid: number[][] | null;  // 20x20 exploration counts
    board?: number[][];       // 20x20 board state (0=empty, 1-4=players)
}

const PLAYER_COLORS: Record<number, string> = {
    1: 'rgba(239, 68, 68, 0.6)',   // RED
    2: 'rgba(59, 130, 246, 0.6)',  // BLUE
    3: 'rgba(34, 197, 94, 0.6)',   // GREEN
    4: 'rgba(234, 179, 8, 0.6)',   // YELLOW
};

export const BoardExplorationHeatmap: React.FC<Props> = ({ grid, board }) => {
    const { normalizedGrid, maxCount } = useMemo(() => {
        if (!grid) return { normalizedGrid: null, maxCount: 0 };
        let max = 0;
        for (const row of grid) {
            for (const v of row) {
                if (v > max) max = v;
            }
        }
        return { normalizedGrid: grid, maxCount: max };
    }, [grid]);

    if (!normalizedGrid || maxCount === 0) {
        return <div className="text-xs text-gray-500 p-4 text-center">No exploration data</div>;
    }

    const cellSize = 16;
    const gridSize = 20;

    return (
        <div>
            <div className="flex items-center gap-2 mb-2 px-1">
                <span className="text-[10px] text-gray-500">Exploration intensity (max: {maxCount})</span>
                <div className="flex items-center gap-0.5">
                    {[0, 0.25, 0.5, 0.75, 1.0].map(v => (
                        <div
                            key={v}
                            className="w-3 h-3 rounded-sm"
                            style={{ backgroundColor: `rgba(99, 102, 241, ${v * 0.8 + 0.1})` }}
                        />
                    ))}
                    <span className="text-[9px] text-gray-600 ml-1">low → high</span>
                </div>
            </div>
            <div
                className="inline-grid border border-charcoal-700 rounded"
                style={{
                    gridTemplateColumns: `repeat(${gridSize}, ${cellSize}px)`,
                    gridTemplateRows: `repeat(${gridSize}, ${cellSize}px)`,
                    gap: '0px',
                }}
            >
                {normalizedGrid.map((row, r) =>
                    row.map((count, c) => {
                        const intensity = count / maxCount;
                        const isOccupied = board && board[r]?.[c] > 0;
                        const playerColor = isOccupied ? PLAYER_COLORS[board![r][c]] : null;

                        return (
                            <div
                                key={`${r}-${c}`}
                                title={`(${r},${c}) explored ${count}x`}
                                style={{
                                    width: cellSize,
                                    height: cellSize,
                                    backgroundColor: isOccupied
                                        ? playerColor!
                                        : count > 0
                                            ? `rgba(99, 102, 241, ${intensity * 0.8 + 0.1})`
                                            : 'rgba(30, 30, 40, 0.5)',
                                    borderRight: c < gridSize - 1 ? '1px solid rgba(55,65,81,0.3)' : 'none',
                                    borderBottom: r < gridSize - 1 ? '1px solid rgba(55,65,81,0.3)' : 'none',
                                }}
                            />
                        );
                    })
                )}
            </div>
        </div>
    );
};
