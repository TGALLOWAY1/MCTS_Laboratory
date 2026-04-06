import json
from pathlib import Path
import sys

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analytics.tournament.trueskill_rating import TrueSkillTracker

def compute_trueskill(jsonl_path: Path):
    tracker = TrueSkillTracker()
    
    with open(jsonl_path, 'r') as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            game_data = json.loads(line)
            seat_scores = game_data.get('final_scores', {})
            seat_assignment = game_data.get('seat_assignment', {})
            agent_scores = {seat_assignment[seat]: score for seat, score in seat_scores.items()}
            tracker.update_game(agent_scores)
            
    print(f"Processed {idx+1} games.")
    print("\nFinal TrueSkill Leaderboard:")
    print("=" * 60)
    print(f"{'Rank':<5} | {'Agent':<25} | {'TrueSkill (Conservative)':<25}")
    print("-" * 60)
    
    leaderboard = tracker.get_leaderboard()
    for entry in leaderboard:
        # We merge 1 and 2 if they are clones, but for now we print exact
        print(f"{entry['rank']:<5} | {entry['agent_id']:<25} | {entry['conservative']:.3f} (μ: {entry['mu']:.2f}, σ: {entry['sigma']:.2f})")
        
    print("=" * 60)
    
    # Let's save a beautiful markdown file
    out_md = PROJECT_ROOT / "docs" / "trueskill_final.md"
    with open(out_md, 'w') as f:
        f.write("# Final TrueSkill Leaderboard (254 Games)\n\n")
        f.write("| Rank | Agent | Conservative TrueSkill (μ - 3σ) | μ (Mean) | σ (Uncertainty) |\n")
        f.write("|------|-------|-------------------------------|----------|-----------------|\n")
        for entry in leaderboard:
            f.write(f"| {entry['rank']} | `{entry['agent_id']}` | **{entry['conservative']:.3f}** | {entry['mu']:.3f} | {entry['sigma']:.3f} |\n")
            
    print(f"\nWritten markdown leaderboard to: {out_md}")

if __name__ == "__main__":
    compute_trueskill(Path("arena_runs/20260402_223205_565018a4/games.jsonl"))
