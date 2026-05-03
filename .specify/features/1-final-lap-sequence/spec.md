# Feature Specification: Final Lap Sequence & Cooldown Sweep

**Feature Branch**: `1-final-lap-sequence`  
**Created**: 2026-05-03  
**Status**: Draft  
**Input**: User description: "insert the hints from ther analyser step into the main auto director. lets startw ith the data about number of laps and the routine for the last lap and focussing on the leader"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Leader Final Lap Coverage (Priority: P1)

As a viewer, I want the Auto Director to automatically cut to a trackside camera on the Race Leader during the second half of the final lap, so that I never miss the race winner crossing the finish line, regardless of other battles on track.

**Why this priority**: Capturing the winner is the most important broadcast requirement of any motorsport race. If the director is distracted by a midfield battle at the finish line, it is a broadcast failure.

**Independent Test**: Can be fully tested by running a short race/replay and verifying that the director forces the camera to the leader at the halfway point of the final lap.

**Acceptance Scenarios**:

1. **Given** the race leader begins the final lap, **When** the elapsed time on that lap reaches 50% of the leader's previous lap pace, **Then** the Auto Director switches to the leader.
2. **Given** the director is focused on the leader during the final lap sequence, **When** a high-scoring battle occurs elsewhere, **Then** the director ignores the battle and maintains focus on the leader.

---

### User Story 2 - Cascading Cooldown Sweep (Priority: P2)

As a viewer, after the leader crosses the finish line, I want the director to immediately cut to the next highest-placed driver who is approaching the finish line, so that I can watch the rest of the field take the checkered flag sequentially.

**Why this priority**: Once the leader finishes, the story shifts to the remaining podium and points battles resolving at the line.

**Independent Test**: Can be fully tested by watching the conclusion of a race and verifying that the camera steps down the grid (P2, P3, P4) as each car crosses the line.

**Acceptance Scenarios**:

1. **Given** the race leader crosses the finish line, **When** 1.0 second has passed, **Then** the Auto Director switches to the active driver with the highest position who has not yet finished.
2. **Given** the director is sweeping the grid, **When** the targeted driver finishes, **Then** the director holds for 1.0 second before hunting for the next driver.

### Edge Cases

- What happens if the next highest placed driver has already crossed the line before the camera can switch to them?
- How does the sequence behave in a timed race where "total laps" is not known until the timer expires?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST determine the total laps for the event (using Shared Memory or the UDP fallback).
- **FR-002**: System MUST calculate the midpoint timestamp of the leader's final lap based on their previous lap time.
- **FR-003**: System MUST execute a high-priority "Leader Lap Trackside" override at the final lap midpoint to lock onto the leader.
- **FR-004**: System MUST trigger a "Cooldown Sweep" state once the leader completes their final lap.
- **FR-005**: System MUST evaluate the remaining participants in the Cooldown Sweep state and select the highest-placed driver still racing.
- **FR-006**: System MUST expose the post-finish dwell time in the Tuning GUI, defaulting to 1.0 seconds.

### Key Entities

- **Timeline Engine State**: Tracks if the race is active or in cooldown/finish mode.
- **Finished Drivers Dictionary**: Tracks which participants have completed the race to exclude them from the sweep.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of races/replays conclude with the camera on the leader crossing the finish line.
- **SC-002**: Cooldown sweep successfully captures at least the top 3 finishers (P1, P2, P3) if they are appropriately spaced out on track.
- **SC-003**: Camera sequence perfectly mirrors the `generate_finish_sequence` logic from the legacy V3 Analyser.
