# Implementation Plan: Raw JSON Telemetry Dumps

**Branch**: `feature/9-raw-json-telemetry` | **Date**: 2026-05-12 | **Spec**: `/specs/9-raw-json-telemetry/spec.md`
**Input**: Feature specification from `/specs/9-raw-json-telemetry/spec.md`

## Summary

Implement a diagnostic feature that dumps raw telemetry data (Shared Memory and UDP packets) to static JSON snapshot files (`shm_dump.json`, `udp_dump.json`) every 1 second when active. This will provide complete visibility into the raw structures and nested fields to aid in debugging hybrid telemetry sync issues without creating infinitely growing logs.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Standard library (`json`, `ctypes`, `time`), existing `core.telemetry_provider`
**Storage**: Local JSON files (static snapshots overwritten every second)
**Testing**: `pytest` for unit testing the serializer logic
**Target Platform**: Windows
**Project Type**: Single desktop application (AMS2 Auto Director)
**Performance Goals**: Serialization to JSON should not noticeably degrade the 60Hz tick loop
**Constraints**: Deeply nested `ctypes` objects and byte arrays must be safely serialized without throwing TypeErrors
**Scale/Scope**: ~2 small snapshot files updated 1x/sec

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No complex architecture violations. Implementation fits securely into the existing telemetry/diagnostics pipeline.

## Project Structure

### Documentation (this feature)

```text
specs/9-raw-json-telemetry/
├── plan.md              # This file
├── research.md          # Skipping (No unknowns)
├── data-model.md        # Skipping (No DB models/APIs)
├── quickstart.md        # Skipping (Internal diagnostic tool)
└── tasks.md             # To be created
```

### Source Code (repository root)

```text
src/
├── core/
│   ├── telemetry_provider.py    # Trigger the dump conditionally during poll()
│   ├── utils/
│   │   └── ctypes_serializer.py # New recursive serializer for structs
└── dashboard/
    └── bridge.py                # No changes needed
```

**Structure Decision**: Added a generic `ctypes_serializer` to handle the recursive expansion of `ctypes` fields (bytes, arrays, structs) into dictionaries so `json.dump` can safely serialize the Shared Memory and UDP structures. The `telemetry_provider` will use this serializer conditionally on a 1-second timer.
