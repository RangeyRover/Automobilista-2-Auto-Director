# Data Model: AMS2 Auto Director V4.0

## Entities

### Participant (in-memory dict, keyed by index 0-31)

| Field | Type | Source | Description |
|---|---|---|---|
| `name` | `str` | `SharedMemory.mParticipantInfo[i].mName` | Driver name (decoded UTF-8, stripped) |
| `race_position` | `int` | `mRacePosition` | Current race position (1-based) |
| `is_active` | `bool` | `mIsActive` | Whether participant slot is occupied |
| `lap_distance` | `float` | `mCurrentLapDistance` | Distance into current lap (meters) |
| `current_lap` | `int` | `mLapsCompleted` | Laps completed |
| `current_sector` | `int` | `mCurrentSector` | Current track sector |
| `speed` | `float` | Derived | Speed in m/s (calculated from distance delta / time delta) |
| `pit_mode` | `int` | `mPitModes[i]` | 0=none, 1=entering, 2=in pit, 3=exiting, 4=garage |
| `race_state` | `int` | `mRaceStates[i]` | 0=invalid, 1=not started, 2=racing, 3=finished |
| `true_distance` | `float` | Derived | `laps_completed * track_length + lap_distance` |
| `gap_ahead` | `float` | Derived | Gap to participant ahead in meters |
| `cars_ahead_250m` | `int` | Derived | Count of active participants within 250m ahead |
| `flag_colour` | `int` | `mHighestFlagColours[i]` | Highest flag colour for this participant |
| `flag_reason` | `int` | `mHighestFlagReasons[i]` | Flag reason (0=none, 1=solo crash, 2=vehicle crash) |
| `fastest_lap` | `float` | `mFastestLapTimes[i]` | Best lap time in seconds |
| `last_lap` | `float` | `mLastLapTimes[i]` | Last lap time in seconds |

### ScoreBreakdown (in-memory dict, keyed by participant index)

| Field | Type | Description |
|---|---|---|
| `pit_mode_penalty` | `float` | -10 if in pits, else 0 |
| `speed_penalty` | `float` | -5 if speed < 5 m/s, else 0 |
| `cars_ahead_bonus` | `float` | Leader: count*2, Others: count*0.4 |
| `close_racing_bonus` | `float` | (50-gap)/5 if gap in 0-50m |
| `race_position_bonus` | `float` | factor * (1 - (pos-1)/32) |
| `replay_enhancement` | `float` | Bonus from replay log events (V4.0 future) |
| `total_score` | `float` | Sum of all components |

### TrackInfo (in-memory dict, singleton)

| Field | Type | Source | Description |
|---|---|---|---|
| `track_name` | `str` | `mTrackLocation` | Track name |
| `track_variation` | `str` | `mTrackVariation` | Track variant |
| `track_length` | `float` | `mTrackLength` | Track length in meters |
| `num_participants` | `int` | `mNumParticipants` | Active participant count |

### DirectorState (in-memory, owned by main.py)

| Field | Type | Description |
|---|---|---|
| `is_enabled` | `bool` | Whether auto director is active |
| `is_connected` | `bool` | Whether AMS2 data source is available |
| `current_focus_position` | `int \| None` | Race position currently being viewed |
| `last_switch_time` | `float` | Wall-clock time of last camera switch |
| `switch_interval` | `float` | Seconds between auto-director switches (default 7) |
| `game_time` | `float \| None` | Current game time from `mCurrentTime` |

## State Transitions

### Connection State
```
DISCONNECTED  --[poll() returns data]--> CONNECTED
CONNECTED     --[poll() returns None]--> DISCONNECTED
```

### Director State
```
DISABLED  --[spacebar]--> ENABLED
ENABLED   --[spacebar]--> DISABLED
ENABLED   --[disconnected]--> DISABLED (auto)
```
