# Feature Specification: Cascade Sweep Fix

**Feature Branch**: `feature/2-cascade-sweep-fix`  
**Created**: 2026-05-04  
**Status**: Draft  
**Input**: User description: "the leader gets the very high score, but 2nd place does not or 3rd and so on which we desired in the sequence — resolve the cascade sweep so that after the leader finishes, the camera cascades down through P2, P3, etc."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Leader Finish Focus (Priority: P1)

When the race leader crosses the finish line on the final lap, the system assigns maximum focus priority (+10,000 pts) to the leader during the second half of their final lap, ensuring the camera is locked to the leader as they approach the chequered flag.

**Why this priority**: The leader crossing the line is the single most important narrative moment in any race broadcast. This currently works correctly and must not regress.

**Independent Test**: Can be tested by mocking a participant with `current_lap == laps_in_event`, `race_position == 1`, and `lap_distance >= track_length / 2` and verifying a +10,000 sequence bonus is returned.

**Acceptance Scenarios**:

1. **Given** a 13-lap race with the leader on lap 13 past the halfway point, **When** scores are calculated, **Then** the leader receives a +10,000 sequence bonus and all other drivers receive 0 sequence bonus.
2. **Given** the leader has not yet reached the halfway point of the final lap, **When** scores are calculated, **Then** no sequence bonus is awarded to any driver.

---

### User Story 2 — Cascade Sweep Activation (Priority: P1)

When the leader's `current_lap` exceeds `laps_in_event` (i.e. they have crossed the finish line and their lap counter has incremented past the race distance), the system activates a "Cascade Sweep" mode. In this mode, only **one** driver at a time receives a massive +5,000 sequence bonus, starting with the highest-placed driver who has not yet finished.

**Why this priority**: This is the core bug. After the leader finishes, the sweep never activates for P2/P3/etc., leaving the camera without strong directional guidance during the critical finish sequence.

**Independent Test**: Can be tested by simulating a full grid where P1 has finished (`current_lap > laps_in_event`) and P2–P17 are still racing. Verify that exactly one driver (P2) receives the +5,000 bonus, and all others receive 0.

**Acceptance Scenarios**:

1. **Given** the leader has finished (`current_lap > laps_in_event`), **When** scores are calculated for the full grid, **Then** the sweep mode activates and exactly one driver (the highest-placed unfinished driver) receives +5,000 pts.
2. **Given** P1 and P2 have both finished, **When** scores are calculated, **Then** only P3 (the next highest-placed unfinished driver) receives the +5,000 bonus.
3. **Given** sweep mode is active but no unfinished drivers remain, **When** scores are calculated, **Then** no sequence bonus is awarded to anyone.

---

### User Story 3 — Dwell After Finish (Priority: P2)

When the currently focused sweep target crosses the finish line, the system continues to hold focus on them for a configurable dwell period (default 1.0 seconds, tunable from the GUI) before moving the sweep target to the next highest-placed unfinished driver.

**Why this priority**: Provides a natural "finish moment" for each driver before the camera moves on. Without it, the camera snaps away the instant a driver crosses the line, which feels jarring on broadcast.

**Independent Test**: Can be tested by simulating P2 finishing while they are the active sweep target, then verifying that P2 retains the +5,000 bonus for the dwell period and P3 only receives it after the dwell expires.

**Acceptance Scenarios**:

1. **Given** P2 is the active sweep target and just crossed the finish line, **When** scores are calculated within the dwell window, **Then** P2 still receives +5,000 pts.
2. **Given** P2 finished more than `sweep_dwell_time` seconds ago, **When** scores are calculated, **Then** P3 (the next unfinished driver) receives the +5,000 bonus and P2 receives 0.
3. **Given** the dwell time is changed from 1.0s to 3.0s via the GUI tuning panel, **When** the sweep target finishes, **Then** they hold focus for 3.0 seconds before cascading.

---

### Edge Cases

- What happens when multiple drivers cross the finish line on the exact same scoring tick? The system should process them in race position order (lowest position number first) and immediately cascade to the next unfinished driver.
- What happens when a driver is inactive (disconnected/retired) during the sweep? They should be excluded from sweep target eligibility entirely.
- What happens when `laps_in_event` is 0 (time-based replay)? The system should fall back to `timeline_laps_in_event` parsed from the replay log footer. If both are 0, no sequence bonus should be awarded.
- What happens if the replay log was not loaded? `timeline_laps_in_event` remains 0 and the sweep never activates — this is safe default behaviour.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST activate the cascade sweep mode when the race leader's `current_lap` exceeds the total laps in the event.
- **FR-002**: System MUST assign the +5,000 sequence bonus to exactly one driver at a time — the highest-placed driver who has not yet finished the race.
- **FR-003**: System MUST detect sweep activation and select the sweep target **within the same scoring tick** that the leader finishes, not on a subsequent tick.
- **FR-004**: System MUST hold focus on a finishing driver for the configured dwell time before cascading to the next eligible driver.
- **FR-005**: System MUST exclude finished drivers (past their dwell window) from sweep target eligibility.
- **FR-006**: System MUST exclude inactive drivers from sweep target eligibility.
- **FR-007**: System MUST fall back to `timeline_laps_in_event` when primary telemetry reports 0 laps in the event.
- **FR-008**: System MUST NOT break the existing +10,000 leader final lap bonus (US1 from feature/1-final-lap-sequence).

### Key Entities

- **Participant**: A driver on the grid. Key attributes: `name`, `race_position`, `current_lap`, `lap_distance`, `is_active`.
- **Sweep Target**: The single participant currently receiving the +5,000 cascade bonus. Only one sweep target can exist at any time.
- **Finished Participants**: A registry of drivers who have crossed the finish line, keyed by name with their finish timestamp as the value.

## Assumptions

- The `current_lap` field uses 1-indexed `mCurrentLap` from the AMS2 shared memory (established in feature/1-final-lap-sequence).
- The replay log footer `Leader Laps Completed: N` is normalized to `N-1` by the timeline parser (established in feature/1-final-lap-sequence).
- The sweep dwell time is owned by `ScoringEngine.sweep_dwell_time` and is writable from the GUI tuning panel.
- The race position ordering from telemetry is authoritative and does not need re-validation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the leader finishes, the second-placed driver receives a non-zero sequence bonus within 1 scoring tick (200ms).
- **SC-002**: At any point during the cascade sweep, exactly one driver has a non-zero sequence bonus.
- **SC-003**: The cascade correctly progresses through P2 → P3 → P4 → ... as each driver crosses the finish line, with zero skipped drivers.
- **SC-004**: All existing unit tests (110 tests) continue to pass without modification (anti-regression).
- **SC-005**: The bug is reproducible via a deterministic unit test before the fix, and the test passes after.
