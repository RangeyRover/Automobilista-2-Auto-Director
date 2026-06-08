# Developer Quickstart: Testing Spline Trimming

This guide explains how to run tests and verify the implementation of the spline trimming feature.

## Prerequisites

Ensure all dependencies are installed and the virtual environment is active.
The tests are executed via `pytest`.

---

## 1. Running Unit Tests

To run the unit tests verifying the `trim_future_points` method and its integration:

```bash
# Run spline tests
pytest tests/test_spline.py -v

# Run flywheel stabilization integration tests
pytest tests/test_physics_flywheel.py -v
pytest tests/test_leaderboard_integration.py -v
```

---

## 2. Test Verification Scenarios

### Spline Trimming Unit Verification
The unit tests verify:
1. Trimming a populated spline with multiple points correctly discards only points where `time > current_time`.
2. Trimming with a `current_time` larger than all recorded points is a no-op.
3. Trimming with a `current_time` smaller than all recorded points empties the spline cleanly.
4. Trimming preserves length alignment between `distances` and `times`.

### Telemetry Provider Integration Verification
Integration tests verify:
1. Simulating a flywheel resync triggers a trim and clears the future timestamps.
2. Simulating a negative time step (rewind) triggers a trim and discards points beyond the rewind timestamp.
3. Gaps fall back to physical estimation if the spline is emptied by trimming.
