# AMS2 Auto Director V4.0 - Specification

> This specification was reverse-engineered from `AMS2AutoDirector.py` (902 lines, 37KB).
> Review and refine before using for future development.

## Overview

The AMS2 Auto Director V3.0 is a **real-time telemetry-driven broadcast camera controller** for Automobilista 2. It reads live race data (via Shared Memory or UDP), calculates a composite "interest score" for each of the 32 possible participants, and automatically injects keyboard commands (`pyKey`) to switch the in-game camera to the highest-scoring driver at a configurable interval.

The application uses a `tkinter` GUI to display a live leaderboard grid with scoring breakdowns, and provides runtime-tunable parameters via input fields and buttons.

## Clarifications

### Session 2026-05-03
- Q: How should the system determine the current `game_time` to match against replay log timestamps? → A: Read `game_time` from Shared Memory `mCurrentTime` field.
- Q: What should the Director do when AMS2 is not running? → A: Poll silently with "Waiting for AMS2..." status, then display confirmation when connected.
- Q: Which GUI framework for the unified V4.0? → A: tkinter (V4.0 style). GUI must be a thin shell fully abstracted from testable business logic — no tkinter testing.
- Q: Should V4.0 eliminate the pandas dependency? → A: Yes. Remove pandas entirely — use plain dicts and lists for scoring and grid display.
- Q: Should V4.0 keep the UDP data source pathway? → A: Yes. Keep both UDP and Shared Memory for full backwards compatibility.

## Functional Requirements (Existing)

### FR-1: Dual Data Source Ingestion
- **FR-1.1**: Read AMS2 telemetry from the `$pcars2$` shared memory mapped file using `ctypes` and `mmap`.
- **FR-1.2**: Read AMS2 telemetry from UDP packets on a configurable port (default `5606`).
- **FR-1.3**: User selects data source mode at startup via console prompt.
- **FR-1.4**: Shared Memory polled every `200ms`. UDP processed every `1s`.
- **FR-1.5**: Read `game_time` from the `SharedMemory.mCurrentTime` field for synchronising replay log event windows against live telemetry.

### FR-2: Participant Data Extraction
- **FR-2.1**: Extract per-participant fields: Race Position, Is Active, Lap Distance, Current Sector, Current Lap, Fastest/Last Lap Times, Speed, Pit Mode, Flag Colours/Reasons, Race State.
- **FR-2.2**: Calculate **True Distance Traveled** (`laps_completed * track_length + current_lap_distance`).
- **FR-2.3**: Calculate **Gap to Player Ahead** (distance delta between sorted participants by true distance).
- **FR-2.4**: Calculate **Cars Ahead within 250m** (count of active participants within 250m ahead on track).
- **FR-2.5**: Detect track changes and reset all participant data when track info changes.
- **FR-2.6**: Extract driver name from `SharedMemory.mParticipantInfo[i].mName` (decoded UTF-8, null-stripped) for GUI display and logging.

### FR-3: Scoring Engine
- **FR-3.1**: **Pit Mode Penalty** (`-10` if pit mode != 0).
- **FR-3.2**: **Speed Penalty** (`-5` if speed < 5 m/s).
- **FR-3.3**: **Cars Ahead Bonus** (Leader: `count * 2`, Others: `count * 2/5`). Zeroed if in pits.
- **FR-3.4**: **Close Racing Bonus** (`(50 - gap) / 5` if gap is between 0 and 50m).
- **FR-3.5**: **Race Position Bonus** (`FACTOR * (1 - (pos-1)/32)`). Linear decay from P1 to P32.
- **FR-3.6**: **Total Score** = Sum of all components.
- **FR-3.7**: The participant with the highest Total Score is selected as `current_focus_position`.

### FR-4: Camera Control (Auto Director)
- **FR-4.1**: When enabled and the configurable interval elapses, inject key presses using **delta navigation**:
  - Calculate delta = `target_position - current_position`.
  - Press DOWN (delta) times if positive, UP (|delta|) times if negative.
  - Press ENTER to confirm.
  - **Fallback** (if current position is unknown): Scroll UP 32 times to top, then DOWN to `target_position - 1`.
- **FR-4.2**: Key timing: 10ms hold + 10ms gap per stroke.
- **FR-4.3**: Toggle auto director on/off with Spacebar.
- **FR-4.4**: Default interval: `7 seconds` (configurable at startup and via GUI).

