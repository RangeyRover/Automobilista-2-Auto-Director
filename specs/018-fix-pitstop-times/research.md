# Technical Research: Standalone Server Flywheel Pitstop Times

This document outlines the technical research, findings, and architectural decisions for resolving pitstop timing inaccuracies in the standalone SHM leaderboard server.

## Findings & Evaluation

### Current Execution Ordering
In `tools/shm_leaderboard_server.py`, the `correlate_drivers` function performs correlation in two passes:
1. **Pass 1 (Participant Correlation Loop)**: Iterates over the raw participant array. It extracts raw `mCurrentTime` and directly computes:
   ```python
   driver["_pit_time"] = current_time - pit_entry_times[driver_name]
   ```
2. **Pass 2 (Leaderboard Calculations)**: Runs after all drivers have been correlated. It computes `leader_dist` and then runs the `PhysicsFlywheel` to stabilize `current_time`:
   ```python
   if flywheel is not None:
       current_time = flywheel.process(current_time, leader_dist)
   ```

Because Pass 1 uses the raw, unstabilized `mCurrentTime` to calculate both the entry timestamp and the active duration, any timing anomalies or camera-switch jumps in shared memory cause `_pit_time` to jump instantly.

### Solution Alternatives

#### Option A: Defer `_pit_time` Calculation (Chosen)
- **Design**: Move the `_pit_time` calculation logic from Pass 1 (raw participant loop) to Pass 2 (leaderboard loop), which runs *after* `current_time` has been stabilized by the flywheel.
- **Pros**:
  - Extremely simple and non-invasive refactoring.
  - Guarantees `_pit_time` uses the exact same stabilized clock as distance-time gaps.
  - Zero state accumulation overhead.
- **Cons**: Requires deferring the check until the second loop.

#### Option B: Delta-Accumulation inside `PitTracker`
- **Design**: Refactor the main app's `PitTracker` and the server's tracking dictionaries to accumulate frame-to-frame delta time (`dt`) and filter out deltas $> 5$s.
- **Pros**: Immune to large clock snaps/resyncs.
- **Cons**: Rejected by user preference for Option A/Step 1 (using flywheel-stabilized time directly to keep the clock source fully synchronized and unified across components).

## Decision & Rationale
We will implement **Option A**. By moving the `_pit_time` calculation downstream in `correlate_drivers` to the loop that has access to the flywheel-processed `current_time`, we ensure that both entry times and active pit durations are calculated using the stabilized clock, resolving the jumping values.
