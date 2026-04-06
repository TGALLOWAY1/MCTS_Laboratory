from dataclasses import dataclass
from typing import List, Tuple, Set

from .spatial_analysis import TurnAnalysis

@dataclass
class TurnDelta:
    frontier_added: List[Tuple[int, int]]
    frontier_removed: List[Tuple[int, int]]
    reachable_added: List[Tuple[int, int]]
    reachable_removed: List[Tuple[int, int]]
    
    influence_delta: List[List[float]]
    opponent_pressure_delta: List[List[float]]
    
    metrics_delta: dict

def compute_delta(prev_turn: TurnAnalysis, curr_turn: TurnAnalysis) -> TurnDelta:
    """Calculate the difference between two TurnAnalysis snapshots."""
    size = len(curr_turn.influence_map)
    
    prev_front = set(tuple(p) for p in prev_turn.frontier_points)
    curr_front = set(tuple(p) for p in curr_turn.frontier_points)
    
    frontier_added = list(curr_front - prev_front)
    frontier_removed = list(prev_front - curr_front)
    
    reachable_added = []
    reachable_removed = []
    
    inf_delta = []
    opp_delta = []
    
    for r in range(size):
        inf_row = []
        opp_row = []
        for c in range(size):
            # Reachability
            r_prev = prev_turn.reachable_space[r][c]
            r_curr = curr_turn.reachable_space[r][c]
            if r_curr > 0 and r_prev == 0:
                reachable_added.append((r, c))
            elif r_curr == 0 and r_prev > 0:
                reachable_removed.append((r, c))
                
            # Influence
            inf_row.append(curr_turn.influence_map[r][c] - prev_turn.influence_map[r][c])
            # Opponent pressure
            opp_row.append(curr_turn.opponent_pressure_map[r][c] - prev_turn.opponent_pressure_map[r][c])
            
        inf_delta.append(inf_row)
        opp_delta.append(opp_row)
        
    metrics = {
        "legal_moves": curr_turn.legal_moves_count - prev_turn.legal_moves_count,
        "contested": curr_turn.contested_cells - prev_turn.contested_cells,
        "influence_mass": curr_turn.influence_mass - prev_turn.influence_mass
    }
    
    return TurnDelta(
        frontier_added=frontier_added,
        frontier_removed=frontier_removed,
        reachable_added=reachable_added,
        reachable_removed=reachable_removed,
        influence_delta=inf_delta,
        opponent_pressure_delta=opp_delta,
        metrics_delta=metrics
    )
