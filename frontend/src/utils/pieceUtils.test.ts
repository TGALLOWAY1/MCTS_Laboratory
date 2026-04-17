/**
 * Tests for piece placement anchor logic.
 * The backend expects anchor_row, anchor_col to be the top-left of the piece.
 * calculatePiecePositions uses anchor as the position of shape[0][0].
 */
import { describe, it, expect } from 'vitest';
import { calculatePiecePositions, getPieceCursorOffset, getPieceShape } from './pieceUtils';

describe('calculatePiecePositions (anchor = top-left)', () => {
  it('piece 1 (monomino) at anchor (0,0) places at (0,0)', () => {
    const positions = calculatePiecePositions(1, 0, 0, 0);
    expect(positions).toEqual([{ row: 0, col: 0 }]);
  });

  it('piece 2 (domino) at anchor (0,0) places at (0,0) and (0,1)', () => {
    const positions = calculatePiecePositions(2, 0, 0, 0);
    expect(positions).toEqual([
      { row: 0, col: 0 },
      { row: 0, col: 1 },
    ]);
  });

  it('piece 6 (2x2) at anchor (0,0) places all four cells', () => {
    const positions = calculatePiecePositions(6, 0, 0, 0);
    expect(positions).toEqual([
      { row: 0, col: 0 },
      { row: 0, col: 1 },
      { row: 1, col: 0 },
      { row: 1, col: 1 },
    ]);
  });

  it('piece 6 at anchor (1,1) places with correct offset', () => {
    const positions = calculatePiecePositions(6, 0, 1, 1);
    expect(positions).toEqual([
      { row: 1, col: 1 },
      { row: 1, col: 2 },
      { row: 2, col: 1 },
      { row: 2, col: 2 },
    ]);
  });

  it('clicking bottom-right of 2x2 at (1,1) requires anchor (0,0)', () => {
    // User clicks (1,1). Piece covers (0,0),(0,1),(1,0),(1,1).
    // Anchor must be (0,0) so the piece covers the clicked cell.
    const anchorRow = 0;
    const anchorCol = 0;
    const positions = calculatePiecePositions(6, 0, anchorRow, anchorCol);
    const includesClicked = positions.some((p) => p.row === 1 && p.col === 1);
    expect(includesClicked).toBe(true);
  });
});

describe('getPieceCursorOffset', () => {
  it('always returns a filled cell for every piece and orientation', () => {
    for (let pieceId = 1; pieceId <= 21; pieceId++) {
      for (let orientation = 0; orientation < 8; orientation++) {
        const shape = getPieceShape(pieceId, orientation);
        const offset = getPieceCursorOffset(pieceId, orientation);
        expect(shape[offset.row]?.[offset.col]).toBe(1);
      }
    }
  });

  it('returns (0,0) for a monomino', () => {
    expect(getPieceCursorOffset(1, 0)).toEqual({ row: 0, col: 0 });
  });

  it('placing preview via cursor keeps the cursor cell covered', () => {
    // For every piece and orientation, placing the piece so that its anchor is
    // (cursor - offset) must produce a cell covering the cursor itself.
    const cursorRow = 7;
    const cursorCol = 7;
    for (let pieceId = 1; pieceId <= 21; pieceId++) {
      for (let orientation = 0; orientation < 8; orientation++) {
        const offset = getPieceCursorOffset(pieceId, orientation);
        const positions = calculatePiecePositions(
          pieceId,
          orientation,
          cursorRow - offset.row,
          cursorCol - offset.col
        );
        const covers = positions.some((p) => p.row === cursorRow && p.col === cursorCol);
        expect(covers).toBe(true);
      }
    }
  });
});
