import pytest
import time
from core.models.sector_tracker import SectorTracker

def test_initial_state():
    tracker = SectorTracker()
    assert tracker.get_display_sectors(time.time()) == [0.0, 0.0, 0.0]
    assert not tracker.tracking_valid

def test_start_lap_makes_tracking_valid():
    tracker = SectorTracker()
    # 3 -> 1 transition marks the start of a valid lap
    tracker.update(sector=3, game_time=10.0, in_pits=False, current_wall_time=1.0)
    assert not tracker.tracking_valid
    
    tracker.update(sector=1, game_time=15.0, in_pits=False, current_wall_time=2.0)
    assert tracker.tracking_valid
    assert tracker.entry_game_time == 15.0
    assert tracker.get_display_sectors(2.0) == [0.0, 0.0, 0.0]

def test_sector_1_to_2_transition():
    tracker = SectorTracker()
    tracker.update(sector=3, game_time=10.0, in_pits=False, current_wall_time=1.0)
    tracker.update(sector=1, game_time=15.0, in_pits=False, current_wall_time=2.0) # Start lap
    
    tracker.update(sector=2, game_time=40.0, in_pits=False, current_wall_time=3.0)
    
    sectors = tracker.get_display_sectors(3.0)
    print("DEBUG SECTORS:", sectors)
    assert sectors[0] == 25.0  # 40.0 - 15.0
    assert sectors[1] == 0.0
    assert sectors[2] == 0.0

def test_sector_2_to_3_transition():
    tracker = SectorTracker()
    tracker.update(sector=3, game_time=10.0, in_pits=False, current_wall_time=1.0)
    tracker.update(sector=1, game_time=15.0, in_pits=False, current_wall_time=2.0)
    tracker.update(sector=2, game_time=40.0, in_pits=False, current_wall_time=3.0)
    
    tracker.update(sector=3, game_time=70.0, in_pits=False, current_wall_time=4.0)
    
    sectors = tracker.get_display_sectors(4.0)
    assert sectors[0] == 25.0
    assert sectors[1] == 30.0  # 70.0 - 40.0
    assert sectors[2] == 0.0

def test_lap_completion_and_hold():
    tracker = SectorTracker()
    tracker.update(sector=3, game_time=10.0, in_pits=False, current_wall_time=1.0)
    tracker.update(sector=1, game_time=15.0, in_pits=False, current_wall_time=2.0)
    tracker.update(sector=2, game_time=40.0, in_pits=False, current_wall_time=3.0)
    tracker.update(sector=3, game_time=70.0, in_pits=False, current_wall_time=4.0)
    
    # Complete lap (3 -> 1)
    tracker.update(sector=1, game_time=95.0, in_pits=False, current_wall_time=5.0)
    
    # Within 5s hold, it should return the completed lap
    sectors = tracker.get_display_sectors(6.0)
    assert sectors[0] == 25.0
    assert sectors[1] == 30.0
    assert sectors[2] == 25.0  # 95.0 - 70.0
    
    # Exactly 5s hold, should return completed lap
    sectors = tracker.get_display_sectors(10.0)
    assert sectors[0] == 25.0
    assert sectors[1] == 30.0
    assert sectors[2] == 25.0
    
    # After 5s hold, it should return the building lap (which is all 0s since we just entered S1)
    sectors = tracker.get_display_sectors(10.1)
    assert sectors == [0.0, 0.0, 0.0]

def test_pit_invalidates_tracking():
    tracker = SectorTracker()
    tracker.update(sector=3, game_time=10.0, in_pits=False, current_wall_time=1.0)
    tracker.update(sector=1, game_time=15.0, in_pits=False, current_wall_time=2.0)
    tracker.update(sector=2, game_time=40.0, in_pits=False, current_wall_time=3.0)
    
    # Driver pits mid-lap
    tracker.update(sector=2, game_time=45.0, in_pits=True, current_wall_time=4.0)
    
    assert not tracker.tracking_valid
    assert tracker.get_display_sectors(4.0) == [0.0, 0.0, 0.0]

def test_pause_reset_invalidates_tracking():
    tracker = SectorTracker()
    tracker.update(sector=3, game_time=10.0, in_pits=False, current_wall_time=1.0)
    tracker.update(sector=1, game_time=15.0, in_pits=False, current_wall_time=2.0)
    tracker.update(sector=2, game_time=40.0, in_pits=False, current_wall_time=3.0)
    
    # Driver resets to pits (jumps from 2 to 1 without 3)
    # The current sector changes unexpectedly.
    tracker.update(sector=1, game_time=45.0, in_pits=False, current_wall_time=4.0)
    assert not tracker.tracking_valid
    assert tracker.get_display_sectors(4.0) == [0.0, 0.0, 0.0]
    
    tracker.update(sector=1, game_time=50.0, in_pits=False, current_wall_time=5.0)
    # Still invalid because they didn't transition from 3->1
    assert not tracker.tracking_valid
    assert tracker.get_display_sectors(5.0) == [0.0, 0.0, 0.0]

def test_same_sector_update():
    tracker = SectorTracker()
    tracker.update(sector=3, game_time=10.0, in_pits=False, current_wall_time=1.0)
    tracker.update(sector=1, game_time=15.0, in_pits=False, current_wall_time=2.0)
    
    # Stay in sector 1
    tracker.update(sector=1, game_time=20.0, in_pits=False, current_wall_time=3.0)
    assert tracker.tracking_valid
    assert tracker.get_display_sectors(3.0) == [5.0, 0.0, 0.0]
    # entry_game_time should NOT change
    assert tracker.entry_game_time == 15.0
