"""Integration tests for the transplanted Leaderboard Heart (Flywheel + Spline)."""
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

def test_flywheel_resync_trims_spline(mock_shared_memory):
    """T005: Simulate flywheel resync, verify future spline points are discarded."""
    provider = TelemetryProvider(mode='shared_memory')
    
    # 1. Establish normal baseline spline point (t=10.0, dist=100m)
    provider.poll(mock_shared_memory(mCurrentTime=10.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=100.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31))
    
    # 2. Simulate future spline points added (e.g. from a drifted flywheel clock)
    provider._leader_spline.record(300.0, 15.0)
    provider._leader_spline.record(400.0, 20.0)
    assert provider._leader_spline.sample_count == 3
    assert provider._leader_spline.times[-1] == 20.0
    
    # 3. Simulate a resync by forcing did_resync = True
    provider._flywheel.did_resync = True
    
    # We call poll() with current_time = 12.0 (representing the resynced stable game clock).
    # Since did_resync is True, poll() should trigger trim_future_points(12.0).
    # Distance is 250.0m (implied speed = 150m / 2s = 75m/s which is healthy).
    provider.poll(mock_shared_memory(mCurrentTime=12.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=250.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31))
    
    # The points at 15.0 and 20.0 must be discarded.
    # The spline should have only the initial point (t=10.0) plus the new point from the current poll (t=12.0).
    assert provider._leader_spline.sample_count == 2
    assert provider._leader_spline.times == [10.0, 12.0]
    assert provider._leader_spline.distances == [100.0, 250.0]

def test_rewind_trims_spline(mock_shared_memory):
    """T008: Simulate replay rewind (negative time step), verify future spline points are discarded."""
    provider = TelemetryProvider(mode='shared_memory')
    
    # 1. Record spline points up to t=20.0
    provider.poll(mock_shared_memory(mCurrentTime=10.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=100.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31))
    
    provider.poll(mock_shared_memory(mCurrentTime=15.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=150.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31))
    
    provider.poll(mock_shared_memory(mCurrentTime=20.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=200.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31))
    
    assert provider._leader_spline.sample_count == 3
    assert provider._leader_spline.times == [10.0, 15.0, 20.0]
    
    # 2. Simulate rewind to t=16.0.
    # The provider poll() should detect stable_time < last spline time (16.0 < 20.0)
    # and trim points > 16.0.
    # The point at t=20.0 should be discarded, and the new point at t=16.0 should be added.
    provider.poll(mock_shared_memory(mCurrentTime=16.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=160.0, laps_completed=0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31))
    
    assert provider._leader_spline.times == [10.0, 15.0, 16.0]
    assert provider._leader_spline.distances == [100.0, 150.0, 160.0]
