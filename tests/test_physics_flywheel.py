"""TDD tests for PhysicsFlywheel — the system-clock time stabilizer.

Tests use an injectable mock clock to control system time deterministically.
"""
import pytest


def _make_mock_clock(start=1000.0, step=0.25):
    """Create a mock clock that advances by `step` each call."""
    state = {"t": start}
    def clock():
        t = state["t"]
        state["t"] += step
        return t
    return clock


# ──────────────────────────────────────────────
# Phase 2: Core Flywheel Logic (T003–T008)
# ──────────────────────────────────────────────

def test_flywheel_first_tick_syncs_clock():
    """T003: First call to process() should sync the internal clock to game time."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    result = fw.process(game_time=100.0, leader_dist=2000.0)

    assert result == 100.0, f"First tick should return game_time exactly, got {result}"
    assert fw.is_active is False, "Flywheel should NOT be active on first tick"


def test_flywheel_normal_tick_accepts_time():
    """T004: A normal 0.25s tick should be accepted and returned as-is."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    result = fw.process(game_time=100.25, leader_dist=2020.0)

    assert result == 100.25, f"Normal tick should return game_time, got {result}"
    assert fw.is_active is False, "Flywheel should NOT be active during normal ticks"


def test_flywheel_normal_tick_updates_speed():
    """T005: Speed should be calculated from healthy ticks: (2020-2000)/(100.25-100.0) = 80 m/s."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    fw.process(game_time=100.25, leader_dist=2020.0)

    assert fw.last_known_speed == pytest.approx(80.0, abs=0.1), \
        f"Speed should be 80.0 m/s, got {fw.last_known_speed}"


def test_flywheel_rejects_massive_forward_jump():
    """T006: A 40s forward jump should be REJECTED. System-time synthetic returned."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    clock = _make_mock_clock()
    fw = PhysicsFlywheel(clock=clock)
    fw.process(game_time=100.0, leader_dist=2000.0)    # clock call 1: 1000.0
    # 40s jump but only 20m distance — physically impossible
    result = fw.process(game_time=140.0, leader_dist=2020.0)  # clock call 2: 1000.25

    assert result != 140.0, "Anomalous game time should be rejected"
    # System dt = 1000.25 - 1000.0 = 0.25s, so synthetic = 100.0 + 0.25 = 100.25
    assert result == pytest.approx(100.25, abs=0.01), \
        f"Synthetic time should be 100.25s (system dt), got {result}"
    assert fw.is_active is True, "Flywheel should be ACTIVE during anomaly"


def test_flywheel_rejects_massive_backward_jump():
    """T007: A 40s backward jump should also be REJECTED."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    clock = _make_mock_clock()
    fw = PhysicsFlywheel(clock=clock)
    fw.process(game_time=100.0, leader_dist=2000.0)
    # Backward jump — time goes from 100 to 60
    result = fw.process(game_time=60.0, leader_dist=2020.0)

    assert result != 60.0, "Backward anomaly should be rejected"
    assert result == pytest.approx(100.25, abs=0.01), \
        f"Synthetic time should be ~100.25s (system dt), got {result}"
    assert fw.is_active is True, "Flywheel should be ACTIVE during backward anomaly"


def test_flywheel_synthetic_time_uses_system_clock():
    """T008: Synthetic dt must come from system clock, not distance/speed."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    # Clock steps: 1000.0, 1000.25, 1000.50 (3 calls)
    clock = _make_mock_clock()
    fw = PhysicsFlywheel(clock=clock)
    # Tick 1: init (clock=1000.0)
    fw.process(game_time=100.0, leader_dist=2000.0)
    # Tick 2: establish speed = 80 m/s (clock=1000.25)
    fw.process(game_time=100.25, leader_dist=2020.0)
    # Tick 3: anomaly (clock=1000.50) — system dt = 0.25s
    result = fw.process(game_time=140.25, leader_dist=2060.0)

    expected_time = 100.25 + 0.25  # 100.50 (system dt, not distance/speed)
    assert result == pytest.approx(expected_time, abs=0.01), \
        f"Synthetic time should be {expected_time}, got {result}"


