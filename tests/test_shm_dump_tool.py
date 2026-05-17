"""Tests for the Shared Memory Leaderboard Test Tool (tools/shm_leaderboard_server.py)."""
import pytest
import ctypes
import json
from shared_memory_struct import SharedMemory
from tools.shm_leaderboard_server import serialise_shm

@pytest.fixture
def zero_shm():
    """Returns a zero-initialised SharedMemory instance using ctypes.from_buffer."""
    return SharedMemory.from_buffer(bytearray(ctypes.sizeof(SharedMemory)))



# --- Phase 6: Driver Correlation Tests ---

from tools.shm_leaderboard_server import correlate_drivers

def test_correlate_drivers_empty_data():
    assert correlate_drivers({"mNumParticipants": 0, "mParticipantInfo": []}) == []

def test_correlate_drivers_basic_mapping():
    data = {
        "mNumParticipants": 2,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "DriverA", "mRacePosition": 2, "mWorldPosition": [1.0, 2.0, 3.0]},
            {"mIsActive": True, "mName": "DriverB", "mRacePosition": 1, "mWorldPosition": [4.0, 5.0, 6.0]}
        ],
        "mSpeeds": [100.0, 200.0],
        "mCurrentSector1Times": [10.0, 20.0],
        "mOrientations": [[1, 0, 0], [0, 1, 0]],
        "mRaceStates_labels": ["RACESTATE_RACING", "RACESTATE_FINISHED"],
        "mCarNames": ["CarA", "CarB"],
        "mCarClassNames": ["ClassA", "ClassB"]
    }
    drivers = correlate_drivers(data, active_only=False)
    assert len(drivers) == 2
    # Should be sorted by mRacePosition
    assert drivers[0]["mName"] == "DriverB"
    assert drivers[0]["mSpeeds"] == 200.0
    assert drivers[0]["mCurrentSector1Times"] == 20.0
    assert drivers[0]["mOrientations"] == [0, 1, 0]
    assert drivers[0]["mRaceStates_label"] == "RACESTATE_FINISHED"
    assert drivers[0]["mCarNames"] == "CarB"

    assert drivers[1]["mName"] == "DriverA"
    assert drivers[1]["mSpeeds"] == 100.0
    assert drivers[1]["mCurrentSector1Times"] == 10.0
    assert drivers[1]["mRaceStates_label"] == "RACESTATE_RACING"

def test_correlate_drivers_active_only_filter():
    data = {
        "mNumParticipants": 2,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "DriverA", "mRacePosition": 1},
            {"mIsActive": False, "mName": "DriverB", "mRacePosition": 2}
        ]
    }
    drivers = correlate_drivers(data, active_only=True)
    assert len(drivers) == 1
    assert drivers[0]["mName"] == "DriverA"

def test_correlate_drivers_sorting():
    data = {
        "mNumParticipants": 3,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "P3", "mRacePosition": 3},
            {"mIsActive": True, "mName": "P1", "mRacePosition": 1},
            {"mIsActive": True, "mName": "P2", "mRacePosition": 2}
        ]
    }
    drivers = correlate_drivers(data)
    assert [d["mName"] for d in drivers] == ["P1", "P2", "P3"]

def test_correlate_drivers_pit_tracking():
    data = {
        "mNumParticipants": 2,
        "mTrackLength": 5000.0,
        "mCurrentTime": 120.0,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "P1", "mRacePosition": 1, "mCurrentLapDistance": 1000.0, "mCurrentLap": 2},
            {"mIsActive": True, "mName": "P2", "mRacePosition": 2, "mCurrentLapDistance": 500.0, "mCurrentLap": 2}
        ],
        "mPitModes": [2, 0] # P1 is in pit, P2 is not
    }
    
    pit_entry_times = {"P1": 110.0} # P1 entered pits at 110.0s
    
    drivers = correlate_drivers(data, pit_entry_times=pit_entry_times)
    
    p1 = drivers[0]
    p2 = drivers[1]
    
    assert p1["mName"] == "P1"
    assert p1["_in_pits"] is True
    assert p1["_pit_time"] == 10.0 # 120.0 - 110.0
    
    assert p2["mName"] == "P2"
    assert p2["_in_pits"] is False
    assert p2["_pit_time"] is None
    
    # Check that pit_entry_times tracks correctly
    assert "P1" in pit_entry_times
    assert "P2" not in pit_entry_times

