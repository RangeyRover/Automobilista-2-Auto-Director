"""TDD tests for F1TV bridge UDP parsing extensions."""
import struct
import pytest
from dashboard.bridge import DashboardBridge

@pytest.fixture
def bridge():
    class MockApp:
        pass
    class MockProvider:
        def get_session_info(self, shm):
            return {}
    b = DashboardBridge()
    b.main_app = MockApp()
    b.provider = MockProvider()
    return b

def test_parse_556_brake_throttle(make_udp_telemetry_packet, bridge):
    bridge.packet_buffer = {556: make_udp_telemetry_packet(brake=128, throttle=255)}
    bridge._parse_packets()
    assert bridge.state["viewed"]["brake"] == pytest.approx(128/255)
    assert bridge.state["viewed"]["throttle"] == pytest.approx(1.0)

def test_parse_556_max_rpm_num_gears(make_udp_telemetry_packet, bridge):
    bridge.packet_buffer = {556: make_udp_telemetry_packet(max_rpm=13000, gear_num_gears=0x86)}
    bridge._parse_packets()
    assert bridge.state["viewed"]["max_rpm"] == 13000
    assert bridge.state["viewed"]["num_gears"] == 8

def test_parse_556_damage_fields(make_udp_telemetry_packet, bridge):
    bridge.packet_buffer = {556: make_udp_telemetry_packet(
        aero_damage=128, engine_damage=64,
        suspension_damage=[50,100,150,200], brake_damage=[25,50,75,100]
    )}
    bridge._parse_packets()
    assert bridge.state["viewed"]["aero_damage"] == pytest.approx(128/255)
    assert bridge.state["viewed"]["engine_damage"] == pytest.approx(64/255)
    assert bridge.state["viewed"]["suspension_damage"][0] == pytest.approx(50/255)
    assert bridge.state["viewed"]["suspension_damage"][3] == pytest.approx(200/255)
    assert bridge.state["viewed"]["brake_damage"][0] == pytest.approx(25/255)

def test_parse_556_tyre_compound(make_udp_telemetry_packet, bridge):
    bridge.packet_buffer = {556: make_udp_telemetry_packet(
        tyre_compound=(b"Soft\x00", b"Medium\x00", b"Hard\x00", b"Wet\x00")
    )}
    bridge._parse_packets()
    assert bridge.state["viewed"]["tyre_compound"][0] == "Soft"
    assert bridge.state["viewed"]["tyre_compound"][1] == "Medium"

def test_parse_556_tyre_wear(make_udp_telemetry_packet, bridge):
    bridge.packet_buffer = {556: make_udp_telemetry_packet(tyre_wear=[30,40,50,60])}
    bridge._parse_packets()
    assert bridge.state["viewed"]["tyre_wear"] == [pytest.approx(30/255), pytest.approx(40/255), pytest.approx(50/255), pytest.approx(60/255)]

def test_parse_556_crash_state(make_udp_telemetry_packet, bridge):
    bridge.packet_buffer = {556: make_udp_telemetry_packet(crash_state=3)}
    bridge._parse_packets()
    assert bridge.state["viewed"]["crash_state"] == 3

def test_session_world_fastest_from_shm(mock_shared_memory, bridge):
    bridge.main_app._shm = mock_shared_memory(mWorldFastestLapTime=72.341, mWorldFastestSector1Time=24.1, mWorldFastestSector2Time=23.9, mWorldFastestSector3Time=24.3)
    bridge.packet_buffer = {}
    bridge._parse_packets()
    assert bridge.state["session"]["world_fastest_lap"] == pytest.approx(72.341)
    assert bridge.state["session"]["world_fastest_sectors"] == [pytest.approx(24.1), pytest.approx(23.9), pytest.approx(24.3)]

def test_session_track_name_from_shm(mock_shared_memory, bridge):
    bridge.main_app._shm = mock_shared_memory(mTranslatedTrackLocation=b"Interlagos\x00", mTranslatedTrackVariation=b"Grand Prix\x00")
    bridge.packet_buffer = {}
    bridge._parse_packets()
    assert bridge.state["session"]["track_name"] == "Interlagos"
    assert bridge.state["session"]["track_variation"] == "Grand Prix"

