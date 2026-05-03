# Unified Score-Based Director - Tasks (Migrated)

All tasks marked [x] represent existing implemented functionality spread across the monoliths.
Tasks marked [ ] are identified gaps required to complete the Strangler Refactor and V4.0 logic.

## Existing Implementation
- [x] Shared Memory Telemetry Extraction (Implemented in both monoliths)
- [x] Base Live Scoring Heuristics (Gap, Speed, Position, Cars Ahead) - Implemented in `AMS2AutoDirector.py`
- [x] Replay Log Regex Parsing (Accidents, Overtakes, Finish Sweeps) - Implemented in `ReplayAutoDirector4.py`
- [x] PyKey Absolute Delta Camera Injection - Implemented in `ReplayAutoDirector4.py`
- [x] Tkinter User Interface Layouts - Implemented in `ReplayAutoDirector4.py`

## Identified Gaps (Strangler Refactor)
- [ ] Create `core/telemetry_scorer.py` and migrate the `AMS2AutoDirector.py` scoring logic into an isolated, testable class.
- [ ] Create `core/replay_enhancer.py` and migrate the Log Parsing logic. Implement the new +/- 8s enhancement window algorithm.
- [ ] Create `core/camera_director.py` and migrate the delta navigation and debounce logic.
- [ ] Create `main.py` UI and wire the `telemetry_scorer` and `replay_enhancer` together to produce a single, unified scoreboard.
- [ ] Integrate Test-Driven Development (TDD) tests for the new `replay_enhancer` +/- 8s windowing math.
