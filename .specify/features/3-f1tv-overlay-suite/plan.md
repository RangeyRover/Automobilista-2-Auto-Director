# Implementation Plan: F1TV Overlay Suite

**Branch**: `feature/3-f1tv-overlay-suite` | **Date**: 2026-05-08 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `.specify/features/3-f1tv-overlay-suite/spec.md`

## Summary

Convert 15 F1TV SimHub dashboard overlays into a monolithic HTML overlay page driven by the Auto Director's WebSocket bridge. The bridge must be extended to parse additional UDP packet types (`sTelemetryData`, `sRaceData`, `sGameStateData`, `sTimeStatsData`, `sParticipantsData`) and expose viewed-car telemetry, weather, per-driver timing stats, pit events, and director camera state. The HTML overlay connects via WebSocket and renders as an OBS Browser Source at 1920×1080 with transparent background.

**Primary data source for viewed-car telemetry**: UDP packets (via `SMS_UDP_Definitions_AMS2_RR.hpp` — the RangeyRover-modified spec is authoritative). SharedMemory fields for brake/throttle/damage/tyres don't reliably follow viewed-car changes; UDP `sTelemetryData` does.

**Primary data source for global/per-participant data**: SharedMemory is preferred for session info (track name, world fastest times, enforced pit stop), weather (temps, rain, wind), and per-participant timing arrays (`mCurrentSector1/2/3Times[64]`, `mFastestSector1/2/3Times[64]`, `mFastestLapTimes[64]`, `mLastLapTimes[64]`). These are global fields that don't depend on viewed-car tracking. UDP used as fallback when SharedMemory is unavailable.

## Technical Context

**Language/Version**: Python 3.13 (bridge), HTML/CSS/JS (overlay)  
**Primary Dependencies**: `websockets`, `asyncio`, `struct` (bridge); Vanilla JS (overlay)  
**Storage**: N/A (in-memory state + static JSON lookup file)  
**Testing**: pytest (bridge unit tests with mock UDP packets)  
**Target Platform**: Windows 11, AMS2 UDP protocol, OBS Browser Source  
**Project Type**: Single project — extension of existing `dashboard/` module  
**Performance Goals**: Bridge ~60Hz broadcast, overlay 60fps render in OBS  
**Constraints**: Must not break existing bridge WebSocket consumers (`timing.html`, `now_watching.html`)  
**Scale/Scope**: 15 overlay components, 6 UDP packet types, 1 static lookup file

## Constitution Check

No constitution file exists. Gate passed by default.

## Research Summary

### Data Source Decision: Hybrid (UDP for viewed car, SharedMemory for global/per-participant)

**Decision**: Use UDP `sTelemetryData` for viewed-car telemetry fields only. Use SharedMemory as the primary source for all global session data, weather, and per-participant timing arrays.
**Rationale**: SharedMemory fields like `mBrake`, `mThrottle`, `mAeroDamage`, `mTyreWear` are viewed-car-specific and don't reliably update when the camera switches. UDP `sTelemetryData` (556 bytes) does track view changes. However, SharedMemory's global fields (`mWorldFastestLapTime`, `mAmbientTemperature`, etc.) and per-participant arrays (`mCurrentSector1/2/3Times[64]`, `mFastestLapTimes[64]`, etc.) are stable and provide MORE data than UDP — notably, SharedMemory has **current-lap sector breakdowns** (`mCurrentSector1/2/3Times[64]`) for all 64 participants, which UDP `sTimeStatsData` does not.
**Alternatives**: UDP-only — rejected because it lacks current-lap sector time arrays. SharedMemory-only — rejected because viewed-car fields are unreliable.

### UDP Packet Map (from `SMS_UDP_Definitions_AMS2_RR.hpp`)

