"""Stateless per-tick scoring engine for AMS2 Auto Director V4.0.

Calculates a composite interest score for each participant based on:
- Pit mode penalty
- Speed penalty
- Cars ahead bonus (leader vs non-leader)
- Close racing bonus (gap-based)
- Race position bonus (linear decay)

No external dependencies. No GUI imports. Fully testable in isolation.
"""


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
        """FR-3.4: (max_gap - gap) / divisor if gap in (0, max_gap], else 0."""
        gap = participant.get('gap_ahead', 0)
        if gap <= 0 or gap >= self.close_racing_max_gap:
            # gap == max_gap edge: (50-50)/5 = 0.0, which matches gap >= max_gap returning 0
            # But spec says "between 0 and 50m" — need to include gap == max_gap as 0
            return 0.0

        return (self.close_racing_max_gap - gap) / self.close_racing_bonus_divisor

    def _calculate_race_position_bonus(self, participant: dict) -> float:
        """FR-3.5: FACTOR * (1 - (pos-1)/32). Linear decay P1→P32."""
        pos = participant.get('race_position', 0)
        if pos <= 0:
            return 0.0
        return self.race_position_bonus_factor * (1 - (pos - 1) / 32)

    def calculate_scores(self, participants: dict) -> dict:
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

        scores = {}
        for idx, p in participants.items():
            pit = self._calculate_pit_mode_penalty(p)
            spd = self._calculate_speed_penalty(p)
            cars = self._calculate_cars_ahead_bonus(p)
            close = self._calculate_close_racing_bonus(p)
            pos = self._calculate_race_position_bonus(p)

            scores[idx] = {
                'pit_mode_penalty': pit,
                'speed_penalty': spd,
                'cars_ahead_bonus': cars,
                'close_racing_bonus': close,
                'race_position_bonus': pos,
                'total_score': pit + spd + cars + close + pos,
            }

        return scores

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
