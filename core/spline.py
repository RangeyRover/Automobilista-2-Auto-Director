"""
Provides the DistanceTimeSpline class.
Responsible for maintaining a monotonically increasing record of (distance, time) pairs for the race leader,
and interpolating time gaps for other drivers.
"""
import bisect

class DistanceTimeSpline:
    """Maintains a history of distance-time pairs for gap interpolation."""
    def __init__(self, min_interval: float = 0.5):
        self.min_interval = min_interval
        self.distances = []
        self.times = []
        
    def reset(self):
        """Clear all recorded samples."""
        self.distances.clear()
        self.times.clear()
        
    @property
    def sample_count(self) -> int:
        return len(self.distances)
        
    @property
    def distance_range(self) -> tuple[float, float] | None:
        if not self.distances:
            return None
        return (self.distances[0], self.distances[-1])
        
    def record(self, distance: float, time: float) -> bool:
        """
        Attempt to record a new sample.
        Rejects if time since last sample < min_interval or if distance is not strictly monotonically increasing.
        Returns True if accepted, False if rejected.
        """
        if self.times:
            if time - self.times[-1] < self.min_interval:
                return False
            if distance <= self.distances[-1]:
                return False
                
        self.distances.append(distance)
        self.times.append(time)
        return True
        
    def interpolate_time(self, distance: float) -> float | None:
        """
        Interpolate the time at a given distance.
        Returns None if there are <2 samples or if the distance is < the first sample.
        Extrapolates if distance is > the last sample.
        """
        if self.sample_count < 2:
            return None
            
        if distance < self.distances[0]:
            return None
            
        if distance > self.distances[-1]:
            idx = self.sample_count - 1
        else:
            idx = bisect.bisect_right(self.distances, distance)
            if idx == 0:
                return self.times[0]
            if idx == self.sample_count:
                idx = self.sample_count - 1
                
        d0, d1 = self.distances[idx - 1], self.distances[idx]
        t0, t1 = self.times[idx - 1], self.times[idx]
        
        if d1 == d0:
            return t0
            
        if distance > d1:
            speed = (d1 - d0) / (t1 - t0) if t1 > t0 else 0.0
            # If game physics paused during camera swap, speed approaches 0.
            # We enforce a 10m/s (~36km/h) minimum speed for extrapolation to prevent crazy time spikes.
            if speed < 10.0:
                speed = 10.0
            return t1 + (distance - d1) / speed
            
        # Linear interpolation
        fraction = (distance - d0) / (d1 - d0)
        return t0 + fraction * (t1 - t0)

def compute_total_distance(current_lap: int, track_length: float, lap_distance: float) -> float:
    """Calculate absolute total distance from lap metrics."""
    return (current_lap - 1) * track_length + lap_distance

def compute_time_gap(driver_total_dist: float, current_time: float, spline: DistanceTimeSpline) -> float | None:
    """
    Calculate the time gap between the leader and a driver at a given distance.
    Returns the time difference in seconds, or None if the distance cannot be interpolated.
    """
    if spline is None:
        return None
    leader_time_at_dist = spline.interpolate_time(driver_total_dist)
    if leader_time_at_dist is None:
        return None
    return max(0.0, current_time - leader_time_at_dist)
