#!/usr/bin/env python3
"""Run detailed spatial analysis offline on an existing heatmap data directory."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import numpy as np

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.board import Board, Player
from engine.bitboard import coords_to_mask
from engine.move_generator import LegalMoveGenerator
from analytics.heatmap.spatial_analysis import generate_turn_analysis, TurnAnalysis
from analytics.heatmap.delta_calculator import compute_delta

def reconstruct_board(grid_list: List[List[int]], used_pieces_dict: Dict[str, List[int]]) -> Board:
    """Rebuild a fully functional Board object from serialized state."""
    board = Board()
    board.grid = np.array(grid_list, dtype=int)
    
    for player_str, pieces in used_pieces_dict.items():
        player = Player(int(player_str))
        for p in pieces:
            board.player_pieces_used[player].add(int(p))
        if pieces:
            board.player_first_move[player] = False
            
    # Rebuild bitboards
    for r in range(board.SIZE):
        for c in range(board.SIZE):
            val = board.grid[r, c]
            if val != 0:
                mask = coords_to_mask([(r, c)])
                board.occupied_bits |= mask
                board.player_bits[Player(val)] |= mask
                
    # Recompute frontiers from scratch
    board.init_frontiers()
    for p in Player:
        board.player_frontiers[p] = board._compute_full_frontier(p)
        
    return board

def run_detailed_analysis_pipeline(data_dir: Path, output_dir: Path):
    """Process a directory of turn JSONs and compile a detailed web dashboard."""
    turn_files = sorted(data_dir.glob("turn_*.json"))
    if not turn_files:
        print(f"No turn data found in {data_dir}", file=sys.stderr)
        return
        
    print(f"Found {len(turn_files)} turns in {data_dir}. Processing...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    move_gen = LegalMoveGenerator()
    
    game_data = []
    prev_analysis = None
    
    for tf in turn_files:
        with open(tf, "r") as f:
            turn_data = json.load(f)
            
        turn_idx = turn_data["turn"]
        player_id = turn_data["player"]
        grid = turn_data["board_grid"]
        chosen_move = turn_data.get("chosen_move")
        used_pieces = turn_data.get("used_pieces")
        
        if not used_pieces:
            print(f"Skipping {tf.name}: 'used_pieces' field is missing. Please regenerate game logs with the updated arena_runner.py.", file=sys.stderr)
            continue
            
        board = reconstruct_board(grid, used_pieces)
        player = Player(player_id)
        
        # Spatial Analysis
        analysis = generate_turn_analysis(board, player, turn_idx, move_gen)
        
        # Delta Analysis
        delta = None
        if prev_analysis is not None:
            # Note: For realistic Delta, we usually compare against the SAME player's previous turn, 
            # but since delta tracks board changes, comparing to previous absolute turn (opponent's move)
            # gives "what changed since last frame", whereas comparing to your own last turn gives "what I gained/lost since my last move".
            # The brainstorming mentions "What did THIS move do?", so we want to compare T against T-1.
            try:
                delta_obj = compute_delta(prev_analysis, analysis)
                delta = delta_obj.__dict__
            except Exception as e:
                print(f"Delta computation failed: {e}")
                
        # To avoid massive file size, round floats
        def round_grid(g):
            return [[round(float(c), 3) for c in row] for row in g]
            
        frame_data = {
            "turn": turn_idx,
            "player": player_id,
            "board_grid": grid,
            "chosen_move": chosen_move,
            "analysis": {
                "frontier_points": analysis.frontier_points,
                "legal_moves_count": analysis.legal_moves_count,
                "contested_cells": analysis.contested_cells,
                "influence_mass": round(analysis.influence_mass, 3),
                "influence_map": round_grid(analysis.influence_map),
                "reachable_space": round_grid(analysis.reachable_space),
                "opponent_pressure_map": round_grid(analysis.opponent_pressure_map),
            },
            "delta": delta
        }
        
        game_data.append(frame_data)
        prev_analysis = analysis
        print(f"Processed turn {turn_idx} (Player {player_id})")
        
    # Write to JS
    js_path = output_dir / "data.js"
    with open(js_path, "w") as f:
        f.write("window.GAME_DATA = " + json.dumps(game_data) + ";\n")
        
    print(f"Wrote analysis data to {js_path}")
    
    # We will copy the viewer HTML template
    template_path = PROJECT_ROOT / "analytics" / "heatmap" / "viewer_template.html"
    if template_path.exists():
        import shutil
        html_path = output_dir / "index.html"
        shutil.copy(template_path, html_path)
        print(f"Wrote dashboard viewer to {html_path}")
    else:
        print(f"Warning: HTML template {template_path} not found.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detailed Spatial Analysis")
    parser.add_argument("--data-dir", type=Path, required=True, help="Input heatmap_data/game_XXX directory")
    parser.add_argument("--output-dir", type=Path, default=None, help="Output directory for viewer")
    
    args = parser.parse_args()
    
    out_dir = args.output_dir if args.output_dir else args.data_dir.parent.parent / "dashboards" / args.data_dir.name
    run_detailed_analysis_pipeline(args.data_dir, out_dir)
