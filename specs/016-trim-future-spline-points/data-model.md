# Data Model: Spline and Master Clock Structures

This document outlines the data model and structural requirements for the `DistanceTimeSpline` class.

## DistanceTimeSpline (In-Memory)

The `DistanceTimeSpline` class maintains the historical progress of the lead car, storing matching distance and time coordinates.

### Internal Attributes
* `self.distances`: A `list` of `float` representing the absolute total distance traveled by the leader (in meters) at each recorded sample.
* `self.times`: A `list` of `float` representing the stabilized master clock timestamps (in seconds) corresponding to each sample.

### Invariants
1. **Length Alignment**: `len(self.distances) == len(self.times)` MUST hold true at all times.
2. **Monotonicity**: Both lists MUST be strictly monotonically increasing.
   - For any index $i > 0$: $distances[i] > distances[i-1]$ and $times[i] > times[i-1]$.

### Structural Modifications

We add the following method to the class interface:

#### `trim_future_points(self, current_time: float) -> None`
* **Purpose**: Truncates both lists to discard points recorded at timestamps strictly greater than `current_time`.
* **Inputs**: `current_time` (`float`): The new reference time boundary.
* **Algorithm**:
  1. If `self.times` is empty, return immediately.
  2. Find `idx = bisect.bisect_right(self.times, current_time)`.
  3. If `idx < len(self.times)`:
     - Slice `self.times = self.times[:idx]`
     - Slice `self.distances = self.distances[:idx]`
* **Post-conditions**:
  - `len(self.distances) == len(self.times)` is preserved.
  - All remaining elements in `self.times` are $\le current\_time$.
