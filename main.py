"""AMS2 Auto Director V4.0 — Main Entry Point.

Thin tkinter GUI shell. All business logic lives in core/ modules.
This file owns no scoring, telemetry, or camera logic.
"""
import tkinter as tk
from tkinter import ttk
import argparse
import time
import mmap
import ctypes

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
        self._current_focus_position = None
        self._last_switch_time = 0.0
        self._switch_interval = 7.0
        self._participants: dict[int, dict] = {}
        self._scores: dict[int, dict] = {}

        # Shared memory handle
        self._shm = None
        self._shm_file = None

        self._build_ui()

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

        self.lbl_track = ttk.Label(status_frame, text='Track: —',
                                    style='Status.TLabel')
        self.lbl_track.pack(side=tk.RIGHT, padx=10)

        # ── Middle: Leaderboard Grid ────────────────────────────────────
        grid_frame = ttk.Frame(self.root, style='Dark.TFrame')
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        columns = ('pos', 'name', 'speed', 'gap', 'cars_ahead',
                    'pit_pen', 'spd_pen', 'cars_bon', 'close_bon', 'pos_bon', 'total')
        self.tree = ttk.Treeview(grid_frame, columns=columns, show='headings',
                                  style='Dark.Treeview', height=20)

        headers = {
            'pos': ('P', 30), 'name': ('Driver', 140), 'speed': ('Speed', 60),
            'gap': ('Gap', 60), 'cars_ahead': ('Cars↑', 50),
            'pit_pen': ('Pit', 45), 'spd_pen': ('Spd', 45),
            'cars_bon': ('Cars', 45), 'close_bon': ('Close', 50),
            'pos_bon': ('Pos', 45), 'total': ('TOTAL', 60),
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
            ('Interval (s)', 'switch_interval', self._switch_interval),
            ('Pos Factor', 'race_position_bonus_factor', self.scorer.race_position_bonus_factor),
            ('Pit Penalty', 'pit_mode_penalty', self.scorer.pit_mode_penalty),
            ('Speed Pen', 'speed_penalty', self.scorer.speed_penalty),
            ('Leader Mult', 'leader_cars_ahead_multiplier', self.scorer.leader_cars_ahead_multiplier),
            ('Other Mult', 'other_cars_ahead_multiplier', self.scorer.other_cars_ahead_multiplier),
            ('Max Gap', 'close_racing_max_gap', self.scorer.close_racing_max_gap),
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

        # Spacebar binding
        self.root.bind('<space>', lambda e: self._toggle_director())

    def _apply_tuning(self):
        """Write GUI values to scorer attributes."""
        try:
            self._switch_interval = float(self._tuning_vars['switch_interval'].get())
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
        except ValueError:
            pass  # Ignore invalid input

    def _toggle_director(self):
        """Toggle auto director on/off."""
        self._director_enabled = not self._director_enabled
        status = 'ON' if self._director_enabled else 'OFF'
        self.lbl_director.configure(text=f'Director: {status}')

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

        # Update connection status
        if self.provider.is_connected():
            self.lbl_connection.configure(text='✅ Connected to AMS2')
            track_info = self.provider.get_track_info(sm)
            if track_info:
                self.lbl_track.configure(
                    text=f"Track: {track_info['track_name']} ({track_info['track_length']:.0f}m)")
        else:
            self.lbl_connection.configure(text='⏳ Waiting for AMS2...')
            self.lbl_track.configure(text='Track: —')

        # Score
        self._scores = self.scorer.calculate_scores(self._participants)

        # Auto director camera switch
        if self._director_enabled and self.provider.is_connected():
            now = time.time()
            if now - self._last_switch_time >= self._switch_interval:
                best = self.scorer.get_best_focus(self._scores, self._participants)
                if best is not None:
                    self.camera.move_to_position(best, self._current_focus_position)
                    self._current_focus_position = best
                    self.lbl_focus.configure(text=f'Focus: P{best}')
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

        for idx in sorted_indices:
            p = self._participants[idx]
            if not p.get('is_active', False):
                continue

            s = self._scores.get(idx, {})
            values = (
                p.get('race_position', '—'),
                p.get('name', '—'),
                f"{p.get('speed', 0):.0f}",
                f"{p.get('gap_ahead', 0):.0f}",
                p.get('cars_ahead_250m', 0),
                f"{s.get('pit_mode_penalty', 0):.1f}",
                f"{s.get('speed_penalty', 0):.1f}",
                f"{s.get('cars_ahead_bonus', 0):.1f}",
                f"{s.get('close_racing_bonus', 0):.1f}",
                f"{s.get('race_position_bonus', 0):.1f}",
                f"{s.get('total_score', 0):.1f}",
            )
            self.tree.insert('', tk.END, values=values)

        self.root.after(self.GRID_UPDATE_MS, self._update_grid)

    def run(self):
        """Start the application."""
        self.root.after(self.TICK_MS, self._tick)
        self.root.after(self.GRID_UPDATE_MS, self._update_grid)
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser(description='AMS2 Auto Director V4.0')
    parser.add_argument('--mode', choices=['shared_memory', 'udp'],
                        default='shared_memory',
                        help='Data source mode (default: shared_memory)')
    args = parser.parse_args()

    app = AutoDirectorApp(mode=args.mode)
    app.run()


if __name__ == '__main__':
    main()
