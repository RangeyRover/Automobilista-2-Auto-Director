"""Stateless per-tick scoring engine for AMS2 Auto Director V4.0.

Calculates a composite interest score for each participant based on:
- Pit mode penalty
- Speed penalty
- Cars ahead bonus (leader vs non-leader)
- Close racing bonus (gap-based)
- Race position bonus (linear decay)

No external dependencies. No GUI imports. Fully testable in isolation.
"""
import os
import time
import logging
from core.timeline_parser import TimelineParser

class ScoringEngine:
    """Stateless per-tick scoring. No memory of previous ticks."""

    # Configurable parameters (set from GUI at runtime)
    race_position_bonus_factor: float = 12
    pit_mode_penalty: float = -10
    speed_penalty: float = -5
    leader_cars_ahead_multiplier: float = 2
    other_cars_ahead_multiplier: float = 2
    close_racing_max_gap: float = 50
    close_racing_bonus_divisor: float = 5

    def __init__(self):
        # Instance copies of class defaults so GUI modifications
        # don't mutate the class-level values
        self.race_position_bonus_factor = ScoringEngine.race_position_bonus_factor
        self.pit_mode_penalty = ScoringEngine.pit_mode_penalty
        self.speed_penalty = ScoringEngine.speed_penalty
        self.leader_cars_ahead_multiplier = ScoringEngine.leader_cars_ahead_multiplier
        self.other_cars_ahead_multiplier = ScoringEngine.other_cars_ahead_multiplier
        self.close_racing_max_gap = ScoringEngine.close_racing_max_gap
        self.close_racing_bonus_divisor = ScoringEngine.close_racing_bonus_divisor
        
        # Narrative Sequence State
        self.sweep_dwell_time = 1.0
        self._sweep_active = False
        self.finished_participants: dict[str, float] = {}
        self._sweep_target_name: str | None = None
        self.timeline_events = []
        self.timeline_laps_in_event = 0
        self.timeline_session_time = 0.0
        self.timeline_pre_offset = 15.0
        self.timeline_post_offset = 10.0

    @property
    def is_sweep_active(self) -> bool:
        return self._sweep_active

    def _calculate_pit_mode_penalty(self, participant: dict) -> float:
        """FR-3.1: -10 if pit_mode != 0, else 0."""
        if participant.get('pit_mode', 0) != 0:
            return self.pit_mode_penalty
        return 0.0

    def _calculate_speed_penalty(self, participant: dict) -> float:
        """FR-3.2: -5 if speed < 5 m/s, else 0."""
        if participant.get('speed', 0) < 5:
            return self.speed_penalty
        return 0.0

    def _calculate_cars_ahead_bonus(self, participant: dict) -> float:
        """FR-3.3: Leader: count * 2, Others: count * 2/5. Zeroed if in pits."""
        if participant.get('pit_mode', 0) != 0:
            return 0.0

        cars_ahead = participant.get('cars_ahead_250m', 0)
        if cars_ahead == 0:
            return 0.0

        if participant.get('race_position', 1) == 1:
            return cars_ahead * self.leader_cars_ahead_multiplier
        else:
            return cars_ahead * self.other_cars_ahead_multiplier / 5

    def _calculate_close_racing_bonus(self, participant: dict) -> float:
        """FR-3.4: Base = (max_gap - gap) / divisor."""
        gap = participant.get('gap_ahead', 0)
        
        # Leader or invalid gap
        if gap <= 0 or gap >= self.close_racing_max_gap:
            return 0.0

        # Base linear bonus curve (from V3.0)
        base_bonus = (self.close_racing_max_gap - gap) / self.close_racing_bonus_divisor
        return min(base_bonus, 50.0)

    def _calculate_closing_speed_bonus(self, participant: dict) -> float:
        """FR-3.6: Closing speed is an independent additive bonus, active only when within max_gap."""
        gap = participant.get('gap_ahead', 0)
        if gap <= 0 or gap >= self.close_racing_max_gap:
            return 0.0
        return participant.get('closing_speed', 0.0)

    def _calculate_race_position_bonus(self, participant: dict) -> float:
        """FR-3.5: FACTOR * (1 - (pos-1)/32). Linear decay P1→P32."""
        pos = participant.get('race_position', 0)
        if pos <= 0:
            return 0.0
        return self.race_position_bonus_factor * (1 - (pos - 1) / 32)

    def _calculate_sequence_bonus(self, participant: dict, session_info: dict, track_info: dict) -> float:
        """Calculate massive point bonuses for Final Lap sequences (FR-003, FR-004)."""
        if not participant.get('is_active', False):
            return 0.0

        current_lap = participant.get('current_lap', 0)
        laps_in_event = session_info.get('laps_in_event', 0)
        if laps_in_event <= 0:
            laps_in_event = self.timeline_laps_in_event
            
        name = participant.get('name')
        
        # US1: Leader Final Lap Coverage (+10000)
        if current_lap == laps_in_event and participant.get('race_position') == 1:
            track_length = track_info.get('track_length', 1.0)
            lap_distance = participant.get('lap_distance', 0.0)
            
            # If halfway through final lap
            if lap_distance >= track_length / 2:
                return 10000.0

        # US2: Cooldown Sweep logic
        # 1. Detect if this participant has finished the race (mCurrentLap > laps_in_event)
        if current_lap > laps_in_event:
            # If the leader finished, activate sweep mode
            if participant.get('race_position') == 1:
                self._sweep_active = True
                
            # Add driver to finished list if not already there with their finish timestamp
            if name not in self.finished_participants:
                self.finished_participants[name] = time.time()
            return 0.0 # Finished cars get no bonus

        # 2. If sweep mode is active, strictly prioritize the highest active sweep target
        if self._sweep_active:
            if name == self._sweep_target_name:
                return 5000.0

        return 0.0

    def load_timeline_log(self, filepath: str) -> None:
        """Loads and parses a Replay Auto Director log file."""
        self.timeline_events = []
        self.timeline_laps_in_event = 0
        self.timeline_session_time = 0.0
        if not os.path.exists(filepath):
            return
            
        parser = TimelineParser()
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                event = parser.parse_line(line.strip())
                if event:
                    if event.get('type') == 'Leader Laps Completed':
                        self.timeline_laps_in_event = event.get('lap', 0)
                    elif event.get('type') == 'Total Session Time':
                        self.timeline_session_time = event.get('timestamp', 0.0)
                    else:
                        self.timeline_events.append(event)
                    
    def _calculate_timeline_bonus(self, participant: dict, current_time: float) -> tuple[float, float]:
        """Calculates bonus points based on loaded timeline events. Returns (accident_bonus, overtake_bonus)."""
        if not participant.get('is_active', False) or current_time is None:
            return 0.0, 0.0
            
        name = participant.get('name')
        if not name:
            return 0.0, 0.0
            
        acc_bonus = 0.0
        ovt_bonus = 0.0
            
        for event in self.timeline_events:
            event_time = event.get('timestamp', 0.0)
            start_time = event_time - self.timeline_pre_offset
            end_time = event_time + self.timeline_post_offset
            
            # If current replay time falls within the event window
            if start_time <= current_time <= end_time:
                # If this driver is involved in the event
                if event.get('target_driver') == name or event.get('target_driver_2') == name:
                    score = event.get('base_score', 0.0)
                    if event.get('type') == 'Accident':
                        acc_bonus = max(acc_bonus, score)
                    elif event.get('type') == 'Overtake':
                        ovt_bonus = max(ovt_bonus, score)
                    
        return acc_bonus, ovt_bonus

    def calculate_scores(self, participants: dict, session_info: dict = None, track_info: dict = None, current_time: float = None) -> dict:
        """Calculate scores for all participants.

        Args:
            participants: dict[int, dict] keyed by participant index.

        Returns:
            dict[int, dict] keyed by participant index, each containing:
              - pit_mode_penalty, speed_penalty, cars_ahead_bonus,
                close_racing_bonus, race_position_bonus, total_score
        """
        if not participants:
            return {}

        # 1b. Sweep Target Selection
        if self._sweep_active:
            import time
            eligible = []
            now = time.time()
            for p in participants.values():
                if not p.get('is_active'):
                    continue
                p_name = p.get('name')
                # If they finished
                if p_name in self.finished_participants:
                    # If this is the currently active sweep target, keep them eligible for the dwell time
                    if p_name == self._sweep_target_name and (now - self.finished_participants[p_name] <= self.sweep_dwell_time):
                        pass
                    else:
                        continue
                eligible.append(p)
            
            if eligible:
                eligible.sort(key=lambda x: x.get('race_position', 99))
                self._sweep_target_name = eligible[0].get('name')
            else:
                self._sweep_target_name = None

        results = {}
        for idx, p in participants.items():
            pit = self._calculate_pit_mode_penalty(p)
            spd = self._calculate_speed_penalty(p)
            cars = self._calculate_cars_ahead_bonus(p)
            close = self._calculate_close_racing_bonus(p)
            cls_spd = self._calculate_closing_speed_bonus(p)
            pos = self._calculate_race_position_bonus(p)
            
            seq_bonus = 0.0
            if session_info and track_info:
                seq_bonus = self._calculate_sequence_bonus(p, session_info, track_info)

            acc_bonus = 0.0
            ovt_bonus = 0.0
            if current_time is not None:
                acc_bonus, ovt_bonus = self._calculate_timeline_bonus(p, current_time)

            results[idx] = {
                'pit_mode_penalty': pit,
                'speed_penalty': spd,
                'cars_ahead_bonus': cars,
                'close_racing_bonus': close,
                'closing_speed_bonus': cls_spd,
                'race_position_bonus': pos,
                'sequence_bonus': seq_bonus,
                'accident_bonus': acc_bonus,
                'overtake_bonus': ovt_bonus,
                'total_score': pit + spd + cars + close + cls_spd + pos + seq_bonus + acc_bonus + ovt_bonus,
            }

        return results

    def get_best_focus(self, scores: dict, participants: dict) -> int | None:
        """Return the race_position of the highest-scoring active participant.

        Excludes inactive participants. Returns None if no valid candidates.
        """
        best_score = float('-inf')
        best_position = None

        for idx, score_entry in scores.items():
            p = participants.get(idx, {})
            if not p.get('is_active', False):
                continue

            total = score_entry.get('total_score', 0)
            if total > best_score:
                best_score = total
                best_position = p.get('race_position')

        return best_position