| Packet | Size | Type ID | Already Parsed | New Fields Needed | Preferred Source |
|---|---|---|---|---|---|
| `sTelemetryData` | 556 | 0 | ✅ speed@36, rpm@40, gear@45, viewedIndex@12 | brake@29, throttle@30, maxRpm@42, numGears@45>>4, crashState@47, aeroDamage@371, engineDamage@372, suspDamage@204-207, brakeDamage@200-203, tyreWear@196-199, tyreCompound@378-537 | **UDP only** (viewed car) |
| `sRaceData` | 308 | 1 | ✅ trackLength@44, lapsTimeInEvent@304 | worldFastestLap@12, worldFastestSectors@32/36/40, trackLocation@48, trackVariation@112, enforcedPitStopLap@306 | **SharedMemory preferred** (global) |
| `sParticipantsData` | 1136 | 2 | ✅ names@16 | | SharedMemory preferred (`mNationalities`) |
| `sTimingsData` | 1063 | 3 | ✅ eventTimeRemaining@17, splitAhead@21, splitBehind@25, per-participant data@31 | No new fields | UDP (already parsed) |
| `sGameStateData` | 24 | 4 | ✅ gameState@14 | ambientTemp@16(int8), trackTemp@17(int8), rainDensity@18(uint8), snowDensity@19(uint8), windSpeed@20(int8) | **SharedMemory preferred** (global) |
| `sTimeStatsData` | 1040 | 7 | ⚠️ Partially (last_lap only for viewed) | Full parse: per-participant fastestLap, lastLap, lastSectorTime, fastestSectors | **SharedMemory preferred** (has current sector times too) |
| `sParticipantVehicleNamesData` | 1164 | 8 | ❌ Not parsed | | SharedMemory preferred (`mCarNames`) |
| `sVehicleClassNamesData` | 1452 | 8 (last) | ❌ Not parsed | | SharedMemory preferred (`mCarClassNames`) |

**SharedMemory-only fields (not available via UDP):**

| Field | SHM Offset | Size | Notes |
|---|---|---|---|
| `mCurrentSector1Times[64]` | 7408 | 256 (float×64) | **Current lap** S1 split for all participants |
| `mCurrentSector2Times[64]` | 7664 | 256 (float×64) | **Current lap** S2 split for all participants |
| `mCurrentSector3Times[64]` | 7920 | 256 (float×64) | **Current lap** S3 split for all participants |
| `mFastestSector1Times[64]` | 8176 | 256 (float×64) | Best S1 for all participants |
| `mFastestSector2Times[64]` | 8432 | 256 (float×64) | Best S2 for all participants |
| `mFastestSector3Times[64]` | 8688 | 256 (float×64) | Best S3 for all participants |
| `mFastestLapTimes[64]` | 8944 | 256 (float×64) | Best lap for all participants |
| `mLastLapTimes[64]` | 9200 | 256 (float×64) | Last lap for all participants |
| `mWorldFastestLapTime` | 6748 | 4 (float) | Session fastest lap |
| `mWorldFastestSector1/2/3Time` | 6788-6796 | 12 (float×3) | Session fastest sectors |
| `mAmbientTemperature` | 7292 | 4 (float) | Current ambient temp |
| `mTrackTemperature` | 7296 | 4 (float) | Current track temp |
| `mRainDensity` | 7300 | 4 (float) | 0.0–1.0 |
| `mWindSpeed` | 7304 | 4 (float) | m/s |
| `mSnowDensity` | 20572 | 4 (float) | 0.0–1.0 |
| `mEnforcedPitStopLap` | 19248 | 4 (int) | Mandatory pit window lap |
| `mNationalities[64]` | | 256 (uint32×64) | Driver nationalities |
| `mCarNames[64]` | | 4096 (char[64]×64)| Driver car names |
| `mCarClassNames[64]` | | 4096 (char[64]×64)| Driver car class names |

### Camera Type Inference

**Decision**: Track camera type internally based on the last key press command sent by the Auto Director.  
**Rationale**: AMS2 does not expose camera type in telemetry. The Auto Director already sends camera switch commands via `CameraController`, so we can infer the current camera set.  
**Limitation**: Only accurate when auto-directing. When the user manually controls the camera, defaults to `"tv_cam"`.

### Fonts

**Decision**: Serve F1TV fonts from `dashboard/_SHFonts/` directory via the existing bridge HTTP server.  
**Rationale**: Simplest approach — the bridge already serves static files from `dashboard/`. No base64 embedding needed.

