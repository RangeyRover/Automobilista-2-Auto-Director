# Task Breakdown: Per-Car Spline Logic for Leaderboard Gaps

**Feature**: `1-fix-leaderboard-spline`  
**Dependencies**: None  

## Implementation Tasks

### 1. Architectural Refactor (`core/telemetry_provider.py`)
- **Action**: Replace the global `self._leader_spline` list with a dictionary of lists: `self._car_splines: dict[int, list[tuple[float, float]]]` in `__init__`.
- **Action**: Update `_calc_live_time_gaps` to identify the current leader's index (`active[0][0]`), and isolate their specific spline.
- **Action**: Modify the recording loop to record the `(true_distance, game_time)` tuple into the personal spline of *every* active participant (so that if they become the leader, their history is available).
- **Action**: Ensure the distance-fallback gap logic uses the current leader's distance instead of the old global distance.
- **Action**: Ensure `get_spline_time_at_distance` takes the `leader_spline` array as an argument instead of referencing a global state.

### 2. TDD Validation (`test_spline_gaps.py`)
- **Action**: Create a new test suite to cover `_calc_live_time_gaps`.
- **Action**: Test Case 1: Simple linear following (Car A is 5m ahead of Car B, constant speed).
- **Action**: Test Case 2: Overtake Simulation (Car B overtakes Car A; Car B's gap drops to 0, Car A's gap calculates correctly against Car B's history).
- **Action**: Test Case 3: Session Reset (Verify `true_distance` dropping clears the spline).
- **Action**: Test Case 4: Missing History Fallback (Follower is 5000m behind, but leader spline only has 100m of history; should fall back to distance/speed equation without crashing).

### 3. Verification & Analysis
- **Action**: Execute `test_spline_gaps.py` to prove functionality.
- **Action**: Confirm there are no regression failures in `test_telemetry_provider.py`.
