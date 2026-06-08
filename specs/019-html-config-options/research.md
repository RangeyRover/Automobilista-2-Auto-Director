# Research: HTML Configuration Options

**Branch**: `019-html-config-options` | **Date**: 2026-06-08

---

## Decision 1: Leaderboard Interval Gaps Toggle

### Choice
Perform the interval gap calculation on the client side (in `dashboard/js/f1tv_overlay.js` and `dashboard/app.js`) using the sorted leaderboard data already sent by the server.

### Rationale
- The server sends a pre-sorted array of drivers in `state.leaderboard` where the $k$-th element is immediately behind the $(k-1)$-th element.
- Calculating the difference in gap `state.leaderboard[k].gap - state.leaderboard[k - 1].gap` in JavaScript is mathematically correct for time gaps, requires zero backend code changes, and requires no additions to the WebSocket telemetry payload schema.
- Synchronizing this setting between the overlay and control panel is already handled by the existing `f1tv_config` sync protocol.

### Alternatives Considered
- **Server-side Calculation**: Add an `interval_gap` field to each driver dictionary on the server. Rejected because it unnecessarily increases the WebSocket payload size and complicates the server serialization logic.

---

## Decision 2: Auto-Camera Restricted Pools

### Choice
Introduce an `"enabled_cameras": ["1", "2", "7"]` list in `camera_config.json`. The `CameraController` will filter standard and close-racing pools using this list.

### Rationale
- The `CameraController` already loads `camera_config.json` dynamically on every driver/camera switch.
- Adding `enabled_cameras` is backwards-compatible. If the property is missing or empty, all cameras (1–7) are considered enabled.
- The HTML Control Panel can easily write to `camera_config.json` using the existing `save_json` WebSocket message handler.

### Alternatives Considered
- **Separate Pool Configurations**: Let the user edit `pool_standard` and `pool_close_racing` arrays directly in the UI. Rejected because it is too complex for a standard user. Checkboxes for active cameras (e.g. Cockpit, Chase, TV Cam) mapped to a simple enabled list is much cleaner.

---

## Decision 3: Disable Auto-Camera Switching from UI

### Choice
Introduce `"disable_camera_change": true/false` in `camera_config.json`. The `CameraController` will read this value and skip sending camera keypresses during automatic director switches when enabled.

### Rationale
- Avoids adding complex state-handling or command-routing in the WebSocket bridge.
- Automatically persists the user's preference.

### Alternatives Considered
- **WebSocket Command**: Add a custom command to call the Tkinter app's `_toggle_camera_change()` method. Rejected because the backend GUI may not always be visible (e.g. if running in a headless or remote setup), whereas configuring it via the JSON file works universally.