## Project Structure

### Documentation (this feature)

```text
.specify/features/3-f1tv-overlay-suite/
├── spec.md              # Feature specification
├── plan.md              # This file
├── data-model.md        # Data model additions
└── tasks.md             # Generated by /speckit.tasks
```

### Source Code (repository root)

```text
dashboard/
├── bridge.py                # MODIFY: parse new UDP packets, add behind/weather/damage/pit/director state
├── f1tv_overlay.html        # NEW: monolithic overlay page (all 15 overlays)
├── team_lookup.json         # NEW: static car class → team identity mapping
├── _SHFonts/                # EXISTING: F1TV fonts (already present, served by bridge HTTP)
├── timing.html              # NO CHANGE (existing overlay)
├── now_watching.html         # NO CHANGE (existing overlay)
└── UI1.png                  # NO CHANGE (existing asset)

core/
├── camera_controller.py     # MODIFY: add camera_type tracking property
├── telemetry_provider.py    # MODIFY: parse nationality from 1136-byte packet, parse vehicle names from 1164/1452-byte packets
└── scoring_engine.py        # NO CHANGE

tests/
├── test_bridge_udp.py       # NEW: unit tests for bridge UDP parsing
└── ...                      # NO CHANGE to existing test files

main.py                      # MODIFY: pass camera_type from camera_controller to bridge
```

**Structure Decision**: Single project. Bridge extension is the largest change (~200 lines). Overlay HTML is a single self-contained file. One new test file for bridge UDP parsing. Three existing files modified.

## Detailed Design

### Phase 1: Bridge Extensions (`bridge.py`)

#### 1.1 Parse 556-byte `sTelemetryData` — Extended Fields

Currently parsed: `viewedIndex@12`, `speed@36`, `rpm@40`, `gear@45`.  
Add parsing for:

```python
# Viewed car extended telemetry (556-byte packet)
state["viewed"]["brake"] = p556[29] / 255.0          # uint8 → 0.0-1.0
state["viewed"]["throttle"] = p556[30] / 255.0        # uint8 → 0.0-1.0
state["viewed"]["max_rpm"] = struct.unpack_from('<H', p556, 42)[0]
state["viewed"]["num_gears"] = (p556[45] >> 4) & 0x0F
state["viewed"]["crash_state"] = p556[47]
state["viewed"]["aero_damage"] = p556[371] / 255.0
state["viewed"]["engine_damage"] = p556[372] / 255.0
state["viewed"]["suspension_damage"] = [p556[204+i] / 255.0 for i in range(4)]  # FL,FR,RL,RR
state["viewed"]["brake_damage"] = [p556[200+i] / 255.0 for i in range(4)]
state["viewed"]["tyre_wear"] = [p556[196+i] / 255.0 for i in range(4)]

# Tyre compound: 4 strings of 40 chars each starting at offset 378
compounds = []
for i in range(4):
    raw = p556[378 + i*40 : 378 + (i+1)*40]
    compounds.append(raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip())
state["viewed"]["tyre_compound"] = compounds
```

#### 1.2 Session Data — SharedMemory Preferred (UDP `sRaceData` Fallback)

Primary source: SharedMemory global fields. These don't depend on viewed-car tracking.

```python
# Session fastest times and track info (from SharedMemory)
shm = self.main_app._shm
if shm is not None:
    state["session"]["world_fastest_lap"] = getattr(shm, 'mWorldFastestLapTime', 0.0)
    state["session"]["world_fastest_sectors"] = [
        getattr(shm, 'mWorldFastestSector1Time', 0.0),
        getattr(shm, 'mWorldFastestSector2Time', 0.0),
        getattr(shm, 'mWorldFastestSector3Time', 0.0),
    ]
    track_raw = getattr(shm, 'mTranslatedTrackLocation', b'')
    state["session"]["track_name"] = track_raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
    track_var = getattr(shm, 'mTranslatedTrackVariation', b'')
    state["session"]["track_variation"] = track_var.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
    state["session"]["enforced_pit_stop_lap"] = getattr(shm, 'mEnforcedPitStopLap', -1)
```