# ──────────────────────────────────────────────
# Phase 4: Recovery & Edge Cases (T015–T018)
# ──────────────────────────────────────────────

def test_flywheel_recovery_relocks_to_game_time():
    """T015: After anomaly ends, flywheel should re-lock to real game time."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    clock = _make_mock_clock()
    fw = PhysicsFlywheel(clock=clock)
    fw.process(game_time=100.0, leader_dist=2000.0)
    # Anomaly tick
    synthetic = fw.process(game_time=140.0, leader_dist=2020.0)
    assert fw.is_active is True

    # Recovery tick — game time returns close to synthetic clock
    result = fw.process(game_time=100.50, leader_dist=2040.0)

    assert result == 100.50, f"Should re-lock to real game time, got {result}"
    assert fw.is_active is False, "Flywheel should deactivate after recovery"


def test_flywheel_zero_speed_uses_system_clock():
    """T016: Even with near-zero speed, system clock dt is used (no divide-by-zero risk)."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    clock = _make_mock_clock()
    fw = PhysicsFlywheel(clock=clock)
    fw.process(game_time=100.0, leader_dist=2000.0)
    # Gradually ramp speed down
    fw.process(game_time=100.25, leader_dist=2005.0)    # 20 m/s
    fw.process(game_time=100.50, leader_dist=2005.75)   # 3.0 m/s
    fw.process(game_time=100.75, leader_dist=2005.85)   # 0.4 m/s
    assert fw.last_known_speed < 1.0, "Speed should be near zero"

    # Anomaly with near-zero speed — system clock still advances
    result = fw.process(game_time=140.0, leader_dist=2005.95)

    # System dt = 0.25s regardless of speed
    expected = 100.75 + 0.25
    assert result == pytest.approx(expected, abs=0.01), \
        f"Should use system clock dt, got {result}"


def test_flywheel_anomaly_advances_by_system_time_not_zero():
    """T017: During anomaly, clock always advances by system dt (never zero)."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    clock = _make_mock_clock()
    fw = PhysicsFlywheel(clock=clock)
    fw.process(game_time=100.0, leader_dist=2000.0)
    fw.process(game_time=100.25, leader_dist=2020.0)

    # Anomaly where distance DECREASED (lap boundary reset)
    result = fw.process(game_time=140.0, leader_dist=1900.0)

    # System dt = 0.25s, so clock advances regardless of distance
    expected = 100.25 + 0.25
    assert result == pytest.approx(expected, abs=0.01), \
        f"Clock should advance by system dt even with negative distance, got {result}"


def test_flywheel_speed_not_updated_during_anomaly():
    """T018: last_known_speed must NOT change during an anomalous frame (FR-002)."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    fw.process(game_time=100.25, leader_dist=2020.0)
    speed_before = fw.last_known_speed  # should be 80.0

    # Anomaly frame
    fw.process(game_time=140.0, leader_dist=2020.0)

    assert fw.last_known_speed == speed_before, \
        f"Speed should remain {speed_before} during anomaly, got {fw.last_known_speed}"


# ──────────────────────────────────────────────
# Phase 5: Session Reset Hook (T026)
# ──────────────────────────────────────────────

def test_flywheel_reset_syncs_clock():
    """T026: reset() should force-sync the clock and clear anomaly state."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    fw.process(game_time=140.0, leader_dist=2020.0)  # Trigger anomaly
    assert fw.is_active is True

    # Session reset
    fw.reset(current_time=0.0, leader_dist=0.0)

    assert fw.internal_master_clock == 0.0, "Clock should sync to reset time"
    assert fw.is_active is False, "Anomaly state should be cleared"
    assert fw.last_leader_distance == 0.0, "Distance should sync to reset distance"


# ──────────────────────────────────────────────
# Phase 6: Scrubbing Compatibility (T031–T035)
# ──────────────────────────────────────────────

def test_flywheel_20x_scrub_accepted():
    """T031: 20x scrub (5s delta) must be ACCEPTED — within 5.5s threshold."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    result = fw.process(game_time=105.0, leader_dist=2400.0)

    assert result == 105.0, f"20x scrub should be accepted, got {result}"
    assert fw.is_active is False


