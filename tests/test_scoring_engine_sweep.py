"""Tests for Cascade Sweep Fix (feature/2-cascade-sweep-fix).

All tests use calculate_scores() (public API) to verify end-to-end behaviour.
Tests are written TDD-first — they MUST fail before implementation.
"""
import unittest
from core.scoring_engine import ScoringEngine


def _make_grid(laps_in_event, drivers):
    """Helper: build participants dict, session_info, track_info from a compact driver spec.
    
    drivers: list of dicts, each with keys:
        name, race_position, current_lap, is_active (default True),
        lap_distance (default 0.0)
    """
    participants = {}
    for i, d in enumerate(drivers):
        participants[i] = {
            'name': d['name'],
            'race_position': d['race_position'],
            'current_lap': d['current_lap'],
            'lap_distance': d.get('lap_distance', 0.0),
            'is_active': d.get('is_active', True),
            'speed': d.get('speed', 200.0),
            'pit_mode': d.get('pit_mode', 0),
            'cars_ahead': d.get('cars_ahead', 0),
            'gap_ahead': d.get('gap_ahead', 999.0),
            'closing_speed': d.get('closing_speed', 0.0),
        }
    session_info = {'laps_in_event': laps_in_event}
    track_info = {'track_length': 4000}
    return participants, session_info, track_info


def _get_sequence_bonuses(results, participants):
    """Extract {name: sequence_bonus} from calculate_scores results."""
    bonuses = {}
    for idx, score_entry in results.items():
        name = participants[idx]['name']
        bonuses[name] = score_entry.get('sequence_bonus', 0.0)
    return bonuses


class TestCascadeSweep(unittest.TestCase):
    """Phase 2+3: Cascade Sweep Activation (US1)"""

    def setUp(self):
        self.scorer = ScoringEngine()

    # ── T003: Bug Reproduction ────────────────────────────────────────
    def test_bug_sweep_activates_same_tick(self):
        """T003: On the tick P1 finishes, P2 MUST receive the sweep bonus.
        This test MUST FAIL against the current (broken) code."""
        participants, session_info, track_info = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},  # finished
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
            {'name': 'P4', 'race_position': 4, 'current_lap': 10},
            {'name': 'P5', 'race_position': 5, 'current_lap': 10},
        ])
        results = self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        bonuses = _get_sequence_bonuses(results, participants)
        self.assertEqual(bonuses['P2'], 5000.0,
                         "P2 must get +5000 sweep bonus on the same tick P1 finishes")

    # ── T004: Pre-scan detects leader finish ──────────────────────────
    def test_prescan_detects_leader_finish(self):
        """T004: After calculate_scores with P1 finished, _sweep_active must be True."""
        participants, session_info, track_info = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        self.assertTrue(self.scorer._sweep_active)

    # ── T005: Pre-scan selects P2 as target ───────────────────────────
    def test_prescan_selects_p2_as_target(self):
        """T005: After calculate_scores with P1 finished, sweep target must be P2."""
        participants, session_info, track_info = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        self.assertEqual(self.scorer._sweep_target_name, 'P2')

    # ── T006: Pre-scan skips inactive drivers ─────────────────────────
    def test_prescan_skips_inactive_drivers(self):
        """T006: P2 inactive, P3 active → sweep target must be P3."""
        participants, session_info, track_info = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10, 'is_active': False},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        self.assertEqual(self.scorer._sweep_target_name, 'P3')

    # ── T007: Pre-scan skips finished drivers ─────────────────────────
    def test_prescan_skips_finished_drivers(self):
        """T007: P1 and P2 both finished → sweep target must be P3."""
        participants, session_info, track_info = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 11},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        self.assertEqual(self.scorer._sweep_target_name, 'P3')

    # ── T008: Exactly one driver gets sweep bonus ─────────────────────
    def test_exactly_one_driver_gets_sweep_bonus(self):
        """T008: Full grid of 5, P1 finished. Exactly 1 driver gets 5000."""
        participants, session_info, track_info = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
            {'name': 'P4', 'race_position': 4, 'current_lap': 10},
            {'name': 'P5', 'race_position': 5, 'current_lap': 10},
        ])
        results = self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        bonuses = _get_sequence_bonuses(results, participants)
        count = sum(1 for v in bonuses.values() if v == 5000.0)
        self.assertEqual(count, 1, f"Exactly 1 driver should get 5000, got {count}: {bonuses}")

    # ── T009: Sweep bonus goes to highest position ────────────────────
    def test_sweep_bonus_goes_to_highest_position(self):
        """T009: The driver with 5000.0 must have race_position == 2."""
        participants, session_info, track_info = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
            {'name': 'P4', 'race_position': 4, 'current_lap': 10},
            {'name': 'P5', 'race_position': 5, 'current_lap': 10},
        ])
        results = self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        for idx, score_entry in results.items():
            if score_entry['sequence_bonus'] == 5000.0:
                self.assertEqual(participants[idx]['race_position'], 2)
                return
        self.fail("No driver received the 5000.0 sweep bonus")

    # ── T010: Sweep bonus injected into total_score ───────────────────
    def test_sweep_bonus_injected_into_total_score(self):
        """T010: P2's total_score must include the 5000.0 sweep bonus."""
        participants, session_info, track_info = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        results = self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        # Find P2's result
        p2_total = None
        for idx, score_entry in results.items():
            if participants[idx]['name'] == 'P2':
                p2_total = score_entry['total_score']
                break
        self.assertIsNotNone(p2_total)
        self.assertGreaterEqual(p2_total, 5000.0,
                                f"P2 total_score should be >= 5000.0, got {p2_total}")


