import { PIECE_SHAPES } from '../constants/gameConstants';

export interface Position {
  row: number;
  col: number;
}

/**
 * Rotate piece 90° counter-clockwise to match backend (numpy rot90).
 * Backend uses np.rot90 which is CCW; mismatch caused preview to differ from placement.
 */
export const rotatePiece = (shape: number[][]): number[][] => {
  const rows = shape.length;
  const cols = shape[0].length;
  const rotated = Array(cols).fill(null).map(() => Array(rows).fill(0));
  
  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      rotated[cols - 1 - j][i] = shape[i][j];
    }
  }
  
  return rotated;
};

export const flipPiece = (shape: number[][]): number[][] => {
  return shape.map(row => [...row].reverse());
};

export const getPieceShape = (pieceId: number, orientation: number): number[][] => {
  let shape = PIECE_SHAPES[pieceId];
  if (!shape) return [];
  
  // Match backend orientation system:
  // 0: Original shape
  // 1-3: 90°, 180°, 270° rotations
  // 4: Reflection (flip)
  // 5-7: Reflected rotations
  
  if (orientation === 0) {
    return shape;
  } else if (orientation <= 3) {
    // Rotations only
    for (let i = 0; i < orientation; i++) {
      shape = rotatePiece(shape);
    }
  } else if (orientation === 4) {
    // Reflection only
    shape = flipPiece(shape);
  } else {
    // Reflected rotations (5-7)
    shape = flipPiece(shape);
    for (let i = 0; i < orientation - 4; i++) {
      shape = rotatePiece(shape);
    }
  }
  
  return shape;
};

export const calculatePiecePositions = (
  pieceId: number,
  orientation: number,
  anchorRow: number,
  anchorCol: number
): Position[] => {
  const shape = getPieceShape(pieceId, orientation);
  const positions: Position[] = [];

  for (let row = 0; row < shape.length; row++) {
    for (let col = 0; col < shape[row].length; col++) {
      if (shape[row][col] === 1) {
        positions.push({
          row: anchorRow + row,
          col: anchorCol + col
        });
      }
    }
  }

  return positions;
};

/**
 * Offset (relative to anchor = bounding-box top-left) of the piece cell that
 * should sit under the cursor. Picks the filled square nearest the shape's
 * centroid; ties resolve to top-most, then left-most. Guarantees the cursor
 * always overlaps an actual piece square.
 */
export const getPieceCursorOffset = (
  pieceId: number,
  orientation: number
): Position => {
  const shape = getPieceShape(pieceId, orientation);
  const filled: Position[] = [];
  for (let row = 0; row < shape.length; row++) {
    for (let col = 0; col < shape[row].length; col++) {
      if (shape[row][col] === 1) filled.push({ row, col });
    }
  }
  if (filled.length === 0) return { row: 0, col: 0 };

  let sumR = 0;
  let sumC = 0;
  for (const p of filled) {
    sumR += p.row;
    sumC += p.col;
  }
  const cR = sumR / filled.length;
  const cC = sumC / filled.length;

  let best = filled[0];
  let bestD = Infinity;
  for (const p of filled) {
    const dr = p.row - cR;
    const dc = p.col - cC;
    const d = dr * dr + dc * dc;
    if (d < bestD - 1e-9 ||
        (Math.abs(d - bestD) < 1e-9 && (p.row < best.row ||
          (p.row === best.row && p.col < best.col)))) {
      best = p;
      bestD = d;
    }
  }
  return best;
};
