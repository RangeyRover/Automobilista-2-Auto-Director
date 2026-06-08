# Implementation Plan: Trim Future Spline Points on Resync and Rewind

**Branch**: `016-trim-future-spline-points` | **Date**: 2026-06-08 | **Spec**: [spec.md](file:///c:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/specs/016-trim-future-spline-points/spec.md)
**Input**: Feature specification from `/specs/016-trim-future-spline-points/spec.md`

## Summary

The technical goal is to implement spline timestamp trimming in `DistanceTimeSpline` whenever the master clock is rewound (replay rewind) or resynced (flywheel recovery). This prevents future-dated timestamps from remaining in the leader spline and causing empty gaps on the HTML overlay.

We will achieve this by:
1. Adding a `trim_future_points(current_time)` method to the `DistanceTimeSpline` class.
2. Invoking this method from the `TelemetryProvider` when the flywheel resyncs (`_flywheel.did_resync` is True) or when `stable_time` jumps backward.
3. Adding rigorous pytest unit tests covering both the spline class changes and the provider-level logic.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: None (stdib bisect)  
**Storage**: In-memory spline lists (`self.distances` and `self.times`)  
**Testing**: pytest  
**Target Platform**: Windows Local PC  
**Project Type**: single  
**Performance Goals**: Spline trimming execution latency <1ms per tick  
**Constraints**: None  
**Scale/Scope**: Up to 32 drivers, max 5000 spline points per driver  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No constitution file exists (`.specify/memory/constitution.md` is missing). Gate passed.

## Project Structure

### Documentation (this feature)

```text
specs/016-trim-future-spline-points/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
└── quickstart.md        # Phase 1 output (/speckit.plan command)
```

### Source Code

```text
core/
├── telemetry_provider.py    # Trigger trim on resync or rewind
├── spline.py                # Add trim_future_points method

tests/
├── test_spline.py           # Unit tests for trim_future_points
└── test_physics_flywheel.py # Existing tests (regression verify)
```

**Structure Decision**: Single project layout matching the existing repository structure.

## Complexity Tracking

No violations.
