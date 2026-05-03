# Tasks: AMS2 Auto Director V4.0 — Strangler Refactor

**Input**: Design documents from `.specify/features/v3_live_engine/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅

**Tests**: TDD approach — all tests written FIRST, verified RED, then implementation turns them GREEN.

**Organization**: Tasks are grouped by module (Scoring Engine → Telemetry Provider → Camera Controller → GUI Shell) following the Strangler Execution Order from the plan.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1=Scoring, US2=Telemetry, US3=Camera, US4=GUI)
- Exact file paths included in all descriptions

---

## Phase 1: Setup (Project Scaffolding)

**Purpose**: Create the directory structure and package boilerplate for the modular V4.0 architecture.

- [ ] T001 Create `core/` package directory and `core/__init__.py` in `AMS2_Auto_Director4.0/core/__init__.py`
- [ ] T002 [P] Create `tests/` package directory and `tests/__init__.py` in `AMS2_Auto_Director4.0/tests/__init__.py`
- [ ] T003 [P] Create `tests/conftest.py` with shared test fixtures (MockParticipant factory, MockSharedMemory factory) in `AMS2_Auto_Director4.0/tests/conftest.py`
- [ ] T004 Verify pytest discovers test directory: run `pytest tests/ --collect-only` from `AMS2_Auto_Director4.0/`
- [ ] T005 Git commit: "Phase 1: project scaffolding"

**Checkpoint**: `pytest tests/ --collect-only` returns 0 errors, empty collection.

---

## Phase 2: Foundational (Shared Test Fixtures)

**Purpose**: Build the mock data factories that ALL test modules depend on. MUST complete before any user story.

**⚠️ CRITICAL**: No module tests can be written until these fixtures exist.

- [ ] T006 Define `make_participant(**overrides)` fixture in `tests/conftest.py` — returns a single participant dict with sensible defaults matching the data-model.md schema (name, race_position, is_active, lap_distance, current_lap, speed, pit_mode, race_state, true_distance, gap_ahead, cars_ahead_250m, flag_colour, flag_reason, fastest_lap, last_lap)
- [ ] T007 [P] Define `make_participants(count, **per_driver_overrides)` fixture in `tests/conftest.py` — returns a `dict[int, dict]` of N participants with sequential positions and sensible spread distances
- [ ] T008 [P] Define `make_mock_shared_memory(**field_overrides)` fixture in `tests/conftest.py` — returns a fake object mimicking the `SharedMemory` ctypes struct fields (mParticipantInfo, mTrackLocation, mTrackLength, mCurrentTime, mSpeeds, mPitModes, mRaceStates, mHighestFlagColours, mHighestFlagReasons)
- [ ] T009 Write a smoke test in `tests/test_fixtures.py` that calls each fixture and asserts the returned dict/object has all required keys/fields
- [ ] T010 Run `pytest tests/test_fixtures.py` — verify all fixture smoke tests PASS
- [ ] T011 Git commit: "Phase 2: shared test fixtures"

**Checkpoint**: All fixture factories return correctly-shaped data. `pytest tests/` passes.

---

## Phase 3: User Story 1 — Scoring Engine (Priority: P1) 🎯 MVP

**Goal**: Extract the V3.0 `next_focus()` scoring logic into a standalone, testable `ScoringEngine` class with zero external dependencies.

**Independent Test**: `pytest tests/test_scoring_engine.py` — all 29 tests pass with no AMS2, no GUI, no pyKey.

### Tests for US1 (TDD — Write FIRST, verify RED)

- [ ] T012 [P] [US1] Write SE-01 to SE-03 (Pit Mode Penalty tests) in `tests/test_scoring_engine.py`
- [ ] T013 [P] [US1] Write SE-04 to SE-07 (Speed Penalty tests) in `tests/test_scoring_engine.py`
- [ ] T014 [P] [US1] Write SE-08 to SE-10 (Cars Ahead Bonus tests) in `tests/test_scoring_engine.py`
- [ ] T015 [P] [US1] Write SE-11 to SE-15 (Close Racing Bonus tests) in `tests/test_scoring_engine.py`
- [ ] T016 [P] [US1] Write SE-16 to SE-19 (Race Position Bonus tests) in `tests/test_scoring_engine.py`
- [ ] T017 [P] [US1] Write SE-20 to SE-22 (Total Score Aggregation tests) in `tests/test_scoring_engine.py`
- [ ] T018 [P] [US1] Write SE-23 to SE-26 (Best Focus Selection tests) in `tests/test_scoring_engine.py`
- [ ] T019 [P] [US1] Write SE-27 to SE-29 (Configurable Parameters tests) in `tests/test_scoring_engine.py`
- [ ] T020 [US1] Run `pytest tests/test_scoring_engine.py` — verify all 29 tests FAIL (RED gate)

### Implementation for US1

- [ ] T021 [US1] Create `ScoringEngine` class skeleton with all configurable attributes in `core/scoring_engine.py`
- [ ] T022 [US1] Implement `_calculate_pit_mode_penalty(participant)` method in `core/scoring_engine.py`
- [ ] T023 [US1] Implement `_calculate_speed_penalty(participant)` method in `core/scoring_engine.py`
- [ ] T024 [US1] Implement `_calculate_cars_ahead_bonus(participant)` method in `core/scoring_engine.py`
- [ ] T025 [US1] Implement `_calculate_close_racing_bonus(participant)` method in `core/scoring_engine.py`
- [ ] T026 [US1] Implement `_calculate_race_position_bonus(participant)` method in `core/scoring_engine.py`
- [ ] T027 [US1] Implement `calculate_scores(participants)` public method that aggregates all components in `core/scoring_engine.py`
- [ ] T028 [US1] Implement `get_best_focus(scores, participants)` public method in `core/scoring_engine.py`
- [ ] T029 [US1] Run `pytest tests/test_scoring_engine.py` — verify all 29 tests PASS (GREEN gate)
- [ ] T030 [US1] Git commit: "US1: scoring engine — 29/29 tests passing"

**Checkpoint**: `pytest tests/test_scoring_engine.py` — 29 PASSED. Scoring engine is fully decoupled and verified.

---

## Phase 4: User Story 2 — Telemetry Provider (Priority: P2)

**Goal**: Extract the V3.0 shared memory and UDP reading logic into a `TelemetryProvider` class that returns normalised participant dicts, including driver names.

**Independent Test**: `pytest tests/test_telemetry_provider.py` — all 21 tests pass using MockSharedMemory. No live AMS2 required.

### Tests for US2 (TDD — Write FIRST, verify RED)

- [ ] T031 [P] [US2] Write TP-01 to TP-05 (Shared Memory Extraction tests) in `tests/test_telemetry_provider.py`
- [ ] T032 [P] [US2] Write TP-06 to TP-08 (True Distance Calculation tests) in `tests/test_telemetry_provider.py`
- [ ] T033 [P] [US2] Write TP-09 to TP-11 (Gap Calculation tests) in `tests/test_telemetry_provider.py`
- [ ] T034 [P] [US2] Write TP-12 to TP-14 (Cars Ahead 250m tests) in `tests/test_telemetry_provider.py`
- [ ] T035 [P] [US2] Write TP-15 to TP-18 (Speed Calculation tests) in `tests/test_telemetry_provider.py`
- [ ] T036 [P] [US2] Write TP-19 to TP-20 (Connection State tests) in `tests/test_telemetry_provider.py`
- [ ] T037 [P] [US2] Write TP-21 (Track Change Detection test) in `tests/test_telemetry_provider.py`
- [ ] T038 [US2] Run `pytest tests/test_telemetry_provider.py` — verify all 21 tests FAIL (RED gate)

### Implementation for US2

- [ ] T039 [US2] Create `TelemetryProvider` class skeleton with `__init__(mode)` in `core/telemetry_provider.py`
- [ ] T040 [US2] Implement `_read_shared_memory()` private method (ctypes mmap read) in `core/telemetry_provider.py`
- [ ] T041 [US2] Implement `_extract_participant(data, index)` method — reads name, position, lap, speed, pit mode, flags from SharedMemory in `core/telemetry_provider.py`
- [ ] T042 [US2] Implement `_calculate_true_distances(participants, track_length)` method in `core/telemetry_provider.py`
- [ ] T043 [US2] Implement `_calculate_gaps(participants, track_length)` method in `core/telemetry_provider.py`
- [ ] T044 [US2] Implement `_calculate_cars_ahead(participants, track_length)` method in `core/telemetry_provider.py`
- [ ] T045 [US2] Implement `_calculate_speed(index)` method using distance/timestamp deques in `core/telemetry_provider.py`
- [ ] T046 [US2] Implement `poll()` public method that orchestrates extraction + derived calculations in `core/telemetry_provider.py`
- [ ] T047 [US2] Implement `get_game_time()` public method in `core/telemetry_provider.py`
- [ ] T048 [US2] Implement `get_track_info()` public method in `core/telemetry_provider.py`
- [ ] T049 [US2] Implement `is_connected()` public method in `core/telemetry_provider.py`
- [ ] T050 [US2] Implement track change detection (reset participants when track info changes) in `core/telemetry_provider.py`
- [ ] T051 [US2] Run `pytest tests/test_telemetry_provider.py` — verify all 21 tests PASS (GREEN gate)
- [ ] T052 [US2] Run full regression `pytest tests/` — verify all 50 tests PASS (29 + 21)
- [ ] T053 [US2] Git commit: "US2: telemetry provider — 21/21 tests passing, 50 total"

**Checkpoint**: `pytest tests/` — 50 PASSED. Telemetry provider fully decoupled with mock-based testing.

---

## Phase 5: User Story 3 — Camera Controller (Priority: P3)

**Goal**: Extract the V3.0/V4.0 `auto_director()` keyboard injection logic into a `CameraController` class with delta-based navigation and configurable timing.

**Independent Test**: `pytest tests/test_camera_controller.py` — all 13 tests pass using monkeypatched pyKey. No real keyboard input injected.

### Tests for US3 (TDD — Write FIRST, verify RED)

- [ ] T054 [P] [US3] Write CC-01 to CC-04 (Delta Navigation tests) in `tests/test_camera_controller.py`
- [ ] T055 [P] [US3] Write CC-05 to CC-07 (Fallback Navigation tests) in `tests/test_camera_controller.py`
- [ ] T056 [P] [US3] Write CC-08 to CC-10 (Key Timing tests) in `tests/test_camera_controller.py`
- [ ] T057 [P] [US3] Write CC-11 to CC-13 (Edge Cases tests) in `tests/test_camera_controller.py`
- [ ] T058 [US3] Run `pytest tests/test_camera_controller.py` — verify all 13 tests FAIL (RED gate)

### Implementation for US3

- [ ] T059 [US3] Create `CameraController` class skeleton with configurable `key_hold_ms`, `key_gap_ms` in `core/camera_controller.py`
- [ ] T060 [US3] Implement `move_to_position(target_pos, current_pos)` with delta navigation (DOWN for positive delta, UP for negative) in `core/camera_controller.py`
- [ ] T061 [US3] Implement fallback path in `move_to_position` when `current_pos is None` (scroll 32x UP then DOWN to target) in `core/camera_controller.py`
- [ ] T062 [US3] Implement `press_enter()` confirmation method in `core/camera_controller.py`
- [ ] T063 [US3] Add guard clauses for invalid positions (P0, P33+) in `core/camera_controller.py`
- [ ] T064 [US3] Run `pytest tests/test_camera_controller.py` — verify all 13 tests PASS (GREEN gate)
- [ ] T065 [US3] Run full regression `pytest tests/` — verify all 63 tests PASS (29 + 21 + 13)
- [ ] T066 [US3] Git commit: "US3: camera controller — 13/13 tests passing, 63 total"

**Checkpoint**: `pytest tests/` — 63 PASSED. All three core modules fully extracted, tested, and decoupled.

---

## Phase 6: User Story 4 — GUI Shell & Integration (Priority: P4)

**Goal**: Wire the three core modules into a tkinter GUI shell that replicates the V4.0 prototype look and feel. No new tests — GUI is a thin shell; all logic is already tested.

**Independent Test**: Manual launch. Verify leaderboard grid displays, tuning parameters adjust scoring, and connection status transitions between "Waiting for AMS2..." and "Connected to AMS2".

### Implementation for US4

- [ ] T067 [US4] Create `main.py` with tkinter root window, dark theme, and application title in `AMS2_Auto_Director4.0/main.py`
- [ ] T068 [US4] Implement connection status panel ("Waiting for AMS2..." / "Connected to AMS2") in `main.py`
- [ ] T069 [US4] Implement leaderboard `ttk.Treeview` grid populated from `provider.poll()` + `scorer.calculate_scores()` in `main.py`
- [ ] T070 [US4] Implement Director Tuning panel — input fields for all 7 configurable `ScoringEngine` parameters in `main.py`
- [ ] T071 [US4] Implement "Apply Tuning" button that writes GUI values to `scorer.*` attributes in `main.py`
- [ ] T072 [US4] Implement main tick loop via `root.after(200, tick)` — polls telemetry, scores, updates grid in `main.py`
- [ ] T073 [US4] Implement auto-director toggle via spacebar hotkey (`keyboard.is_pressed`) in `main.py`
- [ ] T074 [US4] Implement auto-director camera switch logic — on interval elapsed, call `camera.move_to_position(best_focus, current_pos)` in `main.py`
- [ ] T075 [US4] Implement mode selection at startup (shared memory vs UDP) — either via CLI arg or dialog in `main.py`
- [ ] T076 [US4] Run full regression `pytest tests/` — verify all 63 tests still PASS (no regressions)
- [ ] T077 [US4] Manual launch test: run `python main.py` and verify GUI appears with correct layout
- [ ] T078 [US4] Git commit: "US4: tkinter GUI shell wired to core modules"

**Checkpoint**: Application launches. Grid displays. Tuning works. Camera switching fires when AMS2 is running.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, documentation, and final validation.

- [ ] T079 Remove all commented-out debug print statements from legacy code references
- [ ] T080 [P] Add module-level docstrings to all `core/*.py` files
- [ ] T081 [P] Update `README.md` with V4.0 architecture overview and launch instructions
- [ ] T082 [P] Update `.gitignore` if any new artifacts need exclusion
- [ ] T083 Run final full regression `pytest tests/` — verify all 63 tests PASS
- [ ] T084 Git commit: "V4.0 strangler refactor complete — 63 tests, 4 modules"
- [ ] T085 Git tag: `v4.0.0-alpha`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 Scoring)**: Depends on Phase 2 — can start once fixtures exist
- **Phase 4 (US2 Telemetry)**: Depends on Phase 2 — can run in parallel with US1 if desired
- **Phase 5 (US3 Camera)**: Depends on Phase 2 — can run in parallel with US1/US2 if desired
- **Phase 6 (US4 GUI)**: Depends on US1, US2, US3 completion — wires all three together
- **Phase 7 (Polish)**: Depends on US4 completion

### Within Each User Story

1. Tests MUST be written and verified FAIL (RED) before implementation
2. Implementation tasks are sequential within each module
3. GREEN gate must pass before git commit
4. Full regression must pass before moving to next user story

### Parallel Opportunities

- T001, T002, T003 (Phase 1 scaffolding) — all parallel
- T006, T007, T008 (Phase 2 fixtures) — all parallel
- T012–T019 (US1 test groups) — all parallel (same file but different test classes)
- T031–T037 (US2 test groups) — all parallel
- T054–T057 (US3 test groups) — all parallel
- US1, US2, US3 could theoretically run in parallel after Phase 2 (different files, zero cross-dependencies)

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational fixtures
3. Complete Phase 3: User Story 1 (Scoring Engine)
4. **STOP and VALIDATE**: `pytest tests/test_scoring_engine.py` — 29 tests pass
5. The scoring engine is independently usable and verified

### Incremental Delivery

1. Setup + Foundational → Fixtures ready
2. Add US1 (Scoring Engine) → 29 tests pass → Commit
3. Add US2 (Telemetry Provider) → 50 tests pass → Commit
4. Add US3 (Camera Controller) → 63 tests pass → Commit
5. Add US4 (GUI Shell) → Manual verification → Commit
6. Each module adds value without breaking previous modules

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific module for traceability
- Each user story is independently completable and testable
- Verify tests fail before implementing (RED → GREEN cycle)
- Git commit after each user story completes
- Legacy monoliths (`AMS2AutoDirector.py`, `ReplayAutoDirector4.py`) are preserved but never imported
- Total tasks: **85**
- Total tests: **63** (29 + 21 + 13)
