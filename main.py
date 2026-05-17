"""AMS2 Auto Director V4.0 — Main Entry Point.

Thin tkinter GUI shell. All business logic lives in core/ modules.
This file owns no scoring, telemetry, or camera logic.
"""
import tkinter as tk
from tkinter import ttk, filedialog
import argparse
import time
import mmap
import ctypes
import keyboard
import threading

from core.telemetry_provider import TelemetryProvider
from core.scoring_engine import ScoringEngine
from core.camera_controller import CameraController
from core.gui_builder import GUIBuilder
from dashboard.bridge import DashboardBridge


# Try to import the shared memory struct
try:
    from shared_memory_struct import SharedMemory
    HAS_SHARED_MEMORY = True
except ImportError:
    HAS_SHARED_MEMORY = False


class AutoDirectorApp:
    """Thin tkinter GUI shell. Owns no business logic."""

    TICK_MS = 200  # Telemetry poll interval
    GRID_UPDATE_MS = 1000  # GUI grid refresh interval

    def __init__(self, mode: str = 'shared_memory'):
        self.provider = TelemetryProvider(mode=mode)
        self.scorer = ScoringEngine()
        self.camera = CameraController()

        self._mode = mode
        self._user_mode = 'hybrid'  # User's GUI selection: 'hybrid' or 'udp_only'
        self._effective_source = 'hybrid'  # Runtime: 'hybrid', 'udp_auto', or 'udp_manual'
        self._auto_switch_counter = 0  # Hysteresis counter for auto-detection
        self._director_enabled = False
        self._last_switch_time = 0.0
        self._switch_interval = 7.0
        self._camera_close_gap = 0.5
        self._sweep_dwell_time = 1.0
        self._participants: dict[int, dict] = {}
        self._scores: dict[int, dict] = {}
        self._last_logged_cam = None

        # Shared memory handle
        self._shm = None
        self._shm_file = None

        self.bridge = DashboardBridge()

        self.gui_builder = GUIBuilder(self)
        self.gui_builder.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.provider.start_udp()
        self.bridge.start(self.provider, self)

        try:
            def on_key_event(e):
                # Ignore releases
                if e.event_type != 'down':
                    return
                
                print(f"[KEYLOG] {e.name} pressed")
                
                if e.name == '1':
                    print("[CAM EVENT] Key 1 triggered camera change to roof (Halo HUD)")
                    self.camera.current_camera_type = 'roof'
                elif e.name == '2':
                    print("[CAM EVENT] Key 2 triggered camera change to chase")
                    self.camera.current_camera_type = 'chase'
                elif e.name == '3':
                    print("[CAM EVENT] Key 3 triggered camera change to roof (Halo HUD)")
                    self.camera.current_camera_type = 'roof'
                elif e.name in ['4', '5', '6']:
                    print(f"[CAM EVENT] Key {e.name} triggered camera change to chase (Onboard)")
                    self.camera.current_camera_type = 'chase'
                elif e.name in ['7', '8']:
                    print(f"[CAM EVENT] Key {e.name} triggered camera change to tv_cam/trackside")
                    self.camera.current_camera_type = 'tv_cam'
                elif e.name == '9':
                    self.root.after(0, self._toggle_camera_change)

            keyboard.hook(on_key_event)
            keyboard.add_hotkey('ctrl+space', lambda: self.root.after(0, self._toggle_director))
        except Exception as e:
            print(f"Warning: Could not bind global hotkey: {e}")
            # Fallback to application-level global binding
            self.root.bind_all('<Control-space>', lambda e: self._toggle_director())
            self.root.bind_all('1', lambda e: setattr(self.camera, 'current_camera_type', 'roof'))
            self.root.bind_all('2', lambda e: setattr(self.camera, 'current_camera_type', 'chase'))
            self.root.bind_all('3', lambda e: setattr(self.camera, 'current_camera_type', 'roof'))
            for k in ['4', '5', '6']:
                self.root.bind_all(k, lambda e, key=k: setattr(self.camera, 'current_camera_type', 'chase'))
            for k in ['7', '8']:
                self.root.bind_all(k, lambda e, key=k: setattr(self.camera, 'current_camera_type', 'tv_cam'))
            self.root.bind_all('9', lambda e: self._toggle_camera_change())

    def _on_closing(self):
        """Cleanup and close application."""
        self.bridge.stop()
        self.provider.stop_udp()
        self.root.destroy()

    def _open_overlays(self):
        """Open the local dashboard portal in the default web browser."""
        import webbrowser
        webbrowser.open("http://localhost:8765/")

    def _apply_tuning(self):
        """Write GUI values to scorer attributes."""
        try:
            new_port = int(self._tuning_vars['udp_port'].get())
            if new_port != self.provider._udp_port:
                self.provider.set_udp_port(new_port)
                
            self._switch_interval = float(self._tuning_vars['switch_interval'].get())
            self.scorer.sweep_dwell_time = float(self._tuning_vars['sweep_dwell_time'].get())
            self.scorer.race_position_bonus_factor = float(
                self._tuning_vars['race_position_bonus_factor'].get())
            self.scorer.pit_mode_penalty = float(self._tuning_vars['pit_mode_penalty'].get())
            self.scorer.speed_penalty = float(self._tuning_vars['speed_penalty'].get())
            self.scorer.leader_cars_ahead_multiplier = float(
                self._tuning_vars['leader_cars_ahead_multiplier'].get())
            self.scorer.other_cars_ahead_multiplier = float(
                self._tuning_vars['other_cars_ahead_multiplier'].get())
            self.scorer.close_racing_max_gap = float(
                self._tuning_vars['close_racing_max_gap'].get())
            self._camera_close_gap = float(
                self._tuning_vars['camera_close_gap'].get())
            self.scorer.timeline_pre_offset = float(
                self._tuning_vars['timeline_pre_offset'].get())
            self.scorer.timeline_post_offset = float(
                self._tuning_vars['timeline_post_offset'].get())
        except ValueError:
            pass  # Ignore invalid input

    def _toggle_director(self):
        """Toggle Auto Director status (Ctrl+Space)."""
        self._director_enabled = not self._director_enabled
        status = "ACTIVE" if self._director_enabled else "PAUSED"
        color = '#00ff00' if self._director_enabled else '#ffaa00'
        
        self.lbl_director.configure(text=f'Director: {status}')
        
        print(f"Auto Director {status}")

    def _toggle_camera_change(self):
        """Toggle whether the Auto Director can change cameras (Key 9)."""
        self.camera.disable_camera_change = not self.camera.disable_camera_change
        state = "OFF" if self.camera.disable_camera_change else "ON"
        self.lbl_camera.configure(text=f'Auto Cam: {state}')
        print(f"[CAM EVENT] Auto Camera Switch {state}")

    def _toggle_data_source(self):
        """Toggle between Hybrid and UDP Only data source modes."""
        if self._user_mode == 'hybrid':
            self._user_mode = 'udp_only'
            self._effective_source = 'udp_manual'
            self._auto_switch_counter = 0
            self._btn_data_source.configure(text='Mode: UDP Only')
        else:
            self._user_mode = 'hybrid'
            self._effective_source = 'hybrid'
            self._auto_switch_counter = 0
            self._btn_data_source.configure(text='Mode: Hybrid')
        self._update_source_label()

    def _update_source_label(self):
        """Update the status bar source label."""
        labels = {
            'hybrid': 'Source: Hybrid',
            'udp_auto': 'Source: UDP (auto)',
            'udp_manual': 'Source: UDP (manual)'
        }
        self.lbl_source.configure(text=labels.get(self._effective_source, 'Source: Unknown'))

    def _should_auto_switch_to_udp(self, sm) -> bool:
        """Check if conditions warrant auto-switching from Hybrid to UDP.

        Returns True when:
        1. UDP has track_length > 0 (308-byte packet)
        2. UDP has >= 1 participant name cached
        3. SHM has no active participants
        """
        if not self.provider.udp_has_track_length():
            return False
        if not self.provider.udp_has_participant_names():
            return False

        # Check if SHM has no active participants
        if sm is None:
            return True  # SHM unavailable

        num_participants = getattr(sm, 'mNumParticipants', 0)
        if num_participants <= 0:
            return True

        # Check if any participant is actually active
        part_info = getattr(sm, 'mParticipantInfo', [])
        for i in range(min(num_participants, len(part_info))):
            if getattr(part_info[i], 'mIsActive', False):
                return False  # Found an active participant — SHM is viable

        return True  # SHM exists but no active participants

    def _load_log(self):
        """Open a file dialog to load the Replay Analyser Log."""
        filepath = filedialog.askopenfilename(
            title="Select Replay Log",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            self.scorer.load_timeline_log(filepath)
            print(f"Loaded timeline events from {filepath}")

    def _read_shared_memory(self):
        """Attempt to read the AMS2 shared memory mapped file."""
        if not HAS_SHARED_MEMORY:
            return None

        if not hasattr(self, '_shm_lock'):
            self._shm_lock = threading.Lock()

        with self._shm_lock:
            try:
                if self._shm_file is None:
                    self._shm_file = mmap.mmap(-1, ctypes.sizeof(SharedMemory),
                                                '$pcars2$', access=mmap.ACCESS_READ)
                self._shm_file.seek(0)
                self._shm = SharedMemory.from_buffer_copy(self._shm_file.read(
                    ctypes.sizeof(SharedMemory)))
                return self._shm
            except Exception as e:
                import traceback
                print("Error reading shared memory:", e)
                traceback.print_exc()
                self._shm_file = None
                self._shm = None
                return None

    def _tick(self):
        """Main tick loop — poll telemetry, score, update grid."""
        # Determine data source based on user mode and auto-detection
        if self._user_mode == 'udp_only':
            # Manual UDP Only: never read SHM
            sm = None
            self._effective_source = 'udp_manual'
        else:
            # Hybrid mode: read SHM, then check auto-detection
            sm = self._read_shared_memory() if self._mode == 'shared_memory' else None

            # DISABLED UDP FALLBACK FOR TESTING
            # if self._effective_source == 'udp_auto':
            #     # Currently auto-switched to UDP — check if SHM has recovered
            #     if sm is not None and not self._should_auto_switch_to_udp(sm):
            #         # SHM has active participants again — revert to Hybrid
            #         self._effective_source = 'hybrid'
            #         self._auto_switch_counter = 0
            #     else:
            #         sm = None  # Stay on UDP
            # else:
            #     # Currently in Hybrid — check if we should auto-switch
            #     if self._should_auto_switch_to_udp(sm):
            #         self._auto_switch_counter += 1
            #         if self._auto_switch_counter >= 5:
            #             self._effective_source = 'udp_auto'
            #             sm = None  # Use UDP
            #     else:
            #         self._auto_switch_counter = 0
            #         self._effective_source = 'hybrid'
            
            self._effective_source = 'hybrid'

        self._update_source_label()
        self._participants = self.provider.poll(sm) or {}
        
        track_info = None
        session_info = None

        # Update connection status
        if self.provider.is_connected():
            self.lbl_connection.configure(text='✅ Connected to AMS2')
            track_info = self.provider.get_track_info(sm)
            if track_info:
                self.lbl_track.configure(
                    text=f"Track: {track_info['track_name']} ({track_info['track_length']:.0f}m)")
            
            session_info = self.provider.get_session_info(sm)
            if session_info:
                rem = session_info.get('event_time_remaining', -1.0)
                cur = session_info.get('current_time', 0.0)
                laps = session_info.get('laps_in_event', 0)
                if laps <= 0:
                    laps = self.scorer.timeline_laps_in_event
                    
                cur_mins = int(cur) // 60
                cur_secs = int(cur) % 60
                
                if rem <= 0 and self.scorer.timeline_session_time > 0:
                    rem = max(0.0, self.scorer.timeline_session_time - cur)

                rem_str = "null"
                if rem > 0:
                    rem_mins = int(rem) // 60
                    rem_secs = int(rem) % 60
                    rem_str = f"{rem_mins:02d}:{rem_secs:02d}"
                    
                laps_str = str(laps) if laps > 0 else "null"
                
                self.lbl_session_time.configure(
                    text=f"Laps: {laps_str} | Rem: {rem_str} | Elap: {cur_mins:02d}:{cur_secs:02d}"
                )
        else:
            self.lbl_connection.configure(text='⏳ Waiting for AMS2...')
            self.lbl_track.configure(text='Track: —')
            self.lbl_session_time.configure(text='Time: —')

        cur_time = session_info.get('current_time', 0.0) if session_info else None

        # Score
        self._scores = self.scorer.calculate_scores(
            self._participants,
            session_info=session_info,
            track_info=track_info,
            current_time=cur_time
        )

        # Auto director camera switch
        if self._director_enabled and self.provider.is_connected():
            now = time.time()
            active_interval = self._sweep_dwell_time if self.scorer.is_sweep_active else self._switch_interval
            
            if now - self._last_switch_time >= active_interval:
                best = self.scorer.get_best_focus(self._scores, self._participants)
                
                # Extract live camera position from telemetry
                viewed_idx = session_info.get('viewed_participant_index', -1) if session_info else -1
                viewed_pos = None
                if viewed_idx >= 0 and viewed_idx in self._participants:
                    viewed_pos = self._participants[viewed_idx].get('race_position')
                
                if best is not None:
                    is_new_focus = (viewed_pos != best)
                    self.camera.move_to_position(best, viewed_pos)
                    
                    if is_new_focus:
                        # Determine if close racing
                        is_close = False
                        for p in self._participants.values():
                            if p.get('race_position') == best:
                                gap_ahead = p.get('gap_ahead', 999.0)
                                gap_behind = p.get('gap_behind', 999.0)
                                speed = max(p.get('speed', 1.0), 1.0)
                                time_ahead = gap_ahead / speed
                                time_behind = gap_behind / speed
                                if time_ahead <= self._camera_close_gap or time_behind <= self._camera_close_gap:
                                    is_close = True
                                break
                        self.camera.select_random_camera(is_close)
                    
                    best_name = "Unknown"
                    for p in self._participants.values():
                        if p.get('race_position') == best:
                            best_name = p.get('name', 'Unknown')
                            break
                            
                    self.lbl_focus.configure(text=f'Focus: {best_name} (P{best})')
                    self._last_switch_time = now

        if self.camera.current_camera_type != getattr(self, '_last_logged_cam', None):
            print(f"CAMERA TYPE CHANGED TO: {self.camera.current_camera_type}")
            self._last_logged_cam = self.camera.current_camera_type

        # Schedule next tick
        self.root.after(self.TICK_MS, self._tick)

    def run(self):
        """Start the application."""
        self.root.after(self.TICK_MS, self._tick)
        self.root.after(self.GRID_UPDATE_MS, self.gui_builder.update_grid)
        self.root.mainloop()


def main():
    # Enable High DPI awareness for Windows
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    parser = argparse.ArgumentParser(description='AMS2 Auto Director v4.1.1')
    parser.add_argument('--mode', choices=['shared_memory', 'udp'],
                        default='shared_memory',
                        help='Data source mode (default: shared_memory)')
    args = parser.parse_args()

    app = AutoDirectorApp(mode=args.mode)
    app.run()


if __name__ == '__main__':
    main()
