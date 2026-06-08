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

    def _pre_scan_sweep(self, participants: dict, session_info: dict, current_time: float) -> None:
        """Pass 1: Detect finishers, activate sweep, select sweep target.
        
        This MUST run before the per-participant scoring loop so that
        sweep activation and target selection happen on the same tick
        the leader finishes (FR-003).
        """
        laps_in_event = session_info.get('laps_in_event', 0)
        if laps_in_event <= 0:
            laps_in_event = self.timeline_laps_in_event
        if laps_in_event <= 0:
            return  # No lap data — cannot detect finish

        # 1. Scan all participants for finishers
        for p in participants.values():
            if not p.get('is_active', False):
                continue
            name = p.get('name')
            current_lap = p.get('current_lap', 0)

            if current_lap > laps_in_event:
                # Register as finished (with game-time timestamp)
                if name not in self.finished_participants:
                    self.finished_participants[name] = current_time
                # If the leader finished, activate sweep
                if p.get('race_position') == 1:
                    self._sweep_active = True

        if not self._sweep_active:
            return

        # 2. Select sweep target: highest-placed active unfinished driver
        eligible = []
        for p in participants.values():
            if not p.get('is_active', False):
                continue
            name = p.get('name')
            if name in self.finished_participants:
                # Allow dwell: keep current target eligible if within dwell window
                if (name == self._sweep_target_name and
                        current_time - self.finished_participants[name] <= self.sweep_dwell_time):
                    eligible.append(p)
                # Otherwise skip — they're done
                continue
            eligible.append(p)

        if eligible:
            eligible.sort(key=lambda x: x.get('race_position', 99))
            self._sweep_target_name = eligible[0].get('name')
        else:
            # All drivers finished and past dwell — deactivate (FR-009)
            self._sweep_target_name = None
            self._sweep_active = False

    def _calculate_sequence_bonus(self, participant: dict, session_info: dict, track_info: dict) -> float:
        """Pass 2 (per-participant): Read pre-computed sweep state and return bonus.
        
        This method is now a pure reader — all sweep detection and target
        selection has moved to _pre_scan_sweep().
        """
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
            if lap_distance >= track_length / 2:
                return 10000.0

        # US2: Sweep target gets +5000 (checked before finished-driver exclusion
        # because the dwell-active finisher IS the sweep target and should still
        # receive the bonus during their dwell window)
        if self._sweep_active and name == self._sweep_target_name:
            return 5000.0

        # Finished drivers (not the sweep target) get no bonus
        if current_lap > laps_in_event:
            return 0.0

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
                        # Transient decay for overtake points (ramp-up then decay)
                        if current_time < event_time:
                            time_until = event_time - current_time
                            ramp_ratio = 1.0 - (time_until / self.timeline_pre_offset)
                            ramped_score = score * max(0.0, ramp_ratio)
                            ovt_bonus = max(ovt_bonus, ramped_score)
                        else:
                            time_passed = current_time - event_time
                            decay_ratio = 1.0 - (time_passed / self.timeline_post_offset)
                            decayed_score = score * max(0.0, decay_ratio)
                            ovt_bonus = max(ovt_bonus, decayed_score)
                    
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

        # Replay loop / Time backward jump detection
        if current_time is not None:
            if hasattr(self, '_last_current_time') and self._last_current_time is not None:
                if current_time < self._last_current_time - 5.0:
                    # Time jumped backwards — clear all state
                    self._sweep_active = False
                    self._sweep_target_name = None
                    self.finished_participants.clear()
            self._last_current_time = current_time

        # Pass 1: Pre-scan for sweep activation and target selection (FR-003)
        if session_info and current_time is not None:
            self._pre_scan_sweep(participants, session_info, current_time)

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
