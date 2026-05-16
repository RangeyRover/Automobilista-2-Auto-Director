import unittest
from core.telemetry_provider import TelemetryProvider

class TestSplineGaps(unittest.TestCase):
    def setUp(self):
        self.provider = TelemetryProvider(mode="udp_only")

    def test_simple_following_gap(self):
        # Car 0 is the leader at distance 100m, game time 10.0s
        # Car 1 is following at distance 50m. The leader was at 50m at game time 5.0s (constant speed 10m/s).
        
        # We need to simulate the spline history over a few frames.
        
        # Frame 1: T=5.0
        participants = {
            0: {'is_active': True, 'race_position': 1, 'true_distance': 50.0},
            1: {'is_active': True, 'race_position': 2, 'true_distance': 0.0}
        }
        self.provider._calc_live_time_gaps(participants, 1000.0, 5.0)
        
        # Frame 2: T=10.0
        participants = {
            0: {'is_active': True, 'race_position': 1, 'true_distance': 100.0},
            1: {'is_active': True, 'race_position': 2, 'true_distance': 50.0} # Car 1 is exactly where Car 0 was at T=5.0
        }
        self.provider._calc_live_time_gaps(participants, 1000.0, 10.0)
        
        # Car 0 should have 0.0 gap
        self.assertEqual(participants[0]['time_gap_to_leader'], 0.0)
        
        # Car 1 is at 50m. The current leader (Car 0) was at 50m at T=5.0. Current time is 10.0. Gap is 5.0.
        self.assertEqual(participants[1]['time_gap_to_leader'], 5.0)

    def test_overtake_recalculates_against_new_leader(self):
        # Frame 1: T=10.0, Car 0 is leader at 100m, Car 1 is at 80m.
        # Car 1 was at 50m at T=7.0
        participants = {
            0: {'is_active': True, 'race_position': 1, 'true_distance': 100.0},
            1: {'is_active': True, 'race_position': 2, 'true_distance': 80.0}
        }
        # pre-fill splines
        self.provider._car_splines[0] = [(50.0, 5.0), (100.0, 10.0)]
        self.provider._car_splines[1] = [(50.0, 7.0), (80.0, 10.0)]
        self.provider._calc_live_time_gaps(participants, 1000.0, 10.0)
        self.assertEqual(participants[0]['time_gap_to_leader'], 0.0)
        
        # Frame 2: T=15.0, Car 1 overtakes Car 0!
        # Car 1 is now at 150m. Car 0 crashes and is still at 100m.
        # We want to know Car 0's gap to the NEW leader (Car 1).
        # Car 1 was at 100m at T=11.5 (let's insert that into the spline).
        self.provider._car_splines[1].append((100.0, 11.5))
        
        participants_after_overtake = {
            1: {'is_active': True, 'race_position': 1, 'true_distance': 150.0}, # NEW LEADER
            0: {'is_active': True, 'race_position': 2, 'true_distance': 100.0}  # FORMER LEADER
        }
        self.provider._calc_live_time_gaps(participants_after_overtake, 1000.0, 15.0)
        
        # New leader gap should instantly be 0.0
        self.assertEqual(participants_after_overtake[1]['time_gap_to_leader'], 0.0)
        
        # Follower (old leader) gap should be calculated against NEW leader's history.
        # New leader (Car 1) was at 100m at T=11.5. Current time is 15.0.
        # Gap should be 15.0 - 11.5 = 3.5 seconds.
        self.assertEqual(participants_after_overtake[0]['time_gap_to_leader'], 3.5)

    def test_missing_history_fallback(self):
        # Frame 1: T=100.0. Car 0 is at 5000m. Car 1 is at 4500m.
        # Leader's spline only starts at 4800m.
        participants = {
            0: {'is_active': True, 'race_position': 1, 'true_distance': 5000.0, 'last_lap': 100.0}, # speed = track_length / last_lap = 10m/s
            1: {'is_active': True, 'race_position': 2, 'true_distance': 4500.0}
        }
        self.provider._car_splines[0] = [(4800.0, 80.0), (5000.0, 100.0)]
        
        # Car 1 is at 4500m, which is BEFORE the leader's spline history starts.
        # It should fallback to distance estimation.
        # Distance = 500. Speed = 1000.0 / 100.0 = 10m/s. Time gap = 50.0.
        self.provider._calc_live_time_gaps(participants, 1000.0, 100.0)
        
        self.assertAlmostEqual(participants[1]['time_gap_to_leader'], 50.0, places=1)

if __name__ == '__main__':
    unittest.main()