Fallback: parse 308-byte UDP `sRaceData` if SharedMemory is unavailable.

#### 1.3 Weather — SharedMemory Preferred (UDP `sGameStateData` Fallback)

Primary source: SharedMemory global fields.

```python
# Weather (from SharedMemory)
if shm is not None:
    state["weather"] = {
        "ambient_temp": getattr(shm, 'mAmbientTemperature', 0.0),
        "track_temp": getattr(shm, 'mTrackTemperature', 0.0),
        "rain_density": getattr(shm, 'mRainDensity', 0.0),
        "snow_density": getattr(shm, 'mSnowDensity', 0.0),
        "wind_speed": getattr(shm, 'mWindSpeed', 0.0),
    }
```

Fallback: parse 24-byte UDP `sGameStateData` (int8/uint8 values at offsets 16-20).

#### 1.4 Per-Driver Timing Stats — SharedMemory Preferred (UDP `sTimeStatsData` Fallback)

Primary source: SharedMemory per-participant arrays (64 participants, float each).

```python
# Per-participant timing stats (from SharedMemory)
if shm is not None:
    for i in range(64):
        time_stats[i] = {
            "fastest_lap": shm.mFastestLapTimes[i],
            "last_lap": shm.mLastLapTimes[i],
            "current_sector1": shm.mCurrentSector1Times[i],  # Current lap S1
            "current_sector2": shm.mCurrentSector2Times[i],  # Current lap S2
            "current_sector3": shm.mCurrentSector3Times[i],  # Current lap S3
            "fastest_sector1": shm.mFastestSector1Times[i],
            "fastest_sector2": shm.mFastestSector2Times[i],
            "fastest_sector3": shm.mFastestSector3Times[i],
        }
```

The `mCurrentSector1/2/3Times[64]` arrays are **SharedMemory-only** — UDP `sTimeStatsData` does not provide current-lap sector breakdowns, only `lastSectorTime` (the most recent sector crossing).

Fallback: parse 1040-byte UDP `sTimeStatsData` for fastest_lap, last_lap, and fastest_sectors (but NOT current sector times).

#### 1.5 Per-Driver Nationality, Car Name, Car Class — SharedMemory

Primary source: SharedMemory arrays `mNationalities`, `mCarNames`, `mCarClassNames`.
These are available directly in SHM and are much easier to access than parsing the 1136, 1164, and 1452-byte UDP packets.

```python
if shm is not None:
    for i in range(64):
        # Update leaderboard entries with these fields
        pass
```

#### 1.7 New `behind` Object

Mirror the existing `ahead` logic. Find the driver directly behind the viewed participant by race position and compute gap.

#### 1.8 Pit Timer State Machine

New class or internal dict tracking pit events:

```python
# pit_tracker: dict[int, dict] keyed by participant index
# States: NONE → ENTERING (pit_mode 1) → IN_PIT (pit_mode 2) → EXITING (pit_mode 3) → NONE (pit_mode 0)
# Record entry_time when transitioning 0→1, record exit_time when transitioning 3→0
# Calculate duration = exit_time - entry_time
#
# Also track per-driver:
#   pit_count: int — total pit stops completed this session
#   last_pit_lap: int — lap number of last pit entry
#   laps_since_last_pit: int — current_lap - last_pit_lap (calculated per tick)
```

Expose as `state["pit_events"]` — a list of recent pit events with driver name, duration, pit count, laps since last pit, and whether still in progress.

#### 1.9 Director Camera State

Read from `CameraController.current_camera_type` property (added in Phase 1 camera_controller change).

```python
state["director"] = {
    "camera_type": self.main_app.camera_controller.current_camera_type,
    "is_auto_directing": self.main_app.is_enabled,
}
```

### Phase 1B: Camera Controller Extension (`camera_controller.py`)

Add camera type tracking:

