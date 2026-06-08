# Feature Specification: Standalone Server Flywheel Pitstop Times

**Feature Branch**: `018-fix-pitstop-times`  
**Created**: 2026-06-08  
**Status**: Draft  
**Input**: User description: "Pitstop time can be inaccurate jumping up and doiwn investiagte as part of the next branch. It may have part of the same calculation problem that the leaderboard had"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Standalone SHM Leaderboard Tool Pitstops (Priority: P1)

As a developer or user running the standalone SHM leaderboard server (`tools/shm_leaderboard_server.py`), I want pit times (`_pit_time`) in the correlated leaderboard payload to be stable and free from camera-switch or replay-freeze raw time jumps.

**Why this priority**: Highly critical because the standalone tool is used for diagnostics and overlay development, so it must produce correct telemetry matching the main application's stabilized master clock.

**Independent Test**: Verify that the `_pit_time` field in the broadcasted leaderboard JSON remains stable during camera transitions and replay time freezes.

**Acceptance Scenarios**:

1. **Given** a driver is in the pits on the standalone server,  
   **When** the camera view changes or a brief replay freeze occurs,  
   **Then** the `_pit_time` field in the output payload does not exhibit sudden spikes or jumps, but tracks the stabilized master clock.

---

### User Story 2 - Consistent Timing Across Dashboard Components (Priority: P2)

As a broadcast overlay viewer, I want the pitstop duration shown on the web HUD to be consistent with the leaderboard gaps and timing data.

**Why this priority**: Consistency between different HUD overlay widgets prevents confusion during broadcasts.

**Independent Test**: Verify that both the timing screen and the pit stop event duration use the same flywheel-stabilized time source.

**Acceptance Scenarios**:

1. **Given** a driver in the pits,  
   **When** their pitstop duration is broadcasted,  
   **Then** the duration matches the elapsed stabilized game time.

---

### Edge Cases

- **Flywheel Resyncs**: When the physics flywheel force-resyncs to the game clock after a prolonged anomaly, any resulting step-change in master clock time must be handled gracefully.
- **Lap Transitions**: When a driver completes a lap while exiting the pits, the lap count increment must not disrupt the pit duration calculation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The standalone SHM leaderboard server's `correlate_drivers` function MUST compute participant `_pit_time` using the flywheel-stabilized `current_time` rather than raw `mCurrentTime`.
- **FR-002**: The `correlate_drivers` function MUST process `mCurrentTime` through the `PhysicsFlywheel` instance prior to calculating time-based properties for participants, including gaps and pitstop times.
- **FR-003**: The dashboard `PitTracker` class MUST use the flywheel-stabilized game time provided by the telemetry provider to ensure consistency with the leaderboard.
- **FR-004**: The system MUST preserve all existing capabilities, including backward compatibility in the standalone server's `pit_entry_times` dictionary.

### Key Entities

- **correlate_drivers**: The pure correlation function in the standalone leaderboard server that calculates participant properties.
- **PhysicsFlywheel**: Responsible for filtering and stabilizing the game time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Standalone server `_pit_time` values must be calculated using flywheel-stabilized time.
- **SC-002**: Standalone server `_pit_time` values must be free of raw time jumps during replay freezes and anomalies.
- **SC-003**: All 309 existing unit tests must pass successfully, and new tests must verify correct stabilized pitstop calculations.
