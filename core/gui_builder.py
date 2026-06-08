import tkinter as tk
from tkinter import ttk

class GUIBuilder:
    def __init__(self, app):
        self.app = app
        
    def build_ui(self):
        """Build the tkinter GUI."""
        self.app.root = tk.Tk()
        self.app.root.title("AMS2 Auto Director v4.1.6")
        self.app.root.configure(bg='#1a1a2e')
        self.app.root.geometry('1100x700')

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
        style.configure('Dark.TLabel', background=bg_dark, foreground=fg_text, font=('Consolas', 10))
        style.configure('Header.TLabel', background=bg_dark, foreground=highlight, font=('Consolas', 14, 'bold'))
        style.configure('Status.TLabel', background=bg_panel, foreground='#4ecca3', font=('Consolas', 11))
        style.configure('Dark.TButton', background=accent, foreground=fg_text, font=('Consolas', 10))

        style.configure('Dark.Treeview', background='#0a0a1a', foreground=fg_text, fieldbackground='#0a0a1a', font=('Consolas', 9), rowheight=22)
        style.configure('Dark.Treeview.Heading', background=accent, foreground=fg_text, font=('Consolas', 9, 'bold'))
        style.map('Dark.Treeview', background=[('selected', highlight)])

        self.app.tree = None 

        status_frame = ttk.Frame(self.app.root, style='Panel.TFrame')
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.app.lbl_title = ttk.Label(status_frame, text='AMS2 AUTO DIRECTOR v4.1.1', style='Header.TLabel')
        self.app.lbl_title.pack(side=tk.LEFT, padx=10)

        self.app.lbl_connection = ttk.Label(status_frame, text='⏳ Waiting for AMS2...', style='Status.TLabel')
        self.app.lbl_connection.pack(side=tk.LEFT, padx=20)

        self.app.lbl_director = ttk.Label(status_frame, text='Director: OFF', style='Status.TLabel')
        self.app.lbl_director.pack(side=tk.LEFT, padx=20)

        self.app.lbl_camera = ttk.Label(status_frame, text='Auto Cam: ON', style='Status.TLabel')
        self.app.lbl_camera.pack(side=tk.LEFT, padx=20)

        self.app.lbl_focus = ttk.Label(status_frame, text='Focus: —', style='Status.TLabel')
        self.app.lbl_focus.pack(side=tk.LEFT, padx=20)

        self.app.lbl_session_time = ttk.Label(status_frame, text='Time: —', style='Status.TLabel')
        self.app.lbl_session_time.pack(side=tk.RIGHT, padx=20)

        self.app.lbl_source = ttk.Label(status_frame, text='Source: Hybrid', style='Status.TLabel')
        self.app.lbl_source.pack(side=tk.RIGHT, padx=10)

        self.app.lbl_track = ttk.Label(status_frame, text='Track: —', style='Status.TLabel')
        self.app.lbl_track.pack(side=tk.RIGHT, padx=10)

        grid_frame = ttk.Frame(self.app.root, style='Dark.TFrame')
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        columns = ('pos', 'name', 'lap', 'speed', 'gap', 'cars_ahead', 'pit_pen', 'spd_pen', 'cars_bon', 'cls_spd_bon', 'close_bon', 'pos_bon', 'acc_bon', 'ovt_bon', 'seq_bon', 'total')
        self.app.tree = ttk.Treeview(grid_frame, columns=columns, show='headings', style='Dark.Treeview', height=20)
        self.app.tree.tag_configure('highest', foreground='#ffd700', font=('Consolas', 9, 'bold'))

        headers = {
            'pos': ('P', 30), 'name': ('Driver', 140), 'lap': ('Lap', 40), 'speed': ('Speed', 60),
            'gap': ('Gap', 60), 'cars_ahead': ('Cars↑', 50),
            'pit_pen': ('Pit', 45), 'spd_pen': ('Spd', 45),
            'cars_bon': ('Cars', 45), 'cls_spd_bon': ('ClsSpd', 50), 'close_bon': ('Close', 50),
            'pos_bon': ('Pos', 45), 'acc_bon': ('Acc', 45), 'ovt_bon': ('Ovt', 45), 'seq_bon': ('Seq', 45), 'total': ('TOTAL', 60),
        }
        for col, (heading, width) in headers.items():
            self.app.tree.heading(col, text=heading)
            self.app.tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(grid_frame, orient=tk.VERTICAL, command=self.app.tree.yview)
        self.app.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.app.tree.pack(fill=tk.BOTH, expand=True)

        tune_frame = ttk.Frame(self.app.root, style='Panel.TFrame')
        tune_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(tune_frame, text='TUNING', style='Header.TLabel').pack(side=tk.LEFT, padx=10)

        self.app._tuning_vars = {}
        scorer = getattr(self.app, 'scorer', None)
        
        tuning_params = [
            ('UDP Port', 'udp_port', 5606),
            ('Interval (s)', 'switch_interval', self.app._switch_interval),
            ('Sweep Dwell', 'sweep_dwell_time', scorer.sweep_dwell_time if scorer else 1.0),
            ('Pos Factor', 'race_position_bonus_factor', scorer.race_position_bonus_factor if scorer else 1.0),
            ('Pit Penalty', 'pit_mode_penalty', scorer.pit_mode_penalty if scorer else 1.0),
            ('Speed Pen', 'speed_penalty', scorer.speed_penalty if scorer else 1.0),
            ('Leader Mult', 'leader_cars_ahead_multiplier', scorer.leader_cars_ahead_multiplier if scorer else 1.0),
            ('Other Mult', 'other_cars_ahead_multiplier', scorer.other_cars_ahead_multiplier if scorer else 1.0),
            ('Max Gap', 'close_racing_max_gap', scorer.close_racing_max_gap if scorer else 1.0),
            ('Cam Gap (s)', 'camera_close_gap', self.app._camera_close_gap),
            ('Event Pre-Off', 'timeline_pre_offset', scorer.timeline_pre_offset if scorer else 1.0),
            ('Event Post-Off', 'timeline_post_offset', scorer.timeline_post_offset if scorer else 1.0),
        ]

        for label_text, key, default_val in tuning_params:
            f = ttk.Frame(tune_frame, style='Panel.TFrame')
            f.pack(side=tk.LEFT, padx=5)
            ttk.Label(f, text=label_text, style='Dark.TLabel').pack(side=tk.TOP)
            var = tk.StringVar(value=str(default_val))
            entry = tk.Entry(f, textvariable=var, width=6, bg='#0a0a1a', fg='#e0e0e0', font=('Consolas', 10), insertbackground='#e0e0e0')
            entry.pack(side=tk.TOP)
            self.app._tuning_vars[key] = var

        btn_apply = ttk.Button(tune_frame, text='Apply', style='Dark.TButton', command=getattr(self.app, '_apply_tuning', lambda: None))
        btn_apply.pack(side=tk.LEFT, padx=15)

        btn_toggle = ttk.Button(tune_frame, text='Toggle Director (Ctrl+Space)', style='Dark.TButton', command=getattr(self.app, '_toggle_director', lambda: None))
        btn_toggle.pack(side=tk.LEFT, padx=5)

        btn_load_log = ttk.Button(tune_frame, text='Load Replay Log', style='Dark.TButton', command=getattr(self.app, '_load_log', lambda: None))
        btn_load_log.pack(side=tk.LEFT, padx=5)
        
        btn_overlays = ttk.Button(tune_frame, text='Web Overlays', style='Dark.TButton', command=getattr(self.app, '_open_overlays', lambda: None))
        btn_overlays.pack(side=tk.LEFT, padx=5)

        self.app._btn_data_source = ttk.Button(tune_frame, text='Mode: Hybrid', style='Dark.TButton', command=getattr(self.app, '_toggle_data_source', lambda: None))
        self.app._btn_data_source.pack(side=tk.LEFT, padx=5)
        
    def update_grid(self):
        """Update the leaderboard grid (runs at 1s intervals)."""
        try:
            # Clear existing rows
            for item in self.app.tree.get_children():
                self.app.tree.delete(item)

            if not self.app._participants:
                return

            # Sort by race position
            sorted_indices = sorted(
                self.app._participants.keys(),
                key=lambda i: self.app._participants[i].get('race_position', 99)
            )

            # Find highest score for highlighting
            best_score = float('-inf')
            best_idx = None
            for idx in sorted_indices:
                p = self.app._participants[idx]
                if p.get('is_active', False):
                    total = self.app._scores.get(idx, {}).get('total_score', float('-inf'))
                    if total > best_score:
                        best_score = total
                        best_idx = idx

            for idx in sorted_indices:
                p = self.app._participants[idx]
                if not p.get('is_active', False):
                    continue

                s = self.app._scores.get(idx, {})
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
                self.app.tree.insert('', tk.END, values=values, tags=tags)
        except Exception as e:
            import traceback
            print("Grid update error:", e)
            traceback.print_exc()
        finally:
            self.app.root.after(getattr(self.app, 'GRID_UPDATE_MS', 1000), self.update_grid)
