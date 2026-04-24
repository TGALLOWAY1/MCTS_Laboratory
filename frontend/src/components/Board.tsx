import React, { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import { useGameStore } from '../store/gameStore';
import { PLAYER_COLORS, BOARD_SIZE, CELL_SIZE } from '../constants/gameConstants';
import { calculatePiecePositions, getPieceCursorOffset } from '../utils/pieceUtils';

export interface CellOverlay {
  color: string;
  opacity?: number;
  label?: string; // optional small label, e.g. '+' or '-'
}

interface BoardProps {
  onCellClick: (row: number, col: number) => void;
  onCellHover: (row: number, col: number) => void;
  selectedPiece: number | null;
  pieceOrientation: number;
  overlayMap?: Record<string, CellOverlay>; // key: `${row}-${col}`
}

// Constants are now imported from shared constants file

const CellRect = React.memo<{
  row: number;
  col: number;
  cellColor: string;
  opacity: number;
  stroke: string;
  strokeWidth: number;
  hasPiece: boolean;
}>(({ row, col, cellColor, opacity, stroke, strokeWidth, hasPiece }) => (
  <g>
    <rect
      x={col * CELL_SIZE}
      y={row * CELL_SIZE}
      width={CELL_SIZE}
      height={CELL_SIZE}
      fill={cellColor}
      opacity={opacity}
      stroke={stroke}
      strokeWidth={strokeWidth}
      className="transition-all duration-200"
      style={{
        filter: hasPiece ? `drop-shadow(0 0 2px ${cellColor})` : 'none'
      }}
    />
  </g>
));
CellRect.displayName = 'CellRect';

export const Board: React.FC<BoardProps> = ({
  onCellClick,
  onCellHover,
  selectedPiece,
  pieceOrientation,
  overlayMap,
}) => {
  const { gameState, previewMove, setPreviewMove, currentSliderTurn, pendingPlacement } = useGameStore();
  const [hoveredCell, setHoveredCell] = useState<{ row: number, col: number } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const cursorOffset = useMemo(
    () => (selectedPiece ? getPieceCursorOffset(selectedPiece, pieceOrientation) : { row: 0, col: 0 }),
    [selectedPiece, pieceOrientation]
  );

  // Optimistic placement: paint the pending piece immediately with the player's
  // color, skipping squares already filled on the authoritative board (so an
  // illegal overlap never hides the real state).
  const pendingCells = useMemo<Record<string, string>>(() => {
    if (!pendingPlacement) return {};
    const positions = calculatePiecePositions(
      pendingPlacement.piece_id,
      pendingPlacement.orientation,
      pendingPlacement.anchor_row,
      pendingPlacement.anchor_col
    );
    const playerColor =
      PLAYER_COLORS[pendingPlacement.player.toLowerCase() as keyof typeof PLAYER_COLORS] ||
      PLAYER_COLORS.empty;
    const board = gameState?.board;
    const out: Record<string, string> = {};
    for (const p of positions) {
      if (p.row < 0 || p.row >= BOARD_SIZE || p.col < 0 || p.col >= BOARD_SIZE) continue;
      if (board && board[p.row]?.[p.col]) continue;
      out[`${p.row}-${p.col}`] = playerColor;
    }
    return out;
  }, [pendingPlacement, gameState?.board]);

  // Performance instrumentation - measure render time
  useEffect(() => {
    console.time('[UI] Board render');
    return () => {
      console.timeEnd('[UI] Board render');
    };
  });

  // Performance instrumentation - measure effect time when gameState changes
  useEffect(() => {
    if (gameState) {
      console.time('[UI] Board effect (gameState change)');
      // Any async operations or computations would go here
      console.timeEnd('[UI] Board effect (gameState change)');
    }
  }, [gameState]);


  const handleMouseMove = useCallback((event: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;

    const rect = svgRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const col = Math.floor((x / rect.width) * BOARD_SIZE);
    const row = Math.floor((y / rect.height) * BOARD_SIZE);

    if (row >= 0 && row < BOARD_SIZE && col >= 0 && col < BOARD_SIZE) {
      setHoveredCell({ row, col });
      onCellHover(row, col);
    } else {
      setHoveredCell(null);
    }
  }, [onCellHover]);

  const handleClick = useCallback((event: React.MouseEvent<SVGSVGElement>) => {
    if (!svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const col = Math.floor(((event.clientX - rect.left) / rect.width) * BOARD_SIZE);
    const row = Math.floor(((event.clientY - rect.top) / rect.height) * BOARD_SIZE);
    if (row < 0 || row >= BOARD_SIZE || col < 0 || col >= BOARD_SIZE) return;

    if (previewMove) setPreviewMove(null);

    // With a selected piece, cursor sits on cursorOffset within the piece, so
    // translate the cursor cell back to the piece's bounding-box anchor.
    if (selectedPiece) {
      const anchorRow = row - cursorOffset.row;
      const anchorCol = col - cursorOffset.col;
      onCellClick(anchorRow, anchorCol);
      return;
    }
    onCellClick(row, col);
  }, [onCellClick, selectedPiece, cursorOffset, previewMove, setPreviewMove]);

  // Memoize cell color calculation to avoid recomputation
  const cellColors = useMemo(() => {
    let boardToRender = gameState?.board;
    const historyDepth = gameState?.game_history?.length || 0;

    // If user is reviewing history via the slider, show that historic board state
    if (currentSliderTurn !== null && historyDepth > 0 && currentSliderTurn !== historyDepth) {
      const historyIdx = Math.max(0, Math.min(historyDepth - 1, currentSliderTurn - 1));
      boardToRender = gameState!.game_history![historyIdx].board_state;
    }
    // If we're previewing a move from the MCTS table (which represents candidates for the last played move),
    // we should render the board state *before* that move was actually played, so the preview
    // doesn't overlap with the chosen move.
    else if (previewMove && historyDepth > 0) {
      // The state before the last move is either the penultimate history entry, or an empty board
      if (historyDepth > 1) {
        boardToRender = gameState!.game_history![historyDepth - 2].board_state;
      } else {
        // Turn 1's before-state is an empty board
        boardToRender = Array(BOARD_SIZE).fill(0).map(() => Array(BOARD_SIZE).fill(0));
      }
    }

    if (!boardToRender) return null;
    const colors: (string | null)[][] = [];
    for (let row = 0; row < BOARD_SIZE; row++) {
      colors[row] = [];
      for (let col = 0; col < BOARD_SIZE; col++) {
        const cell = boardToRender[row]?.[col];
        if (!cell || cell === 0) {
          colors[row][col] = PLAYER_COLORS.empty;
        } else {
          const colorMap = {
            1: 'red',    // RED -> red
            2: 'blue',   // BLUE -> blue
            3: 'yellow', // YELLOW -> yellow
            4: 'green'   // GREEN -> green
          };
          const colorName = colorMap[cell as keyof typeof colorMap];
          colors[row][col] = PLAYER_COLORS[colorName as keyof typeof PLAYER_COLORS] || PLAYER_COLORS.empty;
        }
      }
    }
    return colors;
  }, [gameState?.board, gameState?.game_history, previewMove, currentSliderTurn]);

  const getCellColor = useCallback((row: number, col: number) => {
    if (!cellColors) return PLAYER_COLORS.empty;
    return cellColors[row]?.[col] || PLAYER_COLORS.empty;
  }, [cellColors]);

  const isPreviewCell = (row: number, col: number) => {
    return piecePreview.some(pos => pos.row === row && pos.col === col);
  };

  const getPendingColor = (row: number, col: number): string | undefined => {
    return pendingCells[`${row}-${col}`];
  };

  const getCellFillColor = (row: number, col: number) => {
    // Optimistic pending placement renders as a solid placed piece.
    const pending = getPendingColor(row, col);
    if (pending) return pending;

    // Preview cells (ghost piece) should be transparent (hollow)
    if (isPreviewCell(row, col)) {
      return 'transparent';
    }

    // Return the normal cell color
    return getCellColor(row, col);
  };

  const getCellOpacity = (row: number, col: number) => {
    // Preview cells are transparent (hollow), so opacity doesn't matter
    if (isPreviewCell(row, col)) {
      return 1.0;
    }

    // Normal cells are fully opaque
    return 1.0;
  };

  const getCellStroke = (row: number, col: number) => {
    // Pending (optimistic) cells render as solid placed pieces — no stroke.
    if (getPendingColor(row, col)) return 'none';
    // Ghost piece cells get preview color stroke only (hollow rectangle)
    if (isPreviewCell(row, col)) {
      return PLAYER_COLORS.preview;
    }
    return 'none';
  };

  const getCellStrokeWidth = (row: number, col: number) => {
    if (getPendingColor(row, col)) return 0;
    // Ghost piece cells get 2px border
    if (isPreviewCell(row, col)) {
      return 2;
    }
    return 0;
  };

  const hasPlacedPiece = (row: number, col: number) => {
    if (getPendingColor(row, col)) return true;
    // Check if this cell has a placed piece (not empty, not preview, not hover)
    const cellColor = getCellColor(row, col);
    return cellColor !== PLAYER_COLORS.empty && !isPreviewCell(row, col);
  };


  // Piece utilities are now imported from shared utils

  const getPiecePreview = () => {
    // MCTS table click preview takes precedence
    if (previewMove) {
      const positions = calculatePiecePositions(
        previewMove.piece_id,
        previewMove.orientation,
        previewMove.anchor_row,
        previewMove.anchor_col
      );
      return positions.filter(
        (pos) =>
          pos.row >= 0 &&
          pos.row < BOARD_SIZE &&
          pos.col >= 0 &&
          pos.col < BOARD_SIZE
      );
    }
    if (!selectedPiece || !hoveredCell) return [];

    // Calculate piece positions based on shape and orientation.
    // cursorOffset is the cell within the piece that sits under the cursor,
    // so the bounding-box anchor is hoveredCell minus that offset.
    const anchorRow = hoveredCell.row - cursorOffset.row;
    const anchorCol = hoveredCell.col - cursorOffset.col;
    const positions = calculatePiecePositions(selectedPiece, pieceOrientation, anchorRow, anchorCol);

    // Filter out positions that are outside the board
    const validPositions = positions.filter(
      (pos) =>
        pos.row >= 0 &&
        pos.row < BOARD_SIZE &&
        pos.col >= 0 &&
        pos.col < BOARD_SIZE
    );

    return validPositions;
  };

  const piecePreview = getPiecePreview();

  return (
    <div className="flex items-center justify-center h-full w-full bg-transparent">
      <div className="aspect-square max-h-full max-w-full h-full">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${BOARD_SIZE * CELL_SIZE} ${BOARD_SIZE * CELL_SIZE}`}
          preserveAspectRatio="xMidYMid meet"
          width="100%"
          height="100%"
          className="cursor-crosshair bg-charcoal-900/50 block"
          onMouseMove={handleMouseMove}
          onClick={handleClick}
        >
        {/* Grid lines - higher contrast against dark background */}
        {Array.from({ length: BOARD_SIZE + 1 }).map((_, i) => (
          <g key={i}>
            <line
              x1={i * CELL_SIZE}
              y1={0}
              x2={i * CELL_SIZE}
              y2={BOARD_SIZE * CELL_SIZE}
              stroke="#525252"
              strokeWidth={1}
            />
            <line
              x1={0}
              y1={i * CELL_SIZE}
              x2={BOARD_SIZE * CELL_SIZE}
              y2={i * CELL_SIZE}
              stroke="#525252"
              strokeWidth={1}
            />
          </g>
        ))}

        {/* Board cells - memoized to prevent unnecessary re-renders */}
        {Array.from({ length: BOARD_SIZE }).map((_, row) =>
          Array.from({ length: BOARD_SIZE }).map((_, col) => {
            const cellColor = getCellFillColor(row, col);
            const opacity = getCellOpacity(row, col);
            const stroke = getCellStroke(row, col);
            const strokeWidth = getCellStrokeWidth(row, col);
            const hasPiece = hasPlacedPiece(row, col);

            return (
              <CellRect
                key={`${row}-${col}`}
                row={row}
                col={col}
                cellColor={cellColor}
                opacity={opacity}
                stroke={stroke}
                strokeWidth={strokeWidth}
                hasPiece={hasPiece}
              />
            );
          })
        )}

        {/* Delta Overlay */}
        {overlayMap && Object.entries(overlayMap).map(([key, ov]) => {
          const [rStr, cStr] = key.split('-');
          const r = parseInt(rStr, 10);
          const c = parseInt(cStr, 10);
          return (
            <rect
              key={`overlay-${key}`}
              x={c * CELL_SIZE}
              y={r * CELL_SIZE}
              width={CELL_SIZE}
              height={CELL_SIZE}
              fill={ov.color}
              opacity={ov.opacity ?? 0.4}
              className="pointer-events-none"
            />
          );
        })}

        {/* Hovered cell highlight - only show if not part of piece preview */}
        {hoveredCell && !isPreviewCell(hoveredCell.row, hoveredCell.col) && (
          <rect
            x={hoveredCell.col * CELL_SIZE}
            y={hoveredCell.row * CELL_SIZE}
            width={CELL_SIZE}
            height={CELL_SIZE}
            fill={PLAYER_COLORS.grid}
            opacity={0.3}
            className="pointer-events-none"
          />
        )}
        </svg>
      </div>
    </div>
  );
};
