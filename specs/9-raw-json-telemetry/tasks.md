# Implementation Tasks: Raw JSON Telemetry Dumps

## Task 1: Create `ctypes_serializer` Utility
- **File**: `core/utils/ctypes_serializer.py`
- **Description**: Develop a generic Python utility function capable of safely converting nested `ctypes` structures into serializable Python dictionaries.
- **Requirements**:
  - Recursively parse `ctypes.Structure` fields.
  - Parse `ctypes.Array` into Python lists.
  - Safely decode `bytes` objects to UTF-8 strings (stripping null terminators `\x00`).
  - Return a standard `dict` that `json.dumps()` can digest.

## Task 2: Add Config and State to TelemetryProvider
- **File**: `core/telemetry_provider.py`
- **Description**: Add the toggle state and tracking variables.
- **Requirements**:
  - Introduce `self._dump_raw_json` flag (default `True` during dev/testing, but controlled via config later if necessary).
  - Add `self._last_json_dump_time = 0.0`.

## Task 3: Implement JSON Output Logic
- **File**: `core/telemetry_provider.py`
- **Description**: Integrate the dump logic into the 60Hz tick loop so it outputs once a second without dragging performance.
- **Requirements**:
  - In `poll()`, if `time.time() - self._last_json_dump_time >= 1.0`, trigger a dump.
  - For Shared Memory mode: Pass `shared_memory_obj` through `ctypes_serializer` and `json.dump` to `shm_dump.json`.
  - For UDP mode: Take the current byte streams in `self._packet_buffer` and write them to `udp_dump.json`. For better visibility, also dump the `track_info` and `participants` dictionaries as parsed so far.
  - Ensure any serialization exceptions are caught and logged rather than crashing the tick loop.
