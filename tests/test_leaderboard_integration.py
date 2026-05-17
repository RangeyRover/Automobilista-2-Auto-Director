"""Integration tests for the transplanted Leaderboard Heart (Flywheel + Spline)."""
import pytest
import time
from core.telemetry_provider import TelemetryProvider
from tests.conftest import MockParticipantInfo

def test_flywheel_stabilises_time_in_main_pipeline(mock_shared_memory):
    """T021: Flywheel rejects massive time jumps and synthesizes stable game time."""
    # First tick
    sm_init = mock_shared_memory(mCurrentTime=100.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=1000.0, laps_completed=1, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31)
    
    provider = TelemetryProvider(mode='shared_memory')
    provider.poll(sm_init)
    
    # 0.25s real time elapsed, but game time jumps by 40s (camera switch anomaly)
    sm_anomaly = mock_shared_memory(mCurrentTime=140.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=1020.0, laps_completed=1, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31)
    
    provider.poll(sm_anomaly)
    
    assert provider._flywheel.is_active is True
    assert provider._flywheel.internal_master_clock < 105.0

def test_spline_continuous_across_leader_change(mock_shared_memory):
    """T022: Simulate P1 swap, assert spline is never reset."""
    provider = TelemetryProvider(mode='shared_memory')
    
    # Tick 1: P1 is Driver A
    sm1 = mock_shared_memory(mCurrentTime=10.0, mParticipantInfo=[
        MockParticipantInfo(name=b"Driver A\x00", race_position=1, lap_distance=100.0, laps_completed=0, is_active=True),
        MockParticipantInfo(name=b"Driver B\x00", race_position=2, lap_distance=90.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 30)
    provider.poll(sm1)
    
    # Tick 2: P1 is Driver B
    sm2 = mock_shared_memory(mCurrentTime=11.0, mParticipantInfo=[
        MockParticipantInfo(name=b"Driver A\x00", race_position=2, lap_distance=150.0, laps_completed=0, is_active=True),
        MockParticipantInfo(name=b"Driver B\x00", race_position=1, lap_distance=160.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 30)
    provider.poll(sm2)
    
    assert provider._leader_spline.sample_count == 2
    assert provider._leader_spline.distances[-1] == 160.0

def test_time_gap_matches_spline_interpolation(mock_shared_memory):
    """T023: Assert time_gap_to_leader uses the spline calculation correctly."""
    provider = TelemetryProvider(mode='shared_memory')
    
    # Tick 1: Leader at 100m, t=10
    provider.poll(mock_shared_memory(mCurrentTime=10.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=100.0, laps_completed=0, is_active=True),
        MockParticipantInfo(race_position=2, lap_distance=50.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 30))
    
    # Tick 2: Leader at 200m, t=12. P2 at 100m.
    # Gap for P2 should be 12 - (spline.interpolate(100m) which is 10) = 2.0s
    participants = provider.poll(mock_shared_memory(mCurrentTime=12.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=200.0, laps_completed=0, is_active=True),
        MockParticipantInfo(race_position=2, lap_distance=100.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 30))
    
    assert participants[1]['time_gap_to_leader'] == 2.0

def test_flywheel_and_spline_same_tick(mock_shared_memory):
    """T024: Assert both are processed within the same poll."""
    provider = TelemetryProvider(mode='shared_memory')
    
    sm = mock_shared_memory(mCurrentTime=50.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=500.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31)
    
    provider.poll(sm)
    
    assert provider._flywheel.internal_master_clock == 50.0
    assert provider._leader_spline.sample_count == 1
    assert provider._leader_spline.distances[0] == 500.0

def test_session_reset_clears_spline(mock_shared_memory):
    """T025: Assert spline is cleared on track change."""
    provider = TelemetryProvider(mode='shared_memory')
    
    sm1 = mock_shared_memory(mTrackLocation=b'TrackA\x00', mCurrentTime=10.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=100.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31)
    provider.poll(sm1)
    
    assert provider._leader_spline.sample_count == 1
    
    sm2 = mock_shared_memory(mTrackLocation=b'TrackB\x00', mCurrentTime=0.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=0.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31)
    provider.poll(sm2)
    
    assert provider._leader_spline.sample_count == 1
    assert provider._leader_spline.distances[0] == 0.0
