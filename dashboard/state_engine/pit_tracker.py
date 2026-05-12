class PitTracker:
    def __init__(self):
        self._pit_tracker: dict = {}
        self._pit_mode_state: dict = {}
        self._pit_events: list = []

    @property
    def pit_events(self) -> list:
        return self._pit_events

    def get_driver_tracker(self, idx: int) -> list:
        return self._pit_tracker.get(idx, [])

    def process_rewind(self, cur_time: float):
        """Handle game-time rewinding by rolling back pit tracker state."""
        for idx, history in self._pit_tracker.items():
            # Keep only stops where entry_time <= cur_time
            pruned = [stop for stop in history if stop.get("entry_time", 0.0) <= cur_time]
            if pruned:
                # Revert exit status if the stop was completed in the "future"
                if pruned[-1].get("exit_time", 0.0) > cur_time:
                    pruned[-1]["exit_time"] = 0.0
                    pruned[-1]["duration"] = 0.0
                    pruned[-1]["in_progress"] = True
            self._pit_tracker[idx] = pruned

    def update(self, participants: dict, current_time: float):
        """Update pit logic for all participants given current game time."""
        for idx, p in participants.items():
            if idx not in self._pit_tracker:
                self._pit_tracker[idx] = []
            if idx not in self._pit_mode_state:
                self._pit_mode_state[idx] = {"prev_pit_mode": 0}
                
            state = self._pit_mode_state[idx]
            history = self._pit_tracker[idx]
            
            prev = state.get("prev_pit_mode", 0)
            current = p.get("pit_mode", 0)
            
            active_stop = history[-1] if history and history[-1].get("in_progress", False) else None
            last_stop = history[-1] if history else None
            
            if prev == 0 and current == 1:
                last_exit = last_stop.get("exit_time", 0.0) if last_stop and not last_stop.get("in_progress", False) else 0.0
                if current_time - last_exit > 20.0:
                    pit_count = len(history) + 1
                    new_stop = {
                        "entry_time": current_time,
                        "entry_lap": p.get("current_lap", 0),
                        "in_progress": True,
                        "pit_count": pit_count,
                        "duration": 0.0
                    }
                    history.append(new_stop)
            elif active_stop and current == 0:
                active_stop["exit_time"] = current_time
                active_stop["duration"] = current_time - active_stop["entry_time"]
                active_stop["in_progress"] = False
                active_stop["exit_lap"] = p.get("current_lap", 0)
                
                # Revert if it was a flicker (< 2s) to avoid deleting real drive-throughs
                if active_stop["duration"] < 2.0:
                    history.pop()
                
            state["prev_pit_mode"] = current

        self._pit_events = []
        for idx, history in self._pit_tracker.items():
            p = participants.get(idx)
            if not p or not history:
                continue
                
            tracker = history[-1]
            in_progress = tracker.get("in_progress", False)
            exit_time = tracker.get("exit_time")
            
            if in_progress or (exit_time and current_time - exit_time <= 15.0):
                exit_lap = tracker.get("exit_lap", -1)
                laps_since = p.get("current_lap", 0) - exit_lap if exit_lap >= 0 else -1
                
                duration = tracker.get("duration")
                if in_progress and "entry_time" in tracker:
                    duration = current_time - tracker["entry_time"]
                
                event = {
                    "driver_name": p.get("name", ""),
                    "position": p.get("race_position", 0),
                    "entry_time": tracker.get("entry_time"),
                    "exit_time": exit_time,
                    "duration": duration,
                    "in_progress": in_progress,
                    "pit_count": tracker.get("pit_count", 0),
                    "entry_lap": tracker.get("entry_lap", 0),
                    "laps_since_last_pit": laps_since
                }
                self._pit_events.append(event)
                tracker["laps_since_last_pit"] = laps_since
