# Data Model: F1TV Overlay Suite (Additions to V4.0 Base)

Extends the base data model from [v3_live_engine/data-model.md](../v3_live_engine/data-model.md).

## New Entities

### ViewedTelemetry (extension of existing `viewed` in BridgeState)

| Field | Type | UDP Source | Offset | Notes |
|---|---|---|---|---|
| `brake` | `float` | `sTelemetryData.sBrake` | byte@29 | uint8 ÷ 255 → 0.0–1.0 |
| `throttle` | `float` | `sTelemetryData.sThrottle` | byte@30 | uint8 ÷ 255 → 0.0–1.0 |
| `max_rpm` | `int` | `sTelemetryData.sMaxRpm` | uint16@42 | Rev limiter threshold |
| `num_gears` | `int` | `sTelemetryData.sGearNumGears` | byte@45 >> 4 | Upper nibble |
| `crash_state` | `int` | `sTelemetryData.sCrashState` | byte@47 | 0=none, 1=offtrack, 2=large prop, 3=spinning, 4=rolling |
| `aero_damage` | `float` | `sTelemetryData.sAeroDamage` | byte@371 | uint8 ÷ 255 → 0.0–1.0 |
| `engine_damage` | `float` | `sTelemetryData.sEngineDamage` | byte@372 | uint8 ÷ 255 → 0.0–1.0 |
| `suspension_damage` | `float[4]` | `sTelemetryData.sSuspensionDamage` | bytes@204-207 | [FL, FR, RL, RR], uint8 ÷ 255 |
| `brake_damage` | `float[4]` | `sTelemetryData.sBrakeDamage` | bytes@200-203 | [FL, FR, RL, RR], uint8 ÷ 255 |
| `tyre_wear` | `float[4]` | `sTelemetryData.sTyreWear` | bytes@196-199 | [FL, FR, RL, RR], uint8 ÷ 255 |
| `tyre_compound` | `str[4]` | `sTelemetryData.sTyreCompound` | bytes@378-537 | 4 × 40-char null-terminated strings |

### BehindDriver (new, mirrors existing `ahead`)

| Field | Type | Source | Description |
|---|---|---|---|
| `name` | `str` | Derived from participants | Driver name behind viewed |
| `position` | `int` | Derived | Race position of behind driver |
| `gap_seconds` | `float` | `sTimingsData.sSplitTimeBehind` | Time gap in seconds |

### WeatherState (new top-level object)

| Field | Type | UDP Source | Offset | Notes |
|---|---|---|---|---|
| `ambient_temp` | `int` | `sGameStateData.sAmbientTemperature` | int8@16 | °C |
| `track_temp` | `int` | `sGameStateData.sTrackTemperature` | int8@17 | °C |
| `rain_density` | `float` | `sGameStateData.sRainDensity` | uint8@18 | ÷ 255 → 0.0–1.0 |
| `snow_density` | `float` | `sGameStateData.sSnowDensity` | uint8@19 | ÷ 255 → 0.0–1.0 |
| `wind_speed` | `int` | `sGameStateData.sWindSpeed` | int8@20 | m/s |

### SessionExtended (extensions to existing `session`)

| Field | Type | UDP Source | Offset | Notes |
|---|---|---|---|---|
| `track_name` | `str` | `sRaceData.sTrackLocation` | char[64]@48 | null-terminated |
| `track_variation` | `str` | `sRaceData.sTrackVariation` | char[64]@112 | null-terminated |
| `world_fastest_lap` | `float` | `sRaceData.sWorldFastestLapTime` | float@12 | seconds, -1.0 = none |
| `world_fastest_sectors` | `float[3]` | `sRaceData.sWorldFastestSector*Time` | float@32,36,40 | seconds per sector |
| `enforced_pit_stop_lap` | `int` | `sRaceData.sEnforcedPitStopLap` | int8@306 | -1 = none |

### ParticipantTimeStats (per-driver, from SharedMemory arrays — preferred)

| Field | Type | SharedMemory Source | Notes |
|---|---|---|---|
| `fastest_lap` | `float` | `mFastestLapTimes[i]` @8944 | Best lap time (seconds) |
| `last_lap` | `float` | `mLastLapTimes[i]` @9200 | Most recent lap time |
| `current_sector1` | `float` | `mCurrentSector1Times[i]` @7408 | **Current lap** S1 split (SharedMemory-only) |
| `current_sector2` | `float` | `mCurrentSector2Times[i]` @7664 | **Current lap** S2 split (SharedMemory-only) |
| `current_sector3` | `float` | `mCurrentSector3Times[i]` @7920 | **Current lap** S3 split (SharedMemory-only) |
| `fastest_sector1` | `float` | `mFastestSector1Times[i]` @8176 | Best S1 time |
| `fastest_sector2` | `float` | `mFastestSector2Times[i]` @8432 | Best S2 time |
| `fastest_sector3` | `float` | `mFastestSector3Times[i]` @8688 | Best S3 time |

