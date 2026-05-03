# AMS2 Auto Director V3.0 (Live Engine) - Tasks (Migrated)

All tasks marked [x] represent existing implemented functionality.
Tasks marked [ ] are inferred gaps or TODOs found in code.

## Existing Implementation

### Telemetry Provider
- [x] Shared Memory reader via `ctypes`/`mmap` - Lines 95–110
- [x] UDP packet listener on configurable port - Lines 790–815
- [x] UDP packet buffer with single-packet retention - Lines 817–825
- [x] Track info packet decoder (308-byte) - Lines 381–401
- [x] Extended packet parser (byte-offset extraction for 32 participants) - Lines 284–329
- [x] Bit-level parsers: race position, lap distance, sector, lap, pit mode, race state - Lines 406–432
- [x] True Distance Traveled calculation (laps * track_length + lap_distance) - Lines 144–152 (SM), 323–329 (UDP)
- [x] Gap to Player Ahead calculation (sorted true distance delta) - Lines 173–187 (SM), 335–344 (UDP)
- [x] Cars Ahead within 250m calculation (with S/F line wrapping) - Lines 154–171 (SM), 346–368 (UDP)
- [x] Speed calculation from distance/timestamp delta pairs - Lines 233–249
- [x] Track change detection and participant data reset - Lines 127–130 (SM), 265–274 (UDP)
- [x] Participant data dict update for active participants - Lines 189–211

### Scoring Engine
- [x] Pit Mode Penalty (-10 if in pits) - Lines 472–474
- [x] Speed Penalty (-5 if < 5 m/s) - Lines 476–478
- [x] Cars Ahead Bonus (Leader: count*2, Others: count*2/5) - Lines 480–488
- [x] Close Racing Bonus ((50-gap)/5 if gap in 0–50m) - Lines 490–496
- [x] Race Position Bonus (linear decay from P1 to P32) - Lines 498–510
- [x] Total Score aggregation - Lines 512–528
- [x] Highest-score participant selection as focus target - Lines 531–545

### Camera Controller
- [x] Scroll-to-top (32x UP) then scroll-down-to-target pattern - Lines 558–579
- [x] Key timing: 5ms hold + 5ms gap - Lines 564–574
- [x] ENTER key to confirm selection - Lines 577–579
- [x] Position 0 fallback to position 4 - Lines 555–556

### GUI (wxPython)
- [x] Dark-themed grid with alternating row colours - Lines 640–653
- [x] Score dict merged into DataFrame for display - Lines 594–609
- [x] Race Control status panel (focus, AD status, track length) - Lines 655–664
- [x] Runtime parameter controls via ▲/▼ buttons (7 parameters) - Lines 698–729
- [x] High DPI awareness for Windows - Lines 670–682
- [x] Clean shutdown via on_close handler (`os._exit(0)`) - Lines 758–760

### Main Loop
- [x] Shared Memory polling at 200ms - Lines 849–855
- [x] UDP processing at 1s interval - Lines 842–847
- [x] Grid update at 1s interval via wx.CallAfter - Lines 857–881
- [x] Auto Director firing at configurable interval - Lines 883–886
- [x] Spacebar toggle with 500ms debounce - Lines 889–892

## Identified Gaps

### Critical for V4.0 Strangler Refactor
- [ ] **Extract Telemetry Provider** into `core/telemetry_provider.py` as a class with `.poll()` method
- [ ] **Extract Scoring Engine** into `core/scoring_engine.py` as a stateless class with `.calculate_scores(participants_dict)` method
- [ ] **Extract Camera Controller** into `core/camera_controller.py` as a class with `.move_to_position(target_pos, current_pos)` method
- [ ] **Eliminate global state**: Convert all 20+ globals into class instance variables
- [ ] **Remove pandas dependency**: Replace DataFrame with plain dict operations for the scoring loop
- [ ] **Add driver names**: Read `mName` from `SharedMemory.mParticipantInfo[i].mName` and display in GUI
- [ ] **Delta-based camera movement**: Replace scroll-to-top pattern with mathematical delta (target_pos - current_pos)

### Testing
- [ ] Unit tests for scoring engine (isolated from telemetry)
- [ ] Unit tests for gap/cars-ahead calculations
- [ ] Unit tests for byte-level UDP parsers

### Code Quality
- [ ] Remove commented-out debug print statements (30+ instances)
- [ ] Handle edge case: `track_length` is `None` when speed calculation divides by zero
- [ ] Fix: UDP `listen_udp()` prints "port in use" error in `finally` block even on clean shutdown
