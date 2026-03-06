# How to Use MCTS Analysis Mode

Welcome to the MCTS Analysis Mode! This feature transforms the Blokus RL agent into an interactive research laboratory, allowing you to peek inside the "brain" of the MCTS engine as it makes decisions.

## Enabling the Mode
1. In the **Game** (or **Research**) panel on the right side of the screen, locate the **Enable MCTS Diagnostics** toggle.
2. Check the box to enable telemetry collection.
3. Once enabled, every AI move played by the `FastMCTSAgent` will attach a deep trace of its search process to the game history.

*(Note: Enabling this feature incurs a small performance overhead as the agent samples its internal tree state during search. Keep it off during high-speed self-play or normal casual matches unless you are actively debugging or analyzing the agent's behavior.)*

## Navigating the Trace
Once a game has begun and MCTS moves have been recorded:
1. Switch the right panel tab to **MCTS Diagnostics**.
2. Use the **MCTS Step Explorer** slider to scrub backward and forward through the history of AI decisions.
3. The charts below will automatically update to reflect the snapshot of the MCTS tree at the moment that specific move was chosen.

## Exporting Data
- Click the **Export Trace JSON** button in the MCTS Step Explorer to download a complete raw JSON dump of the game's MCTS diagnostics. 
- You can use this file for offline analysis, python scripting (e.g. producing matplotlib graphs), or attaching to bug reports when the agent makes a questionable move.
