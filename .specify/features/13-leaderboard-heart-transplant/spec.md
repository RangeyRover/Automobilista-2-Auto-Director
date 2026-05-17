# Feature Specification: Leaderboard Heart Transplant

**Feature Branch**: `13-leaderboard-heart-transplant`
**Created**: 2026-05-17
**Status**: Draft

## Overview

The standalone SHM Leaderboard Tool (`tools/shm_leaderboard_server.py`) has proven a superior time-gap calculation system using distance-time splines, a physics flywheel for camera-swap jitter suppression, and real-time debugging HTML surfaces. This feature transplants those proven components into the main Auto Director program (`main.py` + `core/`) as first-class modules, while simultaneously enforcing a 500-line maximum on all Python files via strangler-pattern decomposition.

## Clarifications

### Session 2026-05-17
- Q: Should the existing 24 flywheel/spline tests be migrated, duplicated, or supplemented with new integration tests for the main program? → A: Existing flywheel tests remain in place (they test the extracted module directly). New TDD integration tests are written before each transplant step to verify the main program's wiring consumes the spline/flywheel correctly. Two layers of coverage without duplication.
- Q: Should the debugging HTML surfaces share the dashboard bridge WebSocket or use a separate port? → A: Single unified WebSocket endpoint — one server, one port. The payload includes both scoring/camera data and diagnostic data (spline, flywheel, leaderboard). Eliminates running two servers and ensures all consumers get the same tick of data.
- Q: Does the 500-line limit count total lines or source-only lines (excluding blanks/comments)? → A: Total lines in file — simple line count, blanks and comments included. No custom tooling needed.
- Q: Should there be a side-by-side comparison phase before the transplant, or a direct swap? → A: Direct swap — the standalone tool's results are already proven. No comparison phase needed; trust the existing test suite and validated behaviour.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Stable Time Gaps in Main Program (Priority: P1)
The main Auto Director currently calculates time gaps using a method that produces multi-second variance during a lap. The proven spline-based system (continuous distance-time recording + linear interpolation) must replace the existing gap calculation, producing time gaps that are stable to within ±0.5 seconds during normal racing.

**Why this priority**: Time gap stability directly affects the scoring engine's ability to identify close battles and trigger camera decisions. Multi-second jitter causes false overtake detections and missed real battles.

**Acceptance Scenarios**:
1. **Given** a replay running at 1x speed with stable telemetry, **When** the main program calculates time gaps for all drivers, **Then** each driver's time gap varies by no more than ±0.5 seconds across a full lap (excluding genuine pace changes).
2. **Given** a camera swap occurs during replay playback, **When** `mCurrentTime` jumps by ~40 seconds, **Then** the physics flywheel suppresses the anomaly and gap calculations remain stable throughout the event.
3. **Given** the leader position changes mid-race, **When** a new driver takes P1, **Then** the spline continues uninterrupted — no reset, no gap of missing data.

---

### User Story 2 — Debugging HTML Tools Available in Main Program (Priority: P1)
The spline debugger and SHM leaderboard HTML surfaces must be served by the main program's WebSocket infrastructure, giving the user real-time visibility into the spline state, flywheel status, mCurrentTime history, and per-driver gap calculations without needing to run a separate standalone tool.

**Why this priority**: Without these diagnostic surfaces, the user cannot verify that the transplanted system is functioning correctly in the main program's runtime context.

**Acceptance Scenarios**:
1. **Given** the main program is running, **When** the user opens the leaderboard debugger URL, **Then** the HTML page connects via WebSocket and displays live leaderboard data with time gaps, flywheel status badge, spline history, and mCurrentTime history.
2. **Given** the spline debugger is open, **When** a camera swap triggers the flywheel, **Then** the "FLYWHEEL ACTIVE" badge appears in real-time and the spline history shows system-clock-synthesized entries (not speed-based dead reckoning).
3. **Given** the debugging tools are running, **When** the main program is also performing its scoring/camera duties, **Then** neither system degrades the other's performance.

---

### User Story 3 — Strangler Refactor: No Python File Exceeds 500 Lines (Priority: P2)
Several Python files currently exceed 500 lines (`tools/shm_leaderboard_server.py`: 586, `main.py`: 631, `core/telemetry_provider.py`: 847, `dashboard/bridge.py`: 580). Each must be decomposed into focused modules using the strangler pattern — extracting cohesive units one at a time without breaking functionality.

**Why this priority**: Maintainability and cognitive load. Files beyond 500 lines become difficult to reason about, test in isolation, and review. The strangler pattern ensures zero-regression decomposition.