def test_session_enforced_pit_stop_from_shm(mock_shared_memory, bridge):
    bridge.main_app._shm = mock_shared_memory(mEnforcedPitStopLap=15)
    bridge.packet_buffer = {}
    bridge._parse_packets()
    assert bridge.state["session"]["enforced_pit_stop_lap"] == 15

def test_weather_from_shm(mock_shared_memory, bridge):
    bridge.main_app._shm = mock_shared_memory(mAmbientTemperature=29.0, mTrackTemperature=42.0, mRainDensity=0.5, mSnowDensity=0.0, mWindSpeed=8.0)
    bridge.packet_buffer = {}
    bridge._parse_packets()
    assert bridge.state["weather"]["ambient_temp"] == pytest.approx(29.0)
    assert bridge.state["weather"]["track_temp"] == pytest.approx(42.0)
    assert bridge.state["weather"]["rain_density"] == pytest.approx(0.5)
    assert bridge.state["weather"]["snow_density"] == pytest.approx(0.0)
    assert bridge.state["weather"]["wind_speed"] == pytest.approx(8.0)

def test_leaderboard_timing_stats_from_shm(mock_shared_memory, bridge):
    bridge.main_app._shm = mock_shared_memory(
        mFastestLapTimes=[72.5] + [0.0]*31,
        mLastLapTimes=[73.1] + [0.0]*31,
        mCurrentSector1Times=[24.2] + [0.0]*63,
        mCurrentSector2Times=[24.0] + [0.0]*63,
        mFastestSector1Times=[23.9] + [0.0]*63,
        mFastestSector2Times=[23.8] + [0.0]*63,
        mFastestSector3Times=[24.1] + [0.0]*63
    )
    bridge.main_app._participants = {
        0: {"is_active": True, "race_position": 1, "name": "Driver 0"}
    }
    bridge.provider.get_session_info = lambda shm: {"game_state": 2}
    bridge.packet_buffer = {}
    bridge._parse_packets()
    
    assert len(bridge.state["leaderboard"]) == 1
    lb = bridge.state["leaderboard"][0]
    assert lb["fastest_lap"] == pytest.approx(72.5)
    assert lb["last_lap"] == pytest.approx(73.1)
    # the bridge now delegates current_sectors to sector_manager, so it will be [0.0, 0.0, 0.0] 
    # since we don't mock the sector_manager game_time updates
    assert lb["current_sectors"] == [0.0, 0.0, 0.0]
    assert lb["fastest_sectors"] == [pytest.approx(23.9), pytest.approx(23.8), pytest.approx(24.1)]

def test_behind_driver_populated(bridge, make_udp_telemetry_packet):
    bridge.main_app._participants = {
        0: {"name": "P1", "race_position": 1},
        1: {"name": "P2", "race_position": 2},
        2: {"name": "P3", "race_position": 3}
    }
    bridge.state["viewed_index"] = 1
    bridge.state["split_behind"] = 1.5
    bridge.packet_buffer = {559: make_udp_telemetry_packet(viewed_index=1)}
    bridge._parse_packets()
    assert bridge.state["behind"]["name"] == "P3"
    assert bridge.state["behind"]["position"] == 3
    assert bridge.state["behind"]["gap_seconds"] == pytest.approx(1.5)

def test_behind_driver_empty_for_last_place(bridge, make_udp_telemetry_packet):
    bridge.main_app._participants = {
        0: {"name": "P1", "race_position": 1},
        1: {"name": "P2", "race_position": 2}
    }
    bridge.packet_buffer = {559: make_udp_telemetry_packet(viewed_index=1)}
    bridge._parse_packets()
    assert bridge.state["behind"]["name"] == ""
    assert bridge.state["behind"]["position"] == 0