```python
class CameraController:
    def __init__(self, ...):
        ...
        self.current_camera_type = "tv_cam"  # Default: broadcast mode
    
    # Called by the main app when camera mode changes
    def set_camera_type(self, camera_type: str):
        """Set from last key press: 'cockpit', 'tv_cam', 'onboard', 'chase'"""
        self.current_camera_type = camera_type
```

### Phase 1C: Telemetry Provider Extension (`telemetry_provider.py`)

No longer required. We will use SharedMemory for nationalities and vehicle names instead of parsing the 1136 and 1164 UDP packets, greatly simplifying the bridge.

### Phase 1D: Static Data (`team_lookup.json`)

Initial version auto-populated from common AMS2 car classes, manually editable:

```json
{
  "Formula Ultimate Gen 2": { "name": "Formula Ultimate", "color": "#E10600", "short": "FU2" },
  "GT3": { "name": "GT3", "color": "#00D2BE", "short": "GT3" },
  "P1": { "name": "Prototype 1", "color": "#0600EF", "short": "P1" }
}
```

---

### Phase 2: Monolithic HTML Overlay (`f1tv_overlay.html`)

Single-file HTML/CSS/JS with these components:

| Component | CSS Region | Visibility Mode | Data Source |
|---|---|---|---|
| Full Leaderboard | Left edge | Always | `leaderboard[]` |
| Mini Leaderboard | Top-left | Always | Top-3 of `leaderboard[]` |
| Driver Name | Bottom-center | Broadcast only | `viewed.name`, `viewed.position` |
| Lap Timer | Top-center | Always | `viewed.last_lap`, sector times |
| Live Speed | Bottom-right | Always | `viewed.speed_kph` |
| Driver Ahead & Behind | Bottom-center | Broadcast | `ahead.*`, `behind.*` |
| Session Info | Top-right | Always | `session.*`, `session.track_name` |
| Fastest Lap | Top-center (animated) | Event-driven | `session.world_fastest_lap` |
| Fastest Sectors | Right-center (animated) | Event-driven | `session.world_fastest_sectors[]` |
| Speedometer | Center-bottom | Cockpit only | speed, rpm, maxRpm, gear, brake, throttle |
| Car Damage | Right | Cockpit only | damage fields |
| Pit Window | Left-bottom | Always | `enforced_pit_stop_lap`, `tyre_compound` |
| Weather | Top-right | Always (current only) | `weather.*` |
| Data Channel | Full-screen | Toggle | All timing data |
| Pit Timer | Center (animated) | Event-driven | `pit_events[]` |

#### Settings Panel

- Toggle visibility with `Tab` key
- Checkboxes for each overlay component
- Preset buttons: "Broadcast" (all broadcast overlays), "Cockpit" (all cockpit overlays), "All On", "All Off"
- Persisted to `localStorage`

#### Animation Style

- F1TV-style slide-in from edges with CSS `transform` + `transition`
- Event overlays (Fastest Lap, Pit Timer) fade in, hold 5s, fade out
- All using CSS transitions (no JS animation libraries)

#### Fonts

Loaded via `@font-face` from `_SHFonts/` served by bridge HTTP:
```css
@font-face {
    font-family: 'Formula1';
    src: url('_SHFonts/Formula1-Bold.ttf') format('truetype');
}
```

---

### Phase 3: OBS Integration

- OBS Browser Source: `http://localhost:8765/f1tv_overlay.html`
- 1920×1080, custom CSS: `body { background: transparent; }`
- URL presets: `?preset=broadcast`, `?preset=cockpit`, `?preset=all`

---

## Extended Bridge State JSON (Target Schema)

