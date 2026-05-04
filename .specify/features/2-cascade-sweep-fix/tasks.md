# Tasks: Cascade Sweep Fix

**Input**: Design documents from `.specify/features/2-cascade-sweep-fix/`
**Prerequisites**: plan.md (required), spec.md (required)

**Tests**: TDD — all test tasks MUST be written and confirmed FAILING before corresponding implementation tasks.

**Organization**: Tasks grouped by user story. Tests before code in every phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create feature branch infrastructure and verify baseline

- [x] T001 Verify all 110 existing tests pass as baseline in `tests/`
- [x] T002 Review current `_calculate_sequence_bonus` and `calculate_scores` in `core/scoring_engine.py` to confirm root cause understanding

**Checkpoint**: Baseline green, root cause confirmed

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Write the bug reproduction test that proves the defect exists before any code changes

**⚠️ CRITICAL**: This test MUST FAIL against the current code to prove the bug is real

### Bug Reproduction Test

- [x] T003 [US1] Write test `test_bug_sweep_activates_same_tick` in `tests/test_scoring_engine_sweep.py` — Call `calculate_scores()` with a full grid where P1 has `current_lap > laps_in_event` and P2-P5 are still racing. Assert that P2's `sequence_bonus` in the returned results dict is `5000.0`. **This test MUST FAIL against current code.**

**Checkpoint**: T003 confirmed FAILING — bug is proven

---

## Phase 3: User Story 1 — Cascade Sweep Activation (Priority: P1) 🎯 MVP

**Goal**: After the leader finishes, exactly one driver (P2) receives the +5,000 sweep bonus within the same scoring tick.

**Independent Test**: Run `calculate_scores()` with P1 finished and verify P2 has `sequence_bonus == 5000.0` in the results dict.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] [US1] Write test `test_prescan_detects_leader_finish` in `tests/test_scoring_engine_sweep.py` — After `calculate_scores()` with P1 at `current_lap > laps_in_event`, assert `scorer._sweep_active == True`
- [x] T005 [P] [US1] Write test `test_prescan_selects_p2_as_target` in `tests/test_scoring_engine_sweep.py` — After `calculate_scores()` with P1 finished and P2-P5 racing, assert `scorer._sweep_target_name == 'P2'`
- [x] T006 [P] [US1] Write test `test_prescan_skips_inactive_drivers` in `tests/test_scoring_engine_sweep.py` — P2 inactive, P3 active → assert `scorer._sweep_target_name == 'P3'`
- [x] T007 [P] [US1] Write test `test_prescan_skips_finished_drivers` in `tests/test_scoring_engine_sweep.py` — P1 and P2 both finished → assert `scorer._sweep_target_name == 'P3'`
- [x] T008 [P] [US1] Write test `test_exactly_one_driver_gets_sweep_bonus` in `tests/test_scoring_engine_sweep.py` — Full grid of 5, P1 finished. Count drivers in results with `sequence_bonus == 5000.0`. Assert count == 1.
- [x] T009 [P] [US1] Write test `test_sweep_bonus_goes_to_highest_position` in `tests/test_scoring_engine_sweep.py` — P1 finished, P2-P5 racing. The driver with `sequence_bonus == 5000.0` must have `race_position == 2`.
- [x] T010 [P] [US1] Write test `test_sweep_bonus_injected_into_total_score` in `tests/test_scoring_engine_sweep.py` — P1 finished, P2 is sweep target. Assert P2's `total_score` includes the 5000.0 bonus (total_score >= 5000.0).
- [x] T011 [US1] Run all new tests, confirm they FAIL against current code

### Implementation for User Story 1

