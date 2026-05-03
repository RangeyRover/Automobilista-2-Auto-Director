# AMS2 Auto Director V3.0 (Live Engine) - Technical Plan (Migrated)

## Current Architecture

`AMS2AutoDirector.py` is a **902-line monolithic script** with zero classes. All state is managed via ~20 global variables. The program flow is:

```
┌──────────────────────────────────────────────────────────┐
│ Startup (Console Prompts: Mode, Interval, Bonus Factor)  │
└────────────────────────┬─────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
  │  UDP Thread  │ │  GUI Thread │ │   Main Loop     │
  │ listen_udp() │ │start_wx_app │ │  (while True)   │
  └──────┬───────┘ └──────┬──────┘ └───────┬─────────┘
         │                │                │
         │  packet_buffer │  wx.CallAfter  │
         └────────┬───────┘    ▲           │
                  │            │           │
                  ▼            │           ▼
         ┌────────────────┐    │   ┌───────────────────┐
         │ process_packets│    │   │ read_shared_memory │
         │ (UDP decode)   │    │   │ (ctypes mmap)      │
         └────────┬───────┘    │   └───────┬───────────┘
                  │            │           │
                  ▼            │           ▼
         ┌─────────────────────────────────────┐
         │    update_participants_data_dict()    │
         │    (True Distance, Gaps, Cars Ahead) │
         └──────────────────┬──────────────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │   next_focus(df)   │
                  │ (Score Calculation)│
                  └─────────┬─────────┘
                            │
                            ▼
                  ┌───────────────────┐
                  │  auto_director()   │
                  │ (pyKey Injection)  │
                  └───────────────────┘
```

## Technology Stack
- **Language**: Python 3.x
- **GUI**: wxPython (`wx`, `wx.grid`)
- **Data**: pandas DataFrame (rebuilt every tick)
- **Input Injection**: pyKey (`pressKey`, `releaseKey`)
- **Telemetry**: ctypes shared memory (`$pcars2$`), UDP socket
- **Threading**: `threading.Thread` for UDP listener and wxPython event loop
- **Keyboard**: `keyboard` library for spacebar hotkey

## Component Map (Strangler Extraction Targets)

### Component A: Telemetry Provider (Lines 95–402)
**Responsibility**: Read raw data from Shared Memory or UDP and produce a normalized `participants_data_dict`.

| Function | Lines | Role |
|---|---|---|
| `read_shared_memory()` | 95–110 | Open mmap, read ctypes struct |
| `update_participants_data_dict()` | 112–214 | Extract fields from SharedMemory struct, calculate True Distance, Gaps, Cars Ahead |
| `process_packets()` | 251–379 | Decode UDP packets into equivalent dict |
| `decode_track_info_packet()` | 381–401 | Parse 308-byte track info UDP packet |
| `parse_race_position()` | 406–410 | Bit manipulation: position & active flag |
| `parse_lap_distance()` | 412–415 | 2-byte little-endian distance |
| `parse_current_sector()` | 417–420 | 4-bit sector extraction |
| `parse_current_lap()` | 422–424 | Raw byte to lap number |
| `parse_pit_mode_schedule()` | 426–429 | 3-bit pit mode + 2-bit schedule |
| `parse_race_state()` | 431–432 | 3-bit race state extraction |
| `initialize_previous_data()` | 223–231 | Reset speed-tracking deques |
| `calculate_speed()` | 233–249 | Delta distance / delta time with S/F crossing |

### Component B: Scoring Engine (Lines 434–545)
**Responsibility**: Take a DataFrame of participant data and calculate composite scores.

| Function | Lines | Role |
|---|---|---|
| `next_focus(df)` | 434–545 | Calculate all scoring components, determine highest-scoring participant |

### Component C: Camera Controller (Lines 548–583)
**Responsibility**: Translate a target race position into physical keyboard inputs.

| Function | Lines | Role |
|---|---|---|
| `auto_director()` | 548–583 | Scroll to top, scroll down to target, press ENTER |

### Component D: GUI (Lines 586–768)
**Responsibility**: wxPython application with grid display and runtime controls.

| Function | Lines | Role |
|---|---|---|
| `populate_grid_from_df()` | 586–664 | Merge scores into DataFrame and render to grid |
| `start_wx_app()` | 668–768 | Build wxPython frame, grid, and controls |
| `add_control()` | 699–720 | Dynamic ▲/▼ button factory for globals |

### Component E: Main Loop (Lines 838–901)
**Responsibility**: Orchestration loop polling telemetry, triggering scoring, and firing camera switches.

| Section | Lines | Role |
|---|---|---|
| Main `while True` | 838–901 | Poll SM/UDP → build DF → update grid → score → auto_director |
| Spacebar toggle | 889–892 | `keyboard.is_pressed('space')` toggle |
