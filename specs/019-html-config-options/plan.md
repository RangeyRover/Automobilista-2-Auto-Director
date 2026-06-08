# Implementation Plan: HTML Configuration Options

**Branch**: `019-html-config-options` | **Date**: 2026-06-08 | **Spec**: [spec.md](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/specs/019-html-config-options/spec.md)
**Input**: Feature specification from `/specs/019-html-config-options/spec.md`

## Summary

The goal of this feature is to resolve two key usability requests:
1. Allow the user to toggle interval timing gaps (gap to car ahead) on the leaderboard instead of gap to the leader.
2. Allow the user to configure the camera views used in the auto director and/or disable auto-camera switching entirely from the HTML control panel.

We will implement client-side gap delta calculations in Javascript (synchronized via the existing `f1tv_config` websocket channel). We will also extend the `CameraController` to filter camera switches and respect auto-switching inhibition based on the `camera_config.json` state, which is saved dynamically by the HTML control panel.

---

## Technical Context

- **Language/Version**: Python 3.13, HTML5, Vanilla JavaScript  
- **Primary Dependencies**: ctypes, websockets, asyncio, pytest  
- **Storage**: `dashboard/camera_config.json` (disk), browser `localStorage` (client)  
- **Testing**: pytest  
- **Target Platform**: Windows 10/11 (server/desktop), modern web browsers (client)  
- **Project Type**: Single python project with web assets  
- **Performance Goals**: Instant client-side timing calculations, no telemetry latency  
- **Constraints**: Standalone server must compile correctly and retain full backwards compatibility if new settings properties are missing.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate 1: Backward Compatibility**: The server must run and load default values correctly if `"enabled_cameras"` or `"disable_camera_change"` are omitted from `camera_config.json`. *Status: Passed.*
- **Gate 2: Thread Safety**: The `CameraController` loads the configuration under a lock or reads it cleanly. Since `_load_config()` only does read operations on the json file, and config saving uses atomic file writes, it is thread-safe. *Status: Passed.*

---

## Project Structure

### Documentation (this feature)

```text
specs/019-html-config-options/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code

```text
core/
└── camera_controller.py      # WILL MODIFY: Filter camera choices and support disable_camera_change

dashboard/
├── f1tv_overlay.html         # WILL MODIFY: Add interval-gaps checkbox and dummy div
├── f1tv_control.html         # WILL MODIFY: Add settings for interval-gaps, auto-camera pool and toggles
├── app.js                    # WILL MODIFY: Add interval gap calculation for the main leaderboard
└── js/
    └── f1tv_overlay.js       # WILL MODIFY: Add interval gap calculation for overlays

tests/
└── test_camera_controller.py # WILL MODIFY: Add unit tests for enabled_cameras filtering and disable_camera_change config
```

**Structure Decision**: Single Python project structure. The modifications are isolated to the camera controller, dashboard assets, and associated unit tests.

---

## TDD Testing Strategy (TDD - Tests Before Code)

We follow a strict Test-Driven Development (TDD) approach. All test cases must be written and run to demonstrate failure (RED) before any production code is modified.

### 1. Camera Filter Verification (User Story 2)
- **File**: [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)
- **Test Case**: `test_camera_controller_filters_choices`
- **Method**: Set `enabled_cameras = ["1", "2"]` in config. Call `select_random_camera` and verify that only camera '1' or '2' is ever chosen.

### 2. Auto-Camera Change Inhibition Verification (User Story 3)
- **File**: [test_camera_controller.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_camera_controller.py)
- **Test Case**: `test_camera_controller_respects_disable_camera_change_config`
- **Method**: Set `disable_camera_change = True` in config. Verify that automatic director camera switches are blocked.
