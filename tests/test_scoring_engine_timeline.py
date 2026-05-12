import unittest
from core.scoring_engine import ScoringEngine

class TestScoringEngineTimeline(unittest.TestCase):
    def setUp(self):
        self.engine = ScoringEngine()
        # Mock some parsed timeline events in the engine
        self.engine.timeline_events = [
            {
                'type': 'Accident',
                'timestamp': 100.0,
                'target_driver': 'Crashy',
                'base_score': 6.0,
                'duration': 15.0
            },
            {
                'type': 'Overtake',
                'timestamp': 200.0,
                'target_driver': 'Passer',
                'target_driver_2': 'Passed',
                'base_score': 4.0,
                'duration': 12.0
            }
        ]

    # T008: Active event bonus
    def test_timeline_bonus_active(self):
        participant = {'name': 'Crashy', 'is_active': True}
        # current_time = 105.0 is within [100.0, 115.0]
        acc, ovt = self.engine._calculate_timeline_bonus(participant, current_time=105.0)
        self.assertEqual(acc, 6.0)
        self.assertEqual(ovt, 0.0)

    # T009: Expired event bonus
    def test_timeline_bonus_expired(self):
        participant = {'name': 'Crashy', 'is_active': True}
        # event is at 100.0, pre_offset is 15.0, post_offset is 10.0
        # window is [85.0, 110.0]
        # current_time = 115.0 is past 110.0
        acc, ovt = self.engine._calculate_timeline_bonus(participant, current_time=115.0)
        self.assertEqual(acc, 0.0)
        self.assertEqual(ovt, 0.0)
        
        # current_time = 84.0 is before window starts (85.0)
        acc_early, ovt_early = self.engine._calculate_timeline_bonus(participant, current_time=84.0)
        self.assertEqual(acc_early, 0.0)
        self.assertEqual(ovt_early, 0.0)

    # T011: Pre-offset active bonus
    def test_timeline_bonus_pre_offset(self):
        participant = {'name': 'Crashy', 'is_active': True}
        # event is at 100.0. window is [85.0, 110.0].
        # current_time = 90.0 is before event, but inside the pre-offset window.
        acc, ovt = self.engine._calculate_timeline_bonus(participant, current_time=90.0)
        self.assertEqual(acc, 6.0)
        self.assertEqual(ovt, 0.0)

    # T010: Target 2 bonus (Overtakes)
    def test_timeline_bonus_target2(self):
        participant_1 = {'name': 'Passer', 'is_active': True}
        participant_2 = {'name': 'Passed', 'is_active': True}
        
        # event is at 200.0, pre is 15.0, post is 10.0
        # window is [185.0, 210.0]
        # current_time = 205.0 is within [185.0, 210.0]
        acc_1, ovt_1 = self.engine._calculate_timeline_bonus(participant_1, current_time=205.0)
        acc_2, ovt_2 = self.engine._calculate_timeline_bonus(participant_2, current_time=205.0)
        
        # Both drivers involved in the overtake should receive the decayed bonus nudge
        # event is at 200.0, current_time is 205.0. 5.0s past event.
        # post_offset is 10.0, so decay ratio is 1.0 - 5.0/10.0 = 0.5
        # 4.0 * 0.5 = 2.0
        self.assertEqual(acc_1, 0.0)
        self.assertEqual(ovt_1, 2.0)
        self.assertEqual(acc_2, 0.0)
        self.assertEqual(ovt_2, 2.0)

    # T016: Load timeline log footer fallback variables
    def test_load_timeline_log_footer_events(self):
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as f:
            f.write("02:09.41 - Accident involving: Ludwig\n")
            f.write("Total Session Time: 15:30.50\n")
            f.write("Leader Laps Completed: 24\n")
            temp_name = f.name
            
        try:
            self.engine.load_timeline_log(temp_name)
            self.assertEqual(self.engine.timeline_laps_in_event, 23)
            self.assertEqual(self.engine.timeline_session_time, 930.5)
            self.assertEqual(len(self.engine.timeline_events), 1)
            self.assertEqual(self.engine.timeline_events[0]['type'], 'Accident')
        finally:
            os.unlink(temp_name)

if __name__ == '__main__':
    unittest.main()