- [x] T012 [US1] Implement `_pre_scan_sweep()` method in `core/scoring_engine.py` — Iterate all participants, detect finishers (`current_lap > laps_in_event`), set `_sweep_active = True` when P1 finishes, register finish timestamps, select highest-placed unfinished active driver as `_sweep_target_name`
- [x] T013 [US1] Refactor `calculate_scores()` in `core/scoring_engine.py` — Call `_pre_scan_sweep()` BEFORE the per-participant scoring loop. Remove sweep activation logic from `_calculate_sequence_bonus()`. Remove the old sweep target selection block from top of `calculate_scores()`.
- [x] T014 [US1] Simplify `_calculate_sequence_bonus()` in `core/scoring_engine.py` — Remove all sweep activation/detection code. Method becomes a pure reader: if `name == _sweep_target_name` return 5000.0, if final lap leader conditions return 10000.0, else 0.0.
- [x] T015 [US1] Run all US1 tests, confirm they PASS
- [x] T016 [US1] Run full test suite (110 existing + new), confirm zero regressions

**Checkpoint**: Sweep activates same-tick as leader finish. Exactly one driver gets +5,000. Bug reproduction test T003 now PASSES.

---

## Phase 4: User Story 2 — Cascade Progression (Priority: P1)

**Goal**: As each driver crosses the finish line, the sweep target cascades down the grid: P2 → P3 → P4 → etc.

**Independent Test**: Simulate multi-tick progression where P1 finishes, then P2 finishes, verify target moves to P3.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T017 [P] [US2] Write test `test_cascade_p1_to_p2_to_p3` in `tests/test_scoring_engine_sweep.py` — Tick 1: P1 finished, P2-P5 racing → P2 gets bonus. Tick 2: P1+P2 finished, P3-P5 racing → P3 gets bonus.
- [x] T018 [P] [US2] Write test `test_cascade_all_finished_no_bonus` in `tests/test_scoring_engine_sweep.py` — All 5 drivers finished → no `sequence_bonus` for anyone, `_sweep_target_name` is None.
- [x] T019 [P] [US2] Write test `test_sweep_deactivates_when_all_done` in `tests/test_scoring_engine_sweep.py` — All drivers finished → after enough ticks for dwell to expire, assert normal scoring resumes (no 5000.0 bonuses anywhere in results).
- [x] T020 [US2] Run all US2 tests, confirm current state (may partially pass if US1 impl handles it)

### Implementation for User Story 2

- [x] T021 [US2] Update `_pre_scan_sweep()` in `core/scoring_engine.py` — When all eligible drivers are finished and past dwell, set `_sweep_target_name = None`. If no eligible drivers remain at all, set `_sweep_active = False` (FR-009).
- [x] T022 [US2] Run all US1 + US2 tests, confirm they PASS
- [x] T023 [US2] Run full test suite, confirm zero regressions

**Checkpoint**: Cascade progresses correctly P2 → P3 → P4. Sweep deactivates when everyone is done.

---

## Phase 5: User Story 3 — Dwell After Finish (Priority: P2)

**Goal**: When the sweep target crosses the finish line, hold focus for a configurable dwell period measured in game time, not wall-clock time.

**Independent Test**: Simulate a finisher as sweep target, verify they hold focus for the correct game-time duration before cascading.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T024 [P] [US3] Write test `test_dwell_holds_finisher_as_target` in `tests/test_scoring_engine_sweep.py` — P2 finishes at game time 120.0s while sweep target. Next call to `calculate_scores` at game time 120.5s still has `_sweep_target_name == 'P2'`.
- [x] T025 [P] [US3] Write test `test_dwell_expires_after_game_time` in `tests/test_scoring_engine_sweep.py` — P2 finishes at game time 120.0s. Call `calculate_scores` at game time 121.5s (>1.0s dwell). Assert `_sweep_target_name == 'P3'`.
- [x] T026 [P] [US3] Write test `test_dwell_time_configurable` in `tests/test_scoring_engine_sweep.py` — Set `sweep_dwell_time = 3.0`. P2 finishes at game time 120.0s. At game time 122.0s, P2 still holds. At game time 123.5s, P3 takes over.
- [x] T027 [US3] Run all US3 tests, confirm they FAIL

### Implementation for User Story 3

