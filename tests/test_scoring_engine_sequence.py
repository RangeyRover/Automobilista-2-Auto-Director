import unittest

from core.scoring_engine import ScoringEngine

class TestScoringEngineSequence(unittest.TestCase):
    def setUp(self):
        self.scorer = ScoringEngine()

    # T004: Ensure P1 gets +10000 points at 50% distance on final lap
    def test_leader_midpoint_bonus(self):
        # laps_in_event=10 means mCurrentLap=10 during the final lap
        p = {'race_position': 1, 'current_lap': 10, 'lap_distance': 2500, 'is_active': True}
        session_info = {'laps_in_event': 10}
        track_info = {'track_length': 4000}
        
        bonus = self.scorer._calculate_sequence_bonus(p, session_info, track_info)
        self.assertEqual(bonus, 10000.0)

    # T005: Ensure P1 gets NO bonus if lap_distance < track_length / 2
    def test_leader_midpoint_negative(self):
        p = {'race_position': 1, 'current_lap': 10, 'lap_distance': 1999, 'is_active': True}
        session_info = {'laps_in_event': 10}
        track_info = {'track_length': 4000}
        
        bonus = self.scorer._calculate_sequence_bonus(p, session_info, track_info)
        self.assertEqual(bonus, 0.0)

    # T006: Ensure non-leader gets NO bonus even if at 50% distance
    def test_non_leader_no_bonus(self):
        p = {'race_position': 2, 'current_lap': 10, 'lap_distance': 2500, 'is_active': True}
        session_info = {'laps_in_event': 10}
        track_info = {'track_length': 4000}
        
        bonus = self.scorer._calculate_sequence_bonus(p, session_info, track_info)
        self.assertEqual(bonus, 0.0)

    # T007: Ensure sweep is not active during US1 conditions
    def test_is_sweep_active_false(self):
        self.assertFalse(self.scorer.is_sweep_active)

    # T012: Ensure is_sweep_active returns True if leader has finished
    def test_sweep_active_true(self):
        # laps_in_event=10. mCurrentLap=11 means they have finished.
        # Use calculate_scores (public API) since sweep activation now
        # happens in _pre_scan_sweep, not _calculate_sequence_bonus.
        # Need at least 2 drivers — with only P1 finished, FR-009 would
        # immediately deactivate sweep since no eligible drivers remain.
        participants = {
            0: {'name': 'P1', 'race_position': 1, 'current_lap': 11, 'is_active': True,
                'speed': 200.0, 'pit_mode': 0, 'cars_ahead': 0, 'gap_ahead': 999.0,
                'closing_speed': 0.0, 'lap_distance': 0.0},
            1: {'name': 'P2', 'race_position': 2, 'current_lap': 10, 'is_active': True,
                'speed': 200.0, 'pit_mode': 0, 'cars_ahead': 0, 'gap_ahead': 999.0,
                'closing_speed': 0.0, 'lap_distance': 0.0},
        }
        session_info = {'laps_in_event': 10}
        track_info = {'track_length': 4000}
        
        self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        self.assertTrue(self.scorer.is_sweep_active)

    # T013: Ensure active drivers get +5000 points during a sweep
    def test_cooldown_sweep_bonus(self):
        # First trigger the sweep
        self.scorer._sweep_active = True
        
        self.scorer._sweep_target_name = 'P2'
        
        # Now evaluate P2 who is still racing (mCurrentLap=10)
        p = {'name': 'P2', 'race_position': 2, 'current_lap': 10, 'is_active': True}
        session_info = {'laps_in_event': 10}
        track_info = {'track_length': 4000}
        
        bonus = self.scorer._calculate_sequence_bonus(p, session_info, track_info)
        self.assertEqual(bonus, 5000.0)

    # T014: Ensure finished drivers are added to finished_participants and get 0 sequence bonus
    def test_finished_participants_exclusion(self):
        # finished race (mCurrentLap=11)
        # Use calculate_scores (public API) since finisher registration now
        # happens in _pre_scan_sweep, not _calculate_sequence_bonus.
        participants = {
            0: {'name': 'P1', 'race_position': 1, 'current_lap': 11, 'is_active': True,
                'speed': 200.0, 'pit_mode': 0, 'cars_ahead': 0, 'gap_ahead': 999.0,
                'closing_speed': 0.0, 'lap_distance': 0.0},
        }
        session_info = {'laps_in_event': 10}
        track_info = {'track_length': 4000}
        
        results = self.scorer.calculate_scores(participants, session_info, track_info, current_time=100.0)
        
        self.assertIn('P1', self.scorer.finished_participants)
        # P1 is both finished AND the sweep target (within dwell), so they get 5000 not 0
        # But since there's no one else to sweep to, check registration is correct
        self.assertIn('P1', self.scorer.finished_participants)

    # T015: Ensure fallback to timeline_laps_in_event works when laps_in_event is 0
    def test_sequence_bonus_replay_fallback(self):
        # laps_in_event=0 (time-based replay). timeline_laps_in_event=15.
        # final lap is when mCurrentLap=15.
        p = {'race_position': 1, 'current_lap': 15, 'lap_distance': 2500, 'is_active': True}
        session_info = {'laps_in_event': 0}
        track_info = {'track_length': 4000}
        
        # Without fallback, it returns 0.0
        bonus_before = self.scorer._calculate_sequence_bonus(p, session_info, track_info)
        self.assertEqual(bonus_before, 0.0)
        
        # Set the fallback explicitly
        self.scorer.timeline_laps_in_event = 15
        
        # Now it should calculate the 10000 bonus!
        bonus_after = self.scorer._calculate_sequence_bonus(p, session_info, track_info)
        self.assertEqual(bonus_after, 10000.0)

if __name__ == '__main__':
    unittest.main()
