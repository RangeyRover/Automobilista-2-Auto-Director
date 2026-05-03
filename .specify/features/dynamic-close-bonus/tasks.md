# Tasks: Dynamic Close Bonus & Session Time

## Phase 1: Test-Driven Development (TDD)
- `[x]` Update `tests/test_scoring_engine.py` to assert the reverted linear math `(max_gap - gap) / divisor` and the additive closing bounds.
- `[x]` Update `tests/test_telemetry_provider.py` to assert `closing_speed` EMA calculation and session time extraction logic.

## Phase 2: Telemetry Implementation
- `[ ]` Modify `core/telemetry_provider.py` to maintain a `_gap_history` and calculate the EMA of `closing_speed` over `dt`.
- `[ ]` Implement `_extract_session_info(sm)` in `core/telemetry_provider.py` to yield `session_time` metrics.

## Phase 3: Scoring Engine Implementation
- `[x]` Modify `core/scoring_engine.py` to consume `closing_speed` and apply it purely additively to the reverted linear `Close` bonus math curve.

## Phase 4: GUI Implementation
- `[ ]` Update `main.py` GUI to format and display `lbl_session_time` in the top bar.
- `[ ]` Update `main.py` Treeview to append the `CloseSpd` column and populate it from the participant dictionary.

## Phase 5: Verification
- `[ ]` Ensure 100% of Pytest tests pass cleanly.
- `[ ]` Confirm GUI correctly binds the session time without crashing.
