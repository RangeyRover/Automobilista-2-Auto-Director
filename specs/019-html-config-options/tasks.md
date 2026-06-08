# Tasks: HTML Configuration Options

**Input**: Design documents from `/specs/019-html-config-options/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Basic verification and preparation

- [x] T001 Verify git working tree is clean and on branch `019-html-config-options` in [core/camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that must be complete before any user story can be implemented

- [x] T002 Ensure [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py) handles defaults/fallback cleanly when loading config, including properties `"enabled_cameras"` (default to empty list `[]`) and `"disable_camera_change"` (default to boolean `False`)

---

## Phase 3: User Story 1 - Leaderboard Interval Gaps Toggle (Priority: P1) 🎯 MVP

**Goal**: Implement client-side gap delta calculations in JavaScript (`f1tv_overlay.js` and `app.js`) and support toggling between Gap to Leader and Interval Gap.

**Independent Test**: Open overlay setting panel, check "Interval Gaps", timing column should display delta to car ahead (e.g. +1.3s) instead of cumulative gap.

### Tests for User Story 1 (TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T003 [P] [US1] Add a TDD test in [test_f1tv_overlay.js](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_f1tv_overlay.js) that runs and fails verifying that interval gaps toggle works, registering the `interval-gaps` component and calculating correct deltas for consecutive leaderboard rows

### Implementation for User Story 1

- [x] T004 [P] [US1] Add a dummy element for `interval-gaps` to prevent element lookup exceptions in [f1tv_overlay.html](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/f1tv_overlay.html)
- [x] T005 [P] [US1] Add the `interval-gaps` component to the components list in [f1tv_overlay.js](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/js/f1tv_overlay.js)
- [x] T006 [P] [US1] Update the leaderboard rendering in [f1tv_overlay.js](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/js/f1tv_overlay.js) to compute interval timing gaps for mini and full leaderboards when enabled
- [x] T007 [P] [US1] Add the `interval-gaps` component to the components list in [f1tv_control.html](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/f1tv_control.html)
- [x] T008 [P] [US1] Add logic to synchronize settings and compute interval gaps on the main telemetry leaderboard in [app.js](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/app.js)

**Checkpoint**: User Story 1 fully functional and testable independently.

---

## Phase 4: User Story 2 - Limit Auto-Camera Pools (Priority: P2)

**Goal**: Restrict auto director camera selection to a subset defined in `camera_config.json`.

**Independent Test**: Select camera views 1, 2, and 7 on the control panel, run auto-director, verify it only switches between those views.

### Tests for User Story 2 (TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T009 [P] [US2] Add TDD test `test_camera_controller_filters_choices` in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py) verifying that when `enabled_cameras` is set in config, only those camera keys are chosen

### Implementation for User Story 2

- [x] T010 [US2] Modify `select_random_camera` and switch sequence logic in [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py) to filter camera choices based on `enabled_cameras`
- [x] T011 [P] [US2] Add camera pool checkboxes (keys 1-7) in [f1tv_control.html](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/f1tv_control.html) styling matching the existing dark theme
- [x] T012 [P] [US2] Add JS logic in [f1tv_control.html](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/f1tv_control.html) to populate check states from `camera_config.json` and write configuration updates via `save_json` websocket command

**Checkpoint**: User Stories 1 and 2 work independently.

---

## Phase 5: User Story 3 - Disable Auto-Camera Switch Toggle (Priority: P3)

**Goal**: Allow freezing automatic camera angle switching while keeping auto driver tracking active.

**Independent Test**: Check "Disable Auto Cam Switch" in control panel settings, verify focus driver switches but camera angle remains locked.

### Tests for User Story 3 (TDD) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US3] Add TDD test `test_camera_controller_respects_disable_camera_change_config` in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py) verifying that when `disable_camera_change` is True, automatic switches are blocked

### Implementation for User Story 3

- [ ] T014 [US3] Update camera change methods in [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py) to read config's `disable_camera_change` and abort automatic camera switches when set
- [ ] T015 [P] [US3] Add a disable auto-camera switch toggle checkbox in [f1tv_control.html](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/f1tv_control.html)
- [ ] T016 [P] [US3] Add JS logic in [f1tv_control.html](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/dashboard/f1tv_control.html) to populate and update `disable_camera_change` config via `save_json` websocket command

**Checkpoint**: All user stories functional and testable independently.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, formatting, documentation and full regression verification

- [ ] T017 Run static checker on modified python files in [core/camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)
- [ ] T018 Run the complete unit test suite with `pytest` to ensure no regressions in [tests/](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests)
- [ ] T019 Run `quickstart.md` validation by launching the server, opening the control panel, toggling the settings, and manually verifying the timing display updates and camera logs

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion.
- **User Stories (Phase 3+)**: Depend on Foundational phase completion.
- **Polish (Final Phase)**: Depends on all user stories being complete.

### Parallel Opportunities

- T003 (US1 TDD test) can run in parallel with T009 (US2 TDD test) and T013 (US3 TDD test) as they are completely independent files and frameworks.
- T004, T005, T007, T008 (US1 UI components and App.js layout tasks) can be implemented in parallel.
- T011, T015 (US2/US3 control panel markup) can be designed in parallel.

---

## Parallel Example: User Story 1

```bash
# Implement the client-side gaps calculation and sync components in parallel:
Task: "Update the leaderboard rendering in f1tv_overlay.js to compute interval timing gaps when enabled"
Task: "Add logic to synchronize settings and compute interval gaps on the main leaderboard in app.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (ensures fallback behavior on loading config)
3. Complete Phase 3: User Story 1 (Interval Timing Gaps)
4. **STOP and VALIDATE**: Verify interval timing works on overlay and dashboard leaderboards.

### Incremental Delivery

1. Complete Setup + Foundational -> Project ready
2. Add User Story 1 -> Test independently -> Demo
3. Add User Story 2 -> Test independently -> Demo
4. Add User Story 3 -> Test independently -> Demo
5. Run full regression suite & static analysis check.
