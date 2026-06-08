import time
import socket
import threading
import pytest
from core.telemetry_provider import TelemetryProvider

def test_packet_slot_and_drop_counter():
    """Verify that multiple packets of the same size overwrite each other and increment the dropped counter."""
    provider = TelemetryProvider(mode='udp')
    
    # We should have a packet buffer lock and counters
    assert hasattr(provider, '_packet_buffer_lock')
    assert hasattr(provider, '_dropped_packets_counter')
    assert hasattr(provider, '_received_packets_counter')
    
    # Add packets of same size
    p1 = b"dummy_packet_308_bytes" + b"\x00" * 286
    p2 = b"newer_packet_308_bytes" + b"\x00" * 286
    
    provider._add_packet_to_buffer(p1)
    assert provider._received_packets_counter == 1
    assert provider._dropped_packets_counter == 0
    
    # Add second packet of same size without reading/consuming
    provider._add_packet_to_buffer(p2)
    assert provider._received_packets_counter == 2
    assert provider._dropped_packets_counter == 1  # First packet was dropped/overwritten

def test_concurrency_thread_safety():
    """Verify concurrent read/write operations to telemetry caches and splines do not crash."""
    provider = TelemetryProvider(mode='udp')
    
    # Setup some initial participants and spline data
    provider._udp_participant_names[0] = "Driver 1"
    provider._leader_spline.record(10.0, 1.0)
    provider._leader_spline.record(20.0, 2.0)
    
    stop_event = threading.Event()
    
    def writer():
        # Continuously record spline data and update participant names
        i = 3
        while not stop_event.is_set():
            provider._leader_spline.record(10.0 * i, float(i))
            provider._udp_participant_names[i % 32] = f"Driver {i}"
            time.sleep(0.01)
            i += 1

    def reader():
        # Continuously read spline_data and poll
        while not stop_event.is_set():
            data = provider.spline_data
            assert isinstance(data, dict)
            assert "distances" in data
            # Trigger poll
            provider.poll()
            time.sleep(0.01)

    t1 = threading.Thread(target=writer)
    t2 = threading.Thread(target=reader)
    
    t1.start()
    t2.start()
    
    time.sleep(0.5)
    stop_event.set()
    
    t1.join()
    t2.join()

def test_udp_socket_timeout():
    """Verify that setting socket timeout allows listener thread to exit cleanly."""
    provider = TelemetryProvider(mode='udp')
    provider.start_udp()
    
    # Wait up to 1 second for socket to bind
    for _ in range(10):
        if provider._udp_socket is not None:
            break
        time.sleep(0.1)
        
    assert provider._udp_socket is not None
    assert provider._udp_socket.gettimeout() == 0.5
    
    # Stop UDP and assert thread terminates quickly
    t0 = time.time()
    provider.stop_udp()
    dt = time.time() - t0
    assert dt < 1.0  # Should stop cleanly within timeout threshold

def test_broadcast_loop_frequency(monkeypatch):
    """Verify that the WebSocket broadcast loop executes at ~60Hz."""
    from dashboard.bridge import DashboardBridge
    bridge = DashboardBridge()
    
    class MockProvider:
        _packet_buffer = {}
    class MockMainApp:
        _effective_source = 'hybrid'
        _mode = 'shared_memory'
        _shm = None
        participants_snapshot = {}
        scores_snapshot = {}
        shm_snapshot = None
        camera = None
        
    bridge.provider = MockProvider()
    bridge.main_app = MockMainApp()
    bridge.packet_buffer = bridge.provider._packet_buffer
    
    call_count = 0
    def mock_parse_packets():
        nonlocal call_count
        call_count += 1
        return False
        
    monkeypatch.setattr(bridge, "_parse_packets", mock_parse_packets)
    bridge._running = True
    
    import asyncio
    async def run_loop_briefly():
        task = asyncio.create_task(bridge._broadcast_loop())
        await asyncio.sleep(1.05)  # Run for slightly over 1 second
        bridge._running = False
        try:
            await task
        except asyncio.CancelledError:
            pass
            
    asyncio.run(run_loop_briefly())
    
    # At ~60Hz (0.016s sleep), it should run roughly 60-65 times in 1.05s,
    # but Windows timer resolution (15.6ms) may result in fewer ticks (~40-50).
    assert 35 <= call_count <= 75
