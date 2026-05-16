# Implementation Plan: Per-Car Spline Logic for Leaderboard Gaps

**Branch**: `1-fix-leaderboard-spline` | **Date**: 2026-05-16 | **Spec**: `specs/1-fix-leaderboard-spline/spec.md`

## Summary

The Auto Director's leaderboard logic currently tracks a single global spline of the "furthest distance achieved" to calculate time gaps. This causes massive gap errors when the leader crashes, pits, or is overtaken. This plan resolves the issue by replacing the global spline with a per-car spline dictionary (`self._car_splines`). To find a follower's gap, their current `true_distance` is queried against the *current leader's* individual physical history spline.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: None (Standard Library)
**Storage**: N/A  
**Testing**: `unittest` or `pytest` 
**Target Platform**: Windows (Desktop App)
**Project Type**: Single Desktop App
**Performance Goals**: `_calc_live_time_gaps` must execute within ~1ms for 32 cars to avoid blocking the 60Hz loop.
**Constraints**: Array memory limits per spline (~5000 points max).
**Scale/Scope**: O(N) lookup against a 5000-length sorted array (using binary search), scaled to 32 cars.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
No constitutional violations. The feature operates exclusively within the established `telemetry_provider.py` module and respects existing boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/1-fix-leaderboard-spline/
├── plan.md              # This file
├── spec.md              # Feature specification
└── tasks.md             # Tasks for implementation
```

### Source Code

```text
AMS2_Auto_Director4.0/
├── core/
│   └── telemetry_provider.py
└── test_spline_gaps.py
```

**Structure Decision**: A single new test file `test_spline_gaps.py` is created at the repository root to validate the logic changes in `core/telemetry_provider.py`.

## Complexity Tracking

N/A
