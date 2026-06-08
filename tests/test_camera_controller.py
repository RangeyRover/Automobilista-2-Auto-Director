"""TDD tests for CameraController — CC-01 to CC-13.
Written BEFORE implementation. All must FAIL initially (RED).
Uses monkeypatched pyKey to capture key sequences.
"""
import pytest
from unittest.mock import patch
import unittest.mock
import json
from core.camera_controller import CameraController


@pytest.fixture
def controller():
    cc = CameraController()
    cc.bypass_focus_check = True
    cc.bypass_threading = True
    return cc


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
        down_presses = [e for e in log if e == ('press', 'DOWN')]
        assert len(down_presses) == 4

    def test_cc02_move_p10_to_p3(self, controller, key_log):
        """CC-02: target=3, current=10 → 7x UP"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(3, 10)
        up_presses = [e for e in log if e == ('press', 'UP')]
        assert len(up_presses) == 7

    def test_cc03_same_position_no_move(self, controller, key_log):
        """CC-03: target=5, current=5 → no keys (not even enter)"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(5, 5)
        # No keys should be pressed, not even ENTER
        assert len(log) == 0

    def test_cc04_p1_to_p1(self, controller, key_log):
        """CC-04: target=1, current=1 → no keys"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(1, 1)
        assert len(log) == 0


# ── Fallback Navigation (CC-05 to CC-07) ───────────────────────────────────

class TestFallbackNavigation:
    def test_cc05_fallback_to_p1(self, controller, key_log):
        """CC-05: target=1, current=None → 32x UP, 0x DOWN"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(1, None)
        up_presses = [e for e in log if e == ('press', 'UP')]
        down_presses = [e for e in log if e == ('press', 'DOWN')]
        assert len(up_presses) == 32
        assert len(down_presses) == 0

    def test_cc06_fallback_to_p10(self, controller, key_log):
        """CC-06: target=10, current=None → 32x UP, 9x DOWN"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(10, None)
        up_presses = [e for e in log if e == ('press', 'UP')]
        down_presses = [e for e in log if e == ('press', 'DOWN')]
        assert len(up_presses) == 32
        assert len(down_presses) == 9

    def test_cc07_fallback_to_p32(self, controller, key_log):
        """CC-07: target=32, current=None → 32x UP, 31x DOWN"""
        log, mock_press, mock_release = key_log
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'):
            controller.move_to_position(32, None)
        up_presses = [e for e in log if e == ('press', 'UP')]
        down_presses = [e for e in log if e == ('press', 'DOWN')]
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
        # Last press should be 'ENTER'
        press_events = [e for e in log if e[0] == 'press']
        assert press_events[-1] == ('press', 'ENTER')


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
        down_presses = [e for e in log if e == ('press', 'DOWN')]
        assert len(down_presses) == 31


# ── Camera Selection & Flags ────────────────────────────────────────────

class TestCameraSelection:
    def test_select_random_camera_enabled(self, controller, key_log):
        """When disable_camera_change is False, a camera key should be pressed."""
        log, mock_press, mock_release = key_log
        controller.disable_camera_change = False
        
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'), \
             patch('random.choice', return_value='3'):
            controller.select_random_camera(is_close=True)
            
        press_events = [e for e in log if e[0] == 'press']
        assert len(press_events) == 1
        assert press_events[0] == ('press', '3')
        assert controller.current_camera_type == 'roof'

    def test_select_random_camera_disabled(self, controller, key_log):
        """When disable_camera_change is True, no camera key should be pressed."""
        log, mock_press, mock_release = key_log
        controller.disable_camera_change = True
        
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'), \
             patch('random.choice', return_value='3'):
            controller.select_random_camera(is_close=True)
            
        assert len(log) == 0

    def test_trackside_anchor_rule(self, controller, key_log):
        """When last shot was special, the next shot must be from trackside_keys."""
        log, mock_press, mock_release = key_log
        controller.disable_camera_change = False
        controller.last_shot_was_special = True
        
        test_config = {
            "trackside_keys": ["7"],
            "pool_close_racing": ["1"],
            "pool_standard": ["2"]
        }
        
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch.object(controller, '_load_config', return_value=test_config), \
             patch('time.sleep'), \
             patch('random.choice') as mock_choice:
            mock_choice.return_value = '7'
            controller.select_random_camera(is_close=True)
            
            # Should have chosen from trackside_keys, not pool_close_racing
            mock_choice.assert_called_once_with(["7"])
            assert controller.last_shot_was_special is False

    def test_config_loading(self, controller, key_log):
        """It should load the configuration file if available."""
        log, mock_press, mock_release = key_log
        controller.disable_camera_change = False
        controller.last_shot_was_special = False
        
        custom_config = {
            "trackside_keys": ["9"],
            "pool_close_racing": ["1"],
            "pool_standard": ["2"]
        }
        
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep'), \
             patch('os.path.exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(custom_config))), \
             patch('random.choice') as mock_choice:
            mock_choice.return_value = '1'
            controller.select_random_camera(is_close=True)
            
            mock_choice.assert_called_once_with(["1"])
            assert controller.last_shot_was_special is True


# ── Asynchronous & Concurrency (T003 to T004, T008, T010) ──────────────────

class TestCameraControllerAsync:
    def test_move_to_position_async_non_blocking(self, controller, key_log):
        """T003: move_to_position returns immediately and executes in background thread."""
        import time
        import threading
        log, mock_press, mock_release = key_log
        controller.bypass_threading = False
        
        # We patch time.sleep to do a small real sleep via Event().wait
        def slow_sleep(sec):
            threading.Event().wait(0.01) # 10ms
            
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep', side_effect=slow_sleep):
            
            start = time.time()
            controller.move_to_position(5, 1)
            duration = time.time() - start
            
            # Should return immediately on calling thread
            assert duration < 0.015
            
            # Wait for background thread to complete
            if hasattr(controller, '_switch_thread') and controller._switch_thread:
                controller._switch_thread.join(timeout=1.0)
                
        # Key presses should still be executed in the background thread
        down_presses = [e for e in log if e == ('press', 'DOWN')]
        assert len(down_presses) == 4
        assert log[-1] == ('release', 'ENTER')

    def test_concurrent_switches_ignored(self, controller, key_log):
        """T004: Subsequent switch requests are ignored while switching."""
        import time
        import threading
        log, mock_press, mock_release = key_log
        controller.bypass_threading = False
        
        # We want the background thread to stay active so we can trigger a second one
        def slow_sleep(sec):
            threading.Event().wait(0.05) # Sleep 50ms in the background thread
            
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep', side_effect=slow_sleep):
            
            # First switch
            controller.move_to_position(5, 1)
            
            # Immediately trigger second switch (should be ignored)
            controller.move_to_position(10, 1)
            
            # Wait for background thread to finish
            if hasattr(controller, '_switch_thread') and controller._switch_thread:
                controller._switch_thread.join(timeout=2.0)
                
        # Total keys logged should only belong to the first switch (P5)
        # P5 requires 4x DOWN + 1x ENTER.
        # P10 would require 9x DOWN + 1x ENTER.
        # If P10 was run, we'd have 13x DOWN presses. If ignored, only 4.
        down_presses = [e for e in log if e == ('press', 'DOWN')]
        assert len(down_presses) == 4
        
    def test_select_random_camera_async(self, controller, key_log):
        """T008: select_random_camera is non-blocking and executes in background thread."""
        import time
        import threading
        log, mock_press, mock_release = key_log
        controller.disable_camera_change = False
        controller.bypass_threading = False
        
        def slow_sleep(sec):
            threading.Event().wait(0.01) # 10ms
            
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep', side_effect=slow_sleep), \
             patch('random.choice', return_value='7'):
            
            start = time.time()
            controller.select_random_camera(is_close=True)
            duration = time.time() - start
            
            assert duration < 0.015
            
            if hasattr(controller, '_switch_thread') and controller._switch_thread:
                controller._switch_thread.join(timeout=1.0)
                
        press_events = [e for e in log if e[0] == 'press']
        assert len(press_events) == 1
        assert press_events[0] == ('press', '7')

    def test_manual_switch_async(self, controller, key_log):
        """T010: manual_switch_to_key is non-blocking and executes in background thread."""
        import time
        import threading
        log, mock_press, mock_release = key_log
        controller.disable_camera_change = False
        controller.bypass_threading = False
        
        def slow_sleep(sec):
            threading.Event().wait(0.01) # 10ms
            
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch('time.sleep', side_effect=slow_sleep):
            
            start = time.time()
            controller.manual_switch_to_key('7')
            duration = time.time() - start
            
            assert duration < 0.015
            
            if hasattr(controller, '_switch_thread') and controller._switch_thread:
                controller._switch_thread.join(timeout=1.0)
                
        press_events = [e for e in log if e[0] == 'press']
        assert len(press_events) == 1
        assert press_events[0] == ('press', '7')

    def test_focus_loss_aborts_sequence(self, controller, key_log):
        """T013: If Automobilista 2 loses focus mid-sequence, the execution aborts."""
        import time
        import threading
        log, mock_press, mock_release = key_log
        controller.disable_camera_change = False
        controller.bypass_threading = False
        controller.bypass_focus_check = False
        
        # Mock _is_ams2_focused to return True once, then False
        focus_returns = [True, False, False]
        def mock_focus():
            if focus_returns:
                return focus_returns.pop(0)
            return False
            
        with patch.object(controller, '_press_key', mock_press), \
             patch.object(controller, '_release_key', mock_release), \
             patch.object(controller, '_is_ams2_focused', side_effect=mock_focus), \
             patch('time.sleep'):
            
            controller.move_to_position(5, 1) # Requires 4x DOWN + ENTER
            
            if hasattr(controller, '_switch_thread') and controller._switch_thread:
                controller._switch_thread.join(timeout=1.0)
                
        # The first key tap (DOWN) should succeed (because _is_ams2_focused returned True first),
        # but the second tap (DOWN) should fail because _is_ams2_focused returns False, raising InterruptedError.
        # So we should only see 1 'press' for DOWN.
        down_presses = [e for e in log if e == ('press', 'DOWN')]
        assert len(down_presses) == 1
        # Reentrancy flag is cleared in finally block
        assert controller._switching_in_progress is False



