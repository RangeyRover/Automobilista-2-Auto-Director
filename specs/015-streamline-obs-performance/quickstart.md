# Performance Quickstart: Streamline OBS Performance

This document describes how to run the performance optimization test suite, profile loop speeds, and monitor diagnostics to ensure the success criteria are met.

## 1. Running the Automated Test Suite

We use TDD to verify the correctness and performance of the synchronization locks and queue management.

Run the entire test suite to ensure no regressions:
```bash
pytest tests
```

To run only the performance-specific and concurrency tests:
```bash
pytest tests/test_performance.py
```

## 2. Simulating Telemetry and Monitoring Diagnostics

To verify real-time loop updates, performance overhead, and dropped packet counts, run the Auto Director application alongside a simulated telemetry stream:

1. **Start the Auto Director Application** (configured for UDP mode):
   ```bash
   python main.py --mode udp
   ```
2. **Launch a Telemetry Simulator** (to generate packet storms):
   - You can use the mock telemetry script:
     ```bash
     python mock_ams2.py
     ```
3. **Monitor Console Output**:
   Every 10 seconds, the console will print a performance diagnostics block, summarizing:
   - **Telemetry Poller Actual Hz** (target is 5Hz / 200ms)
   - **Telemetry Poller Latencies** (Min / Avg / Max ms)
   - **WebSocket Broadcast Actual Hz** (target is 4Hz / 250ms)
   - **WebSocket Broadcast Latencies** (Min / Avg / Max ms)
   - **UDP Socket Stats**: Received packets count, and dropped packets count (overwritten buffer entries).

### Diagnostic Log Format Example
```text
=================== PERFORMANCE DIAGNOSTICS ===================
[Telemetry Poller]  Actual: 5.02 Hz | Latency: min=0.12ms, avg=0.45ms, max=1.20ms
[WS Broadcast]      Actual: 3.98 Hz | Latency: min=0.08ms, avg=0.22ms, max=0.74ms
[UDP Receiver]      Received: 1040 packets | Dropped: 12 packets
===============================================================
```

## 3. Profiling Success Criteria

- **SC-001 (4Hz WS Broadcast)**: Verify in diagnostics output that `[WS Broadcast] Actual` remains at `4.0 Hz +/- 0.5 Hz`.
- **SC-002 (CPU < 5%)**: Use Windows Task Manager or `psutil` to verify the python process consumes less than 5% CPU during active streaming.
- **SC-003 (Latency < 250ms)**: Verify that the dropped packet counter remains low under standard rate, and that timing changes propagate immediately.
