# Implementation Plan: Logarithmic Closing Speed & Session Time

## Proposed Architecture

### 1. Telemetry Core (`telemetry_provider.py`)
- Introduce a stateful `self._gap_history` dictionary and `self._last_poll_time` in `__init__`.
- In `poll()`, calculate `closing_speed = (previous_gap - current_gap) / dt`.
- Apply a lightweight Exponential Moving Average (EMA) to `closing_speed` to smooth out telemetry jitter over the 200ms polling rate (e.g. `alpha = 0.3`).
- Inject `closing_speed` into each participant's data dictionary.
- Add an `_extract_session_info(sm)` method to pull `mEventTimeRemaining` and `mCurrentTime` from the shared memory.

### 2. Scoring Engine (`scoring_engine.py`)
- Modify `_calculate_close_racing_bonus()` to revert to the linear curve formula `(max_gap - gap) / divisor`.
- Add the `closing_speed` directly to the `base_bonus` to cleanly boost or penalize the score linearly based on how fast they are catching up or falling away.
- Limit the maximum possible score to 50 so it doesn't overflow or dominate all other weights.

### 3. User Interface (`main.py`)
- Add a `lbl_session_time` to the top status bar.
- In `_tick()`, query the new session info and explicitly show "Rem: null" if no session limit exists, and show Elapsed.
- Update the Grid Treeview to include a new column for `CloseSpd` to observe the metric in real-time.

### 4. Testing (TDD)
- Update `test_telemetry_provider.py` to enforce the EMA calculation and delta history logic.
- Update `test_scoring_engine.py` to validate the new asymptotic mathematical curve under various mock edge cases (0 gap, massive closing speed, negative closing speed).