def test_correlate_drivers_gap_calculation():
    # Gap is distance behind leader
    data = {
        "mNumParticipants": 3,
        "mTrackLength": 5000.0,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "P2", "mRacePosition": 2, "mCurrentLapDistance": 1000.0, "mCurrentLap": 6},
            {"mIsActive": True, "mName": "P1", "mRacePosition": 1, "mCurrentLapDistance": 1100.0, "mCurrentLap": 6},
            {"mIsActive": True, "mName": "P3", "mRacePosition": 3, "mCurrentLapDistance": 4900.0, "mCurrentLap": 5} # Lapped!
        ]
    }
    drivers = correlate_drivers(data)
    # Total distances:
    # P1: 5 * 5000 + 1100 = 26100
    # P2: 5 * 5000 + 1000 = 26000
    # P3: 4 * 5000 + 4900 = 24900
    
    assert drivers[0]["mName"] == "P1"
    assert drivers[0]["_gap"] == 0.0
    
    assert drivers[1]["mName"] == "P2"
    assert drivers[1]["_gap"] == 100.0
    
    assert drivers[2]["mName"] == "P3"
    assert drivers[2]["_gap"] == 1200.0

def test_correlate_drivers_includes_total_dist():
    data = {
        "mNumParticipants": 1,
        "mTrackLength": 5000.0,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "P1", "mRacePosition": 1, "mCurrentLapDistance": 1000.0, "mCurrentLap": 2}
        ]
    }
    drivers = correlate_drivers(data)
    assert "_total_dist" in drivers[0]
    assert drivers[0]["_total_dist"] == 6000.0

def test_correlate_drivers_retains_distance_gap():
    data = {
        "mNumParticipants": 2,
        "mTrackLength": 5000.0,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "P2", "mRacePosition": 2, "mCurrentLapDistance": 1000.0, "mCurrentLap": 2},
            {"mIsActive": True, "mName": "P1", "mRacePosition": 1, "mCurrentLapDistance": 1500.0, "mCurrentLap": 2}
        ]
    }
    drivers = correlate_drivers(data)
    assert "_gap" in drivers[0] # P1
    assert drivers[0]["_gap"] == 0.0
    assert "_gap" in drivers[1] # P2
    assert drivers[1]["_gap"] == 500.0

from core.spline import DistanceTimeSpline

def test_correlate_drivers_includes_time_gap_with_spline():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(1000.0, 10.0) # 100 m/s
    
    data = {
        "mCurrentTime": 15.0,
        "mNumParticipants": 2,
        "mTrackLength": 5000.0,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "P2", "mRacePosition": 2, "mCurrentLapDistance": 500.0, "mCurrentLap": 1},
            {"mIsActive": True, "mName": "P1", "mRacePosition": 1, "mCurrentLapDistance": 1500.0, "mCurrentLap": 1}
        ]
    }
    drivers = correlate_drivers(data, spline=spline)
    # P1 is at 1500, P2 is at 500.
    # Leader passed 500 at t=5.0. Current time is 15.0. Time gap should be 10.0s.
    assert "_time_gap" in drivers[1]
    assert isinstance(drivers[1]["_time_gap"], float)
    assert drivers[1]["_time_gap"] == 10.0

def test_correlate_drivers_time_gap_none_without_spline():
    data = {
        "mCurrentTime": 15.0,
        "mNumParticipants": 2,
        "mTrackLength": 5000.0,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "P2", "mRacePosition": 2, "mCurrentLapDistance": 500.0, "mCurrentLap": 1},
            {"mIsActive": True, "mName": "P1", "mRacePosition": 1, "mCurrentLapDistance": 1500.0, "mCurrentLap": 1}
        ]
    }
    drivers = correlate_drivers(data, spline=None)
    assert drivers[1]["_time_gap"] is None