- [x] T028 [US3] Update `_pre_scan_sweep()` in `core/scoring_engine.py` to accept `current_time` parameter — Record `current_time` when a driver finishes. Dwell expires when `current_time - finish_time > sweep_dwell_time`.
- [x] T029 [US3] Update `calculate_scores()` in `core/scoring_engine.py` to pass `current_time` into `_pre_scan_sweep()`
- [x] T030 [US3] Run all US3 tests, confirm they PASS
- [x] T031 [US3] Run full test suite, confirm zero regressions

**Checkpoint**: Dwell works game-time-based. Configurable from GUI. Replay-safe.

---

## Phase 6: Anti-Regression & Polish

**Purpose**: Final validation that nothing from feature/1-final-lap-sequence is broken

### Anti-Regression Tests

- [x] T032 [P] Write test `test_leader_final_lap_bonus_unchanged` in `tests/test_scoring_engine_sweep.py` — P1 on final lap past midpoint → still gets +10,000 via `calculate_scores()` results.
- [x] T033 [P] Write test `test_no_sweep_before_leader_finishes` in `tests/test_scoring_engine_sweep.py` — P1 still on final lap → no sweep bonus for anyone in results.
- [x] T034 [P] Write test `test_timeline_fallback_still_works` in `tests/test_scoring_engine_sweep.py` — `laps_in_event=0`, `timeline_laps_in_event=13` → sweep activates correctly via `calculate_scores()`.
- [x] T035 Run ALL tests (existing 110 + all new sweep tests), confirm 100% pass

### Cleanup

- [x] T036 Remove any dead code from old sweep logic in `core/scoring_engine.py`
- [x] T037 Update existing `tests/test_scoring_engine_sequence.py` to align with refactored method signatures (if any changed)
- [x] T038 Commit all changes to `feature/2-cascade-sweep-fix` branch

**Checkpoint**: Full green suite. Feature complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Bug Reproduction)**: Depends on Phase 1 — MUST confirm FAIL before proceeding
- **Phase 3 (US1 - Sweep Activation)**: Depends on Phase 2 — core fix, BLOCKS all other stories
- **Phase 4 (US2 - Cascade Progression)**: Depends on Phase 3 — may partially work after US1
- **Phase 5 (US3 - Dwell)**: Depends on Phase 3 — independent of Phase 4
- **Phase 6 (Polish)**: Depends on all stories complete

### User Story Dependencies

- **US1 (Sweep Activation)**: MUST complete first — all other stories depend on the two-pass architecture
- **US2 (Cascade Progression)**: Depends on US1 only
- **US3 (Dwell After Finish)**: Depends on US1 only, independent of US2

### Within Each User Story

1. Write ALL tests for the story (T004-T011, T017-T020, T024-T027)
2. Confirm tests FAIL
3. Implement code changes
4. Confirm tests PASS
5. Run full suite for regression check

### Parallel Opportunities

- T004-T010 can all be written in parallel (different test methods, same file)
- T017-T019 can all be written in parallel
- T024-T026 can all be written in parallel
- T034-T036 can all be written in parallel
- US2 and US3 implementation can run in parallel after US1 completes

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Verify baseline
2. Complete Phase 2: Bug reproduction test FAILS
3. Complete Phase 3: Implement two-pass architecture
4. **STOP and VALIDATE**: T003 (bug reproduction) now PASSES
5. Run full suite — zero regressions

### Incremental Delivery

1. Phase 1+2 → Bug proven
2. Phase 3 (US1) → Core fix deployed, P2 gets sweep bonus
3. Phase 4 (US2) → Full cascade P2→P3→P4 working
4. Phase 5 (US3) → Game-time dwell, replay-safe
5. Phase 6 → Anti-regression, cleanup, commit

---

## Notes

- All tests go in a NEW file `tests/test_scoring_engine_sweep.py` to avoid conflicts with existing `test_scoring_engine_sequence.py`
- Tests use `calculate_scores()` (public API) not internal methods, to verify end-to-end injection
- T010 specifically verifies the sweep bonus appears in `total_score` (the value the GUI reads)
- Tick-based dwell replaced with game-time dwell using `current_time` — replay-safe because game time only advances when the simulation advances
- Existing tests in `test_scoring_engine_sequence.py` are left untouched unless method signatures change
