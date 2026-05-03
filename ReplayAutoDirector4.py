import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import ctypes
import mmap
import time
import keyboard
try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    from shared_memory_struct import SharedMemory
    from pyKey import pressKey, releaseKey
    HAS_SHARED_MEM = True
except ImportError:
    HAS_SHARED_MEM = False

class TimelineEngine:
    def __init__(self):
        # Regex patterns
        self.re_time = re.compile(r"^(\d{2}):(\d{2}\.\d{2}) - ")
        self.re_accident = re.compile(r"Accident involving: (.+?)(?: \(P(\d+)\))?$")
        self.re_overtake = re.compile(r"Overtake! (.+?)(?: \(P\d+\))? overtook (.+?)(?: \(P\d+\))? for position (\d+)$")
        self.re_battle = re.compile(r"Close Battle! (.+?)(?: \(P(\d+)\))? is pressuring (.+?)(?: \(P\d+\))?$")
        self.re_leader = re.compile(r"Leader (.+?) \(P1\) started Lap (\d+)$")
        self.re_total_time = re.compile(r"Total Session Time: (\d{2}):(\d{2}\.\d{2})")
        self.re_leader_laps = re.compile(r"Leader Laps Completed: (\d+)")
        self.re_driver_lap = re.compile(r"DEBUG: (.+?) \(P(\d+)\) started Lap (\d+)")
        
        # Scoring configuration
        self.base_accident_score = 800
        self.base_overtake_score = 500
        self.base_battle_score = 100
        self.base_leader_score = 2000  # Final lap tracking is highest priority
        
        self.accident_dwell = 15.0
        self.overtake_dwell = 12.0
        self.battle_dwell = 12.0
        self.anticipation_time = 0.0
        
        self.screen_time_history = {}
        self.penalty_weight = 0.5
        
    def parse_line(self, line):
        """Extracts event data from a log line."""
        
        # 5. Footer: Total Session Time (Check this before time_match)
        time_total_match = self.re_total_time.search(line)
        if time_total_match:
            minutes = int(time_total_match.group(1))
            seconds = float(time_total_match.group(2))
            timestamp = (minutes * 60) + seconds
            return {
                'type': 'Total Session Time',
                'timestamp': timestamp
            }
            
        # 6. Footer: Leader Laps Completed
        laps_match = self.re_leader_laps.search(line)
        if laps_match:
            return {
                'type': 'Leader Laps Completed',
                'lap': int(laps_match.group(1))
            }
            
        # Standard events require a timestamp prefix
        time_match = self.re_time.match(line)
        if not time_match:
            return None
            
        minutes = int(time_match.group(1))
        seconds = float(time_match.group(2))
        timestamp = (minutes * 60) + seconds
        
        event_str = line[time_match.end():]
        
        # 1. Accident
        acc_match = self.re_accident.match(event_str)
        if acc_match:
            return {
                'type': 'Accident',
                'timestamp': timestamp,
                'target_driver': acc_match.group(1),
                'position': int(acc_match.group(2)) if acc_match.group(2) else None
            }
            
        # 2. Overtake
        ov_match = self.re_overtake.match(event_str)
        if ov_match:
            return {
                'type': 'Overtake',
                'timestamp': timestamp,
                'target_driver': ov_match.group(1),
                'target_driver_2': ov_match.group(2),
                'position': int(ov_match.group(3))
            }
            
        # 3. Close Battle
        bat_match = self.re_battle.match(event_str)
        if bat_match:
            return {
                'type': 'Close Battle',
                'timestamp': timestamp,
                'target_driver': bat_match.group(1),
                'target_driver_2': bat_match.group(3),
                'position': int(bat_match.group(2)) if bat_match.group(2) else None
            }
            
        # 4. Leader Lap
        lead_match = self.re_leader.match(event_str)
        if lead_match:
            return {
                'type': 'Leader Lap',
                'timestamp': timestamp,
                'target_driver': lead_match.group(1),
                'position': 1,
                'lap': int(lead_match.group(2))
            }
            
            
        # 5. Driver Lap
        m_dl = self.re_driver_lap.search(event_str)
        if m_dl:
            return {
                'type': 'Driver Lap',
                'timestamp': timestamp,
                'target_driver': m_dl.group(1),
                'position': int(m_dl.group(2)),
                'lap': int(m_dl.group(3))
            }
            
        return None

    def generate_finish_sequence(self, events, leader_laps_completed):
        """Calculates lap pace for the final lap and generates the cascading sweep sequence."""
        if leader_laps_completed >= 999:
            return []
            
        driver_laps = [e for e in events if e['type'] == 'Driver Lap']
        if not driver_laps:
            return []
            
        start_of_final_lap = leader_laps_completed - 1
        
        p1_laps = [e for e in driver_laps if e['position'] == 1]
        
        final_lap_start_event = next((e for e in p1_laps if e['lap'] == start_of_final_lap), None)
        penult_lap_start_event = next((e for e in p1_laps if e['lap'] == start_of_final_lap - 1), None)
        race_end_event = next((e for e in p1_laps if e['lap'] == leader_laps_completed), None)
        
        finish_sequence = []
        checkered_flag_ms = None
        
        if final_lap_start_event and penult_lap_start_event and race_end_event:
            pace = final_lap_start_event['timestamp'] - penult_lap_start_event['timestamp']
            midpoint = final_lap_start_event['timestamp'] + (pace / 2)
            checkered_flag_ms = race_end_event['timestamp']
            
            # Dwell 1.0s after the leader crosses the line
            leader_end_time = checkered_flag_ms + 1.0
            duration = leader_end_time - midpoint
            
            if duration > 0:
                finish_sequence.append({
                    'type': 'Leader Lap Trackside',
                    'timestamp': midpoint,
                    'target_driver': race_end_event['target_driver'],
                    'position': 1,
                    'camera': 7,
                    'duration': duration,
                    'score': self.base_leader_score,
                    'base_score': self.base_leader_score
                })
                
        if not checkered_flag_ms:
            return finish_sequence
            
        finishers = [e for e in driver_laps if e['lap'] == leader_laps_completed]
        finishers.sort(key=lambda x: x['timestamp'])
        
        cascade_events = []
        last_sweep_end = leader_end_time
        
        for curr in finishers:
            # If this driver crossed the line before our camera became available, skip them!
            if curr['timestamp'] <= last_sweep_end:
                continue
                
            # Start watching them now, and hold until 1.0s after they cross the line
            event_start = last_sweep_end
            event_end = curr['timestamp'] + 1.0
            duration = event_end - event_start
            
            if duration > 0:
                cascade_events.append({
                    'type': 'Finish Sweep Trackside',
                    'timestamp': event_start,
                    'target_driver': curr['target_driver'],
                    'position': curr['position'],
                    'camera': 7,
                    'duration': duration,
                    'score': 2000,
                    'base_score': 2000
                })
                last_sweep_end = event_end
                
        finish_sequence.extend(cascade_events)
        return finish_sequence

    def get_next_finish_target(self, participants, leader_laps_completed, finish_targets):
        """Identifies the highest placed driver who has not yet finished their race."""
        best_candidate = None
        highest_pos = 999
        
        for p in participants:
            name = p['name']
            pos = p['position']
            lap = p['current_lap']
            
            has_finished = False
            if lap > leader_laps_completed:
                has_finished = True
            elif name in finish_targets and lap >= finish_targets[name]:
                has_finished = True
                
            if not has_finished and pos < highest_pos:
                highest_pos = pos
                best_candidate = name
                
        return best_candidate

    def apply_base_scores(self, events):
        """Applies configured base scores to a list of events."""
        scored = []
        for e in events:
            new_e = e.copy()
            if e['type'] == 'Accident':
                pos = e.get('position') or 1
                penalty = max(0, (pos - 1) * 20)
                new_e['base_score'] = max(0, self.base_accident_score - penalty)
                new_e['duration'] = self.accident_dwell
                new_e['camera'] = 7
            elif e['type'] == 'Overtake':
                new_e['base_score'] = self.base_overtake_score
                new_e['duration'] = self.overtake_dwell
            elif e['type'] == 'Close Battle':
                new_e['base_score'] = self.base_battle_score
                new_e['duration'] = self.battle_dwell
            elif e['type'] in ['Leader Lap', 'Leader Lap Trackside', 'Finish Sweep Trackside']:
                new_e['base_score'] = self.base_leader_score
            else:
                new_e['base_score'] = 0
                
            # Apply Anticipation Time (Start Early, Leave Early)
            # Exempt absolute timing events related to the end sequence
            if new_e['type'] not in ['Leader Lap Trackside', 'Finish Sweep Trackside', 'Total Session Time', 'Leader Laps Completed']:
                if 'timestamp' in new_e:
                    new_e['timestamp'] = max(0.0, new_e['timestamp'] - self.anticipation_time)
                    
            scored.append(new_e)
        return scored

    def apply_position_modifier(self, events):
        """Adds a position modifier to the base score (50 - position) to break ties."""
        scored = []
        for e in events:
            event_copy = e.copy()
            # If base_score isn't set, default to 0
            base = event_copy.get('base_score', 0)
            pos = event_copy.get('position')
            
            if pos is not None:
                # Add (50 - position) to the score. P1 gets +49, P20 gets +30.
                modifier = max(0, 50 - pos)
                event_copy['score'] = base + modifier
            else:
                event_copy['score'] = base
                
            scored.append(event_copy)
        return scored

    def apply_lookahead_modifier(self, events):
        """Scans ahead 15s. If a Close Battle results in an Overtake, elevate the battle score."""
        scored = []
        for i, e in enumerate(events):
            event_copy = e.copy()
            
            if event_copy['type'] == 'Close Battle':
                # Look ahead for overtakes within 15s
                for j in range(i + 1, len(events)):
                    future_event = events[j]
                    time_diff = future_event['timestamp'] - event_copy['timestamp']
                    
                    if time_diff > 15:
                        break  # Outside window, stop looking
                        
                    if future_event['type'] == 'Overtake':
                        # Check if drivers match
                        drivers_battle = {event_copy.get('target_driver'), event_copy.get('target_driver_2')}
                        drivers_overtake = {future_event.get('target_driver'), future_event.get('target_driver_2')}
                        
                        if drivers_battle == drivers_overtake:
                            # Elevate the battle score significantly
                            event_copy['base_score'] = self.base_overtake_score + 100
                            break
                            
            scored.append(event_copy)
        return scored

    def apply_screen_time_penalty(self, events, current_time):
        """Deducts score based on screen time in the last 180 seconds."""
        scored = []
        for e in events:
            event_copy = e.copy()
            base = event_copy.get('base_score', 0)
            driver1 = event_copy.get('target_driver')
            driver2 = event_copy.get('target_driver_2')
            
            # Calculate total screen time in last 180s for drivers involved
            window_start = current_time - 180
            total_screen_time = 0
            
            for driver in [driver1, driver2]:
                if not driver or driver not in self.screen_time_history:
                    continue
                for start, end in self.screen_time_history[driver]:
                    if end < window_start:
                        continue # Too old
                    # Calculate overlap with the 3-minute window
                    overlap_start = max(start, window_start)
                    overlap_end = min(end, current_time)
                    if overlap_end > overlap_start:
                        total_screen_time += (overlap_end - overlap_start)
                        
            penalty = total_screen_time * self.penalty_weight
            event_copy['score'] = base - penalty
            scored.append(event_copy)
            
        return scored

    def resolve_overlaps(self, events, min_cam_time=5.0):
        """Builds a non-overlapping schedule, higher scores win, enforcing minimum camera time."""
        # Sort chronologically
        sorted_events = sorted(events, key=lambda x: x['timestamp'])
        schedule = []
        
        for e in sorted_events:
            new_ev = e.copy()
            while schedule:
                last_ev = schedule[-1]
                last_end = last_ev['timestamp'] + last_ev.get('duration', 0)
                
                if new_ev['timestamp'] < last_end:
                    # Overlap detected
                    if new_ev.get('score', 0) > last_ev.get('score', 0):
                        time_since_last_start = new_ev['timestamp'] - last_ev['timestamp']
                        
                        is_accident = new_ev.get('type') == 'Accident'
                        is_override = new_ev.get('type') in ['Manual Override', 'Leader Lap Trackside', 'Finish Sweep Trackside']
                        
                        if time_since_last_start < min_cam_time and not is_accident and not is_override:
                            # Push the new event back to satisfy min_cam_time
                            push_amount = min_cam_time - time_since_last_start
                            new_ev['timestamp'] += push_amount
                            new_ev['duration'] -= push_amount
                            if new_ev['duration'] < min_cam_time:
                                # Discard new_ev entirely
                                new_ev = None
                                break
                                
                        # Re-calculate in case new_ev was pushed
                        last_ev['duration'] = new_ev['timestamp'] - last_ev['timestamp']
                        
                        last_ev_is_accident = last_ev.get('type') == 'Accident'
                        last_ev_is_override = last_ev.get('type') in ['Manual Override', 'Leader Lap Trackside', 'Finish Sweep Trackside']
                        
                        if last_ev['duration'] < min_cam_time and not last_ev_is_accident and not last_ev_is_override:
                            schedule.pop()
                            continue # Re-evaluate new_ev against the new last_ev
                        elif last_ev['duration'] <= 0:
                            schedule.pop()
                            continue # Re-evaluate new_ev against the new last_ev
                            
                        break # Successfully truncated last_ev, no need to keep popping
                    else:
                        # Old event wins, new event is discarded
                        new_ev = None
                        break
                else:
                    break # No overlap
                    
            if new_ev is not None:
                schedule.append(new_ev)
                
        return schedule

    def generate_schedule(self, lines, min_cam_time=5.0, manual_overrides=None):
        """Headless orchestration method to parse raw lines and produce the final schedule."""
        if manual_overrides is None:
            manual_overrides = []
            
        # 1. Parse lines
        events = []
        leader_laps_completed = 999
        for line in lines:
            parsed = self.parse_line(line)
            if parsed:
                if parsed.get('type') == 'Leader Laps Completed':
                    leader_laps_completed = parsed.get('lap', 999)
                elif parsed.get('type') != 'Total Session Time':
                    events.append(parsed)
                    
        # 1.5 Inject Final Lap Trackside Sequence & Cascade
        finish_seq = self.generate_finish_sequence(events, leader_laps_completed)
        
        # Remove Driver Lap telemetry from the broadcast schedule
        events = [e for e in events if e['type'] != 'Driver Lap']
        
        events.extend(finish_seq)

        # 2. Score and Add Durations
        events = self.apply_base_scores(events)
        events = self.apply_position_modifier(events)
        events = self.apply_lookahead_modifier(events)
        
        # apply_base_scores already assigns durations, but Leader Lap needs 0 to be filtered out
        # User requested: Min cam time overwrites all lower times if set.
        for e in events:
            if e['type'] == 'Leader Lap':
                e['duration'] = 0
            elif e['type'] in ['Leader Lap Trackside', 'Finish Sweep Trackside']:
                pass # Do not apply min_cam_time to finish sequences
            elif e.get('duration', 0) > 0:
                e['duration'] = max(e['duration'], min_cam_time)

        # Screen time penalty needs to be applied chronologically
        events.sort(key=lambda x: x['timestamp'])
        self.screen_time_history.clear()
        
        scored_events = []
        for e in events:
            # Apply penalty
            penalized = self.apply_screen_time_penalty([e], e['timestamp'])[0]
            scored_events.append(penalized)
            
            # Record screen time for future events
            driver1 = penalized.get('target_driver')
            driver2 = penalized.get('target_driver_2')
            dur = penalized.get('duration', 0)
            for d in [driver1, driver2]:
                if d:
                    if d not in self.screen_time_history:
                        self.screen_time_history[d] = []
                    self.screen_time_history[d].append((penalized['timestamp'], penalized['timestamp'] + dur))

        # 3. Inject Overrides
        scored_events.extend(manual_overrides)
        
        # 4. Resolve Overlaps
        schedule = self.resolve_overlaps(scored_events, min_cam_time=min_cam_time)
        
        # Filter out 0 duration events
        schedule = [s for s in schedule if s.get('duration', 0) > 0]
        
        # 4.5 Assign Cameras sequentially for finalized timeline
        battle_cycle = [2, 3, 4, 5, 7]
        cycle_idx = 0
        for s in schedule:
            if s.get('type') in ['Overtake', 'Close Battle'] and not s.get('camera'):
                s['camera'] = battle_cycle[cycle_idx]
                cycle_idx = (cycle_idx + 1) % len(battle_cycle)
                
        return schedule, leader_laps_completed


class DirectorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AMS2 Replay Auto Director (Phase 2)")
        self.geometry("2000x1400")
        self.configure(bg="#1e1e1e")
        
        self.engine = TimelineEngine()
        self.is_running = False
        self.manual_overrides = []
        self.active_schedule = []
        self.current_focus_participant = None
        self.current_focus_camera = None
        self.leader_laps_completed = 999 # Default high
        self.last_camera_change_time = 0
        self.race_is_in_cooldown = False
        self.driver_finish_targets = {} # {driver_name: target_lap}
        
        self.shared_memory_file = "$pcars2$"
        self.memory_size = ctypes.sizeof(SharedMemory) if HAS_SHARED_MEM else 0
        self.file_handle = None
        if HAS_SHARED_MEM:
            self.setup_shared_memory()
            
        self.setup_ui()
        
        # Use a global hotkey so spacebar toggles director even out of focus
        try:
            keyboard.on_press_key("space", self.global_toggle_director)
        except Exception as e:
            print(f"Failed to bind global hotkey: {e}")
            self.bind('<space>', self.toggle_director) # Fallback to local bind
        
        # Start the polling loop (runs every 100ms, but only acts if is_running)
        self.after(100, self.poll_memory)

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#1e1e1e')
        style.configure('TLabel', background='#1e1e1e', foreground='#ffffff', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'), foreground='#4da6ff')
        style.configure('TButton', font=('Segoe UI', 10, 'bold'))
        
        self.main_frame = ttk.Frame(self, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top Status Bar
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        self.status_label = tk.Label(status_frame, text="🔴 DIRECTOR STANDBY (Press Space to Activate)", font=('Segoe UI', 14, 'bold'), fg="#ff4d4d", bg="#1e1e1e")
        self.status_label.pack(side=tk.LEFT)
        
        self.build_settings_panel()
        self.build_viewers_panel()
        self.build_injector_panel()

    def setup_shared_memory(self):
        try:
            self.file_handle = mmap.mmap(-1, self.memory_size, self.shared_memory_file, access=mmap.ACCESS_READ)
            print("Connected to AMS2 Shared Memory.")
        except Exception as e:
            print(f"Failed to connect to Shared Memory: {e}")

    def read_shared_memory(self):
        if not self.file_handle:
            return None
        try:
            data = SharedMemory()
            self.file_handle.seek(0)
            ctypes.memmove(ctypes.addressof(data), self.file_handle.read(ctypes.sizeof(data)), ctypes.sizeof(data))
            
            # Auto-reconnect if memory is empty/invalid (GameState 0)
            if data.mGameState == 0:
                self.file_handle.close()
                self.setup_shared_memory()
                
            return data
        except Exception:
            return None

    def global_toggle_director(self, event=None):
        """Thread-safe global hotkey callback."""
        self.after(0, self.toggle_director)

    def toggle_director(self, event=None):
        """Toggles the live execution engine."""
        # Ignore spacebar if user is typing in an Entry widget
        if event and isinstance(event.widget, (tk.Entry, ttk.Entry, ttk.Combobox)):
            return
            
        self.is_running = not self.is_running
        if self.is_running:
            self.status_label.config(text="🟢 DIRECTOR ACTIVE", fg="#4dff4d")
            # Pull the current schedule from the treeview / engine
            # The most recent schedule is what was last populated
            self.refresh_timeline() # ensures self.active_schedule is up to date
        else:
            self.status_label.config(text="🔴 DIRECTOR STANDBY (Press Space to Activate)", fg="#ff4d4d")

    def poll_memory(self):
        """Task 5.2: Polling loop placeholder"""
        if self.is_running and HAS_SHARED_MEM:
            # Task 5.1: Ensure we only inject if AMS2 is focused
            ams2_focused = False
            if HAS_WIN32:
                try:
                    hwnd = win32gui.GetForegroundWindow()
                    window_title = win32gui.GetWindowText(hwnd)
                    if "Automobilista 2" in window_title:
                        ams2_focused = True
                except Exception:
                    pass
            else:
                # Fallback if win32gui not installed
                ams2_focused = True
                
            if ams2_focused:
                self.execute_director_logic()
            
        self.after(100, self.poll_memory)

    def execute_director_logic(self):
        data = self.read_shared_memory()
        if not data:
            return
            
        game_time_raw = data.mCurrentTime
        
        try:
            offset = float(self.replay_offset_var.get())
        except Exception:
            offset = 6.0
            
        game_time = game_time_raw - offset
        
        # --- Task 5.4 & 5.5: Live Final Lap Sweep ---
        sweep_driver = None
        
        # 1. Update Checkered Flag State
        if not self.race_is_in_cooldown:
            for i in range(data.mNumParticipants):
                p = data.mParticipantInfo[i]
                if p.mIsActive and p.mRacePosition == 1:
                    if p.mCurrentLap > self.leader_laps_completed:
                        self.race_is_in_cooldown = True
                        print("🏁 Leader has finished! Latching final lap targets for all lapped cars.")
                        break
                        
        if self.race_is_in_cooldown:
            # Latch targets for everyone
            for i in range(data.mNumParticipants):
                p = data.mParticipantInfo[i]
                if p.mIsActive:
                    name = p.mName.decode('utf-8', errors='ignore').strip('\x00')
                    if name not in self.driver_finish_targets:
                        self.driver_finish_targets[name] = p.mCurrentLap + 1
                        
            # Hunt for the next driver crossing the line
            participants_list = []
            for i in range(data.mNumParticipants):
                p = data.mParticipantInfo[i]
                if p.mIsActive:
                    name = p.mName.decode('utf-8', errors='ignore').strip('\x00')
                    participants_list.append({
                        'name': name,
                        'position': p.mRacePosition,
                        'current_lap': p.mCurrentLap
                    })
            sweep_driver = self.engine.get_next_finish_target(participants_list, self.leader_laps_completed, self.driver_finish_targets)
                                
        # 2. Select Active Event
        if sweep_driver:
            active_event = {
                'target_driver': sweep_driver,
                'camera': 7 # Trackside for finish
            }
        else:
            # Fallback to normal schedule
            active_event = None
            for s in self.active_schedule:
                start_time = s['timestamp']
                end_time = start_time + s.get('duration', 0)
                if start_time <= game_time <= end_time:
                    active_event = s
                    break
                    
        # Always extract currently viewed driver for debug
        viewed_idx = data.mViewedParticipantIndex
        viewed_name = "[Unknown]"
        viewed_pos = 0
        
        if 0 <= viewed_idx < data.mNumParticipants:
            viewed_p = data.mParticipantInfo[viewed_idx]
            if viewed_p.mIsActive:
                viewed_name = viewed_p.mName.decode('utf-8', errors='ignore').strip('\x00').strip()
                viewed_pos = viewed_p.mRacePosition
                    
        # --- Console Debug Tracking (Throttled to 1s) ---
        if not hasattr(self, 'last_debug_print'):
            self.last_debug_print = 0
            
        sys_time = time.time()
        if sys_time - self.last_debug_print >= 1.0:
            print(f"\n--- TIMELINE TRACKER ---")
            print(f"Raw Game Time: {game_time_raw:.2f}s | Offset: {offset:.2f}s | Evaluating Timeline At: {game_time:.2f}s")
            print(f"Currently Viewing: '{viewed_name}' (P{viewed_pos}) | GameState: {data.mGameState} | SessionState: {data.mSessionState}")
            
            # Show next upcoming shot
            next_events = [e for e in self.active_schedule if e['timestamp'] > game_time]
            if next_events:
                next_e = next_events[0]
                dist = next_e['timestamp'] - game_time
                print(f"-> NEXT SHOT IN {dist:.1f}s: {next_e.get('target_driver')} (Type: {next_e.get('type')})")
            else:
                print("-> NEXT SHOT: [End of Schedule]")
                
            if active_event:
                print(f"-> ACTIVE NOW: {active_event.get('target_driver')} for {active_event.get('duration', 0):.1f}s")
            else:
                print(f"-> ACTIVE NOW: [None]")
                
            self.last_debug_print = sys_time
                    
        if active_event:
            target_driver = active_event['target_driver']
            
            # Visually highlight the active event in the treeview
            tree_id = active_event.get('tree_id')
            if tree_id and self.timeline_tree.exists(tree_id):
                self.timeline_tree.selection_set(tree_id)
                self.timeline_tree.see(tree_id)
            
            # Task 5.4 Live Abort: Ensure the scheduled driver hasn't already finished
            target_pos = None
            has_finished = False
            is_in_pits = False
            
            # Wait for AMS2 engine to settle after the last change before making more decisions
            if time.time() - self.last_camera_change_time < 0.3:
                return
                
            for i in range(data.mNumParticipants):
                p = data.mParticipantInfo[i]
                if p.mIsActive:
                    name = p.mName.decode('utf-8', errors='ignore').strip('\x00').strip()
                    if name == target_driver:
                        target_pos = p.mRacePosition # Use actual race position!
                        
                        # Mathematical Finish Detection
                        if p.mCurrentLap > self.leader_laps_completed:
                            has_finished = True
                        elif name in self.driver_finish_targets and p.mCurrentLap >= self.driver_finish_targets[name]:
                            has_finished = True
                            
                        # PitMode == 0 is PIT_MODE_NONE. Anything else means they are pitting/garaged
                        if data.mPitModes[i] != 0:
                            is_in_pits = True
                        break
                        
            if target_pos is None:
                print(f"-> WARNING: Scheduled driver '{target_driver}' NOT FOUND in live game telemetry! (Aborting shot)")
                        
            # Abort the shot if they already finished or are pitting (unless it's the manual override or sweep)
            is_manual = active_event.get('score', 0) == 1000000
            is_sweep = sweep_driver == target_driver
            
            if (has_finished or is_in_pits) and not is_manual and not is_sweep:
                return # Live Abort: Drop the camera from this driver
                
            if target_pos and self.current_focus_participant != target_driver:
                print(f"!!! TRIGGERING KEYPRESSES !!!")
                print(f"Scheduled switch to '{target_driver}' (P{target_pos}). Camera was on '{viewed_name}' (P{viewed_pos}).")
                self.move_focus_to_position(target_pos, viewed_pos)
                self.current_focus_participant = target_driver
                self.last_camera_change_time = time.time()
                
            # Switch camera if necessary
            target_camera = active_event.get('camera')
            if target_camera and target_camera != self.current_focus_camera:
                self.switch_camera(target_camera)
                self.current_focus_camera = target_camera
                self.last_camera_change_time = time.time()

    def move_focus_to_position(self, target_pos, current_pos):
        """Task 5.3: pyKey injection utilizing Absolute Delta Tracking via Shared Memory."""
        if not HAS_SHARED_MEM:
            return
            
        if current_pos is None:
            # Fallback if shared memory view is invalid
            for _ in range(32):
                pressKey('UP')
                time.sleep(0.01)
                releaseKey('UP')
                time.sleep(0.01)
                
            for _ in range(target_pos - 1):
                pressKey('DOWN')
                time.sleep(0.01)
                releaseKey('DOWN')
                time.sleep(0.01)
        else:
            # Mathematical Delta Tracking (Smooth Navigation)
            delta = target_pos - current_pos
            
            if delta > 0:
                for _ in range(delta):
                    pressKey('DOWN')
                    time.sleep(0.01) # Hold key for 10ms
                    releaseKey('DOWN')
                    time.sleep(0.01) # Pause for 10ms between keystrokes
            elif delta < 0:
                for _ in range(abs(delta)):
                    pressKey('UP')
                    time.sleep(0.01) # Hold key for 10ms
                    releaseKey('UP')
                    time.sleep(0.01) # Pause for 10ms between keystrokes
            
        # Confirm selection
        pressKey('ENTER')
        time.sleep(0.01)
        releaseKey('ENTER')
        
    def switch_camera(self, camera_id):
        # We assume 1-9 numeric keys trigger cameras
        key = str(camera_id)
        if key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            pressKey(key)
            time.sleep(0.05) # Increased to 50ms to ensure AMS2 registers the input!
            releaseKey(key)

    def build_settings_panel(self):
        settings_frame = ttk.LabelFrame(self.main_frame, text="Director Tuning (Live)", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Grid layout for settings
        ttk.Label(settings_frame, text="Accident Score:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.accident_score_var = tk.StringVar(value=str(self.engine.base_accident_score))
        ttk.Entry(settings_frame, textvariable=self.accident_score_var, width=8).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Overtake Score:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.overtake_score_var = tk.StringVar(value=str(self.engine.base_overtake_score))
        ttk.Entry(settings_frame, textvariable=self.overtake_score_var, width=8).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Battle Score:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.battle_score_var = tk.StringVar(value=str(self.engine.base_battle_score))
        ttk.Entry(settings_frame, textvariable=self.battle_score_var, width=8).grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Penalty Weight:").grid(row=0, column=6, padx=5, pady=5, sticky="e")
        self.penalty_weight_var = tk.StringVar(value=str(self.engine.penalty_weight))
        ttk.Entry(settings_frame, textvariable=self.penalty_weight_var, width=8).grid(row=0, column=7, padx=5, pady=5)
        
        # Dwell times
        ttk.Label(settings_frame, text="Accident Dwell (s):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.accident_dwell_var = tk.StringVar(value="15")
        ttk.Entry(settings_frame, textvariable=self.accident_dwell_var, width=8).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Overtake Dwell (s):").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.overtake_dwell_var = tk.StringVar(value="12")
        ttk.Entry(settings_frame, textvariable=self.overtake_dwell_var, width=8).grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(settings_frame, text="Battle Dwell (s):").grid(row=1, column=4, padx=5, pady=5, sticky="e")
        self.battle_dwell_var = tk.StringVar(value="12")
        ttk.Entry(settings_frame, textvariable=self.battle_dwell_var, width=8).grid(row=1, column=5, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Replay Offset (s):").grid(row=1, column=6, padx=5, pady=5, sticky="e")
        self.replay_offset_var = tk.StringVar(value="-8.0")
        ttk.Entry(settings_frame, textvariable=self.replay_offset_var, width=6).grid(row=1, column=7, padx=5, pady=5)
        
        # Row 2 (Extra Tuning)
        ttk.Label(settings_frame, text="Min Cam Time (s):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.min_cam_time_var = tk.StringVar(value="12")
        ttk.Entry(settings_frame, textvariable=self.min_cam_time_var, width=8).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Anticipation Time (s):").grid(row=2, column=2, padx=5, pady=5, sticky="e")
        self.anticipation_var = tk.StringVar(value="3.0")
        ttk.Entry(settings_frame, textvariable=self.anticipation_var, width=8).grid(row=2, column=3, padx=5, pady=5)

        self.apply_btn = ttk.Button(settings_frame, text="Apply Tuning", command=self.refresh_timeline)
        self.apply_btn.grid(row=2, column=8, padx=10, pady=5, sticky="we")
        
        self.load_btn = ttk.Button(settings_frame, text="Load Log File", command=self.load_log_file)
        self.load_btn.grid(row=2, column=9, padx=10, pady=5, sticky="we")

    def apply_tuning(self):
        try:
            self.engine.base_accident_score = int(self.accident_score_var.get())
            self.engine.base_overtake_score = int(self.overtake_score_var.get())
            self.engine.base_battle_score = int(self.battle_score_var.get())
            self.engine.penalty_weight = float(self.penalty_weight_var.get())
            
            self.engine.accident_dwell = float(self.accident_dwell_var.get())
            self.engine.overtake_dwell = float(self.overtake_dwell_var.get())
            self.engine.battle_dwell = float(self.battle_dwell_var.get())
            
            anticipation = float(self.anticipation_var.get())
            if anticipation < -8.0 or anticipation > 8.0:
                messagebox.showwarning("Warning", "Anticipation Time must be between -8.0s and 8.0s.")
                return False
            self.engine.anticipation_time = anticipation
            return True
            
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numeric values for all fields.")
            return False

    def build_viewers_panel(self):
        # Container for side-by-side viewers
        viewers_frame = ttk.Frame(self.main_frame)
        viewers_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        viewers_frame.columnconfigure(0, weight=1)
        viewers_frame.columnconfigure(1, weight=2) # Treeview gets more space
        viewers_frame.rowconfigure(0, weight=1)

        # Left Side: Raw Event Listbox
        raw_frame = ttk.LabelFrame(viewers_frame, text="Raw File Events", padding="10")
        raw_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        self.raw_listbox = tk.Listbox(raw_frame, bg="#2d2d2d", fg="#ffffff", font=('Consolas', 11))
        self.raw_listbox.pack(fill=tk.BOTH, expand=True)
        self.raw_listbox.bind('<<ListboxSelect>>', self.on_raw_listbox_select)
        
        # Add scrollbar to listbox
        raw_scroll = ttk.Scrollbar(self.raw_listbox, orient=tk.VERTICAL, command=self.raw_listbox.yview)
        raw_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.raw_listbox.configure(yscrollcommand=raw_scroll.set)

        # Right Side: Scheduled Timeline Treeview
        timeline_frame = ttk.LabelFrame(viewers_frame, text="Calculated Threat Timeline", padding="10")
        timeline_frame.grid(row=0, column=1, sticky="nsew")

        # Define columns
        columns = ('Timestamp', 'Duration', 'Type', 'Target Driver', 'Target Driver 2', 'Position', 'Score', 'Camera')
        self.timeline_tree = ttk.Treeview(timeline_frame, columns=columns, show='headings', selectmode='browse')
        
        # Configure headings and columns
        for col in columns:
            self.timeline_tree.heading(col, text=col)
            # Adjust column widths based on expected content
            width = 120 if col in ('Type', 'Target Driver', 'Target Driver 2') else 80
            self.timeline_tree.column(col, width=width, anchor=tk.CENTER)
            
        self.timeline_tree.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar to treeview
        tree_scroll = ttk.Scrollbar(self.timeline_tree, orient=tk.VERTICAL, command=self.timeline_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.timeline_tree.configure(yscrollcommand=tree_scroll.set)

    def build_injector_panel(self):
        injector_frame = ttk.LabelFrame(self.main_frame, text="Manual Override Injector (Pass 3)", padding="10")
        injector_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Label(injector_frame, text="Start Time (MM:SS.ms):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.inj_time_var = tk.StringVar()
        ttk.Entry(injector_frame, textvariable=self.inj_time_var, width=12).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(injector_frame, text="Duration (s):").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.inj_duration_var = tk.StringVar(value="10")
        ttk.Entry(injector_frame, textvariable=self.inj_duration_var, width=8).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(injector_frame, text="Target Driver:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.inj_driver_var = tk.StringVar()
        self.inj_driver_cb = ttk.Combobox(injector_frame, textvariable=self.inj_driver_var, width=20, state="readonly")
        self.inj_driver_cb.grid(row=0, column=5, padx=5, pady=5)
        
        ttk.Label(injector_frame, text="Camera:").grid(row=0, column=6, padx=5, pady=5, sticky="e")
        self.inj_camera_var = tk.StringVar(value="Trackside (7)")
        cameras = ["Action (2)", "Helmet (3)", "Roof (4)", "Bumper (5)", "Trackside (7)"]
        self.inj_camera_cb = ttk.Combobox(injector_frame, textvariable=self.inj_camera_var, values=cameras, width=15, state="readonly")
        self.inj_camera_cb.grid(row=0, column=7, padx=5, pady=5)
        
        self.inject_btn = ttk.Button(injector_frame, text="⚡ Inject Manual Shot", command=self.inject_manual_shot)
        self.inject_btn.grid(row=0, column=8, padx=15, pady=5)

    def inject_manual_shot(self):
        """Task 4.3: Manual Injection Logic"""
        try:
            # Parse time MM:SS.ms to float seconds
            time_str = self.inj_time_var.get()
            minutes, seconds = time_str.split(':')
            timestamp = (int(minutes) * 60) + float(seconds)
            
            duration = float(self.inj_duration_var.get())
            driver = self.inj_driver_var.get()
            
            # Extract camera ID from "Trackside (7)"
            cam_str = self.inj_camera_var.get()
            camera_id = 7
            match = re.search(r'\((\d+)\)', cam_str)
            if match:
                camera_id = int(match.group(1))
                
            override = {
                'type': 'Manual Override',
                'timestamp': timestamp,
                'target_driver': driver,
                'duration': duration,
                'score': 1000000, # Unbeatable priority
                'camera': camera_id
            }
            
            self.manual_overrides.append(override)
            messagebox.showinfo("Success", f"Injected override for {driver} at {time_str}")
            
            self.refresh_timeline()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to inject override: {e}")

    def on_raw_listbox_select(self, event):
        """Task 4.1: Click-to-Fill UX"""
        selection = self.raw_listbox.curselection()
        if not selection:
            return
            
        line = self.raw_listbox.get(selection[0])
        parsed = self.engine.parse_line(line)
        
        if parsed and parsed.get('type') not in ['Total Session Time', 'Leader Laps Completed']:
            # Extract formatted time directly from the log string
            time_match = self.engine.re_time.match(line)
            if time_match:
                time_str = f"{time_match.group(1)}:{time_match.group(2)}"
                self.inj_time_var.set(time_str)
                
            driver = parsed.get('target_driver', '')
            if driver:
                self.inj_driver_var.set(driver)
                
                # If combobox doesn't have the driver, add it
                current_values = list(self.inj_driver_cb['values'])
                if driver not in current_values:
                    current_values.append(driver)
                    self.inj_driver_cb['values'] = current_values

    def load_log_file(self):
        path = filedialog.askopenfilename(
            title="Select Race Data Log",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if path:
            self.raw_listbox.delete(0, tk.END)
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    self.raw_listbox.insert(tk.END, line.strip())
            self.refresh_timeline()

    def refresh_timeline(self):
        """Generates the schedule from the listbox and overrides, populating the treeview."""
        # 1. Gather lines from listbox
        lines = [self.raw_listbox.get(i) for i in range(self.raw_listbox.size())]
        
        try:
            min_cam_time = float(self.min_cam_time_var.get())
        except Exception:
            min_cam_time = 5.0

        # Ensure tuning variables are applied to engine before generation
        if not self.apply_tuning():
            return

        # Generate schedule via headless engine
        schedule, leader_laps = self.engine.generate_schedule(
            lines, 
            min_cam_time=min_cam_time, 
            manual_overrides=self.manual_overrides
        )
        
        self.leader_laps_completed = leader_laps
        self.active_schedule = schedule
        
        # 5. Populate Treeview
        self.timeline_tree.delete(*self.timeline_tree.get_children())
        for s in schedule:
            # Format timestamp
            minutes = int(s['timestamp'] // 60)
            seconds = s['timestamp'] % 60
            ts_str = f"{minutes:02}:{seconds:05.2f}"
            
            values = (
                ts_str,
                f"{s.get('duration', 0):.1f}s",
                s.get('type', ''),
                s.get('target_driver', ''),
                s.get('target_driver_2', ''),
                s.get('position', ''),
                f"{s.get('score', 0):.1f}",
                s.get('camera', 'Auto')
            )
            item_id = self.timeline_tree.insert('', tk.END, values=values)
            s['tree_id'] = item_id

if __name__ == "__main__":
    # Make the Tkinter GUI High-DPI aware on Windows
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
            
    app = DirectorApp()
    app.mainloop()
