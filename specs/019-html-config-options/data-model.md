# Data Model: HTML Configuration Options

**Branch**: `019-html-config-options` | **Date**: 2026-06-08

---

## 1. Camera Configuration File Schema (`camera_config.json`)

Stored under `dashboard/camera_config.json`. Managed by `CameraController` and updated via WebSocket `save_json` payload.

### Fields

| Field Name | Type | Description | Default / Validation |
|---|---|---|---|
| `trackside_keys` | `list[str]` | List of camera keys for TV/trackside views. | `["7"]` |
| `pool_close_racing` | `list[str]` | Camera pool for close racing scenarios. | `["1", "1", "1", "2", "3", "7"]` |
| `pool_standard` | `list[str]` | Camera pool for standard scenarios. | `["7", "7", "7", "7", "2", "3"]` |
| `enabled_cameras` | `list[str]` | List of keys (e.g. `'1'`, `'2'`, `'7'`) allowed for auto-director changes. | Optional. If empty/missing, all cameras are enabled. |
| `disable_camera_change` | `bool` | Inhibit automatic camera angle switching when true. | `false` |

---

## 2. Client-Side Components Layout Settings (`localStorage`)

Persisted on the client-side browser context.

### Keys

| Key | Type | Description | Default |
|---|---|---|---|
| `toggle-interval-gaps` | `string` | `"true"` if the leaderboard timing column should render interval gaps; `"false"` for gap to leader. | `"false"` |
| `toggle-tenths-timing` | `string` | `"true"` to show timing tenths; `"false"` for thousandths. | `"true"` |
