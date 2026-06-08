# Implementation Plan: Standalone Server Flywheel Pitstop Times

**Branch**: `018-fix-pitstop-times` | **Date**: 2026-06-08 | **Spec**: [spec.md](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/specs/018-fix-pitstop-times/spec.md)
**Input**: Feature specification from `/specs/018-fix-pitstop-times/spec.md`

## Summary

The goal of this feature is to stabilize pitstop times (`_pit_time`) in the standalone SHM leaderboard server (`tools/shm_leaderboard_server.py`). Currently, `_pit_time` is calculated using raw `mCurrentTime` from shared memory directly inside the participant correlation loop. This loop runs *before* `mCurrentTime` is stabilized by the `PhysicsFlywheel`. As a result, any camera switch or raw game time jumps instantly cause `_pit_time` to jump up and down.

The proposed solution will refactor `correlate_drivers` to run the `PhysicsFlywheel` process first, obtaining a stabilized `current_time` master clock. The `_pit_time` calculations for all drivers will then be calculated in the downstream loop using this stabilized clock, eliminating all telemetry-induced jumps.

---

## Technical Context

- **Language/Version**: Python 3.13  
- **Primary Dependencies**: ctypes, websockets, asyncio, pytest  
- **Storage**: N/A  
- **Testing**: pytest  
- **Target Platform**: Windows 10/11  
- **Project Type**: Single python project  
- **Performance Goals**: Standalone WS server broadcasts stable telemetry at its native loop frequency without timing fluctuations during anomalies.  
- **Constraints**: Maintain absolute backward compatibility with existing tests that initialize the `pit_entry_times` dictionary with flat float values.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Gate 1: Backward Compatibility**: Must not break existing unit tests in `test_shm_dump_tool.py` that verify flat dict entries in `pit_entry_times`. *Status: Passed.*
- **Gate 2: Core State Safety**: Do not modify shared memory structures or add stateful dependencies to pure correlation functions. *Status: Passed.*

---

## Project Structure

### Documentation (this feature)

```text
specs/018-fix-pitstop-times/
├── spec.md              # Feature specification
├── plan.md              # This file (Implementation Plan)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
└── quickstart.md        # Phase 1 output (/speckit.plan command)
```

### Source Code

```text
core/
├── physics_flywheel.py
├── spline.py
└── shm_serialiser.py

tools/
└── shm_leaderboard_server.py  # WILL MODIFY: Defer _pit_time calculation to stabilized pass

tests/
├── test_shm_dump_tool.py      # WILL MODIFY: Add regression checks for stabilized pitstop timings
└── test_pit_tracker.py
```

**Structure Decision**: Single Python project structure. The modifications are isolated to [shm_leaderboard_server.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tools/shm_leaderboard_server.py) and test verifications.

---

## TDD Testing Strategy (TDD - Tests Before Code)

We follow a strict Test-Driven Development (TDD) approach. All test cases must be written and run to demonstrate failure (RED) before any production code is modified.

### 1. Standalone Server Pitstop Verification (User Story 1)
- **File**: [test_shm_dump_tool.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_shm_dump_tool.py)
- **Test Case**: `test_correlate_drivers_stabilized_pit_time`
- **Method**: Mock raw `mCurrentTime` with a large timing jump (e.g. 40 seconds) but feed a stabilized flywheel to the correlation engine. Assert that the returned `_pit_time` follows the flywheel's stabilized clock, rather than the raw `mCurrentTime`.
- **Validation**: Ensure this test fails on current code, then passes after implementation.

### 2. Main App Pit Tracker Verification (User Story 2)
- **File**: [test_pit_tracker.py](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_pit_tracker.py)
- **Test Case**: `test_pit_tracker_uses_stabilized_clock`
- **Method**: Run a simulation where game time has timing snaps. Assert that the `PitTracker.update` method receives the stabilized time, and verifies the duration calculations don't fluctuate.
