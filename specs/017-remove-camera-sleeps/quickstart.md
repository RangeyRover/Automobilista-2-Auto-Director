# Quickstart Guide: Non-Blocking Camera Switches

This guide explains how to run the new non-blocking camera controller, verify its behavior, and run tests.

## Running the Application

To start the Auto Director in normal execution:
```bash
python main.py
```
Trigger a camera switch by enabling the Director (`Ctrl+Space`) while connected to the game. Observe standard output logs:
- `[CAM EVENT] Switch started to P5`
- `[CAM EVENT] Switch completed to P5 (took 0.45s)`
Verify that the main GUI remains fully interactive (menus, buttons, window moving) during the switch.

---

## Technical Verification (TDD Testing)

All new non-blocking behaviors are covered by unit tests in `tests/test_camera_controller.py`.

### Running Tests
Execute the pytest suite using:
```bash
pytest tests/test_camera_controller.py
```

### Key Test Scenarios
1. **Async Non-Blocking Execution**:
   - `test_move_to_position_async_non_blocking`
   - Checks that calling `move_to_position` returns immediately (< 5ms) while the mock key taps are run.
2. **Concurrency Lockout**:
   - `test_concurrent_switches_ignored`
   - Asserts that triggering a second switch while one is running is ignored.
3. **Focus Loss Safety**:
   - `test_focus_loss_aborts_sequence`
   - Verifies that keypresses stop if the game window loses focus mid-sequence.
