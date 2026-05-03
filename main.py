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

from core.telemetry_provider import TelemetryProvider
from core.scoring_engine import ScoringEngine
from core.camera_controller import CameraController


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
        self._director_enabled = False
        self._last_switch_time = 0.0
        self._switch_interval = 7.0
        self._sweep_dwell_time = 1.0
        self._participants: dict[int, dict] = {}
        self._scores: dict[int, dict] = {}

        # Shared memory handle
        self._shm = None
        self._shm_file = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.provider.start_udp()

    def _on_closing(self):
        """Cleanup and close application."""
        self.provider.stop_udp()
        self.root.destroy()

    def _build_ui(self):
        """Build the tkinter GUI."""
        self.root = tk.Tk()
        self.root.title("AMS2 Auto Director V4.0")
        self.root.configure(bg='#1a1a2e')
        self.root.geometry('1100x700')

        style = ttk.Style()
        style.theme_use('clam')

        # Dark theme colours
        bg_dark = '#1a1a2e'
        bg_panel = '#16213e'
        fg_text = '#e0e0e0'
        accent = '#0f3460'
        highlight = '#e94560'

        style.configure('Dark.TFrame', background=bg_dark)
        style.configure('Panel.TFrame', background=bg_panel)
        style.configure('Dark.TLabel', background=bg_dark, foreground=fg_text,
                         font=('Consolas', 10))
        style.configure('Header.TLabel', background=bg_dark, foreground=highlight,
                         font=('Consolas', 14, 'bold'))
        style.configure('Status.TLabel', background=bg_panel, foreground='#4ecca3',
                         font=('Consolas', 11))
        style.configure('Dark.TButton', background=accent, foreground=fg_text,
                         font=('Consolas', 10))

        # Configure Treeview for dark theme
        style.configure('Dark.Treeview',
                         background='#0a0a1a',
                         foreground=fg_text,
                         fieldbackground='#0a0a1a',
                         font=('Consolas', 9),
                         rowheight=22)
        style.configure('Dark.Treeview.Heading',
                         background=accent,
                         foreground=fg_text,
                         font=('Consolas', 9, 'bold'))
        style.map('Dark.Treeview', background=[('selected', highlight)])

        # Configure tag for highest score highlighting
        self.tree = None # Created below, but we define the tag later


        # ── Top: Status Bar ─────────────────────────────────────────────
        status_frame = ttk.Frame(self.root, style='Panel.TFrame')
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.lbl_title = ttk.Label(status_frame, text='AMS2 AUTO DIRECTOR V4.0',
                                    style='Header.TLabel')
        self.lbl_title.pack(side=tk.LEFT, padx=10)

        self.lbl_connection = ttk.Label(status_frame, text='⏳ Waiting for AMS2...',
                                         style='Status.TLabel')
        self.lbl_connection.pack(side=tk.LEFT, padx=20)

        self.lbl_director = ttk.Label(status_frame, text='Director: OFF',
                                       style='Status.TLabel')
        self.lbl_director.pack(side=tk.LEFT, padx=20)

        self.lbl_focus = ttk.Label(status_frame, text='Focus: —',
                                    style='Status.TLabel')
        self.lbl_focus.pack(side=tk.LEFT, padx=20)

        self.lbl_session_time = ttk.Label(status_frame, text='Time: —',
                                          style='Status.TLabel')
        self.lbl_session_time.pack(side=tk.RIGHT, padx=20)

        self.lbl_track = ttk.Label(status_frame, text='Track: —',
                                    style='Status.TLabel')
        self.lbl_track.pack(side=tk.RIGHT, padx=10)

        # ── Middle: Leaderboard Grid ────────────────────────────────────
        grid_frame = ttk.Frame(self.root, style='Dark.TFrame')
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        columns = ('pos', 'name', 'lap', 'speed', 'gap', 'cars_ahead',
                    'pit_pen', 'spd_pen', 'cars_bon', 'cls_spd_bon', 'close_bon', 'pos_bon', 'acc_bon', 'ovt_bon', 'seq_bon', 'total')
        self.tree = ttk.Treeview(grid_frame, columns=columns, show='headings',
                                  style='Dark.Treeview', height=20)
        self.tree.tag_configure('highest', foreground='#ffd700', font=('Consolas', 9, 'bold'))

        headers = {
            'pos': ('P', 30), 'name': ('Driver', 140), 'lap': ('Lap', 40), 'speed': ('Speed', 60),
            'gap': ('Gap', 60), 'cars_ahead': ('Cars↑', 50),
            'pit_pen': ('Pit', 45), 'spd_pen': ('Spd', 45),
            'cars_bon': ('Cars', 45), 'cls_spd_bon': ('ClsSpd', 50), 'close_bon': ('Close', 50),
            'pos_bon': ('Pos', 45), 'acc_bon': ('Acc', 45), 'ovt_bon': ('Ovt', 45), 'seq_bon': ('Seq', 45), 'total': ('TOTAL', 60),
        }
        for col, (heading, width) in headers.items():
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        # ── Bottom: Tuning Panel ────────────────────────────────────────
        tune_frame = ttk.Frame(self.root, style='Panel.TFrame')
        tune_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(tune_frame, text='TUNING', style='Header.TLabel').pack(side=tk.LEFT, padx=10)

        self._tuning_vars = {}
        tuning_params = [
            ('UDP Port', 'udp_port', 5606),
            ('Interval (s)', 'switch_interval', self._switch_interval),
            ('Sweep Dwell', 'sweep_dwell_time', self.scorer.sweep_dwell_time),
            ('Pos Factor', 'race_position_bonus_factor', self.scorer.race_position_bonus_factor),
            ('Pit Penalty', 'pit_mode_penalty', self.scorer.pit_mode_penalty),
            ('Speed Pen', 'speed_penalty', self.scorer.speed_penalty),
            ('Leader Mult', 'leader_cars_ahead_multiplier', self.scorer.leader_cars_ahead_multiplier),
            ('Other Mult', 'other_cars_ahead_multiplier', self.scorer.other_cars_ahead_multiplier),
            ('Max Gap', 'close_racing_max_gap', self.scorer.close_racing_max_gap),
            ('Event Pre-Off', 'timeline_pre_offset', self.scorer.timeline_pre_offset),
            ('Event Post-Off', 'timeline_post_offset', self.scorer.timeline_post_offset),
        ]

        for label_text, key, default_val in tuning_params:
            f = ttk.Frame(tune_frame, style='Panel.TFrame')
            f.pack(side=tk.LEFT, padx=5)
            ttk.Label(f, text=label_text, style='Dark.TLabel').pack(side=tk.TOP)
            var = tk.StringVar(value=str(default_val))
            entry = tk.Entry(f, textvariable=var, width=6, bg='#0a0a1a', fg='#e0e0e0',
                              font=('Consolas', 10), insertbackground='#e0e0e0')
            entry.pack(side=tk.TOP)
            self._tuning_vars[key] = var

        btn_apply = ttk.Button(tune_frame, text='Apply', style='Dark.TButton',
                                command=self._apply_tuning)
        btn_apply.pack(side=tk.LEFT, padx=15)

        btn_toggle = ttk.Button(tune_frame, text='Toggle Director (Space)',
                                 style='Dark.TButton', command=self._toggle_director)
        btn_toggle.pack(side=tk.LEFT, padx=5)

        btn_load_log = ttk.Button(tune_frame, text='Load Replay Log',
                                   style='Dark.TButton', command=self._load_log)
        btn_load_log.pack(side=tk.LEFT, padx=5)

        # True OS-level global binding for Ctrl+Space
        try:
            keyboard.add_hotkey('ctrl+space', lambda: self.root.after(0, self._toggle_director))
        except Exception as e:
            print(f"Warning: Could not bind global hotkey: {e}")
            # Fallback to application-level global binding
            self.root.bind_all('<Control-space>', lambda e: self._toggle_director())

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
            self.scorer.timeline_pre_offset = float(
                self._tuning_vars['timeline_pre_offset'].get())
            self.scorer.timeline_post_offset = float(
                self._tuning_vars['timeline_post_offset'].get())
        except ValueError:
            pass  # Ignore invalid input

    def _toggle_director(self):
        """Toggle auto director on/off."""
        self._director_enabled = not self._director_enabled
        status = 'ON' if self._director_enabled else 'OFF'
        self.lbl_director.configure(text=f'Director: {status}')

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

        try:
            if self._shm_file is None:
                self._shm_file = mmap.mmap(-1, ctypes.sizeof(SharedMemory),
                                            '$pcars2$', access=mmap.ACCESS_READ)
            self._shm_file.seek(0)
            self._shm = SharedMemory.from_buffer_copy(self._shm_file.read(
                ctypes.sizeof(SharedMemory)))
            return self._shm
        except Exception:
            self._shm_file = None
            self._shm = None
            return None

    def _tick(self):
        """Main tick loop — poll telemetry, score, update grid."""
        sm = self._read_shared_memory() if self._mode == 'shared_memory' else None
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
                    self.camera.move_to_position(best, viewed_pos)
                    
                    best_name = "Unknown"
                    for p in self._participants.values():
                        if p.get('race_position') == best:
                            best_name = p.get('name', 'Unknown')
                            break
                            
                    self.lbl_focus.configure(text=f'Focus: {best_name} (P{best})')
                    self._last_switch_time = now

        # Schedule next tick
        self.root.after(self.TICK_MS, self._tick)

    def _update_grid(self):
        """Update the leaderboard grid (runs at 1s intervals)."""
        # Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self._participants:
            self.root.after(self.GRID_UPDATE_MS, self._update_grid)
            return

        # Sort by race position
        sorted_indices = sorted(
            self._participants.keys(),
            key=lambda i: self._participants[i].get('race_position', 99)
        )

        # Find highest score for highlighting
        best_score = float('-inf')
        best_idx = None
        for idx in sorted_indices:
            p = self._participants[idx]
            if p.get('is_active', False):
                total = self._scores.get(idx, {}).get('total_score', float('-inf'))
                if total > best_score:
                    best_score = total
                    best_idx = idx

        for idx in sorted_indices:
            p = self._participants[idx]
            if not p.get('is_active', False):
                continue

            s = self._scores.get(idx, {})
            values = (
                str(p.get('race_position', 0)),
                str(p.get('name', 'Unknown')),
                str(p.get('current_lap', 0)),
                f"{p.get('speed', 0.0):.0f}",
                f"{p.get('gap_ahead', 0.0):.0f}",
                p.get('cars_ahead_250m', 0),
                f"{s.get('pit_mode_penalty', 0):.1f}",
                f"{s.get('speed_penalty', 0):.1f}",
                f"{s.get('cars_ahead_bonus', 0):.1f}",
                f"{s.get('closing_speed_bonus', 0):.1f}",
                f"{s.get('close_racing_bonus', 0):.1f}",
                f"{s.get('race_position_bonus', 0):.1f}",
                f"{s.get('accident_bonus', 0):.1f}",
                f"{s.get('overtake_bonus', 0):.1f}",
                f"{s.get('sequence_bonus', 0):.1f}",
                f"{s.get('total_score', 0):.1f}",
            )
            tags = ('highest',) if idx == best_idx else ()
            self.tree.insert('', tk.END, values=values, tags=tags)

        self.root.after(self.GRID_UPDATE_MS, self._update_grid)

    def run(self):
        """Start the application."""
        self.root.after(self.TICK_MS, self._tick)
        self.root.after(self.GRID_UPDATE_MS, self._update_grid)
        self.root.mainloop()


def main():
    # Enable High DPI awareness for Windows
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    parser = argparse.ArgumentParser(description='AMS2 Auto Director V4.0')
    parser.add_argument('--mode', choices=['shared_memory', 'udp'],
                        default='shared_memory',
                        help='Data source mode (default: shared_memory)')
    args = parser.parse_args()

    app = AutoDirectorApp(mode=args.mode)
    app.run()


if __name__ == '__main__':
    main()
