# Tasks: Trim Future Spline Points on Resync and Rewind

**Input**: Design documents from `/specs/016-trim-future-spline-points/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: Tests are requested ("sdd tdd tests before code" in the user prompt). Test tasks are included and must be written and verified as failing (RED) before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- Paths shown assume single project structure at `AMS2_Auto_Director4.0/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verification of baseline environment

- [x] T001 Run baseline test suite with `pytest tests/test_spline.py tests/test_physics_flywheel.py tests/test_leaderboard_integration.py` to confirm baseline stability in `AMS2_Auto_Director4.0/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core logic implementation of the `trim_future_points` method in `DistanceTimeSpline`

**⚠️ CRITICAL**: No user story integration work can begin until this phase is complete.

### Tests for Foundation
> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**
- [x] T002 [P] Write unit tests for `DistanceTimeSpline.trim_future_points` in `tests/test_spline.py` covering populated spline trimming, no-op cases, empty spline behavior, and length alignment preservation (MUST fail)

### Implementation for Foundation
- [x] T003 Implement `trim_future_points` method using binary search (`bisect.bisect_right`) in `core/spline.py`
- [x] T004 Run `pytest tests/test_spline.py` to verify unit tests pass (GREEN)

**Checkpoint**: Foundation ready - spline trimming is verified and ready to be integrated.

---

## Phase 3: User Story 1 - Stable Gaps After Flywheel Resync (Priority: P1) 🎯 MVP

**Goal**: Leaderboard time gaps calculate correctly and do not drop out to blank cells when master clock recovers from a telemetry glitch (did_resync = True).

**Independent Test**: Simulate a telemetry gap where the flywheel drifts forward, then resyncs, and verify that the spline is trimmed of future-dated points and subsequent gaps calculate correctly.

### Tests for User Story 1
> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**
- [x] T005 [P] [US1] Write integration test in `tests/test_leaderboard_integration.py` simulating a flywheel drift followed by a resync (`_flywheel.did_resync = True`), asserting spline is trimmed and gaps calculate correctly (MUST fail)

### Implementation for User Story 1
- [x] T006 [US1] Integrate flywheel resync trimming trigger in `poll()` method in `core/telemetry_provider.py` when `_flywheel.did_resync` is True
- [x] T007 [US1] Run `pytest tests/test_leaderboard_integration.py` to verify integration tests pass (GREEN)

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Support Replay Scrubbing and Rewinding (Priority: P2)

**Goal**: Support replay review by trimming future points when the user scrubs or rewinds backward in time.

**Independent Test**: Simulate a backward jump in stabilized game time and verify that spline points with timestamps greater than the new time are discarded.

### Tests for User Story 2
> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**
- [x] T008 [P] [US2] Write integration test in `tests/test_leaderboard_integration.py` simulating a backward time jump, asserting spline is trimmed of future points and gaps calculate correctly (MUST fail)

### Implementation for User Story 2
- [x] T009 [US2] Integrate rewind trimming trigger in `poll()` method in `core/telemetry_provider.py` when `stable_time` is strictly less than the last recorded spline timestamp (`self._leader_spline.times[-1]`)
- [x] T010 [US2] Run `pytest tests/test_leaderboard_integration.py` to verify integration tests pass (GREEN)

**Checkpoint**: User Story 2 is fully functional and testable independently.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Robustness checks, edge case handling, and cleanup

- [x] T011 [P] Write robustness test in `tests/test_spline.py` verifying fallback to physical distance/speed gap calculation when spline is trimmed to < 2 points or empty
- [x] T012 Run the entire test suite `pytest` to ensure zero regressions in other parts of the application
- [x] T013 [P] Perform static analysis and lint checks (ruff, mypy) on modified files `core/spline.py`, `core/telemetry_provider.py`, `tests/test_spline.py`, `tests/test_leaderboard_integration.py`
- [x] T014 [P] Update `walkthrough.md` in `specs/016-trim-future-spline-points/` with details of implementation and test coverage results

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Implementation must follow tests
- Verify green before proceeding

---

## Parallel Example: User Story 1

```bash
# Launch test and implementation tasks:
Task: "Write integration test in tests/test_leaderboard_integration.py simulating a flywheel drift followed by a resync..."
Task: "Integrate flywheel resync trimming trigger in poll() method in core/telemetry_provider.py..."
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently

### Incremental Delivery

1. Foundation ready (Phase 2)
2. US1 Stable Gaps on Resync (Phase 3) -> Deploy/Demo (MVP!)
3. US2 Replay Scrubbing & Rewinding (Phase 4)
4. Polish & Edge Cases (Phase 5)
