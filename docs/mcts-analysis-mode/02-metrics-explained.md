# MCTS Metrics Explained

When you navigate through the MCTS Diagnostics panel, you will see a variety of metrics and charts. Here is what they mean and how to interpret them:

## Core Statistics (Top Row)
- **Simulations**: The total number of MCTS iterations (rollouts/evaluations) performed before settling on an action.
- **Time Spent**: The actual wall-clock time the agent spent thinking on this move, in milliseconds.
- **Speed**: Simulations per second. A drop in this number might indicate memory pressure or a very deep search tree dragging down Pyodide execution.
- **Entropy**: Policy Entropy. See below.
- **Max Depth**: The deepest branch the agent explored in the search tree.

## Root Policy & Q-Values (Bar Chart)
This chart displays the top 20 candidate moves evaluated at the root node.
- **Gray Bars (Visits)**: How many times the agent simulated a particular move. Higher visits correspond to higher confidence in the move.
- **Blue Bars (Q-Mean)**: The empirical expected win rate (or expected reward) of the move, ranging from 0 to 1. 

**Interpretation**: MCTS selects the move with the highest visit count. Usually, this corresponds to the move with the highest Q-Mean, but the UCB1 formula mixes exploration and exploitation, so a slightly lower Q-Mean move with huge visits is often the chosen "safe" line.

## Convergence & Entropy Trace (Line Chart)
This traces the "thought process" of the agent *while* it was thinking about a single move. We sample the state of the tree periodically during the search time budget limit.
- **Best Move Q-Mean (Blue Line)**: Tracks the Q-value of the most-visited move over time. If this line wildly oscillates right until the time limit, the agent was confused and didn't converge. If it is flat, the agent found its answer quickly.
- **Policy Entropy (Purple Step Line)**: Tracks confidence. High entropy (e.g., > 3.0) means the visits are spread evenly across many moves (uncertainty). Low entropy (e.g., < 1.0) means the agent heavily favored a single forced line. As the search converges, entropy should decrease.

## Search Tree Depth (Histogram)
This chart plots the distribution of *all expanded nodes* in the search tree by their depth relative to the root.
- **Wide & Shallow**: In the early game, the agent expands many legal moves at depth 1 or 2.
- **Narrow & Deep**: In the late game, or during forced tactical sequences, you will see a "long tail" stretching rightward to high depths (e.g., Depth 15+). 
- Measuring the branching factor and max depth helps diagnose if your heuristic or rollout policy is guiding the search effectively or thrashing randomly.

## Game Flow / Entropy History (Line Chart)
Unlike the Convergence trace, this chart tracks **Policy Entropy across the entire game**. 
- The X-axis is the turn number. 
- You will typically see high entropy at the start of the game (many viable opening moves), dipping in the mid-game as tactical fights force specific responses, and plunging near the endgame when moves become completely deterministic. Peaks in this chart denote critical, highly complex turns.