def test_correlate_drivers_leader_time_gap_zero():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(1000.0, 10.0)
    
    data = {
        "mCurrentTime": 15.0,
        "mNumParticipants": 1,
        "mTrackLength": 5000.0,
        "mParticipantInfo": [
            {"mIsActive": True, "mName": "P1", "mRacePosition": 1, "mCurrentLapDistance": 1500.0, "mCurrentLap": 1}
        ]
    }
    drivers = correlate_drivers(data, spline=spline)
    assert drivers[0]["_time_gap"] == 0.0

# --- Phase 7: Server Pipeline Tests ---

from tools.shm_leaderboard_server import process_shm, broadcast_telemetry

def test_pipeline_integration(zero_shm):
    # Set up some dummy data
    zero_shm.mNumParticipants = 1
    zero_shm.mParticipantInfo[0].mIsActive = True
    zero_shm.mParticipantInfo[0].mName = b"TestDriver\x00"
    zero_shm.mParticipantInfo[0].mRacePosition = 1
    zero_shm.mTrackLength = 1000.0
    
    payload = process_shm(zero_shm, active_only=False)
    
    assert "raw" in payload
    assert "leaderboard" in payload
    
    assert payload["raw"]["mNumParticipants"] == 1
    assert payload["leaderboard"][0]["mName"] == "TestDriver"
    assert payload["leaderboard"][0]["mRacePosition"] == 1

def test_pipeline_integration_active_only(zero_shm):
    zero_shm.mNumParticipants = 2
    zero_shm.mParticipantInfo[0].mIsActive = True
    zero_shm.mParticipantInfo[0].mName = b"Active\x00"
    zero_shm.mParticipantInfo[0].mRacePosition = 1
    
    zero_shm.mParticipantInfo[1].mIsActive = False
    zero_shm.mParticipantInfo[1].mName = b"Inactive\x00"
    zero_shm.mParticipantInfo[1].mRacePosition = 2
    
    payload = process_shm(zero_shm, active_only=True)
    
    # Leaderboard should only have 1
    assert len(payload["leaderboard"]) == 1
    assert payload["leaderboard"][0]["mName"] == "Active"
    
    # Raw should still have 2 in the participant array (though raw has 64 always)
    # But specifically, we check the raw array wasn't filtered
    assert len(payload["raw"]["mParticipantInfo"]) == 64
    assert payload["raw"]["mParticipantInfo"][1]["mName"] == "Inactive"

import asyncio
import pytest

# --- Phase 10: Server Loop Tracking Tests ---

from tools.shm_leaderboard_server import should_reset_spline, get_leader_name
from core.spline import DistanceTimeSpline

def test_session_reset_detection():
    # Only reset when leaving SESSION_RACE (5) or participants drop to 0
    # SESSION_RACE -> SESSION_RACE (no change) -> False
    assert should_reset_spline(5, 5, 20, 20) is False
    
    # SESSION_RACE -> GAME_FRONT_END (or anything else) -> True
    assert should_reset_spline(5, 1, 20, 20) is True
    
    # QUALIFY -> RACE (entering race, not leaving) -> False
    assert should_reset_spline(3, 5, 20, 20) is False
    
    # PRACTICE -> QUALIFY (not leaving race) -> False
    assert should_reset_spline(1, 3, 20, 20) is False
    
    # Any state -> 0 participants (session reset) -> True
    assert should_reset_spline(5, 5, 20, 0) is True
    assert should_reset_spline(3, 3, 20, 0) is True

def test_leader_changed_detection():
    leaderboard = [
        {"mName": "DriverA", "_total_dist": 1000},
        {"mName": "DriverB", "_total_dist": 900}
    ]
    assert get_leader_name(leaderboard) == "DriverA"
    
    # empty leaderboard -> None
    assert get_leader_name([]) is None

@pytest.mark.asyncio
async def test_broadcast_telemetry():
    class MockWebsocket:
        def __init__(self):
            self.sent_messages = []
        async def send(self, msg):
            self.sent_messages.append(msg)
            
    ws1 = MockWebsocket()
    ws2 = MockWebsocket()
    clients = {ws1, ws2}
    
    await broadcast_telemetry(clients, {"test": "data"})
    
    assert len(ws1.sent_messages) == 1
    assert len(ws2.sent_messages) == 1
    assert ws1.sent_messages[0] == '{"test": "data"}'

# --- Phase 2: Total Distance Tests ---