```json
{
  "viewed_index": 5,
  "viewed": {
    "position": 3,
    "name": "Max Verstappen",
    "gear": 4,
    "speed_kph": 287.5,
    "rpm": 11200,
    "last_lap": 92.341,
    "brake": 0.0,
    "throttle": 0.85,
    "max_rpm": 13000,
    "num_gears": 8,
    "crash_state": 0,
    "aero_damage": 0.0,
    "engine_damage": 0.0,
    "suspension_damage": [0.0, 0.0, 0.0, 0.0],
    "brake_damage": [0.0, 0.0, 0.0, 0.0],
    "tyre_wear": [0.12, 0.10, 0.15, 0.14],
    "tyre_compound": ["Medium", "Medium", "Medium", "Medium"]
  },
  "ahead": {
    "name": "Lewis Hamilton",
    "position": 2,
    "gap_seconds": 0.812
  },
  "behind": {
    "name": "Lando Norris",
    "position": 4,
    "gap_seconds": 1.234
  },
  "session": {
    "state": 2,
    "session_state": 5,
    "laps_in_event": 57,
    "leader_lap": 23,
    "time_remaining": 3600.0,
    "yellow_flag_state": 0,
    "total_drivers": 20,
    "track_name": "Interlagos",
    "track_variation": "Grand Prix",
    "world_fastest_lap": 72.341,
    "world_fastest_sectors": [24.112, 23.891, 24.338],
    "enforced_pit_stop_lap": 15
  },
  "weather": {
    "ambient_temp": 29,
    "track_temp": 42,
    "rain_density": 0.0,
    "snow_density": 0.0,
    "wind_speed": 5
  },
  "leaderboard": [
    {
      "pos": 1, "name": "Charles Leclerc", "lap": 23, "gap": 0.0,
      "speed": 52.3, "pit": 0, "fastest_lap": 72.341,
      "last_lap": 73.102, "fastest_sectors": [24.112, 23.891, 24.338],
      "nationality": 74, "car_name": "Formula Ultimate Gen 2",
      "car_class": "Formula Ultimate Gen 2"
    }
  ],
  "pit_events": [
    {
      "driver_name": "Carlos Sainz",
      "position": 8,
      "entry_time": 1234.5,
      "exit_time": null,
      "duration": null,
      "in_progress": true
    }
  ],
  "director": {
    "camera_type": "tv_cam",
    "is_auto_directing": true
  }
}
```

## Anti-Regression Guarantees

- Existing `timing.html` and `now_watching.html` overlays consume a subset of the bridge state. All existing fields remain at their current JSON paths.
- The `leaderboard[]` array is extended with new fields (additive only — `pos`, `name`, `lap`, `gap`, `speed`, `pit` are unchanged).
- No changes to `scoring_engine.py`, `timeline_parser.py`, or any test files outside the new `test_bridge_udp.py`.

## Test Plan

### Bridge UDP Parsing Tests (`test_bridge_udp.py`)

| Test ID | Name | Description |
|---|---|---|
| T-B01 | `test_parse_556_brake_throttle` | Mock 556-byte packet with known brake/throttle bytes → verify state values |
| T-B02 | `test_parse_556_damage_fields` | Mock 556-byte with damage bytes → verify aero/engine/suspension/brake damage |
| T-B03 | `test_parse_556_tyre_compound` | Mock 556-byte with compound strings → verify decoded names |
| T-B04 | `test_parse_308_world_fastest` | Mock 308-byte with known floats → verify fastest lap/sectors |
| T-B05 | `test_parse_308_track_name` | Mock 308-byte with track string → verify decoded track name |
| T-B06 | `test_parse_308_enforced_pit_stop` | Mock 308-byte with pit lap value → verify correctly parsed |
| T-B07 | `test_parse_24_weather` | Mock 24-byte with known temp/rain values → verify weather state |
| T-B08 | `test_parse_1040_per_driver_stats` | Mock 1040-byte with known stats → verify per-driver fastest/last/sectors |
| T-B09 | `test_parse_1136_nationalities` | Mock 1136-byte with nationality values → verify parsed correctly |
| T-B10 | `test_behind_driver_computed` | Mock participants with positions → verify behind object populated |
| T-B11 | `test_pit_timer_entry_exit` | Simulate pit_mode 0→1→2→3→0 transitions → verify pit event with duration |
| T-B12 | `test_pit_timer_multiple_simultaneous` | Two drivers pit at once → verify independent tracking |
| T-B13 | `test_existing_state_fields_unchanged` | Verify viewed.position, viewed.name, ahead.*, session.*, leaderboard[].pos etc. still present and correct |

## Complexity Tracking

No constitution violations to justify.
