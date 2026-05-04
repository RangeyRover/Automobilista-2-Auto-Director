import unittest
from core.scoring_engine import ScoringEngine

def _make_grid(laps_in_event, drivers):
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

class TestReplayLoopHandling(unittest.TestCase):
    def setUp(self):
        self.scorer = ScoringEngine()

    def test_replay_loop_resets_sweep_state(self):
        """T039: If the replay loops (current_time goes backwards), sweep state must be reset."""
        # 1. End of race: P1 and P2 finished
        p_end, si, ti = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 11},
            {'name': 'P2', 'race_position': 2, 'current_lap': 11},
            {'name': 'P3', 'race_position': 3, 'current_lap': 10},
        ])
        
        # Call at time 120.0
        self.scorer.calculate_scores(p_end, si, ti, current_time=120.0)
        self.assertTrue(self.scorer._sweep_active)
        self.assertIn('P1', self.scorer.finished_participants)
        self.assertEqual(self.scorer._sweep_target_name, 'P3')

        # 2. Replay loops back to start: laps back to 1, time back to 0.0
        p_start, _, _ = _make_grid(10, [
            {'name': 'P1', 'race_position': 1, 'current_lap': 1},
            {'name': 'P2', 'race_position': 2, 'current_lap': 1},
            {'name': 'P3', 'race_position': 3, 'current_lap': 1},
        ])
        
        # Call at time 0.0 (jumped backwards by 120 seconds)
        self.scorer.calculate_scores(p_start, si, ti, current_time=0.0)
        
        # State should be completely reset
        self.assertFalse(self.scorer._sweep_active, "Sweep should deactivate on replay loop")
        self.assertIsNone(self.scorer._sweep_target_name, "Sweep target should clear on replay loop")
        self.assertEqual(len(self.scorer.finished_participants), 0, "Finished participants should clear on replay loop")

if __name__ == '__main__':
    unittest.main()
