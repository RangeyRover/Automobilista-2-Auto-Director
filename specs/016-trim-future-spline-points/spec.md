# Feature Specification: Trim Future Spline Points on Resync and Rewind

**Feature Branch**: `016-trim-future-spline-points`  
**Created**: 2026-06-08  
**Status**: Draft  
**Input**: User request to fix leaderboard time-gap dropouts by trimming future-dated spline points upon flywheel resync and replay rewinds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stable Gaps After Flywheel Resync (Priority: P1)

As a broadcast director, I want the leaderboard time gaps to calculate correctly and not drop out to blank cells when the telemetry provider's master clock recovers from a telemetry glitch (such as a camera transition or loading screen pause).

**Why this priority**: The primary bug is that the drifted flywheel clock contaminates the leader spline with future-dated points. Once the flywheel resyncs, the master clock snaps back to the game clock, but the future points remain in the spline, causing dropouts for all close cars. Trimming the future points immediately resolves this stuck state.

**Independent Test**: Can be fully tested by simulating a telemetry gap where the flywheel drifts forward, then resyncs (setting `did_resync = True`), and verifying that the spline is trimmed of future-dated points and subsequent gaps calculate correctly instead of dropping out.

**Acceptance Scenarios**:

1. **Given** the flywheel master clock has drifted to `475.0` while raw game time is at `448.0`, **When** the flywheel resyncs and snaps back to the game clock at `455.0`, **Then** the spline must discard all recorded points with timestamps $> 455.0$.
2. **Given** a trimmed spline, **When** the next ticks are processed, **Then** new spline points must be recorded successfully and time gaps must calculate normally.

---

### User Story 2 - Support Replay Scrubbing and Rewinding (Priority: P2)

As a user reviewing a replay, I want to be able to rewind or scrub backward in time without breaking the leaderboard gaps.

**Why this priority**: Replay review is a core feature of the Auto Director program. Rewinding the replay must not leave future-dated points in the spline that block future calculations.

**Independent Test**: Can be fully tested by simulating a backward jump in stabilized game time and verifying that any spline points with timestamps greater than the new current time are discarded, enabling correct gap calculations as the replay resumes playing forward.

**Acceptance Scenarios**:

1. **Given** the spline has recorded points up to `475.0`, **When** the game time is rewound to `468.0` (time step is negative), **Then** the spline must discard all points with timestamps $> 468.0$.

---

### Edge Cases

- **Empty Spline After Trim**: What happens if the spline is trimmed so far back that it contains fewer than 2 points (or becomes empty)? 
  - *Resolution*: The system must gracefully fall back to physical distance/speed gap estimation for all follower cars.
- **Floating-point Jitter**: What if the time step is slightly negative due to floating-point noise rather than an actual rewind?
  - *Resolution*: Standard noise is small ($<0.01$s). A threshold of `0.0` is safe since the spline minimum recording interval is `0.5` seconds. Any negative delta should trigger the trim to guarantee safety.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `DistanceTimeSpline` MUST implement a method `trim_future_points(current_time)` that removes all recorded points with timestamps strictly greater than `current_time`.
- **FR-002**: The `TelemetryProvider` MUST invoke `trim_future_points(stable_time)` on the leader spline when `PhysicsFlywheel.did_resync` is `True`.
- **FR-003**: The `TelemetryProvider` MUST invoke `trim_future_points(stable_time)` on the leader spline when `stable_time` is strictly less than the last recorded spline timestamp (`self._leader_spline.times[-1]`).
- **FR-004**: When the spline is trimmed, all subsequent `DistanceTimeSpline` recording and gap interpolation MUST function normally.
- **FR-005**: If the spline becomes empty or has insufficient points ($<2$) after trimming, the system MUST fall back to physical distance/speed gap calculations.

### Key Entities

- **DistanceTimeSpline**: The historical record of the leader's track progress.
- **Stable Time**: The stabilized master clock value returned by the flywheel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Trimming the spline prevents any gap dropouts (evaluating to 0.0) for follower cars that are behind the leader.
- **SC-002**: Trimming the spline of future points takes less than 1ms and does not degrade loop frequencies.
- **SC-003**: Unit tests validate spline trimming for both resync and rewind scenarios, achieving 100% code coverage.