### FR-5: GUI (tkinter)
- **FR-5.1**: Dark-themed tkinter UI in the style of the V4.0 prototype, displaying participant data merged with scoring breakdown.
- **FR-5.2**: Race Control panel showing: current focus, auto director status, track length, connection status.
- **FR-5.3**: Runtime-tunable parameters via input fields/buttons.
- **FR-5.4**: Grid updates every `1 second`.
- **FR-5.5**: **Strict GUI Abstraction**: The GUI is a thin rendering shell only. All scoring, telemetry, and camera logic must live in `core/` modules with no tkinter imports. No tkinter unit testing will be performed; all business logic is tested independently.

## Key Entities

> For the full V4.0 entity definitions, field types, and state transitions, see [data-model.md](data-model.md).

| V4.0 Class | Replaces (V3.0 Global) | Description |
|---|---|---|
| `TelemetryProvider.poll()` → `dict[int, dict]` | `participants_data_dict` | Per-participant telemetry keyed by index (0-31) |
| `ScoringEngine.calculate_scores()` → `dict[int, dict]` | `scores_dict` | Per-participant scoring breakdown keyed by index |
| `TelemetryProvider._packet_buffer` | `packet_buffer` | UDP packet ring buffer by packet type |
| `TelemetryProvider._previous_data` | `previous_data_dict` | Rolling distance/timestamp deques for speed calc |
| `SharedMemory` (unchanged) | `SharedMemory` | 363-line ctypes struct for AMS2 telemetry |

## Key Constants

| Constant | Default | Description |
|---|---|---|
| `AUTO_DIRECTOR_INTERVAL` | `7` | Seconds between camera switches |
| `RACE_POSITION_BONUS_FACTOR` | `12` | Weight for race position scoring |
| `PIT_MODE_PENALTY_MULTIPLIER` | `-10` | Penalty applied when driver is in pits |
| `SPEED_PENALTY_MULTIPLIER` | `-5` | Penalty applied when speed < 5 m/s |
| `LEADER_CARS_AHEAD_MULTIPLIER` | `2` | Bonus weight for leader's traffic density |
| `OTHER_CARS_AHEAD_MULTIPLIER` | `2` | Bonus weight for non-leader's traffic density |
| `CLOSE_RACING_BONUS_DIVISOR` | `5` | Divisor for close racing bonus calculation |
| `CLOSE_RACING_MAX_GAP` | `50` | Maximum gap (meters) for close racing bonus |

## Architectural Observations

### Strengths
- The scoring engine is **stateless per-tick**: it recalculates everything from scratch each cycle with no memory of previous scores. This makes it inherently resilient to drift.
- The gap/cars-ahead calculations use true distance traveled (accounting for laps) which correctly handles the start/finish line crossing edge case.
- The GUI is decoupled from the main loop via tkinter's `root.after()`, preventing UI lag from blocking telemetry processing.

### Weaknesses / Technical Debt
- **Global State Everywhere**: 20+ global variables manage state. No classes, no encapsulation.
- **UDP Fallback is Brittle**: The UDP packet parser uses hardcoded byte offsets (e.g., `31 + i * 32 + 16`) with no validation. **Decision: Retain for backwards compatibility but migrate into `core/telemetry_provider.py` with improved structure.**
- **No Driver Names**: The scoring engine works purely by participant index and race position. It never reads `mName` from shared memory, so the GUI cannot display driver names.
- **Scroll-to-Top Every Time**: The `auto_director()` function scrolls UP 32 times before scrolling DOWN to the target. This is wasteful when positions only shift by 1-2 places.
- **`pandas` Dependency**: Heavy use of `pd.DataFrame` for what is essentially a 32-row dictionary. The DataFrame is rebuilt from scratch every second. **Decision: Remove pandas entirely in V4.0. Use plain dicts/lists.**

## Edge Cases & Failure Handling
- **EC-1**: When AMS2 is not running (shared memory unavailable), the Director displays "Waiting for AMS2..." in the GUI status panel and polls silently every 200ms. When the connection is established, the status updates to confirm the connection (e.g., "Connected to AMS2").
- **EC-2**: If AMS2 disconnects mid-session (shared memory becomes invalid), the Director reverts to "Waiting for AMS2..." status and suspends camera control until reconnection.
