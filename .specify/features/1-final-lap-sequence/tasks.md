# Task Execution Plan: Final Lap Sequence & Cooldown Sweep

## Strategy
This execution plan follows a strict Test-Driven Development (TDD) approach, delivering the highest priority User Story (US1: Leader Final Lap Coverage) first, followed by US2 (Cascading Cooldown Sweep). Granular testing tasks are explicitly ordered *before* implementation tasks to satisfy the specification's architectural intent.

## Dependencies & Phase Order
1. **Phase 1: Foundation**: Test infrastructure and core fixes.
2. **Phase 2: US1 - Leader Final Lap**: Stateful detection of the leader crossing 50% track distance.
3. **Phase 3: US2 - Cooldown Sweep**: Stateful tracking of finished drivers and cascading camera logic.

---

## Phase 1: Foundation & Pre-requisites

- [ ] T001 Initialize `tests/test_scoring_engine_sequence.py` with standard `unittest` boilerplate.
- [ ] T002 Write test in `tests/test_camera_controller.py` ensuring `move_to_position` does not send ENTER if `target_pos == current_pos`.
- [ ] T003 Fix `move_to_position` in `core/camera_controller.py` to return early when `delta == 0`.

---

## Phase 2: US1 - Leader Final Lap Coverage
**Goal**: Auto Director locks onto the race leader halfway through the final lap.

### TDD Setup (Before Code)
- [ ] T004 [US1] Write test `test_leader_midpoint_bonus` in `tests/test_scoring_engine_sequence.py` ensuring P1 gets +10000 points when `current_lap == laps_in_event` and `lap_distance >= track_length / 2`.
- [ ] T005 [US1] Write test `test_leader_midpoint_negative` ensuring P1 gets NO bonus if `lap_distance < track_length / 2`.
- [ ] T006 [US1] Write test `test_non_leader_no_bonus` ensuring P2 gets NO bonus even if they cross 50% distance.
- [ ] T007 [US1] Write test `test_is_sweep_active_false` ensuring `is_sweep_active` property returns `False` during US1 conditions.

### Implementation
- [ ] T008 [US1] Implement `_calculate_sequence_bonus(self, p, session_info, track_info)` in `core/scoring_engine.py` addressing Leader Trackside bonus (+10000).
- [ ] T009 [US1] Update `calculate_scores` signature in `core/scoring_engine.py` to accept `session_info` and `track_info`.
- [ ] T010 [US1] Call `_calculate_sequence_bonus` inside `calculate_scores` in `core/scoring_engine.py` and add it to `total_score`.
- [ ] T011 [US1] Update `main.py` `_tick()` to extract `track_info` and `session_info` early and pass them into `self.scorer.calculate_scores(participants, session_info, track_info)`.

---

## Phase 3: US2 - Cascading Cooldown Sweep
**Goal**: Auto Director sweeps the grid with a rapid 1.0s interval after the leader finishes.

### TDD Setup (Before Code)
- [ ] T012 [US2] Write test `test_sweep_active_true` in `tests/test_scoring_engine_sequence.py` ensuring `is_sweep_active` returns `True` if leader has finished (`current_lap > laps_in_event`).
- [ ] T013 [US2] Write test `test_cooldown_sweep_bonus` ensuring the highest-placed driver *not* in `finished_participants` gets +5000 points during a sweep.
- [ ] T014 [US2] Write test `test_finished_participants_exclusion` ensuring that when a driver's `current_lap > laps_in_event`, they are added to `finished_participants` and get 0 sequence bonus.

### Implementation
- [ ] T015 [US2] Add `finished_participants = set()` to `ScoringEngine.__init__` in `core/scoring_engine.py`.
- [ ] T016 [US2] Expose `@property def is_sweep_active(self)` in `core/scoring_engine.py`.
- [ ] T017 [US2] Update `_calculate_sequence_bonus` in `core/scoring_engine.py` to detect finishes, append to `finished_participants`, and apply the +5000 Cooldown Sweep bonus.
- [ ] T018 [US2] Add `Sweep Dwell (s)` tuning UI field in `main.py` bound to `self._sweep_dwell_time = 1.0`.
- [ ] T019 [US2] Update `main.py` `_tick()` interval logic: `interval = self._sweep_dwell_time if self.scorer.is_sweep_active else self._switch_interval`.

---

## Final Phase: Polish & Validation
- [ ] T020 Run `pytest tests/test_scoring_engine_sequence.py tests/test_camera_controller.py` to confirm 100% test passing.
- [ ] T021 Validate `main.py` GUI renders correctly and tuning applies to `_sweep_dwell_time`.
