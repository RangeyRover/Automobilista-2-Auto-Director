# Tasks: Roof Camera Session Info Overlay & Tenths Leaderboard Format

**Input**: Design documents from `/specs/014-roof-cam-tenths-leaderboard/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/websocket-protocol.md

**Tests**: A strict Test-Driven Development (TDD) approach is used. Test cases are written and verified as failing *before* any implementation code is modified.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test framework and test environment setup

- [ ] T001 Create blank test suite file `tests/test_f1tv_overlay.js`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core test harness implementation and pre-verification

**⚠️ CRITICAL**: No implementation work can begin until this phase is complete and the tests are verified as failing.

- [ ] T002 Implement unit tests in `tests/test_f1tv_overlay.js` for timing formats (`formatGapTenths`, `formatTimeTenths`) and visibility presets.
- [ ] T003 Execute test suite `node tests/test_f1tv_overlay.js` and verify that all assertions fail (timing functions undefined, HTML structures unchanged).

**Checkpoint**: TDD base ready - all tests are verified in a failing state. User story implementation can now begin.

---

## Phase 3: User Story 1 - Session Info Onboard Visibility (Priority: P1) 🎯 MVP

**Goal**: Keep Session Info visible on onboard cameras when enabled, respecting presets and manual toggles.

**Independent Test**: Run `node tests/test_f1tv_overlay.js` and verify the visibility preset test passes.

### Implementation for User Story 1

- [ ] T004 [US1] Modify `#session-info` class from `broadcast-only` to `always-visible` in `dashboard/f1tv_overlay.html`
- [ ] T005 [US1] Update `presets` in `dashboard/js/f1tv_overlay.js` to ensure `session-info` is enabled in `broadcast` preset list and excluded from `cockpit` preset list
- [ ] T006 [US1] Update `presets` in `dashboard/f1tv_control.html` to align with javascript presets
- [ ] T007 [US1] Run `node tests/test_f1tv_overlay.js` and verify User Story 1 visibility test passes

**Checkpoint**: User Story 1 is fully functional, verified by automated tests, and testable independently.

---

## Phase 4: User Story 2 - Selectable Timing in Tenths (Priority: P2)

**Goal**: Display gaps and lap times in tenths format on leaderboards, defaulting to enabled, and instantly fallback to milliseconds when disabled.

**Independent Test**: Run `node tests/test_f1tv_overlay.js` and verify both timing format tests pass.

### Implementation for User Story 2

- [ ] T008 [US2] Add dummy hidden div with ID `tenths-timing` in `dashboard/f1tv_overlay.html`
- [ ] T009 [US2] Add component `tenths-timing` to settings lists and presets in `dashboard/js/f1tv_overlay.js` and `dashboard/f1tv_control.html`
- [ ] T010 [US2] Implement helper functions `formatGapTenths(gap)` and `formatTimeTenths(sec)` in `dashboard/js/f1tv_overlay.js`
- [ ] T011 [US2] Update Mini Leaderboard gap formatting to respect `tenths-timing` toggle in `dashboard/js/f1tv_overlay.js`
- [ ] T012 [US2] Update Full Leaderboard gap and lap time formatting to respect `tenths-timing` toggle in `dashboard/js/f1tv_overlay.js`
- [ ] T013 [US2] Run `node tests/test_f1tv_overlay.js` and verify timing format tests pass

**Checkpoint**: User Story 2 is fully functional and verified by automated tests.

---

## Phase 5: User Story 3 - Larger Leaderboard Text Size (Priority: P3)

**Goal**: Scale leaderboard row heights, container widths, column layouts, and font sizes to 15px.

**Independent Test**: Open overlay in browser and verify there is no layout overlapping or name truncation.

### Implementation for User Story 3

- [ ] T014 [US3] Add CSS variable `--leaderboard-font-size: 15px` to `:root` and apply to `#mini-leaderboard` and `.flb-row` in `dashboard/css/f1tv_overlay.css`
- [ ] T015 [US3] Increase container widths and row heights in `dashboard/css/f1tv_overlay.css` to accommodate larger font
- [ ] T016 [US3] Update injected column width values (Pos: 24px, Gaps: 70px, Tyre info: 50px) in `dashboard/js/f1tv_overlay.js`
- [ ] T017 [US3] Verify visually in browser that the expanded font displays cleanly with zero clipping

**Checkpoint**: Leaderboard size is scaled, readable, and functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verification and documentation cleanup

- [ ] T018 Execute full unit test suite `node tests/test_f1tv_overlay.js` and verify all tests pass
- [ ] T019 Perform final manual verification on the live app server per quickstart instructions

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. **BLOCKS all implementation**.
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion.
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion. Can run in parallel with US1.
- **User Story 3 (Phase 5)**: Depends on Phase 4 completion (as column adjustments map directly to tenths timing text sizes).
- **Polish (Phase 6)**: Depends on completion of all implementation phases.

### Parallel Opportunities

- T004, T005, and T006 (User Story 1 setup) can be worked on in parallel.
- T008 and T009 (User Story 2 setup) can be worked on in parallel.
- User Story 1 (Phase 3) and User Story 2 (Phase 4) can be implemented in parallel.

---

## Parallel Example: User Stories 1 & 2

```bash
# Launch User Story 1 (Session Info class changes):
Task: "Modify #session-info class to always-visible in dashboard/f1tv_overlay.html"

# Launch User Story 2 (Tenths timing toggles):
Task: "Add dummy hidden div with ID tenths-timing in dashboard/f1tv_overlay.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup and Foundational test harness.
2. Complete User Story 1 implementation and verify with tests.
3. Validate manually that session info works on roof cam.

### Incremental Delivery

1. Foundation: Test suite in place.
2. Increment 1: Session Info fixed.
3. Increment 2: Tenths Timing implemented (defaulting to tenths).
4. Increment 3: Font size enlarged to 15px.
