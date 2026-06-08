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

# Single source of truth: AMS2 number key → internal camera type
KEY_TO_CAMERA = {
    '1': 'cockpit',
    '2': 'chase',
    '3': 'roof',
    '4': 'chase',
    '5': 'chase',
    '6': 'chase',
    '7': 'tv_cam',
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
        
        import threading
        self._switch_lock = threading.Lock()
        self._switching_in_progress = False
        self.bypass_threading = False
        self._pending_select_camera: bool | None = None
        
        # Determine paths
        core_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(os.path.dirname(core_dir), "dashboard", "camera_config.json")
        
        # Default config if file is missing
        self.default_config = {
            "trackside_keys": ["7"],
            "pool_close_racing": ["1", "1", "1", "2", "3", "7"],
            "pool_standard": ["7", "7", "7", "7", "2", "3"],
            "enabled_cameras": [],
            "disable_camera_change": False
        }

    def _press_key(self, key: str):
        """Press a key. Override in tests via monkeypatch."""
        try:
            import pyKey  # type: ignore
            pyKey.pressKey(key)
        except ImportError:
            pass

    def _release_key(self, key: str):
        """Release a key. Override in tests via monkeypatch."""
        try:
            import pyKey  # type: ignore
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
            raise InterruptedError("Automobilista 2 lost focus")
            
        self._press_key(key)
        time.sleep(self.key_hold_ms)
        self._release_key(key)
        time.sleep(self.key_gap_ms)

    def move_to_position(self, target_pos: int, current_pos: int | None):
        """Navigate to target position using delta keypresses (Non-Blocking)."""
        if target_pos < 1 or target_pos > 32:
            return

        if current_pos is not None and target_pos - current_pos == 0:
            return

        with self._switch_lock:
            if self._switching_in_progress:
                print("[CAM EVENT] Switch ignored: another switch in progress")
                return
            self._switching_in_progress = True
            self._pending_select_camera = None

        if getattr(self, 'bypass_threading', False):
            self._execute_switch_sequence(target_pos, current_pos)
            return

        # Start background thread
        import threading
        self._switch_thread = threading.Thread(
            target=self._execute_switch_sequence,
            args=(target_pos, current_pos),
            daemon=True
        )
        self._switch_thread.start()

    def _execute_switch_sequence(self, target_pos: int, current_pos: int | None):
        start_time = time.time()
        print(f"[CAM EVENT] Switch started to P{target_pos}")
        try:
            if current_pos is None:
                # Fallback: scroll to top (32x UP) then down to target
                for _ in range(32):
                    self._tap_key('UP')
                for _ in range(target_pos - 1):
                    self._tap_key('DOWN')
            else:
                delta = target_pos - current_pos
                if delta > 0:
                    for _ in range(delta):
                        self._tap_key('DOWN')
                elif delta < 0:
                    for _ in range(abs(delta)):
                        self._tap_key('UP')

            # Confirm selection
            self._tap_key('ENTER')

            # Short sleep to allow select_random_camera to run in main thread
            time.sleep(0.01)

            with self._switch_lock:
                pending_close = self._pending_select_camera
                self._pending_select_camera = None

            if pending_close is not None:
                config = self._load_config()
                if getattr(self, "disable_camera_change", False) or config.get("disable_camera_change", False):
                    pass
                else:
                    trackside_keys = config.get("trackside_keys", self.default_config["trackside_keys"])
                    if self.last_shot_was_special:
                        choices = trackside_keys
                    else:
                        if pending_close:
                            choices = config.get("pool_close_racing", self.default_config["pool_close_racing"])
                        else:
                            choices = config.get("pool_standard", self.default_config["pool_standard"])
                    if not choices:
                        choices = trackside_keys
                    
                    enabled = config.get("enabled_cameras", [])
                    choices = self._filter_choices(choices, enabled)
                    
                    choice = random.choice(choices)
                    self.last_shot_was_special = choice not in trackside_keys
                    
                    # Stabilization sleep
                    time.sleep(0.2)
                    self._tap_key(choice)
                    self.update_camera_for_key(choice)

            elapsed = time.time() - start_time
            print(f"[CAM EVENT] Switch completed to P{target_pos} (took {elapsed:.2f}s)")
        except InterruptedError as e:
            print(f"[CAM EVENT] Switch aborted: {e}")
        except Exception as e:
            print(f"[CAM ERROR] Switch sequence failed: {e}")
        finally:
            with self._switch_lock:
                self._switching_in_progress = False
                self._pending_select_camera = None

    def press_enter(self):
        """Confirm camera selection."""
        self._tap_key('ENTER')

    def update_camera_type(self, camera_set_name: str):
        """Update the internal camera type based on the AMS2 camera set name."""
        self.current_camera_type = CAMERA_SET_MAP.get(camera_set_name, "tv_cam")

    def _filter_choices(self, choices: list[str], enabled: list[str]) -> list[str]:
        if not enabled:
            return choices
        filtered = [c for c in choices if c in enabled]
        if not filtered:
            return enabled
        return filtered

    def _load_config(self) -> dict:
        """Load the camera configuration from disk, with a fallback to defaults."""
        config = dict(self.default_config)
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        config.update(loaded)
        except Exception:
            pass
        return config

    def select_random_camera(self, is_close: bool):
        """Select a random camera based on proximity rules and anchor logic (Non-Blocking)."""
        config = self._load_config()
        if getattr(self, 'disable_camera_change', False) or config.get("disable_camera_change", False):
            return

        with self._switch_lock:
            if self._switching_in_progress:
                # Set pending flag for active thread
                self._pending_select_camera = is_close
                return
            self._switching_in_progress = True

        if getattr(self, 'bypass_threading', False):
            self._execute_direct_camera_change(is_close)
            return

        import threading
        self._switch_thread = threading.Thread(
            target=self._execute_direct_camera_change,
            args=(is_close,),
            daemon=True
        )
        self._switch_thread.start()

    def _execute_direct_camera_change(self, is_close: bool):
        try:
            config = self._load_config()
            trackside_keys = config.get("trackside_keys", self.default_config["trackside_keys"])
            if self.last_shot_was_special:
                choices = trackside_keys
            else:
                if is_close:
                    choices = config.get("pool_close_racing", self.default_config["pool_close_racing"])
                else:
                    choices = config.get("pool_standard", self.default_config["pool_standard"])
            if not choices:
                choices = trackside_keys
            
            enabled = config.get("enabled_cameras", [])
            choices = self._filter_choices(choices, enabled)
            
            choice = random.choice(choices)
            self.last_shot_was_special = choice not in trackside_keys
            
            time.sleep(0.2)
            self._tap_key(choice)
            self.update_camera_for_key(choice)
        except InterruptedError as e:
            print(f"[CAM EVENT] Direct camera switch aborted: {e}")
        except Exception as e:
            print(f"[CAM ERROR] Direct camera switch failed: {e}")
        finally:
            with self._switch_lock:
                self._switching_in_progress = False

    def manual_switch_to_key(self, key: str):
        """Manually trigger a camera keypress sequence (Non-Blocking)."""
        with self._switch_lock:
            if self._switching_in_progress:
                return
            self._switching_in_progress = True

        if getattr(self, 'bypass_threading', False):
            self._execute_manual_key_change(key)
            return

        import threading
        self._switch_thread = threading.Thread(
            target=self._execute_manual_key_change,
            args=(key,),
            daemon=True
        )
        self._switch_thread.start()

    def _execute_manual_key_change(self, key: str):
        start_time = time.time()
        print(f"[CAM EVENT] Manual switch started to key {key}")
        try:
            self._tap_key(key)
            self.update_camera_for_key(key)
            elapsed = time.time() - start_time
            print(f"[CAM EVENT] Manual switch completed to key {key} (took {elapsed:.2f}s)")
        except InterruptedError as e:
            print(f"[CAM EVENT] Manual switch to key {key} aborted: {e}")
        except Exception as e:
            print(f"[CAM ERROR] Manual switch to key {key} failed: {e}")
        finally:
            with self._switch_lock:
                self._switching_in_progress = False

    def update_camera_for_key(self, key: str):
        """Update internal camera type based on a number key press.
        
        Uses KEY_TO_CAMERA as the single source of truth for both
        auto director and human key presses.
        """
        cam_type = KEY_TO_CAMERA.get(key)
        if cam_type:
            self.current_camera_type = cam_type

