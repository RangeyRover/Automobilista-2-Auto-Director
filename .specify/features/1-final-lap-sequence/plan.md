# Final Lap Sequence & Cooldown Sweep Implementation Plan

This Software Design Document (SDD) outlines the architecture for integrating the final lap and finish line sequence into the V4 Auto Director. The implementation prioritizes TDD, granular task definition, and decoupling stateful sequencing logic from the stateless scoring engine.

## Proposed Changes

### Core Sequence Engine

We will introduce a new module to handle stateful timeline events (overrides) that supersede the live scoring engine.

#### [NEW] `core/sequence_engine.py`
A state machine that tracks the race finish sequence:
- `evaluate(session_info, track_info, participants)` -> Returns `target_participant_id` if a sequence is active, else `None`.
- **State: Standby**: Listens for the leader to begin the final lap (`current_lap == laps_in_event`).
- **State: Leader Trackside**: Triggers when the leader crosses 50% track distance on the final lap. Forces camera to the leader.
- **State: Cooldown Sweep**: Triggers when the leader finishes (`current_lap > laps_in_event`). Keeps a `finished_participants` set and a `last_sweep_time`. Evaluates the grid and forces the camera to the highest-placed driver who is still racing. Dwells for the configured `sweep_dwell_time` before stepping down the grid.

### GUI & Configuration

#### [MODIFY] `main.py`
- Add `Sweep Dwell (s)` to the tuning UI, bound to `sweep_dwell_time` (default 1.0s).
- Instantiate `SequenceEngine` inside `AutoDirectorApp`.
- Modify `_tick()`:
  - Call `self.sequence.evaluate()`.
  - If it returns a target, bypass `self.scorer.get_best_focus()` and force the camera to the target.
  - Update UI labels to reflect sequence state (e.g., `Director: SWEEPING`).

### Telemetry Enhancements

#### [MODIFY] `core/telemetry_provider.py`
- Ensure `track_length` is robustly passed into the `_tick` loop for distance calculations.

## Verification Plan

### Automated Tests (TDD)
- We will strictly follow Test-Driven Development.
- `test_sequence_engine.py`:
  - `test_detects_final_lap_midpoint`: Mocks telemetry at 49% and 51% distance to ensure trigger.
  - `test_cooldown_sweep_cascades`: Simulates cars finishing and verifies the engine yields the correct next target.
  - `test_cooldown_dwell_time`: Ensures the engine holds the target for the configured dwell duration.

### Manual Verification
- Launch AMS2 in Replay Mode for a short race finish.
- Verify the director snaps to the leader on the final lap.
- Verify the cascading camera changes as each car finishes.
