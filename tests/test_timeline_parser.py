import unittest
from core.timeline_parser import TimelineParser

class TestTimelineParser(unittest.TestCase):
    def setUp(self):
        self.parser = TimelineParser()

    # T001: Parse Accident
    def test_parse_invalid(self):
        line = "Just some random log text without timestamp"
        self.assertIsNone(self.parser.parse_line(line))

    def test_parse_leader_laps(self):
        line = "Leader Laps Completed: 24"
        event = self.parser.parse_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event['type'], 'Leader Laps Completed')
        self.assertEqual(event['lap'], 23)

    def test_parse_total_session_time(self):
        line = "Total Session Time: 15:30.50"
        event = self.parser.parse_line(line)
        self.assertIsNotNone(event)
        self.assertEqual(event['type'], 'Total Session Time')
        self.assertEqual(event['timestamp'], 930.5)

    def test_parse_accident(self):
        line = "02:09.41 - Accident involving: Ludwig"
        event = self.parser.parse_line(line)
        
        self.assertIsNotNone(event)
        self.assertEqual(event['type'], 'Accident')
        self.assertEqual(event['timestamp'], 129.41)
        self.assertEqual(event['target_driver'], 'Ludwig')
        self.assertEqual(event['base_score'], 6.0)
        self.assertEqual(event['duration'], 15.0)

    # T002: Parse Overtake
    def test_parse_overtake(self):
        line = "00:05.33 - Overtake! SzakicMo overtook LUISO_1995 for position 6"
        event = self.parser.parse_line(line)
        
        self.assertIsNotNone(event)
        self.assertEqual(event['type'], 'Overtake')
        self.assertEqual(event['timestamp'], 5.33)
        self.assertEqual(event['target_driver'], 'SzakicMo')
        self.assertEqual(event['target_driver_2'], 'LUISO_1995')
        self.assertEqual(event['base_score'], 4.0)
        self.assertEqual(event['duration'], 12.0)

    # T003: Ignore Close Battle
    def test_ignore_close_battle(self):
        line = "00:44.84 - Close Battle! SzakicMo is pressuring LUISO_1995"
        event = self.parser.parse_line(line)
        
        self.assertIsNone(event)

if __name__ == '__main__':
    unittest.main()
