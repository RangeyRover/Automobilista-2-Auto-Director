# Data Model - Roof Camera Session Info Overlay & Tenths Leaderboard Format

This document details the configuration model and the WebSocket telemetry state schema utilized by the overlay dashboard.

## Local Storage Configuration Model

The overlay settings are persisted in the browser's `localStorage` as simple key-value string pairs.

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `toggle-session-info` | `Boolean` (as `"true"`/`"false"`) | Whether the Session Info panel is active. | `true` |
| `toggle-tenths-timing` | `Boolean` (as `"true"`/`"false"`) | Whether timings are shown to 1 decimal place (tenths). | `true` |
| `toggle-full-leaderboard` | `Boolean` (as `"true"`/`"false"`) | Whether the full grid leaderboard is active. | `true` |
| `toggle-mini-leaderboard` | `Boolean` (as `"true"`/`"false"`) | Whether the mini 10-driver leaderboard is active. | `true` |

---

## WebSocket State Schema

The websocket payload received by `f1tv_overlay.js` on every tick is a JSON object with the following schema details relevant to this feature:

### `state` (JSON Object)

```json
{
  "director": {
    "camera_type": "tv_cam" // String: "tv_cam" | "roof" | "cockpit" | "chase"
  },
  "viewed": {
    "name": "Driver Name",
    "position": 5,
    "last_lap": 91.245,      // Float: Viewed driver's last lap time in seconds
    "speed_kph": 245
  },
  "viewed_index": 2,
  "leaderboard": [
    {
      "pos": 1,
      "name": "Leader Driver",
      "gap": 0,              // Float/String: 0 for leader, or gap in seconds (e.g. 1.234)
      "last_lap": 91.112,    // Float: Driver last lap time in seconds
      "car_class": "GT3",
      "nationality": "br",
      "tyre_compound": "Soft",
      "tyre_stint_laps": 4
    },
    {
      "pos": 2,
      "name": "Chaser Driver",
      "gap": 1.258,          // Float/String: Gap in seconds or string (e.g. "+1 LAP")
      "last_lap": 91.458,
      "car_class": "GT3",
      "nationality": "gb",
      "tyre_compound": "Medium",
      "tyre_stint_laps": 12
    }
  ],
  "weather": {
    "rain_density": 0.0,
    "snow_density": 0.0,
    "ambient_temp": 24.5,
    "track_temp": 32.1,
    "wind_speed": 12.5
  },
  "session": {
    "track_name": "Interlagos",
    "time_remaining": 3245,
    "leader_lap": 12,
    "laps_in_event": 25,
    "world_fastest_sectors": [23.456, 34.567, 33.221]
  }
}
```
