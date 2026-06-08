# Tasks: Non-Blocking Camera Switches

**Input**: Design documents from `/specs/017-remove-camera-sleeps/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. Tests are written and run first (TDD).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initial setups and preparations.

- [x] T001 Initialize branch checklist and verify clean working state in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

- [x] T002 Configure threading structure and lock placeholder in [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Smooth Auto-Directing without GUI Freezes (Priority: P1) 🎯 MVP

**Goal**: Refactor `CameraController.move_to_position` to execute key press sequences on a background thread and return immediately, preventing GUI stutters.

**Independent Test**: Verify that calling `move_to_position` with mock sleeps returns immediately (< 5ms) on the calling thread.

### Tests for User Story 1 (TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Write test verifying `move_to_position` execution time is non-blocking on calling thread in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)
- [x] T004 [P] [US1] Write test verifying concurrent `move_to_position` requests are ignored while switching in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)

### Implementation for User Story 1

- [x] T005 [P] [US1] Add `self._switch_lock = threading.Lock()` and `self._switching_in_progress = False` to `CameraController.__init__` in [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)
- [x] T006 [US1] Implement helper method `_execute_switch_sequence` that runs key injection under lock and resets state in `finally` block in [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)
- [x] T007 [US1] Update `move_to_position` to spawn `_execute_switch_sequence` in a daemon thread and return immediately in [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Real-Time Dashboard Broadcasting during Switches (Priority: P2)

**Goal**: Refactor `select_random_camera` to run its stabilization delay and key tap on a background thread so the dashboard WebSocket loop remains unblocked.

**Independent Test**: Verify that calling `select_random_camera` returns immediately (< 5ms) on the calling thread.

### Tests for User Story 2 (TDD) ⚠️

- [x] T008 [P] [US2] Write test verifying `select_random_camera` execution time is non-blocking on calling thread in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)

### Implementation for User Story 2

- [x] T009 [US2] Update `select_random_camera` to run key tap and stabilization delay in a background thread in [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently.

---

## Phase 5: User Story 3 - Non-Blocking Manual Camera Switches (Priority: P3)

**Goal**: Ensure manual camera type hotkeys or GUI camera switches execute asynchronously.

**Independent Test**: Trigger a manual camera switch via GUI/Hotkey and verify it is processed without blocking.

### Tests for User Story 3 (TDD) ⚠️

- [x] T010 [P] [US3] Write test verifying that key injection for manual switch is non-blocking in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)

### Implementation for User Story 3

- [x] T011 [US3] Integrate non-blocking keystroke tap for manual GUI/hotkey updates in [main.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/main.py) and [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: High-level logging, cleanup, and validation.

- [x] T012 [P] Implement high-level logging (sequence start/finish/duration) in `_execute_switch_sequence` in [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)
- [x] T013 Verify focus-loss abort mechanism by adding a test case in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)
- [x] T014 Run full static analysis and ensure all 306+ tests pass successfully

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion.
- **User Stories (Phase 3+)**: All depend on Foundational phase completion.
- **Polish (Final Phase)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories.
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 background logic.
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Uses the same thread-safe non-blocking execution path.

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD).
- Sequence control (lock/flag) must be added before threading runner.
- Thread runner before individual camera handlers.

---

## Parallel Opportunities

- All tests marked [P] can run in parallel (T003, T004, T008, T010).
- Model and initialization tasks (T005) can run in parallel with tests.

---

## Parallel Example: User Story 1

```bash
# Run tests in parallel:
Task: "Write test verifying move_to_position execution time is non-blocking on calling thread"
Task: "Write test verifying concurrent move_to_position requests are ignored"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Write tests first, then implement `move_to_position` async thread).
4. **STOP and VALIDATE**: Verify that GUI remains interactive and no lag spikes occur.

### Incremental Delivery

1. Setup + Foundation ready
2. Add User Story 1 (MVP) -> Deploy/Demo
3. Add User Story 2 (Overlay telemetry continuity) -> Deploy/Demo
4. Add User Story 3 (Manual non-blocking) -> Deploy/Demo
5. Polish & Logging
