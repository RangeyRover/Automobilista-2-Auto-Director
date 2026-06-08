# Implementation Plan: Non-Blocking Camera Switches

**Branch**: `017-remove-camera-sleeps` | **Date**: 2026-06-08 | **Spec**: [spec.md](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/specs/017-remove-camera-sleeps/spec.md)
**Input**: Feature specification from `/specs/017-remove-camera-sleeps/spec.md`

## Summary

The goal of this feature is to prevent camera switches from blocking the main Tkinter thread of the Auto Director. Currently, during a camera change, the `CameraController` executes synchronous `time.sleep` calls (for key hold, gap, and stabilization delays) directly in the main thread's `_tick()` loop. This freezes the GUI and scoring updates for up to 0.6s. 

The proposed solution will refactor `CameraController` to execute keypress sequence injection in a separate, short-lived background thread (`threading.Thread`). A concurrency lock will prevent overlapping sequences by ignoring new requests while a switch is in progress. The Tkinter GUI thread and Dashboard Bridge thread will remain completely unblocked and fully responsive.

---

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: Tkinter, pyKey, keyboard, threading  
**Storage**: N/A  
**Testing**: pytest  
**Target Platform**: Windows 10/11 (DPI Aware)  
**Project Type**: Single python project  
**Performance Goals**: Tkinter main GUI thread remains responsive with zero lag spikes exceeding 50ms during camera switches. Telemetry poll frequency remains stable at 5.0Hz. Dashboard Bridge continues broadcasting at 60Hz.  
**Constraints**: All existing key timings (`key_hold_ms=0.03`, `key_gap_ms=0.03`, `stabilization=0.2s`) and configurations MUST be preserved. Focus checks MUST run before every individual key tap.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate 1: Thread Safety**: The background thread must update only atomic string attributes (`self.current_camera_type`) and must NOT directly call Tkinter widget methods (which are not thread-safe). *Status: Passed.*
- **Gate 2: Key Release Guarantees**: Background threads must not get stuck or terminate leaving simulated keys in a pressed-down state. *Status: Passed.*
- **Gate 3: Focus Loss Safety**: Checks for game window focus must happen prior to every keystroke in the sequence. *Status: Passed.*

---

## Project Structure

### Documentation (this feature)

```text
specs/017-remove-camera-sleeps/
├── spec.md              # Feature specification
├── plan.md              # This file (Implementation Plan)
├── research.md          # Technical research & concurrency evaluation
├── data-model.md        # State attribute definitions & lifecycle diagram
├── quickstart.md        # Verification, test execution, & logging details
├── checklists/
│   └── requirements.md  # Spec quality validation checklist
└── contracts/
    └── camera_controller_api.md  # Class API contract
```

### Source Code

```text
core/
├── camera_controller.py  # WILL MODIFY: Add threading runner, concurrency locks, and logging
├── telemetry_provider.py
├── scoring_engine.py
└── gui_builder.py

dashboard/
└── bridge.py

main.py                   # WILL MODIFY: Ensure async switches are integrated smoothly

tests/
├── test_camera_controller.py  # WILL MODIFY: Add TDD unit & integration tests for async switching
└── test_performance.py
```

**Structure Decision**: Single Python project structure. The core changes are confined to [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py) and [main.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/main.py), with tests in [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py).

---

## Proposed Changes

### [core]

#### [MODIFY] [camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/core/camera_controller.py)
- Introduce `self._switch_lock = threading.Lock()` and `self._switching_in_progress = False`.
- Refactor `move_to_position()` and `select_random_camera()` to return immediately. Under the hood, they will acquire the lock and spawn a background daemon thread running `self._execute_switch_sequence()`.
- If `self._switching_in_progress` is `True`, any new switch requests are immediately discarded.
- In `_execute_switch_sequence()`, execute key taps (with focus checks before each tap), perform the 0.2s stabilization delay, log high-level events (start, finish, duration) to stdout, and clear the switching flag in a `finally` block to guarantee the lockout is released.

#### [MODIFY] [main.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/main.py)
- Confirm integration points: `main.py` simply calls `self.camera.move_to_position` and `self.camera.select_random_camera` which now execute asynchronously.
- Ensure that the focus label `self.lbl_focus` continues to update correctly in the main thread.

### [tests]

#### [MODIFY] [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)
- **TDD Test 1**: Test that `move_to_position` returns immediately (< 5ms) when mock sleeps are active, proving non-blocking execution.
- **TDD Test 2**: Test that calling `move_to_position` concurrent with a running switch gets ignored.
- **TDD Test 3**: Test that focus loss mid-sequence stops the background sequence.
- **TDD Test 4**: Test that existing key mapping and timing parameters are preserved.

---

## Verification Plan

### Automated Tests
Run pytest to verify the full suite passes, including all new concurrency and timing tests:
```bash
pytest tests/test_camera_controller.py
```

### Manual Verification
1. Run `main.py` with mock telemetry or connected to AMS2.
2. Enable the Director (`Ctrl+Space`) to trigger camera switches.
3. Verify the main GUI stays responsive (can drag the window and click tabs) during camera changes.
4. Verify stdout logs print high-level switch events (start/finish/duration).
