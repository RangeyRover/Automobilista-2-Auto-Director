# Unified Score-Based Director - Specification (Migrated)

> This specification was auto-generated from existing code during the V4.0 Migration.
> Review and refine before using for future development.

## Overview
The codebase currently contains two disparate monolithic scripts:
1. `AMS2AutoDirector.py` (V3.0): A live heuristic engine that evaluates telemetry (gaps, speed, position) and dynamically scores drivers to identify close battles in real-time.
2. `ReplayAutoDirector4.py` (V4.0 prototype): A replay-driven engine that parses static race logs to build a rigid "Threat Timeline" and schedules camera changes mechanically.

## Functional Requirements (Existing)
- Parse AMS2 Shared Memory telemetry.
- Inject `pyKey` keyboard commands to navigate the AMS2 broadcast UI (UP/DOWN/ENTER).
- Calculate live telemetry scores (Pit Mode Penalty, Speed Penalty, Cars Ahead Bonus, Close Racing Bonus, Race Position Bonus).
- Parse race analyser logs (Accidents, Overtakes).

## Identified Gaps for V4.0 Target
The current scripts are monolithic and conceptually separated. The target architecture requires them to be unified into a single Score-Based Engine where replay events (Overtakes, Accidents) act as temporary (+/- 8s) score multipliers injected into the live heuristic loop.