UDP fallback (1040-byte `sTimeStatsData`): fastestLap@+0, lastLap@+4, lastSectorTime@+8, fastestSector1/2/3@+12/16/20. Base offset: 16 + (index × 32). Does NOT include current-lap sector breakdowns.

### PitEvent (new, tracked by bridge)

| Field | Type | Source | Description |
|---|---|---|---|
| `driver_index` | `int` | Internal | Participant index |
| `driver_name` | `str` | From participants | Driver name |
| `position` | `int` | From participants | Race position at pit entry |
| `entry_time` | `float` | Bridge wall-clock | Time of `pit_mode` 0→1 transition |
| `exit_time` | `float \| None` | Bridge wall-clock | Time of `pit_mode` 3→0 transition, None if still in progress |
| `duration` | `float \| None` | Derived | `exit_time - entry_time`, None if in progress |
| `in_progress` | `bool` | Derived | True while driver is in pit sequence |
| `pit_count` | `int` | Tracked | Total pit stops completed this session (incremented on exit) |
| `entry_lap` | `int` | From participants | `current_lap` at pit entry |
| `laps_since_last_pit` | `int` | Derived | `current_lap - last_pit_exit_lap` (−1 if first pit stop) |

### DirectorState (new top-level object)

| Field | Type | Source | Description |
|---|---|---|---|
| `camera_type` | `str` | `CameraController.current_camera_type` | `"cockpit"`, `"tv_cam"`, `"onboard"`, `"chase"` |
| `is_auto_directing` | `bool` | `main.py.is_enabled` | Whether auto director is controlling camera |

### TeamLookup (static file: `team_lookup.json`)

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Display team name |
| `color` | `str` | Hex colour code (e.g., `"#E10600"`) |
| `short` | `str` | Short abbreviation (3-4 chars) |

Keyed by car class name string (from `sVehicleClassNamesData` or `mCarClassNames`).

## Extended Leaderboard Entry

The existing `leaderboard[]` array entries are extended with:

| Field | Type | Source | New? |
|---|---|---|---|
| `pos` | `int` | `race_position` | Existing |
| `name` | `str` | `name` | Existing |
| `lap` | `int` | `current_lap` | Existing |
| `gap` | `float` | `gap_ahead` | Existing |
| `speed` | `float` | `speed` | Existing |
| `pit` | `int` | `pit_mode` | Existing |
| `fastest_lap` | `float` | SharedMemory `mFastestLapTimes[i]` | **NEW** |
| `last_lap` | `float` | SharedMemory `mLastLapTimes[i]` | **NEW** |
| `current_sectors` | `float[3]` | SharedMemory `mCurrentSector1/2/3Times[i]` | **NEW** (SHM-only) |
| `fastest_sectors` | `float[3]` | SharedMemory `mFastestSector1/2/3Times[i]` | **NEW** |
| `nationality` | `int` | UDP `sParticipantsData` | **NEW** |
| `car_name` | `str` | UDP `sParticipantVehicleNamesData` | **NEW** |
| `car_class` | `str` | UDP `sVehicleClassNamesData` | **NEW** |
| `pit_count` | `int` | Bridge pit tracker | **NEW** |
| `laps_since_last_pit` | `int` | Bridge pit tracker | **NEW** |

## State Transitions

### Pit Event State Machine

```
NONE (pit_mode=0)
  │
  └──[pit_mode→1]──→ ENTERING (record entry_time)
                        │
                        └──[pit_mode→2]──→ IN_PIT
                                            │
                                            └──[pit_mode→3]──→ EXITING
                                                                │
                                                                └──[pit_mode→0]──→ COMPLETED (record exit_time, calc duration)
```

### Camera Type Inference

```
AUTO_DIRECTING ──[camera key press]──→ camera_type updated
NOT_DIRECTING ──→ camera_type defaults to "tv_cam"
```

## Nationality Codes

The `nationality` field uses AMS2 integer codes. Common values:

| Code | Country | Code | Country |
|---|---|---|---|
| 2 | Australian | 44 | Italian |
| 11 | Brazilian | 52 | Mexican |
| 18 | Dutch | 74 | French |
| 24 | Finnish | 81 | British |
| 27 | German | 82 | Spanish |
| 48 | Japanese | 84 | Canadian |
