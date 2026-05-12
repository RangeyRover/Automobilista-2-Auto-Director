import time
import pytest
from dashboard.state_engine.pit_tracker import PitTracker

@pytest.fixture
def pit_tracker():
    tracker = PitTracker()
    return tracker

def test_pit_entry_recorded(pit_tracker):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 1, "current_lap": 10}
    }
    pit_tracker._pit_tracker = {0: []}
    pit_tracker._pit_mode_state = {0: {"prev_pit_mode": 0}}
    
    pit_tracker.update(participants, 100.0)
        
    assert 0 in pit_tracker._pit_tracker
    assert len(pit_tracker._pit_tracker[0]) == 1
    assert pit_tracker._pit_tracker[0][-1].get("entry_time") == 100.0
    assert pit_tracker._pit_tracker[0][-1].get("in_progress") == True
    assert pit_tracker._pit_mode_state[0].get("prev_pit_mode") == 1
    assert pit_tracker._pit_tracker[0][-1].get("pit_count", 0) == 1

def test_pit_exit_calculates_duration(pit_tracker):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 10}
    }
    pit_tracker._pit_tracker = {
        0: [{
            "entry_time": 100.0, 
            "in_progress": True,
            "pit_count": 1
        }]
    }
    pit_tracker._pit_mode_state = {
        0: {"prev_pit_mode": 3}
    }
    
    pit_tracker.update(participants, 125.5)
        
    assert pit_tracker._pit_tracker[0][-1].get("in_progress") == False
    assert pit_tracker._pit_tracker[0][-1].get("duration") == pytest.approx(25.5)
    assert pit_tracker._pit_tracker[0][-1].get("exit_lap") == 10

def test_pit_count_increments(pit_tracker):
    participants_enter1 = {0: {"name": "Driver A", "race_position": 3, "pit_mode": 1, "current_lap": 10}}
    participants_exit1 = {0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 10}}
    participants_enter2 = {0: {"name": "Driver A", "race_position": 3, "pit_mode": 1, "current_lap": 20}}
    participants_exit2 = {0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 20}}
    
    pit_tracker._pit_tracker = {0: []}
    pit_tracker._pit_mode_state = {0: {"prev_pit_mode": 0}}

    pit_tracker.update(participants_enter1, 100.0)
    pit_tracker._pit_mode_state[0]["prev_pit_mode"] = 3
    # Use >2s difference to avoid flicker revert
    pit_tracker.update(participants_exit1, 110.0)
    
    assert pit_tracker._pit_tracker[0][-1].get("pit_count") == 1
    
    pit_tracker._pit_mode_state[0]["prev_pit_mode"] = 0
    # Add >20s difference between exit and new entry to pass debounce
    pit_tracker.update(participants_enter2, 140.0)
    pit_tracker._pit_mode_state[0]["prev_pit_mode"] = 3
    pit_tracker.update(participants_exit2, 150.0)
    
    assert pit_tracker._pit_tracker[0][-1].get("pit_count") == 2

def test_laps_since_last_pit(pit_tracker):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 23}
    }
    pit_tracker._pit_tracker = {
        0: [{
            "exit_lap": 10,
            "exit_time": 100.0,
            "in_progress": False
        }]
    }
    pit_tracker._pit_mode_state = {0: {"prev_pit_mode": 0}}
    
    pit_tracker.update(participants, 102.0)
    assert len(pit_tracker._pit_events) == 1
    assert pit_tracker._pit_events[0]["laps_since_last_pit"] == 13

def test_multiple_drivers_pit_simultaneously(pit_tracker):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 1, "current_lap": 10},
        1: {"name": "Driver B", "race_position": 4, "pit_mode": 1, "current_lap": 10}
    }
    pit_tracker._pit_tracker = {0: [], 1: []}
    pit_tracker._pit_mode_state = {0: {"prev_pit_mode": 0}, 1: {"prev_pit_mode": 0}}
    
    pit_tracker.update(participants, 100.0)
    
    assert pit_tracker._pit_tracker[0][-1].get("in_progress") == True
    assert pit_tracker._pit_tracker[1][-1].get("in_progress") == True

def test_pit_events_list_contains_recent(pit_tracker):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 10}
    }
    now = 100.0
    pit_tracker._pit_tracker = {
        0: [{
            "exit_time": now - 5.0,
            "in_progress": False,
            "duration": 25.0,
            "pit_count": 1,
            "exit_lap": 10
        }]
    }
    pit_tracker._pit_mode_state = {0: {"prev_pit_mode": 0}}
    
    pit_tracker.update(participants, now)
    
    assert len(pit_tracker._pit_events) == 1
    event = pit_tracker._pit_events[0]
    assert event["driver_name"] == "Driver A"
    assert event["duration"] == 25.0
    assert event["pit_count"] == 1
    
    # Now test an old event (> 15s)
    pit_tracker._pit_tracker[0][-1]["exit_time"] = now - 20.0
    pit_tracker.update(participants, now)
    assert len(pit_tracker._pit_events) == 0