def test_flywheel_backward_scrub_accepted():
    """T032: Backward scrub (5s backward delta) must be ACCEPTED."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    result = fw.process(game_time=95.0, leader_dist=1600.0)

    assert result == 95.0, f"Backward scrub should be accepted, got {result}"
    assert fw.is_active is False


def test_flywheel_boundary_5_4s_accepted():
    """T033: Delta of exactly 5.4s must be ACCEPTED (below 5.5s threshold)."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    result = fw.process(game_time=105.4, leader_dist=2432.0)

    assert result == 105.4, f"5.4s delta should be accepted, got {result}"
    assert fw.is_active is False


def test_flywheel_boundary_5_5s_exact_accepted():
    """T034: Delta of exactly 5.5s must be ACCEPTED (<=5.5 per FR-003)."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    result = fw.process(game_time=105.5, leader_dist=2440.0)

    assert result == 105.5, f"Exactly 5.5s delta should be accepted, got {result}"
    assert fw.is_active is False


def test_flywheel_boundary_6s_rejected():
    """T035: Delta of 6.0s must be REJECTED (>5.5 per FR-003)."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    result = fw.process(game_time=106.0, leader_dist=2020.0)

    assert result != 106.0, f"6.0s delta should be rejected, got {result}"
    assert fw.is_active is True, "Flywheel should be active"


# ──────────────────────────────────────────────
# Speed-Based Lie Detector Tests
# ──────────────────────────────────────────────

def test_flywheel_speed_lie_detector_rejects_implausible_speed():
    """Time delta within threshold (3s) but implied speed is <10% of last_known.
    
    Scenario: car at 80 m/s, camera swap causes 3s time jump but only 5m distance.
    Implied speed = 5/3 = 1.67 m/s which is < 10% of 80 = 8.0 m/s → REJECT.
    """
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    fw.process(game_time=100.25, leader_dist=2020.0)  # establish speed = 80 m/s
    assert fw.last_known_speed == pytest.approx(80.0, abs=0.1)

    # 3s delta (within 5.5s threshold) but only 5m moved → implied 1.67 m/s
    result = fw.process(game_time=103.25, leader_dist=2025.0)

    assert result != 103.25, f"Implausible speed frame should be rejected, got {result}"
    assert fw.is_active is True, "Flywheel should be active"
    assert fw.last_known_speed == pytest.approx(80.0, abs=0.1), \
        "Speed should NOT update from rejected frame"


def test_flywheel_speed_lie_detector_accepts_proportional_scrub():
    """Time delta within threshold AND implied speed is proportional → ACCEPT."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    fw.process(game_time=100.25, leader_dist=2020.0)  # establish speed = 80 m/s

    # 5s delta + 400m → implied 80 m/s, well above 10% threshold
    result = fw.process(game_time=105.25, leader_dist=2420.0)

    assert result == 105.25, f"Proportional scrub should be accepted, got {result}"
    assert fw.is_active is False


def test_flywheel_speed_lie_detector_skips_backward_time():
    """Speed lie detector should NOT trigger on backward time deltas (scrub backward)."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    fw.process(game_time=100.25, leader_dist=2020.0)  # establish speed = 80 m/s

    # Backward scrub: time goes back 3s, distance goes back
    result = fw.process(game_time=97.25, leader_dist=1780.0)

    assert result == 97.25, f"Backward scrub should be accepted, got {result}"
    assert fw.is_active is False


# ──────────────────────────────────────────────
# Negative Distance Delta (Lap Boundary Fix)
# ──────────────────────────────────────────────