def test_leaderboard_has_nationality_and_car_info(mock_shared_memory, bridge):
    bridge.main_app._shm = mock_shared_memory(
        mNationalities=[81] + [0]*63,
        mCarNames=[b"Formula Ultimate Gen 2\x00"] + [b""]*63,
        mCarClassNames=[b"Formula Ultimate Gen 2\x00"] + [b""]*63
    )
    bridge.main_app._participants = {
        0: {"is_active": True, "race_position": 1, "name": "Driver 0"}
    }
    bridge.provider.get_session_info = lambda shm: {"game_state": 2}
    bridge.packet_buffer = {}
    bridge._parse_packets()
    
    assert len(bridge.state["leaderboard"]) == 1
    lb = bridge.state["leaderboard"][0]
    # bridge.py hashes name to nationality
    assert "nationality" in lb
    assert lb["car_name"] == "Formula Ultimate Gen 2"
    assert lb["car_class"] == "Formula Ultimate Gen 2"

def test_director_state_broadcast(bridge):
    class MockCameraController:
        current_camera_type = "cockpit"
    bridge.main_app.camera = MockCameraController()
    bridge.main_app._director_enabled = True
    bridge.packet_buffer = {}
    bridge._parse_packets()
    assert bridge.state["director"]["camera_type"] == "cockpit"
    assert bridge.state["director"]["is_auto_directing"] == True

def test_udp_fallback_session_data(make_udp_race_data_packet, bridge):
    bridge.main_app._shm = None
    bridge.packet_buffer = {308: make_udp_race_data_packet()}
    bridge._parse_packets()
    assert bridge.state["session"]["world_fastest_lap"] == pytest.approx(72.5)
    assert bridge.state["session"]["world_fastest_sectors"] == [pytest.approx(24.0), pytest.approx(24.0), pytest.approx(24.5)]
    assert bridge.state["session"]["track_name"] == "Interlagos"
    assert bridge.state["session"]["track_variation"] == "Grand Prix"
    assert bridge.state["session"]["enforced_pit_stop_lap"] == -1

def test_udp_fallback_weather(make_udp_game_state_packet, bridge):
    bridge.main_app._shm = None
    bridge.packet_buffer = {24: make_udp_game_state_packet()}
    bridge._parse_packets()
    assert bridge.state["weather"]["ambient_temp"] == 25
    assert bridge.state["weather"]["track_temp"] == 35
    assert bridge.state["weather"]["rain_density"] == pytest.approx(0.0)
    assert bridge.state["weather"]["snow_density"] == pytest.approx(0.0)
    assert bridge.state["weather"]["wind_speed"] == 5

def test_udp_fallback_timing_stats(make_udp_time_stats_packet, bridge):
    bridge.main_app._shm = None
    stats = [{"fastest_lap": 72.5, "last_lap": 73.1, "last_sector_time": 0.0, "fastest_sector1": 23.9, "fastest_sector2": 23.8, "fastest_sector3": 24.1}]
    stats += [{"fastest_lap": 0.0, "last_lap": 0.0, "last_sector_time": 0.0, "fastest_sector1": 0.0, "fastest_sector2": 0.0, "fastest_sector3": 0.0}] * 31
    bridge.packet_buffer = {1040: make_udp_time_stats_packet(stats=stats)}
    bridge.main_app._participants = {
        0: {"is_active": True, "race_position": 1, "name": "Driver 0"}
    }
    bridge.provider.get_session_info = lambda shm: {"game_state": 2}
    bridge._parse_packets()
    assert len(bridge.state["leaderboard"]) == 1
    lb = bridge.state["leaderboard"][0]
    assert lb["fastest_lap"] == pytest.approx(72.5)
    assert lb["last_lap"] == pytest.approx(73.1)
    assert lb["fastest_sectors"] == [pytest.approx(23.9), pytest.approx(23.8), pytest.approx(24.1)]

def test_udp_fallback_nationality(make_udp_participants_packet, bridge):
    bridge.main_app._shm = None
    participants = [{"name": "Driver 0", "nationality": 81}] + [{"name": "", "nationality": 0}] * 15
    bridge.packet_buffer = {1136: make_udp_participants_packet(participants=participants)}
    bridge.main_app._participants = {
        0: {"is_active": True, "race_position": 1, "name": "Driver 0"}
    }
    bridge.provider.get_session_info = lambda shm: {"game_state": 2}
    bridge._parse_packets()
    assert len(bridge.state["leaderboard"]) == 1
    lb = bridge.state["leaderboard"][0]
    assert "nationality" in lb
