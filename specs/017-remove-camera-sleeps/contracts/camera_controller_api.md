# Class API Contract: CameraController

This document describes the public and private API contract for the `CameraController` class.

## Public Interface

### `__init__(self, key_hold_ms: float = 0.03, key_gap_ms: float = 0.03)`
- **Arguments**:
  - `key_hold_ms`: Keystroke hold duration (seconds, default 30ms).
  - `key_gap_ms`: Keystroke pause gap (seconds, default 30ms).
- **Behavior**: Initializes state, sets defaults, and loads configuration.

### `move_to_position(self, target_pos: int, current_pos: int | None)`
- **Arguments**:
  - `target_pos`: Race position to navigate to (1-32).
  - `current_pos`: Current position, or `None` for fallback scroll-to-top.
- **Contract**: 
  - **Thread-Safety**: This method is non-blocking. It spawns a background thread to execute the key tap sequence.
  - **Reentrancy**: If a switch sequence is already in progress, this call returns immediately, discarding the request.

### `select_random_camera(self, is_close: bool)`
- **Arguments**:
  - `is_close`: True if the target driver is in a close battle.
- **Contract**:
  - **Thread-Safety**: Non-blocking. Spawns a background thread to wait for stabilization and select a camera.
  - **Reentrancy**: Discarded if a switch is already in progress.

### `update_camera_for_key(self, key: str)`
- **Arguments**:
  - `key`: The keyboard character pressed (e.g. `'1'`, `'7'`).
- **Behavior**: Thread-safe atomic update of `self.current_camera_type`.

---

## Internal Operations (Run on background thread)

### `_execute_switch_sequence(self, target_pos: int, current_pos: int | None, select_cam_fn=None)`
- **Arguments**:
  - `target_pos`: Target position.
  - `current_pos`: Current position.
  - `select_cam_fn`: Optional callable to run random camera selection after positioning.
- **Behavior**:
  - Acquired `_switch_lock`, sets `_switching_in_progress = True`.
  - Loops over UP/DOWN taps. Focus is validated before each tap.
  - Taps ENTER.
  - If `select_cam_fn` is provided, executes it (with 0.2s stabilization delay and camera key tap).
  - Clears `_switching_in_progress = False`.
