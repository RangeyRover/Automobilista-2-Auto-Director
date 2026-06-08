"""Tests for DashboardBridge payload generation."""
from dashboard.bridge import DashboardBridge
from core.telemetry_provider import TelemetryProvider

def test_bridge_payload_includes_flywheel_and_spline(mock_shared_memory, make_participant):
    """T035: Bridge broadcast payload includes spline, flywheel_active, and time_history."""
    bridge = DashboardBridge()
    provider = TelemetryProvider(mode='shared_memory')
    bridge.provider = provider
    bridge.main_app = type("MockApp", (), {
        '_participants': {0: make_participant(race_position=1, true_distance=100.0, is_active=True)},
        'scorer': None,
        'camera': None
    })()
    bridge.packet_buffer = {}
    
    from tests.conftest import MockParticipantInfo
    
    # Tick telemetry provider to generate spline/flywheel state
    sm = mock_shared_memory(mCurrentTime=10.0, mParticipantInfo=[
        MockParticipantInfo(race_position=1, lap_distance=100.0, is_active=True)
    ] + [MockParticipantInfo(is_active=False)] * 31)
    
    provider.poll(sm)
    
    # Force DashboardBridge to build payload
    # Note: _parse_packets returns whether state changed, and mutates self.state
    bridge._parse_packets()
    
    assert "spline" in bridge.state
    assert "distances" in bridge.state["spline"]
    assert "times" in bridge.state["spline"]
    
    assert "flywheel_active" in bridge.state
    assert bridge.state["flywheel_active"] is False
    
    assert "time_history" in bridge.state
    assert isinstance(bridge.state["time_history"], list)
