"""Camera controller for AMS2 Auto Director V4.0.

Manages pyKey injection for AMS2 camera switching with delta-based
navigation and configurable key timing.

No GUI imports. Testable via monkeypatched _press_key/_release_key.
"""
import time
import random
import json
import os

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
        self.disable_camera_change = False
        self.last_shot_was_special = False
        
        # Determine paths
        core_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(os.path.dirname(core_dir), "dashboard", "camera_config.json")
        
        # Default config if file is missing
        self.default_config = {
            "trackside_keys": ["7", "8"],
            "pool_close_racing": ["1", "1", "1", "2", "3", "7", "8"],
            "pool_standard": ["7", "7", "7", "7", "8", "8", "2", "3"]
        }

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

    def _is_ams2_focused(self) -> bool:
        """Check if Automobilista 2 is the foreground window."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return "automobilista 2" in buf.value.lower()
        except Exception:
            return True  # Fallback to true if API fails so we don't break functionality

    def _tap_key(self, key: str):
        """Press, hold, release a single key with configured timing."""
        if not getattr(self, 'bypass_focus_check', False) and not self._is_ams2_focused():
            return
            
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

    def _load_config(self) -> dict:
        """Load the camera configuration from disk, with a fallback to defaults."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return self.default_config

    def select_random_camera(self, is_close: bool):
        """Select a random camera based on proximity rules and anchor logic.
        
        Args:
            is_close: True if the target driver is in a close battle.
        """
        if getattr(self, 'disable_camera_change', False):
            return
            
        config = self._load_config()
        trackside_keys = config.get("trackside_keys", self.default_config["trackside_keys"])
        
        # Enforce Trackside Anchor Rule
        if self.last_shot_was_special:
            choices = trackside_keys
        else:
            if is_close:
                choices = config.get("pool_close_racing", self.default_config["pool_close_racing"])
            else:
                choices = config.get("pool_standard", self.default_config["pool_standard"])
                
        # Ensure choices isn't empty due to a bad config
        if not choices:
            choices = trackside_keys
            
        choice = random.choice(choices)
        
        # Update Anchor State
        self.last_shot_was_special = choice not in trackside_keys
        
        # Pause briefly to allow AMS2 to process the driver switch (ENTER)
        # before we attempt to change the camera angle
        time.sleep(0.2)
        
        self._tap_key(choice)
        
        # Optimistically update the internal state
        if choice == '1':
            self.current_camera_type = 'cockpit'
        elif choice in trackside_keys:
            self.current_camera_type = 'tv_cam'
        else:
            self.current_camera_type = 'chase'
