import numpy as np
from dataclasses import dataclass
from typing import Set, Tuple, List, Dict

from engine.board import Board, Player
from engine.move_generator import LegalMoveGenerator, Move
from engine.pieces import ALL_PIECE_ORIENTATIONS

@dataclass
class TurnAnalysis:
    player_id: int
    turn_index: int
    frontier_points: List[Tuple[int, int]]
    legal_moves_count: int
    
    # 2D scalar fields
    influence_map: List[List[float]]
    reachable_space: List[List[float]]
    opponent_pressure_map: List[List[float]]
    
    # Summary metrics
    contested_cells: int
    influence_mass: float

def get_move_positions(move: Move) -> List[Tuple[int, int]]:
    """Get the board coordinates covered by a given move."""
    orientations = ALL_PIECE_ORIENTATIONS[move.piece_id]
    piece_orientation = orientations[move.orientation]
    positions = []
    for r, c in piece_orientation.offsets:
        positions.append((move.anchor_row + r, move.anchor_col + c))
    return positions

def compute_distance_field(points: Set[Tuple[int, int]], size: int) -> np.ndarray:
    """Compute Manhattan distance from all cells to the nearest point in the set."""
    if not points:
        return np.full((size, size), np.inf)
    
    # For a small 20x20 grid, a simple broadside BFS is extremely fast
    grid = np.full((size, size), np.inf)
    queue = list(points)
    for r, c in queue:
        grid[r, c] = 0
        
    head = 0
    while head < len(queue):
        r, c = queue[head]
        head += 1
        d = grid[r, c]
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < size and 0 <= nc < size:
                if grid[nr, nc] > d + 1:
                    grid[nr, nc] = d + 1
                    queue.append((nr, nc))
    return grid

def generate_turn_analysis(
    board: Board, 
    player: Player, 
    turn_index: int, 
    move_gen: LegalMoveGenerator
) -> TurnAnalysis:
    """Compute all strategic spatial metric fields for the given player's turn."""
    size = board.SIZE
    
    frontier_cells = board.get_frontier(player)
    legal_moves = move_gen.get_legal_moves(board, player)
    
    empty_mask = (board.grid == 0)

    # 1. Reachable Space (Depth 1)
    # 1.0 = reachable in 1 move
    reachable_map = np.zeros((size, size), dtype=float)
    for move in legal_moves:
        for r, c in get_move_positions(move):
            if 0 <= r < size and 0 <= c < size:
                reachable_map[r, c] = 1.0
                
    # 2. Opponent Pressure Map
    # Sum of exp(-0.5 * distance to opponent frontier)
    opp_pressure_map = np.zeros((size, size), dtype=float)
    for opp in Player:
        if opp != player:
            opp_frontier = board.get_frontier(opp)
            if opp_frontier:
                opp_dist = compute_distance_field(opp_frontier, size)
                opp_pressure_map += np.exp(-0.5 * opp_dist)
                
    # Limit pressure map to empty cells
    opp_pressure_map *= empty_mask

    # Normalize opponent pressure on empty cells
    max_opp_pressure = np.max(opp_pressure_map)
    if max_opp_pressure > 0:
        norm_opp_pressure = opp_pressure_map / max_opp_pressure
    else:
        norm_opp_pressure = opp_pressure_map
                
    # 3. Territorial Influence Map
    my_dist = compute_distance_field(frontier_cells, size)
    # Score decays with distance: exp(-0.3 * r), penalised by opponent pressure
    influence_map = np.exp(-0.3 * my_dist) * (1.0 - norm_opp_pressure)
    influence_map *= empty_mask  # Re-mask
    
    # Compute contested cells (where both you have influence and opponent has pressure)
    contested_mask = (influence_map > 0.1) & (norm_opp_pressure > 0.1) & empty_mask
    contested_cells = int(np.sum(contested_mask))
    influence_mass = float(np.sum(influence_map))

    return TurnAnalysis(
        player_id=int(player.value),
        turn_index=turn_index,
        frontier_points=list(frontier_cells),
        legal_moves_count=len(legal_moves),
        influence_map=influence_map.tolist(),
        reachable_space=reachable_map.tolist(),
        opponent_pressure_map=opp_pressure_map.tolist(),
        contested_cells=contested_cells,
        influence_mass=influence_mass,
    )
