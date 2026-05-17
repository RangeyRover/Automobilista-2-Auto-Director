"""
TDD tests for DistanceTimeSpline and associated standalone gap calculation functions.
"""
import pytest
from core.spline import DistanceTimeSpline, compute_total_distance, compute_time_gap

# --- Phase 1: Distance Calculation ---

def test_compute_total_distance_lap_1():
    assert compute_total_distance(1, 5000.0, 1200.0) == 1200.0

def test_compute_total_distance_lap_3():
    assert compute_total_distance(3, 5000.0, 1200.0) == 11200.0

def test_compute_total_distance_lap_2_start():
    assert compute_total_distance(2, 5000.0, 0.0) == 5000.0

# --- Phase 2: DistanceTimeSpline Tests ---

def test_spline_empty_interpolate_returns_none():
    spline = DistanceTimeSpline()
    assert spline.interpolate_time(100.0) is None

def test_spline_single_sample_returns_none():
    spline = DistanceTimeSpline()
    spline.record(50.0, 1.0)
    assert spline.interpolate_time(50.0) is None

def test_spline_record_and_interpolate_exact():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(100.0, 1.0)
    assert spline.interpolate_time(100.0) == 1.0

def test_spline_interpolate_midpoint():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(100.0, 1.0)
    assert spline.interpolate_time(50.0) == 0.5

def test_spline_out_of_range_low():
    spline = DistanceTimeSpline()
    spline.record(10.0, 0.1)
    spline.record(100.0, 1.0)
    assert spline.interpolate_time(5.0) is None

def test_spline_extrapolate_high():
    spline = DistanceTimeSpline()
    spline.record(10.0, 0.1)
    spline.record(100.0, 1.0)
    
    # 105.0 is exactly 5m past the last record.
    # The segment was 90m in 0.9s (0.01 s/m).
    # 105.0 should extrapolate to 1.0 + (5 * 0.01) = 1.05s
    assert abs(spline.interpolate_time(105.0) - 1.05) < 0.001

def test_spline_min_interval_enforced():
    spline = DistanceTimeSpline(min_interval=0.5)
    assert spline.record(0.0, 0.0) is True
    assert spline.record(10.0, 0.3) is False  # rejected
    assert spline.record(20.0, 0.5) is True   # accepted

def test_spline_monotonic_distance_enforced():
    spline = DistanceTimeSpline()
    assert spline.record(100.0, 1.0) is True
    assert spline.record(90.0, 1.5) is False  # rejected, distance went backwards

def test_spline_reset_clears_data():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(100.0, 1.0)
    spline.reset()
    assert spline.sample_count == 0
    assert spline.interpolate_time(50.0) is None

def test_spline_distance_range():
    spline = DistanceTimeSpline()
    assert spline.distance_range is None
    spline.record(10.0, 0.5)
    spline.record(200.0, 2.0)
    assert spline.distance_range == (10.0, 200.0)

def test_spline_multi_segment_interpolation():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(50.0, 2.0)    # Slow: 25m/s
    spline.record(150.0, 3.0)   # Fast: 100m/s
    spline.record(200.0, 4.0)   # Slow: 50m/s
    
    # Halfway in first segment (0 to 50): 25m should be 1.0s
    assert abs(spline.interpolate_time(25.0) - 1.0) < 0.001
    # Halfway in second segment (50 to 150): 100m should be 2.5s
    assert abs(spline.interpolate_time(100.0) - 2.5) < 0.001
    # Interpolating between segments at exact boundary
    assert spline.interpolate_time(150.0) == 3.0

# --- Phase 3: Time Gap Tests ---

def test_time_gap_basic():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(1000.0, 10.0)
    # driver at distance 500, leader passed there at t=5.0. current time is 12.0
    # gap should be 12.0 - 5.0 = 7.0
    assert compute_time_gap(500.0, 12.0, spline) == 7.0

def test_time_gap_leader_at_front():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(100.0, 10.0)
    # leader is at distance 100 at time 10.0
    assert compute_time_gap(100.0, 10.0, spline) == 0.0

def test_time_gap_out_of_range():
    spline = DistanceTimeSpline()
    spline.record(500.0, 5.0)
    spline.record(1000.0, 10.0)
    # driver at distance 100, which is out of recorded range
    assert compute_time_gap(100.0, 12.0, spline) is None

def test_time_gap_speed_variation():
    spline = DistanceTimeSpline()
    spline.record(0.0, 0.0)
    spline.record(100.0, 2.0)   # slow: 50m/s
    spline.record(200.0, 2.5)   # fast: 200m/s
    
    # 50m behind leader when leader is at 100m (slow section)
    # Driver is at 50m. Spline says t=1.0 at 50m. Current time is 2.0.
    # Gap = 2.0 - 1.0 = 1.0s
    gap_slow = compute_time_gap(50.0, 2.0, spline)
    
    # 50m behind leader when leader is at 200m (fast section)
    # Driver is at 150m. Spline says t=2.25 at 150m. Current time is 2.5.
    # Gap = 2.5 - 2.25 = 0.25s
    gap_fast = compute_time_gap(150.0, 2.5, spline)
    
    assert gap_slow == 1.0
    assert gap_fast == 0.25
    assert gap_slow > gap_fast