**Acceptance Scenarios**:
1. **Given** the refactor is complete, **When** line counts are checked across all `.py` files in the project, **Then** no single Python file exceeds 500 lines.
2. **Given** any file has been decomposed, **When** the full test suite runs, **Then** all existing tests pass with zero regressions.
3. **Given** the decomposed modules, **When** a developer examines any single file, **Then** it has a single clear responsibility described in its module docstring.


## Requirements *(mandatory)*

### Functional Requirements

**Spline & Flywheel Transplant**:
- **FR-001**: The main program MUST use a single continuous `DistanceTimeSpline` instance per race session that is never reset except on session transitions.
- **FR-002**: The main program MUST use the `PhysicsFlywheel` to stabilize `mCurrentTime` before any downstream consumer (spline recording, gap calculation, scoring engine).
- **FR-003**: The flywheel MUST use system wall-clock time (`time.monotonic`) for synthetic time during anomalies, not distance/speed dead-reckoning.
- **FR-004**: The flywheel MUST include self-healing: after 40 consecutive healthy game-time deltas (~10 seconds), force-resync to real game time.
- **FR-005**: Time gap calculation MUST use `current_time - spline.interpolate_time(driver_total_dist)` where `current_time` is flywheel-stabilized.
- **FR-006**: The spline recording and leaderboard gap calculation MUST execute in the same tick — they cannot be on separate cadences.

**Debugging HTML Surfaces**:
- **FR-007**: The main program MUST serve the spline debugger HTML page showing: distance-time history (newest first), speed column, mCurrentTime history with delta column.
- **FR-008**: The main program MUST serve the SHM leaderboard HTML page showing: sorted driver list with position, name, lap, distance gap, time gap, pit status.
- **FR-009**: Both HTML pages MUST display a real-time flywheel status badge ("FLYWHEEL ACTIVE" red badge when engaged, hidden when not).
- **FR-010**: The main program MUST serve all data (scoring, camera, leaderboard, spline diagnostics) through a single unified WebSocket endpoint on one port. The HTML debugging pages connect to the same server as the dashboard.

**Strangler Refactor**:
- **FR-011**: No Python file in the project shall exceed 500 lines after the refactor.
- **FR-012**: Each decomposed module MUST have a module-level docstring describing its single responsibility.
- **FR-013**: Decomposition MUST follow the strangler pattern: extract → verify tests pass → remove old code.
- **FR-014**: The following files MUST be decomposed:
  - `core/telemetry_provider.py` (847 lines) — highest priority
  - `main.py` (631 lines)
  - `tools/shm_leaderboard_server.py` (586 lines)
  - `dashboard/bridge.py` (580 lines)

**Testing Strategy**:
- **FR-015**: Development MUST follow TDD — integration tests for each transplant step are written before the implementation code. The existing 24 `test_physics_flywheel.py` unit tests remain in place testing the extracted modules directly; new integration tests verify the main program's wiring and consumption of those modules.

### Key Entities
- **DistanceTimeSpline**: Continuous distance-time reference curve recording the leader's trajectory. Used for all time-gap interpolation.
- **PhysicsFlywheel**: System-clock time stabilizer that rejects anomalous `mCurrentTime` values and substitutes wall-clock-based synthetic time.
- **Spline Debugger**: HTML diagnostic surface showing spline state, speed profile, and mCurrentTime health.
- **SHM Leaderboard**: HTML diagnostic surface showing live driver standings with computed time gaps.

## Assumptions

- The existing test suite (282 tests) serves as the regression baseline — all tests must pass after every decomposition step.
- The standalone `tools/shm_leaderboard_server.py` is the source of truth for the spline, flywheel, and gap calculation logic. The main program's existing gap logic is the deprecated target.
- The 500-line limit is total lines in the file (including blanks and comments) — measurable with a simple line count, no custom tooling required.
- The HTML debugging surfaces are development/diagnostic tools, not end-user-facing — they do not require production-grade styling or error handling beyond functional correctness.
- The WebSocket server is a single unified endpoint — one port serves the dashboard, leaderboard, and spline debugger. No separate diagnostic server.

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: Time gap variance for any driver during a stable lap (no real overtakes) is ≤ 0.5 seconds in the main program.
- **SC-002**: Camera swap anomalies (40s time jumps) produce zero negative time gaps and zero spline resets in the main program.
- **SC-003**: The flywheel self-heals from any false-positive lock-in within 10 seconds of game time stabilization.
- **SC-004**: No Python file in the project exceeds 500 lines of source code.
- **SC-005**: All 282+ existing tests pass after every incremental step of the transplant and refactor.
- **SC-006**: Both debugging HTML surfaces (spline debugger, SHM leaderboard) connect and display live data when the main program is running.
