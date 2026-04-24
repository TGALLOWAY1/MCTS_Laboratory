#!/bin/bash

# build_browser_core.sh
# Bundles the pure-python core engine for the Pyodide WebWorker
# Run this whenever changing the python game engine or agents.

echo "📦 Bundling Python core for Pyodide WebWorker..."

# 1. Ensure browser_python directory is up-to-date with backend changes
echo "Syncing backend code to browser_python directory..."
mkdir -p browser_python/engine browser_python/mcts browser_python/agents browser_python/config
cp -R engine/* browser_python/engine/
cp -R mcts/* browser_python/mcts/
cp -R agents/* browser_python/agents/
cp config/challenge_champion_config.json browser_python/config/

# 2. Package into the frontend public directory
echo "Zipping to frontend/public/blokus_core.zip..."
cd browser_python
# Remove old zip if it exists
rm -f ../frontend/public/blokus_core.zip
# Zip the necessary python directories
zip -r ../frontend/public/blokus_core.zip engine/ mcts/ agents/ config/ worker_bridge.py -x "*/__pycache__/*" "*.pyc"

echo "✅ Done! Pyodide code bundle updated."
