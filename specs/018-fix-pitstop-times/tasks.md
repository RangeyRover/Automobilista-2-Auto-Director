# Tasks: Standalone Server Flywheel Pitstop Times

**Input**: Design documents from `/specs/018-fix-pitstop-times/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Basic verification and preparation

- [x] T001 Verify git branch is `018-fix-pitstop-times` and working tree is clean in [shm_leaderboard_server.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tools/shm_leaderboard_server.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Prerequisites before story work begins

- [x] T002 [P] Inspect structure of `correlate_drivers` in [shm_leaderboard_server.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tools/shm_leaderboard_server.py)

---

## Phase 3: User Story 1 - Standalone SHM server stabilized pitstop times (Priority: P1) 🎯 MVP

**Goal**: Defer `_pit_time` calculation to the second pass of `correlate_drivers` where the flywheel-processed clock is available.

**Independent Test**: Verify `_pit_time` is correctly calculated using the stabilized clock during anomalies.

### Tests for User Story 1 (TDD) ⚠️

- [x] T003 [P] [US1] Create TDD unit test in [test_shm_dump_tool.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_shm_dump_tool.py) verifying that `_pit_time` calculation uses the flywheel-stabilized time instead of raw game time

### Implementation for User Story 1

- [x] T004 [US1] Refactor `correlate_drivers` in [shm_leaderboard_server.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tools/shm_leaderboard_server.py) to remove pit calculations from the first loop and place them in the second loop where stabilized `current_time` is available
- [x] T005 [US1] Ensure `correlate_drivers` handles backward compatibility for flat float values in the `pit_entry_times` dictionary in [shm_leaderboard_server.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tools/shm_leaderboard_server.py)

**Checkpoint**: User Story 1 functional and testable independently.

---

## Phase 4: User Story 2 - Consistent Timing Across Dashboard Components (Priority: P2)

**Goal**: Ensure the main dashboard components consistently use the stabilized master clock.

**Independent Test**: Verify that both timing and pit durations on the dashboard are stable during replay timing anomalies.

### Tests for User Story 2 (TDD) ⚠️

- [x] T006 [P] [US2] Create integration test in [test_pit_tracker.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_pit_tracker.py) verifying that the `PitTracker` processes updates with the stabilized game clock

### Implementation for User Story 2

- [x] T007 [US2] Verify that [payload_builder.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/payload_builder.py) correctly passes the stabilized `_last_current_time` to the `PitTracker.update` call

**Checkpoint**: User Stories 1 and 2 work consistently.

---

- [x] T008 Run the full test suite with `pytest` and verify all 309+ tests pass successfully

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion.
- **User Stories (Phase 3+)**: Depend on Foundational phase completion.
- **Polish (Final Phase)**: Depends on all user stories being complete.

### Parallel Opportunities

- T003 (US1 tests) and T006 (US2 tests) can be developed in parallel as they target separate files.
