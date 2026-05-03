# Unified Score-Based Director - Technical Plan (Migrated)

## Current Architecture
The `AMS2_Auto_Director4.0` directory contains the two monolithic source files representing the previous disparate architectural approaches:
- `AMS2AutoDirector.py` (37KB): Handles Shared Memory, UDP fallbacks, `wxPython` GUI, and continuous real-time score evaluations based on telemetry.
- `ReplayAutoDirector4.py` (48KB): Handles `tkinter` GUI, absolute delta camera positioning, Regex parsing of `race_analyser` logs, and strict Timeline execution.

## Technology Stack
- **Language**: Python 3.x
- **UI Framework**: Transitioning from `wxPython` (V3.0) / `tkinter` (V4.0) to a unified standard (likely `tkinter` as used in V4.0).
- **Interfacing**: `pyKey` (keyboard injection), `ctypes` (memory mapping AMS2 shared memory).

## Component Map (Strangler Target)
To execute the Strangler Refactor safely, we will extract functional blocks into the following architecture:
1. `core/telemetry_scorer.py`: Extracted from `AMS2AutoDirector.py` (Live gap/speed calculations).
2. `core/replay_enhancer.py`: Extracted from `ReplayAutoDirector4.py` (Log file regex parsing and +/- 8s enhancement logic).
3. `core/camera_director.py`: Extracted from both (Delta positioning, pyKey injection).
4. `main.py`: The unified UI and application loop.
