"""Camera controller for AMS2 Auto Director V4.0.

Manages pyKey injection for AMS2 camera switching with delta-based
navigation and configurable key timing.

No GUI imports. Testable via monkeypatched _press_key/_release_key.
"""
import time


class CameraController:
    """Manages pyKey injection for AMS2 camera switching."""

    def __init__(self, key_hold_ms: float = 0.01, key_gap_ms: float = 0.01):
        """Initialise with configurable key timing.

        Args:
            key_hold_ms: Hold duration per keystroke (seconds, default 10ms).
            key_gap_ms: Gap between keystrokes (seconds, default 10ms).
        """
        self.key_hold_ms = key_hold_ms
        self.key_gap_ms = key_gap_ms

    def _press_key(self, key: str):
        """Press a key. Override in tests via monkeypatch."""
        try:
            import pyKey
            pyKey.pressKey(key)
        except ImportError:
            pass

    def _release_key(self, key: str):
        """Release a key. Override in tests via monkeypatch."""
        try:
            import pyKey
            pyKey.releaseKey(key)
        except ImportError:
            pass

    def _tap_key(self, key: str):
        """Press, hold, release a single key with configured timing."""
        self._press_key(key)
        time.sleep(self.key_hold_ms)
        self._release_key(key)
        time.sleep(self.key_gap_ms)

    def move_to_position(self, target_pos: int, current_pos: int | None):
        """Navigate to target position using delta keypresses.

        Args:
            target_pos: Race position to navigate to (1-32).
            current_pos: Current position, or None for fallback scroll-to-top.
        """
        # Guard: invalid positions
        if target_pos < 1 or target_pos > 32:
            return

        if current_pos is None:
            # Fallback: scroll to top (32x UP) then down to target
            for _ in range(32):
                self._tap_key('UP')
            for _ in range(target_pos - 1):
                self._tap_key('DOWN')
        else:
            delta = target_pos - current_pos
            if delta == 0:
                return  # No movement needed, do not send ENTER
            elif delta > 0:
                for _ in range(delta):
                    self._tap_key('DOWN')
            elif delta < 0:
                for _ in range(abs(delta)):
                    self._tap_key('UP')

        # Confirm selection
        self._tap_key('ENTER')

    def press_enter(self):
        """Confirm camera selection."""
        self._tap_key('ENTER')

    def switch_camera_type(self, camera_name: str):
        """Switch to a specific camera type.

        Camera types are cycled via a key press. This is a placeholder
        for future camera type logic.
        """
        pass