class TestCascadeProgression(unittest.TestCase):
    """Phase 4: Cascade Progression (US2)"""

    def setUp(self):
        self.scorer = ScoringEngine()

    # ── T017: Cascade P1 → P2 → P3 ───────────────────────────────────
    def test_cascade_p1_to_p2_to_p3(self):
        """T017: Tick 1: P1 finished → P2 bonus. Tick 2: P1+P2 finished, dwell expired → P3 bonus."""
        # Tick 1: only P1 finished
        p_tick1, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        results1 = self.scorer.calculate_scores(p_tick1, si, ti, current_time=100.0)
        bonuses1 = _get_sequence_bonuses(results1, p_tick1)
        self.assertEqual(bonuses1['P2'], 5000.0, f"Tick 1: P2 should get bonus, got {bonuses1}")

        # Tick 2: P2 also finishes
        p_tick2, _, _ = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 11},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        # P2 finishes at 110.0s — dwell holds P2 until 111.0s
        self.scorer.calculate_scores(p_tick2, si, ti, current_time=110.0)

        # Tick 3: Past dwell (112.0s > 110.0 + 1.0 dwell) → P3 takes over
        results3 = self.scorer.calculate_scores(p_tick2, si, ti, current_time=112.0)
        bonuses3 = _get_sequence_bonuses(results3, p_tick2)
        self.assertEqual(bonuses3['P3'], 5000.0, f"Tick 3: P3 should get bonus after dwell, got {bonuses3}")

    # ── T018: All finished → no bonus ─────────────────────────────────
    def test_cascade_all_finished_no_bonus(self):
        """T018: All drivers finished → no sequence bonus for anyone."""
        participants, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 11},
            {'name': 'P3', 'race_position': 3, 'current_lap': 11},
        ])
        results = self.scorer.calculate_scores(participants, si, ti, current_time=200.0)
        bonuses = _get_sequence_bonuses(results, participants)
        for name, bonus in bonuses.items():
            self.assertEqual(bonus, 0.0, f"{name} should have 0 bonus, got {bonus}")

    # ── T019: Sweep deactivates when all done ─────────────────────────
    def test_sweep_deactivates_when_all_done(self):
        """T019: All drivers finished → sweep deactivates."""
        participants, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 11},
            {'name': 'P3', 'race_position': 3, 'current_lap': 11},
        ])
        # Multiple calls to let dwell expire
        for t in [200.0, 202.0, 204.0]:
            self.scorer.calculate_scores(participants, si, ti, current_time=t)
        self.assertIsNone(self.scorer._sweep_target_name)


