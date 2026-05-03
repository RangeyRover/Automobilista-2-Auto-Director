"""TDD tests for CameraController — CC-01 to CC-13.
Written BEFORE implementation. All must FAIL initially (RED).
Uses monkeypatched pyKey to capture key sequences.
"""
import pytest
from unittest.mock import patch, call
from core.camera_controller import CameraController


@pytest.fixture
def controller():
    return CameraController()


@pytest.fixture
def key_log():
    """Captures all key presses/releases as a list of tuples."""
    log = []

    def mock_press(key):
        log.append(('press', key))

    def mock_release(key):
        log.append(('release', key))

    return log, mock_press, mock_release


# ── Delta Navigation (CC-01 to CC-04) ──────────────────────────────────────

class TestDeltaNavigation:
    def test_cc01_move_p1_to_p5(self, controller, key_log):
        """CC-01: target=5, current=1 → 4x DOWN"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(5, 1)
        down_presses = [e for e in log if e == ('press', 'down')]
        assert len(down_presses) == 4

    def test_cc02_move_p10_to_p3(self, controller, key_log):
        """CC-02: target=3, current=10 → 7x UP"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(3, 10)
        up_presses = [e for e in log if e == ('press', 'up')]
        assert len(up_presses) == 7

    def test_cc03_same_position_no_move(self, controller, key_log):
        """CC-03: target=5, current=5 → no keys"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(5, 5)
        # Only enter should be pressed, no UP/DOWN
        direction_presses = [e for e in log if e[1] in ('up', 'down')]
        assert len(direction_presses) == 0

    def test_cc04_p1_to_p1(self, controller, key_log):
        """CC-04: target=1, current=1 → no keys"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(1, 1)
        direction_presses = [e for e in log if e[1] in ('up', 'down')]
        assert len(direction_presses) == 0


# ── Fallback Navigation (CC-05 to CC-07) ───────────────────────────────────

class TestFallbackNavigation:
    def test_cc05_fallback_to_p1(self, controller, key_log):
        """CC-05: target=1, current=None → 32x UP, 0x DOWN"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(1, None)
        up_presses = [e for e in log if e == ('press', 'up')]
        down_presses = [e for e in log if e == ('press', 'down')]
        assert len(up_presses) == 32
        assert len(down_presses) == 0

    def test_cc06_fallback_to_p10(self, controller, key_log):
        """CC-06: target=10, current=None → 32x UP, 9x DOWN"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(10, None)
        up_presses = [e for e in log if e == ('press', 'up')]
        down_presses = [e for e in log if e == ('press', 'down')]
        assert len(up_presses) == 32
        assert len(down_presses) == 9

    def test_cc07_fallback_to_p32(self, controller, key_log):
        """CC-07: target=32, current=None → 32x UP, 31x DOWN"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(32, None)
        up_presses = [e for e in log if e == ('press', 'up')]
        down_presses = [e for e in log if e == ('press', 'down')]
        assert len(up_presses) == 32
        assert len(down_presses) == 31


# ── Key Timing (CC-08 to CC-10) ────────────────────────────────────────────

class TestKeyTiming:
    def test_cc08_hold_duration(self, controller, key_log):
        """CC-08: time.sleep(0.01) called after each pressKey."""
        log, mock_press, mock_release = key_log
        sleep_calls = []
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep', side_effect=lambda t: sleep_calls.append(t)):
            controller.move_to_position(2, 1)  # 1x DOWN + enter
        # Each press has a sleep of 0.01
        assert all(t >= 0.01 for t in sleep_calls)

    def test_cc09_gap_duration(self, controller, key_log):
        """CC-09: time.sleep(0.01) called after each releaseKey."""
        log, mock_press, mock_release = key_log
        sleep_calls = []
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep', side_effect=lambda t: sleep_calls.append(t)):
            controller.move_to_position(2, 1)
        # Should have sleep calls for hold AND gap
        assert len(sleep_calls) >= 2

    def test_cc10_enter_pressed_after_move(self, controller, key_log):
        """CC-10: Final key is ENTER press+release."""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(3, 1)
        # Last press should be 'enter'
        press_events = [e for e in log if e[0] == 'press']
        assert press_events[-1] == ('press', 'enter')


# ── Edge Cases (CC-11 to CC-13) ────────────────────────────────────────────

class TestEdgeCases:
    def test_cc11_target_p0_invalid(self, controller, key_log):
        """CC-11: target=0 → no keys (guard clause)"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(0, 1)
        assert len(log) == 0

    def test_cc12_target_p33_invalid(self, controller, key_log):
        """CC-12: target=33 → no keys (guard clause)"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(33, 1)
        assert len(log) == 0

    def test_cc13_large_delta(self, controller, key_log):
        """CC-13: P1 to P32 → 31x DOWN + timing"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(32, 1)
        down_presses = [e for e in log if e == ('press', 'down')]
        assert len(down_presses) == 31
