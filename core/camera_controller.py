"""Camera controller for AMS2 Auto Director V4.0.

Manages pyKey injection for AMS2 camera switching with delta-based
navigation and configurable key timing.

No GUI imports. Testable via monkeypatched _press_key/_release_key.
"""
import time
import random

CAMERA_SET_MAP = {
    "Cockpit": "cockpit", 
    "Helmet": "cockpit", 
    "TV Pod": "cockpit", 
    "TV Cam 1": "tv_cam", 
    "TV Cam 2": "tv_cam", 
    "TV Cam 3": "tv_cam", 
    "Chase Near": "chase", 
    "Chase Far": "chase", 
    "Chase Bumper": "chase"
}
class CameraController:
    """Manages pyKey injection for AMS2 camera switching."""

    def __init__(self, key_hold_ms: float = 0.03, key_gap_ms: float = 0.03):
        """Initialise with configurable key timing.

        Args:
            key_hold_ms: Hold duration per keystroke (seconds, default 30ms).
            key_gap_ms: Gap between keystrokes (seconds, default 30ms).
        """
        self.key_hold_ms = key_hold_ms
        self.key_gap_ms = key_gap_ms
        self.current_camera_type = "tv_cam"

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

    def update_camera_type(self, camera_set_name: str):
        """Update the internal camera type based on the AMS2 camera set name."""
        self.current_camera_type = CAMERA_SET_MAP.get(camera_set_name, "tv_cam")

    def select_random_camera(self, is_close: bool):
        """Select a random camera based on proximity rules.
        
        Args:
            is_close: True if the target driver is in a close battle.
        """
        if is_close:
            choices = ['1', '1', '2', '3', '4', '5']
        else:
            choices = ['7', '2', '3', '4', '5']
            
        choice = random.choice(choices)
        
        # Pause briefly to allow AMS2 to process the driver switch (ENTER)
        # before we attempt to change the camera angle
        time.sleep(0.2)
        
        self._tap_key(choice)
        
        # Optimistically update the internal state
        if choice == '1':
            self.current_camera_type = 'cockpit'
        elif choice == '7':
            self.current_camera_type = 'tv_cam'
        elif choice in ['2', '3', '4', '5']:
            self.current_camera_type = 'chase'
