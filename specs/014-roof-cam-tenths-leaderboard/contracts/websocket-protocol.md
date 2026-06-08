# WebSocket Sync Protocol - Roof Camera Session Info Overlay & Tenths Leaderboard Format

This document defines the WebSocket message contract for synchronizing settings between `f1tv_control.html` (the control panel) and `f1tv_overlay.js` (the overlay page).

## 1. Remote Settings Synchronization Message

When the user changes a checkbox (or clicks a preset button) on `f1tv_control.html`, the control panel sends a JSON payload to the WebSocket server which broadcasts it to the active overlay page(s).

### Client Request Payload (Sent by Control Panel)

- **Type**: `f1tv_config`
- **Fields**:
  - `type` (String): Must be `"f1tv_config"`.
  - `config` (Object): Map of component names to their boolean visibility states.

#### Example JSON:
```json
{
  "type": "f1tv_config",
  "config": {
    "full-leaderboard": true,
    "mini-leaderboard": true,
    "driver-name": true,
    "lap-timer": true,
    "live-speed": false,
    "ahead-behind": true,
    "session-info": true,
    "fastest-lap": true,
    "fastest-sectors": true,
    "weather-panel": true,
    "pit-window": true,
    "pit-timer": true,
    "connection-status": true,
    "tenths-timing": true
  }
}
```

---

## 2. Server Broadcast Behavior

The Python WebSocket server listens for `f1tv_config` payloads and broadcasts them unmodified to all connected WebSocket clients (the overlay dashboard instances).

Upon receiving this payload, the overlay instances:
1. Update their respective checkbox states in the local settings panel.
2. Persist the updated values to their local `localStorage`.
3. Call `updateVisibility()` to update the UI elements immediately.