class TestDwellBehaviour(unittest.TestCase):
    """Phase 5: Dwell After Finish (US3)"""

    def setUp(self):
        self.scorer = ScoringEngine()

    # ── T024: Dwell holds finisher as target ──────────────────────────
    def test_dwell_holds_finisher_as_target(self):
        """T024: P2 finishes at 120.0s. At 120.5s, P2 still holds as sweep target."""
        # Tick 1: P1 finished, P2 racing → P2 becomes target
        p1, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(p1, si, ti, current_time=119.0)
        self.assertEqual(self.scorer._sweep_target_name, 'P2')

        # Tick 2: P2 also finishes at game time 120.0s
        p2, _, _ = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 11},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(p2, si, ti, current_time=120.0)

        # Tick 3: 0.5s later — P2 should still hold (within 1.0s dwell)
        self.scorer.calculate_scores(p2, si, ti, current_time=120.5)
        self.assertEqual(self.scorer._sweep_target_name, 'P2',
                         "P2 should hold as target during dwell period")

    # ── T025: Dwell expires after game time ───────────────────────────
    def test_dwell_expires_after_game_time(self):
        """T025: P2 finishes at 120.0s. At 121.5s (>1.0s dwell), P3 takes over."""
        # Tick 1: P1 finished, P2 becomes target
        p1, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(p1, si, ti, current_time=119.0)

        # Tick 2: P2 finishes at 120.0s
        p2, _, _ = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 11},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(p2, si, ti, current_time=120.0)

        # Tick 3: 1.5s later — dwell expired, P3 should take over
        self.scorer.calculate_scores(p2, si, ti, current_time=121.5)
        self.assertEqual(self.scorer._sweep_target_name, 'P3',
                         "After dwell expires, P3 should become sweep target")

    # ── T026: Dwell time configurable ─────────────────────────────────
    def test_dwell_time_configurable(self):
        """T026: sweep_dwell_time=3.0. At 122.0s P2 holds. At 123.5s P3 takes over."""
        self.scorer.sweep_dwell_time = 3.0

        # Tick 1: P1 finished, P2 becomes target
        p1, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(p1, si, ti, current_time=119.0)

        # Tick 2: P2 finishes at 120.0s
        p2, _, _ = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 11},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        self.scorer.calculate_scores(p2, si, ti, current_time=120.0)

        # At 122.0s — within 3.0s dwell — P2 should still hold
        self.scorer.calculate_scores(p2, si, ti, current_time=122.0)
        self.assertEqual(self.scorer._sweep_target_name, 'P2',
                         "At 122.0s (2.0s into 3.0s dwell), P2 should still hold")

        # At 123.5s — past 3.0s dwell — P3 should take over
        self.scorer.calculate_scores(p2, si, ti, current_time=123.5)
        self.assertEqual(self.scorer._sweep_target_name, 'P3',
                         "At 123.5s (3.5s past finish, > 3.0s dwell), P3 should take over")


class TestAntiRegression(unittest.TestCase):
    """Phase 6: Anti-Regression"""

    def setUp(self):
        self.scorer = ScoringEngine()

    # ── T032: Leader final lap bonus unchanged ────────────────────────
    def test_leader_final_lap_bonus_unchanged(self):
        """T032: P1 on final lap past midpoint → still gets +10,000."""
        participants, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 10, 'lap_distance': 2500.0},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        results = self.scorer.calculate_scores(participants, si, ti, current_time=90.0)
        bonuses = _get_sequence_bonuses(results, participants)
        self.assertEqual(bonuses['P1'], 10000.0)

    # ── T033: No sweep before leader finishes ─────────────────────────
    def test_no_sweep_before_leader_finishes(self):
        """T033: P1 still on final lap → no sweep bonus for anyone."""
        participants, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 10, 'lap_distance': 1000.0},
            {'name': 'P2', 'race_position': 2, 'current_lap': 10},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        results = self.scorer.calculate_scores(participants, si, ti, current_time=90.0)
        bonuses = _get_sequence_bonuses(results, participants)
        for name, bonus in bonuses.items():
            self.assertNotEqual(bonus, 5000.0, f"{name} should NOT have sweep bonus")

    # ── T034: Timeline fallback still works ───────────────────────────
    def test_timeline_fallback_still_works(self):
        """T034: laps_in_event=0, timeline_laps_in_event=13 → sweep activates."""
        self.scorer.timeline_laps_in_event = 13
        participants, si, ti = _make_grid(0, [  # laps_in_event=0
            {'name': 'P1', 'race_position': 1, 'current_lap': 14},  # > 13
            {'name': 'P2', 'race_position': 2, 'current_lap': 13},
            {'name': 'P3', 'race_position': 3, 'current_lap': 13},
        ])
        results = self.scorer.calculate_scores(participants, si, ti, current_time=100.0)
        bonuses = _get_sequence_bonuses(results, participants)
        self.assertEqual(bonuses['P2'], 5000.0,
                         f"P2 should get sweep bonus with timeline fallback, got {bonuses}")


if __name__ == '__main__':
    unittest.main()
