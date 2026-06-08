# Research Notes: Spline Trimming Strategy

## Decision 1: Spline List Trimming via Binary Search
* **Decision**: Use `bisect.bisect_right` to find the index of the first spline point whose timestamp exceeds `current_time`, and slice both `times` and `distances` lists to that index.
* **Rationale**:
  - `self.times` is guaranteed to be strictly monotonically increasing, which is a prerequisite for binary search.
  - `bisect.bisect_right` operates in $O(\log N)$ time complexity.
  - Slicing `times[:idx]` and `distances[:idx]` in Python is extremely fast ($O(K)$ where $K$ is the size of the slice) and handles trimming in a single line without manual loop overhead.
* **Alternatives considered**:
  - Linear scan: Iterate backwards from the end of the list until a time $\le \text{current\_time}$ is found. This would be $O(M)$ where $M$ is the number of points to trim. For a large number of future-dated points, it could be slower than binary search.

## Decision 2: Triggering Conditions in TelemetryProvider
* **Decision**: Check for spline trimming in `TelemetryProvider.poll()` immediately after the stabilized time is resolved via the flywheel:
  ```python
  stable_time = self._flywheel.process(game_time, leader_dist)
  
  if self._flywheel.did_resync or (self._leader_spline.times and stable_time < self._leader_spline.times[-1]):
      self._leader_spline.trim_future_points(stable_time)
  ```
* **Rationale**:
  - By checking `self._flywheel.did_resync`, we handle the case where the flywheel recovery snaps the clock back from its system-time-based drift to the raw game clock.
  - By checking `stable_time < self._leader_spline.times[-1]`, we handle the case where the user manually rewinds the replay, causing the master clock to jump backward.
* **Alternatives considered**:
  - Trim only on did_resync: This would fail to handle manual replay rewinds where the flywheel doesn't necessarily declare a resync.
  - Trim on every tick: Trimming unconditionally on every tick adds unnecessary overhead. Checking the negative delta boundary ensures we only trim when a time-travel event actually occurs.
