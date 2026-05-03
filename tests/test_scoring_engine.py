"""TDD tests for ScoringEngine — SE-01 to SE-29.
Written BEFORE implementation. All must FAIL initially (RED).
"""
import pytest
from core.scoring_engine import ScoringEngine


@pytest.fixture
def engine():
    return ScoringEngine()


# ── Pit Mode Penalty (SE-01 to SE-03) ───────────────────────────────────────

class TestPitModePenalty:
    def test_se01_pit_penalty_when_in_pits(self, engine, make_participant):
        """SE-01: pit_mode != 0 → penalty = -10"""
        participants = {0: make_participant(pit_mode=2)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['pit_mode_penalty'] == -10

    def test_se02_no_penalty_when_not_in_pits(self, engine, make_participant):
        """SE-02: pit_mode == 0 → penalty = 0"""
        participants = {0: make_participant(pit_mode=0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['pit_mode_penalty'] == 0

    def test_se03_cars_ahead_zeroed_in_pits(self, engine, make_participant):
        """SE-03: cars_ahead_bonus zeroed when pit_mode != 0"""
        participants = {0: make_participant(pit_mode=1, cars_ahead_250m=3, race_position=1)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['cars_ahead_bonus'] == 0


# ── Speed Penalty (SE-04 to SE-07) ──────────────────────────────────────────

class TestSpeedPenalty:
    def test_se04_penalty_when_stationary(self, engine, make_participant):
        """SE-04: speed=0 → speed_penalty = -5"""
        participants = {0: make_participant(speed=0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['speed_penalty'] == -5

    def test_se05_penalty_at_4_9(self, engine, make_participant):
        """SE-05: speed=4.9 → speed_penalty = -5"""
        participants = {0: make_participant(speed=4.9)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['speed_penalty'] == -5

    def test_se06_no_penalty_at_5_0(self, engine, make_participant):
        """SE-06: speed=5.0 → speed_penalty = 0"""
        participants = {0: make_participant(speed=5.0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['speed_penalty'] == 0

    def test_se07_no_penalty_at_racing_speed(self, engine, make_participant):
        """SE-07: speed=80 → speed_penalty = 0"""
        participants = {0: make_participant(speed=80)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['speed_penalty'] == 0


# ── Cars Ahead Bonus (SE-08 to SE-10) ───────────────────────────────────────

class TestCarsAheadBonus:
    def test_se08_leader_with_3_ahead(self, engine, make_participant):
        """SE-08: Leader (P1) with 3 cars ahead → bonus = 6.0 (3*2)"""
        participants = {0: make_participant(race_position=1, cars_ahead_250m=3)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['cars_ahead_bonus'] == pytest.approx(6.0)

    def test_se09_non_leader_with_3_ahead(self, engine, make_participant):
        """SE-09: Non-leader (P5) with 3 cars ahead → bonus = 1.2 (3*2/5)"""
        participants = {0: make_participant(race_position=5, cars_ahead_250m=3)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['cars_ahead_bonus'] == pytest.approx(1.2)

    def test_se10_zero_cars_ahead(self, engine, make_participant):
        """SE-10: 0 cars ahead → bonus = 0"""
        participants = {0: make_participant(cars_ahead_250m=0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['cars_ahead_bonus'] == 0


# ── Close Racing Bonus (SE-11 to SE-15) ─────────────────────────────────────

class TestCloseRacingBonus:
    def test_se11_gap_10m_closing(self, engine, make_participant):
        """SE-11: gap=10, closing=2.0 → base=(50-10)/5=8.0, cls_spd=2.0"""
        participants = {0: make_participant(gap_ahead=10, closing_speed=2.0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['close_racing_bonus'] == pytest.approx(8.0)
        assert scores[0]['closing_speed_bonus'] == pytest.approx(2.0)

    def test_se12_gap_50m_edge(self, engine, make_participant):
        """SE-12: gap=50 → base=0.0, cls_spd=0.0"""
        participants = {0: make_participant(gap_ahead=50)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['close_racing_bonus'] == pytest.approx(0.0)
        assert scores[0]['closing_speed_bonus'] == pytest.approx(0.0)

    def test_se13_gap_51m_outside(self, engine, make_participant):
        """SE-13: gap=51 → base=0, cls_spd=0"""
        participants = {0: make_participant(gap_ahead=51, closing_speed=2.0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['close_racing_bonus'] == 0
        assert scores[0]['closing_speed_bonus'] == 0

    def test_se14_gap_0m_leader(self, engine, make_participant):
        """SE-14: gap=0 → base=0, cls_spd=0"""
        participants = {0: make_participant(gap_ahead=0, closing_speed=2.0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['close_racing_bonus'] == 0
        assert scores[0]['closing_speed_bonus'] == 0

    def test_se15_gap_1m_neutral(self, engine, make_participant):
        """SE-15: gap=1, closing=0.0 → base=(50-1)/5=9.8, cls_spd=0.0"""
        participants = {0: make_participant(gap_ahead=1, closing_speed=0.0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['close_racing_bonus'] == pytest.approx(9.8)
        assert scores[0]['closing_speed_bonus'] == pytest.approx(0.0)

    def test_se15b_gap_1m_falling_back(self, engine, make_participant):
        """SE-15b: gap=1, closing=-2.0 → base=9.8, cls_spd=-2.0"""
        participants = {0: make_participant(gap_ahead=1, closing_speed=-2.0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['close_racing_bonus'] == pytest.approx(9.8)
        assert scores[0]['closing_speed_bonus'] == pytest.approx(-2.0)


# ── Race Position Bonus (SE-16 to SE-19) ────────────────────────────────────

class TestRacePositionBonus:
    def test_se16_p1_full_bonus(self, engine, make_participant):
        """SE-16: P1 → bonus = 12.0"""
        participants = {0: make_participant(race_position=1)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['race_position_bonus'] == pytest.approx(12.0)

    def test_se17_p32_near_zero(self, engine, make_participant):
        """SE-17: P32 → bonus ≈ 0.375"""
        participants = {0: make_participant(race_position=32)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['race_position_bonus'] == pytest.approx(0.375)

    def test_se18_p0_invalid(self, engine, make_participant):
        """SE-18: P0 (invalid) → bonus = 0"""
        participants = {0: make_participant(race_position=0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['race_position_bonus'] == 0

    def test_se19_p16_midfield(self, engine, make_participant):
        """SE-19: P16 → bonus ≈ 6.375"""
        participants = {0: make_participant(race_position=16)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['race_position_bonus'] == pytest.approx(6.375)


# ── Total Score Aggregation (SE-20 to SE-22) ────────────────────────────────

class TestTotalScore:
    def test_se20_components_sum(self, engine, make_participant):
        """SE-20: total_score = sum of all 5 components"""
        participants = {0: make_participant(
            pit_mode=0, speed=60, race_position=1,
            cars_ahead_250m=2, gap_ahead=20
        )}
        scores = engine.calculate_scores(participants)
        s = scores[0]
        expected = (s['pit_mode_penalty'] + s['speed_penalty'] +
                    s['cars_ahead_bonus'] + s['close_racing_bonus'] +
                    s['race_position_bonus'])
        assert s['total_score'] == pytest.approx(expected)

    def test_se21_empty_participants(self, engine):
        """SE-21: Empty participants → empty scores"""
        scores = engine.calculate_scores({})
        assert scores == {}

    def test_se22_single_participant(self, engine, make_participant):
        """SE-22: Single active participant → single score entry"""
        participants = {0: make_participant()}
        scores = engine.calculate_scores(participants)
        assert len(scores) == 1
        assert 'total_score' in scores[0]


# ── Best Focus Selection (SE-23 to SE-26) ───────────────────────────────────

class TestBestFocus:
    def test_se23_highest_scorer_selected(self, engine, make_participant):
        """SE-23: Returns race_position of highest-scoring active participant"""
        participants = {
            0: make_participant(race_position=1, speed=60, gap_ahead=10, cars_ahead_250m=3),
            1: make_participant(race_position=2, speed=60, gap_ahead=100, cars_ahead_250m=0),
            2: make_participant(race_position=3, speed=0, gap_ahead=200, cars_ahead_250m=0),
        }
        scores = engine.calculate_scores(participants)
        best = engine.get_best_focus(scores, participants)
        assert best == 1  # P1 should score highest

    def test_se24_all_inactive_returns_none(self, engine, make_participant):
        """SE-24: All inactive → None"""
        participants = {
            0: make_participant(is_active=False),
            1: make_participant(is_active=False),
        }
        scores = engine.calculate_scores(participants)
        best = engine.get_best_focus(scores, participants)
        assert best is None

    def test_se25_tie_breaking(self, engine, make_participant):
        """SE-25: Two equal scores → returns one deterministically"""
        participants = {
            0: make_participant(race_position=1, speed=60, gap_ahead=25,
                                cars_ahead_250m=1, pit_mode=0),
            1: make_participant(race_position=1, speed=60, gap_ahead=25,
                                cars_ahead_250m=1, pit_mode=0),
        }
        scores = engine.calculate_scores(participants)
        best = engine.get_best_focus(scores, participants)
        assert best is not None  # Must return something, not None

    def test_se26_pit_drivers_excluded(self, engine, make_participant):
        """SE-26: Highest score in pits → returns next-highest non-pit driver"""
        participants = {
            0: make_participant(race_position=1, pit_mode=0, speed=60,
                                gap_ahead=5, cars_ahead_250m=5),
            1: make_participant(race_position=2, pit_mode=2, speed=60,
                                gap_ahead=5, cars_ahead_250m=5),
        }
        scores = engine.calculate_scores(participants)
        best = engine.get_best_focus(scores, participants)
        # P1 (index 0) is not in pits, should be selected
        assert best == participants[0]['race_position']


# ── Configurable Parameters (SE-27 to SE-29) ────────────────────────────────

class TestConfigurableParams:
    def test_se27_modified_position_factor(self, make_participant):
        """SE-27: factor=20 → P1 bonus = 20.0"""
        engine = ScoringEngine()
        engine.race_position_bonus_factor = 20
        participants = {0: make_participant(race_position=1)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['race_position_bonus'] == pytest.approx(20.0)

    def test_se28_modified_close_racing_max_gap(self, make_participant):
        """SE-28: max_gap=100, gap=75 → base=(100-75)/5=5.0"""
        engine = ScoringEngine()
        engine.close_racing_max_gap = 100
        participants = {0: make_participant(gap_ahead=75, closing_speed=2.0)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['close_racing_bonus'] == pytest.approx(5.0)
        assert scores[0]['closing_speed_bonus'] == pytest.approx(2.0)

    def test_se29_modified_pit_penalty(self, make_participant):
        """SE-29: penalty=-20 → applied correctly"""
        engine = ScoringEngine()
        engine.pit_mode_penalty = -20
        participants = {0: make_participant(pit_mode=1)}
        scores = engine.calculate_scores(participants)
        assert scores[0]['pit_mode_penalty'] == -20
