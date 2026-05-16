# Feature Specification: Per-Car Spline Logic for Leaderboard Gaps

**Feature Branch**: `1-fix-leaderboard-spline`  
**Created**: 2026-05-16  
**Status**: Draft  
**Input**: User description: "Implement per-car spline logic for time_gap_to_leader in telemetry_provider.py to fix leaderboard tracking when leader changes, including tests"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stable Leaderboard After Overtakes (Priority: P1)

As a broadcast director, I want the time gap to the leader to remain accurate and stable immediately after the lead car is overtaken, so that the broadcast leaderboard does not display broken or massive gaps (e.g., +30s) for cars fighting for the lead.

**Why this priority**: The primary bug is that the current global spline track history does not account for the new leader's distance properly, breaking the core functionality of the broadcast overlay.

**Independent Test**: Can be fully tested by simulating an overtake for P1 and verifying that `time_gap_to_leader` for the new P2 is calculated against the physical history of the *new* P1.

**Acceptance Scenarios**:

1. **Given** Car A is leading and Car B is 5 seconds behind, **When** Car A crashes and Car B overtakes them to become the new leader, **Then** Car B's `time_gap_to_leader` must instantly become `0.0`, and Car A's gap must correctly reflect the time since Car B was at Car A's current track position.
2. **Given** a 32-car grid, **When** gaps are calculated, **Then** the calculations must use the per-car spline belonging to the driver *currently in P1*, not a global "furthest distance" spline.

---

### User Story 2 - Comprehensive Testing Suite (Priority: P2)

As a developer, I want a comprehensive suite of unit tests for the gap calculation logic to ensure that regressions do not occur in the future when modifying telemetry processing.

**Why this priority**: Complex mathematical interpolation and state tracking are prone to edge-case bugs; a robust test suite is necessary for long-term stability.

**Independent Test**: Can be fully tested by running `pytest` or `unittest` over isolated mock telemetry data without requiring the live AMS2 game engine.

**Acceptance Scenarios**:

1. **Given** mock telemetry data with known physical distances and constant speeds, **When** the `_calc_live_time_gaps` function processes the data, **Then** the output gaps must perfectly match the mathematically expected times.
2. **Given** an edge case where the leader's spline is empty or has insufficient distance history to cover the follower's position, **When** calculating gaps, **Then** the system must gracefully fall back to the physical distance/speed estimation.

### Edge Cases

- What happens when a track session resets, and `true_distance` drops to 0? (The spline for that car must clear).
- What happens if the gap to the leader exceeds the size of the tracked spline memory? (The spline array limit must be large enough to hold at least a full lap or multi-lap history, e.g. 5000 points).
- What happens when a follower is further down the track than the leader's recorded history (e.g., a glitch or a massive multi-lap lead)? (It should return `None` from the spline search and fallback to the estimation).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST track an individual `(true_distance, game_time)` historical spline array for all 32 participant indices.
- **FR-002**: The system MUST identify the current leader (the active participant with the highest `true_distance` or lowest `race_position`).
- **FR-003**: The system MUST calculate `time_gap_to_leader` for all participants by interpolating their `true_distance` against the *current leader's* historical spline array.
- **FR-004**: The system MUST clear a participant's spline if their `true_distance` drops significantly (e.g., session restart).
- **FR-005**: The system MUST include deterministic unit tests validating the gap calculations for normal following, overtakes, and fallback logic.

### Key Entities 

- **Car Spline**: A collection of data points `(true_distance, game_time)` recorded at intervals (e.g., every 5 meters) for a specific driver.
- **True Distance**: The absolute distance travelled by a car since the session started, calculated as `laps_completed * track_length + lap_distance`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Overtakes for P1 result in the new leader having a `0.0` time gap within 1 scoring tick.
- **SC-002**: Spline-based gap calculations do not raise unhandled exceptions during array bounds checks or empty states.
- **SC-003**: A dedicated test file (e.g., `test_spline_gaps.py`) executes successfully and covers 100% of the new `_calc_live_time_gaps` logic.
- **SC-004**: System handles up to 32 parallel splines with max 5000 points each without causing memory leaks or tick loop execution times > 16ms.
