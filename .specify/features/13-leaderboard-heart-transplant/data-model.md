# Data Model: Leaderboard Heart Transplant

## Entities

### DistanceTimeSpline
**Location**: `core/spline.py`
**Responsibility**: Maintains a monotonically increasing record of (distance, time) pairs for the race leader. Provides linear interpolation of time-at-distance for any query point.

| Field | Type | Description |
|-------|------|-------------|
| `min_interval` | `float` | Minimum time between accepted samples (0.0 = accept all) |
| `distances` | `list[float]` | Monotonically increasing distance values |
| `times` | `list[float]` | Corresponding flywheel-stabilised time values |

**Lifecycle**:
- Created once per session
- `record()` appends on every tick (same tick as gap calculation)
- `reset()` only on session state transition
- Never reset on leader change or flywheel resync

### PhysicsFlywheel
**Location**: `core/physics_flywheel.py`
**Responsibility**: Stabilises `mCurrentTime` by detecting anomalous jumps (>10s) and substituting system-clock-based synthetic time until game time recovers.

| Field | Type | Description |
|-------|------|-------------|
| `internal_master_clock` | `float` | Authoritative time consumed by spline and gap engines |
| `is_active` | `bool` | True when rejecting game time and synthesising |
| `did_resync` | `bool` | True when force-resync occurred this tick |
| `_healthy_tick_count` | `int` | Counter for consecutive healthy game-time deltas |
| `_last_monotonic` | `float` | Last `time.monotonic()` reading for system-clock synthesis |
| `_last_known_speed` | `float` | Speed from last healthy frame (for lie detection) |

**State Transitions**:
```
LOCKED → (delta > 10s) → ACTIVE → (40 healthy ticks) → RESYNC → LOCKED
```

### Unified WebSocket Payload
**Location**: `dashboard/bridge.py` (extended)
**Consumers**: All HTML debugging surfaces + F1TV overlays

| Field | Type | Description |
|-------|------|-------------|
| `leaderboard` | `list[dict]` | Sorted drivers with `_time_gap`, `_total_dist`, `_in_pits` |
| `spline.distances` | `list[float]` | Current spline distance axis |
| `spline.times` | `list[float]` | Current spline time axis |
| `flywheel_active` | `bool` | Whether flywheel is currently engaged |
| `time_history` | `list[float]` | Recent `mCurrentTime` values for debugging |
| `viewed` | `dict` | Existing F1TV overlay data (unchanged) |
| `weather` | `dict` | Existing weather data (unchanged) |

## Module Dependency Graph

```
core/spline.py          ← zero dependencies (leaf)
core/physics_flywheel.py ← zero dependencies (leaf, uses time.monotonic)
core/shm_serialiser.py  ← depends on shared_memory_struct
core/telemetry_provider.py ← imports spline, physics_flywheel
dashboard/bridge.py     ← imports telemetry_provider (for spline/flywheel state)
tools/shm_leaderboard_server.py ← imports spline, physics_flywheel, shm_serialiser
```
