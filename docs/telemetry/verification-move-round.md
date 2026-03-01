# Verification: Move vs Round

Update: 2026-03-01  
**Verification checklist for round alignment.**

## 1. Manual Verification Scenarios (UI)

1.  **Open the Analysis Dashboard (`/analysis`).**
2.  **Toggle between MOVE and ROUND modes.**
    - Confirm the charts switch between `turn` and `round` x-axis labels.
    - Confirm the curves align by the same x-coordinate in Round mode (Series for RED, BLUE, etc. should start at x=1 simultaneously).
3.  **Confirm the slider Move label.**
    - Label `Move 1 / N` should represent the 1-based index (formerly `Turn`).
4.  **Confirm the Reference Line positioning.**
    - In Move mode, the Reference Line should follow the slider index exactly (e.g. x=5).
    - In Round mode, it should snap to the corresponding round (e.g. x=2 for moves 5–8) via `Math.floor((currentSliderTurn-1) / 4) + 1`.

## 2. Telemetry Verification (API/Data)

1.  **Run a game and check `StepLog`.**
    - `StepLog` entries in `results/steps.jsonl` should now include `round_index`, `position_in_round`, and `seat_index`.
2.  **Check `move_records` API (`/game/{id}/replay` or `XHR`).**
    - The JSON response should include `roundIndex`, `positionInRound`, and `seatIndex` for both placements and passes.
3.  **Verify Pass scenarios.**
    - `_record_pass()` must correctly increment `sequenceIndex` and derive `roundIndex` from it, ensuring the round counter doesn't stall when a player has no moves.
4.  **Verify save/load compatibility.**
    - Load a legacy game (without the new fields) and confirm it still works.
    - Confirm that the `WebWorkerGameBridge.get_state` backfill logic populates missing indices on-the-fly (`move_index`, `round_index`, etc.).

## 3. Automated Test Verification

Confirm that `tests/test_worker_bridge_save_load.py` passes:
```bash
./.venv/bin/python3 -m pytest tests/test_worker_bridge_save_load.py
```
This verifies that:
- history entries have all required keys (additive).
- indices are present and correct (`move_index == i`).
- round/position logic is consistent.