def test_flywheel_negative_distance_delta_does_not_trigger_speed_lie_detector():
    """Negative distance_delta (lap boundary) should NOT trigger the speed lie detector."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    fw.process(game_time=100.25, leader_dist=2020.0)  # speed = 80 m/s

    # Lap boundary: distance drops by 20m, but time delta is healthy (0.25s)
    result = fw.process(game_time=100.50, leader_dist=2000.0)

    assert result == 100.50, f"Negative distance_delta should not trigger lie detector, got {result}"
    assert fw.is_active is False


# ──────────────────────────────────────────────
# Self-Healing Resync Tests
# ──────────────────────────────────────────────

def test_flywheel_self_healing_resyncs_after_consecutive_healthy_ticks():
    """If flywheel is stuck active but game time shows 40 consecutive healthy
    deltas (~10s), force-resync to real game time."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    
    # Force the flywheel into a stuck state: massive time jump
    fw.process(game_time=140.0, leader_dist=2020.0)
    assert fw.is_active is True
    
    # Simulate 40 consecutive healthy game-time ticks at 0.25s intervals
    for i in range(40):
        game_t = 140.25 + i * 0.25
        leader_d = 2040.0 + i * 20.0
        result = fw.process(game_time=game_t, leader_dist=leader_d)
    
    # After 40+ healthy ticks, flywheel should have resynced
    assert fw.is_active is False, "Flywheel should self-heal after 40 healthy ticks"
    assert fw.did_resync is True, "did_resync flag should be set"
    assert fw.internal_master_clock == game_t, \
        f"Clock should resync to real game time {game_t}, got {fw.internal_master_clock}"


def test_flywheel_self_healing_does_not_trigger_too_early():
    """Self-healing should NOT fire before 40 consecutive healthy ticks."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    
    # Trigger anomaly
    fw.process(game_time=140.0, leader_dist=2020.0)
    assert fw.is_active is True
    
    # 39 healthy ticks — just under the threshold
    for i in range(39):
        game_t = 140.25 + i * 0.25
        leader_d = 2040.0 + i * 20.0
        fw.process(game_time=game_t, leader_dist=leader_d)
    
    assert fw.is_active is True, "Should NOT resync at only 39 healthy ticks"
    assert fw.did_resync is False


def test_flywheel_self_healing_does_not_trigger_during_real_anomaly():
    """Self-healing should NOT fire if game time deltas are erratic (real anomaly)."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    fw = PhysicsFlywheel(clock=_make_mock_clock())
    fw.process(game_time=100.0, leader_dist=2000.0)
    
    # Trigger anomaly
    fw.process(game_time=140.0, leader_dist=2020.0)
    assert fw.is_active is True
    
    # 3 healthy ticks then a bad one — should NOT resync
    fw.process(game_time=140.25, leader_dist=2040.0)
    fw.process(game_time=140.50, leader_dist=2060.0)
    fw.process(game_time=140.75, leader_dist=2080.0)
    fw.process(game_time=180.0, leader_dist=2100.0)   # another jump — resets counter
    fw.process(game_time=180.25, leader_dist=2120.0)
    fw.process(game_time=180.50, leader_dist=2140.0)
    
    assert fw.is_active is True, "Should NOT resync with interrupted healthy sequence"


# ──────────────────────────────────────────────
# System Clock Clamping
# ──────────────────────────────────────────────

def test_flywheel_system_dt_clamped_to_2s_max():
    """System dt must be clamped to 2.0s max to prevent huge advances from stalls."""
    from tools.shm_leaderboard_server import PhysicsFlywheel

    # Clock jumps 5 seconds on the anomaly tick
    call_count = {"n": 0}
    def stalling_clock():
        call_count["n"] += 1
        if call_count["n"] <= 2:
            return 1000.0 + (call_count["n"] - 1) * 0.25
        return 1005.0  # 5s jump — simulates system stall
    
    fw = PhysicsFlywheel(clock=stalling_clock)
    fw.process(game_time=100.0, leader_dist=2000.0)   # clock=1000.0
    result = fw.process(game_time=140.0, leader_dist=2020.0)  # clock=1000.25, anomaly
    # Next anomaly tick would see system dt = 1005.0 - 1000.25 = 4.75s → clamped to 2.0
    result2 = fw.process(game_time=140.25, leader_dist=2040.0)
    
    # Internal clock should advance by at most 2.0s from the clamped dt
    # First anomaly: 100.0 + 0.25 = 100.25
    # Second anomaly: 100.25 + 2.0 = 102.25 (clamped)
    assert result2 == pytest.approx(102.25, abs=0.01), \
        f"System dt should be clamped to 2.0s, got {result2}"
