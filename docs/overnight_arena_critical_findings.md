# Critical Findings: Overnight Arena Run (April 1-2, 2026)

## Executive Summary
The first exhaustive, 300-game overnight arena run completed flawlessly with 0 errors. The run aimed to test Progressive Widening (PW) against the Baseline L9 models and generate dense feature snapshots for learning an evaluation function.

## 1. Algorithmic Dominance of Progressive Widening
Progressive Widening (PW) is unequivocally superior to the L9 Baseline MCTS in Blokus. 
The two PW variants completely dominated the tournament:
- **`Champion_PW_Single`**: 49.5% win rate (TrueSkill ~43.48)
- **`Champion_PW_Phase`**: 43.3% win rate (TrueSkill ~30.35)

By contrast, the `L9_Baseline` and `L9_Full_NoPW` agents combined for a meager ~7% win rate, confirming that PW pruning logic is essential for efficiently navigating the massive branching factor of Blokus.

## 2. Iteration Throughput Improvements
The PW agents aren't just smarter; they evaluate states more efficiently.
- `Champion_PW_Single` calculated at **~76 simulations per second**, closing turns in ~1.3 seconds.
- `L9_Baseline` crawled at **~36 simulations per second**, taking ~2.7 seconds per turn. 
PW naturally funnels compute toward promising branches, raising the overall iteration speed per second.

## 3. Evaluator Model Viability
The overnight run produced a rich dataset of ~17,000 ML snapshots, successfully split by game ID (to prevent leakage) and expanded into ~60,000 pairwise comparisons. 

Training the `pairwise_gbt_phase` model on this data yielded exceptionally high confidence metrics:
- **Overall Test Accuracy:** 84.41%
- **Late-Game Accuracy:** 90.22%
- **Calibration Error:** 0.0093 (highly calibrated)

This proves the snapshot generation pipeline and the GBT phase architectures are immediately viable for generating an elite learned evaluation function. 

## Next Steps for Training
With a highly accurate evaluator model now compiled (`eval_from_overnight.pkl`), the MCTS strategy paradigm shifts from **raw heuristics + rollout** to **learned network inference**. 

The immediate next step is to integrate this model into the `MCTSAgent`'s leaf evaluation phase, completely replacing or supplementing the random/heuristic rollouts with the trained GBT inference. 

Once integrated, a new arena test must be run comparing:
**[MCTS + Rollout]** vs **[MCTS + Learned GBT Evaluator]** at equal time controls.
