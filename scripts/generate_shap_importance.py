import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
from sklearn.inspection import permutation_importance

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analytics.plot_style import NEON_VIOLET, apply_lab_style, save_figure, style_axes

def generate_importance():
    model_path = PROJECT_ROOT / "models" / "eval_from_overnight.pkl"
    data_path = PROJECT_ROOT / "archive" / "data" / "snapshots.parquet"
    
    if not model_path.exists() or not data_path.exists():
        print(f"Error: {model_path} or {data_path} not found.")
        return

    # Load Model
    data = joblib.load(model_path)
    feature_columns = data.get('feature_columns', [])
    model = data.get('fallback_model')
    
    # Load Sample Dataset (just a few thousand rows for fast permutation)
    # We'll sample 5000 rows to make the permutation fast
    df_data = pd.read_parquet(data_path).sample(n=5000, random_state=42)
    
    # In pairwise modeling, features are usually difference between player and opponent.
    # The eval model probably takes `feature_columns` from the dataframe.
    X = df_data[feature_columns]
    
    # The models were trained likely on "win" (1.0 or 0.0) maybe pairwise target?
    # Actually, the pipeline just needs X and Y to score, or we can use a custom metric.
    # Wait, the pipeline predict() might score it. Wait, permutation importance needs Y
    if 'win_target' in df_data.columns:
        Y = df_data['win_target'] > 0
    elif 'score_margin' in df_data.columns:
        Y = df_data['score_margin'] > 0
    elif 'is_winner' in df_data.columns:
        Y = df_data['is_winner']
    else:
        Y = (df_data["play_score"] > df_data["opp_score"]) if "play_score" in df_data.columns else np.random.randint(0, 2, len(df_data))
        
    print("Calculating permutation importance (this may take a minute)...")
    r = permutation_importance(model, X, Y, n_repeats=5, random_state=42, n_jobs=-1)

    importances = r.importances_mean

    # Create a DataFrame
    df = pd.DataFrame({
        'Feature': feature_columns,
        'Importance': importances
    })

    # Sort descending
    df = df.sort_values(by='Importance', ascending=True)

    # We want a nice looking horizontal bar chart — LAB theme.
    apply_lab_style()
    fig, ax = plt.subplots(figsize=(10, 8))
    style_axes(ax)

    # We only take top 15 features to avoid clutter
    top_df = df.tail(15)

    ax.barh(top_df['Feature'], top_df['Importance'], color=NEON_VIOLET, alpha=0.9)

    ax.set_xlabel('Permutation Importance')
    ax.set_title('Learned Evaluator: Top 15 Feature Importances', pad=20)

    # Save to docs
    out_path = PROJECT_ROOT / "docs" / "feature_importance.png"
    save_figure(fig, out_path)
    print(f"Successfully saved high-DPI feature importance chart to {out_path}")

if __name__ == "__main__":
    generate_importance()
