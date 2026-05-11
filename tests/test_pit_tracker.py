import time
import pytest
from dashboard.bridge import DashboardBridge
from unittest.mock import patch, MagicMock

@pytest.fixture
def bridge():
    b = DashboardBridge()
    b.main_app = MagicMock()
    b.main_app._participants = {}
    b.state["session"]["laps_in_event"] = 20
    b.state["session"]["time_remaining"] = 3600.0
    return b

def test_pit_entry_recorded(bridge):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 1, "current_lap": 10}
    }
    bridge._pit_tracker = {0: {"prev_pit_mode": 0}}
    
    bridge._update_pit_tracker(participants, 100.0)
        
    assert 0 in bridge._pit_tracker
    assert bridge._pit_tracker[0].get("entry_time") == 100.0
    assert bridge._pit_tracker[0].get("in_progress") == True
    assert bridge._pit_tracker[0].get("prev_pit_mode") == 1
    assert bridge._pit_tracker[0].get("pit_count", 0) == 1

def test_pit_exit_calculates_duration(bridge):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 10}
    }
    bridge._pit_tracker = {
        0: {
            "prev_pit_mode": 3, 
            "entry_time": 100.0, 
            "in_progress": True,
            "pit_count": 1
        }
    }
    
    bridge._update_pit_tracker(participants, 125.5)
        
    assert bridge._pit_tracker[0].get("in_progress") == False
    assert bridge._pit_tracker[0].get("duration") == pytest.approx(25.5)
    assert bridge._pit_tracker[0].get("exit_lap") == 10

def test_pit_count_increments(bridge):
    participants_enter1 = {0: {"name": "Driver A", "race_position": 3, "pit_mode": 1, "current_lap": 10}}
    participants_exit1 = {0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 10}}
    participants_enter2 = {0: {"name": "Driver A", "race_position": 3, "pit_mode": 1, "current_lap": 20}}
    participants_exit2 = {0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 20}}
    
    bridge._pit_tracker = {0: {"prev_pit_mode": 0}}

    bridge._update_pit_tracker(participants_enter1, 100.0)
    bridge._pit_tracker[0]["prev_pit_mode"] = 3
    # Use >5s difference to avoid flicker revert
    bridge._update_pit_tracker(participants_exit1, 110.0)
    
    assert bridge._pit_tracker[0].get("pit_count") == 1
    
    bridge._pit_tracker[0]["prev_pit_mode"] = 0
    # Add >20s difference between exit and new entry to pass debounce
    bridge._update_pit_tracker(participants_enter2, 140.0)
    bridge._pit_tracker[0]["prev_pit_mode"] = 3
    bridge._update_pit_tracker(participants_exit2, 150.0)
    
    assert bridge._pit_tracker[0].get("pit_count") == 2

def test_laps_since_last_pit(bridge):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 23}
    }
    bridge._pit_tracker = {
        0: {
            "prev_pit_mode": 0,
            "exit_lap": 10,
            "exit_time": 100.0,
            "in_progress": False
        }
    }
    
    bridge._update_pit_tracker(participants, 102.0)
    assert len(bridge._pit_events) == 1
    assert bridge._pit_events[0]["laps_since_last_pit"] == 13

def test_multiple_drivers_pit_simultaneously(bridge):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 1, "current_lap": 10},
        1: {"name": "Driver B", "race_position": 4, "pit_mode": 1, "current_lap": 10}
    }
    bridge._pit_tracker = {
        0: {"prev_pit_mode": 0},
        1: {"prev_pit_mode": 0}
    }
    
    bridge._update_pit_tracker(participants, 100.0)
    
    assert bridge._pit_tracker[0].get("in_progress") == True
    assert bridge._pit_tracker[1].get("in_progress") == True

def test_pit_events_list_contains_recent(bridge):
    participants = {
        0: {"name": "Driver A", "race_position": 3, "pit_mode": 0, "current_lap": 10}
    }
    now = 100.0
    bridge._pit_tracker = {
        0: {
            "prev_pit_mode": 0,
            "exit_time": now - 5.0,
            "in_progress": False,
            "duration": 25.0,
            "pit_count": 1,
            "exit_lap": 10
        }
    }
    
    bridge._update_pit_tracker(participants, now)
    
    assert len(bridge._pit_events) == 1
    event = bridge._pit_events[0]
    assert event["driver_name"] == "Driver A"
    assert event["duration"] == 25.0
    assert event["pit_count"] == 1
    
    # Now test an old event (> 15s)
    bridge._pit_tracker[0]["exit_time"] = now - 20.0
    bridge._update_pit_tracker(participants, now)
    assert len(bridge._pit_events) == 0
