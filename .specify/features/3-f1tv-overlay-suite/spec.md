# Feature Specification: F1TV Overlay Suite

**Feature Branch**: `feature/3-f1tv-overlay-suite`  
**Created**: 2026-05-08  
**Status**: Draft  
**Input**: User description: "Convert F1TV v4.2 SimHub dashboards into a monolithic HTML overlay driven by the Auto Director bridge WebSocket, with feature toggles per overlay, cockpit-view-only filtering inferred from last camera key press, and OBS Browser Source integration."

## Clarifications

### Session 2026-05-08

- Q: Are SharedMemory fields for the viewed car reliable? → A: SharedMemory never changes to the viewed car reliably. Use UDP as primary data source. The RR UDP mapping (`SMS_UDP_Definitions_AMS2_RR.hpp`) is the most reliable and most recent reference.
- Q: How to detect cockpit vs broadcast camera view? → A: Infer from last key press sent by the Auto Director. AMS2 does not expose camera type in telemetry.
- Q: How to handle team names/colours? → A: Static JSON lookup file keyed by car class name → team identity (name + hex colour).
- Q: Tyre compound source? → A: Must come from UDP `sTelemetryData` packet (bytes 378-537, 4×40 char strings).
- Q: Weather forecast (future conditions)? → A: Show current conditions only, no forecast.
- Q: Pit stop timing? → A: Calculate from `pit_mode` state transitions. Track entry/exit timestamps per driver.
- Q: F1TV fonts? → A: Serve from `dashboard/_SHFonts/` directory — the bridge HTTP server already serves the dashboard folder.
- Q: FIA Stewards / penalties? → A: Not feasible — AMS2 has no penalty telemetry. Out of scope.
- Q: Turn indicator? → A: Not feasible — no track turn data in telemetry. Out of scope.
- Q: Constructors standings? → A: No constructor data. Out of scope.
- Q: Race Classification overlay? → A: Allow via manual team lookup by car/class name from static JSON.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Bridge Delivers Extended Telemetry (Priority: P1)

The WebSocket bridge extends beyond its current state to broadcast all telemetry fields required by the overlay suite: viewed car damage, tyre wear, compound, brake/throttle, weather, per-driver sector/lap statistics, nationalities, track name, world fastest times, and pit window data — primarily sourced from UDP packets.

**Why this priority**: Without the data, no overlays can function.

**Independent Test**: Mock UDP packets with known byte values and verify the bridge state JSON contains the expected parsed fields.

**Acceptance Scenarios**:

1. **Given** a 556-byte UDP `sTelemetryData` packet is received, **When** the bridge processes it, **Then** `state.viewed` contains `brake`, `throttle`, `max_rpm`, `aero_damage`, `engine_damage`, `suspension_damage[4]`, `tyre_wear[4]`, and `tyre_compound[4]`. *(UDP only — SharedMemory viewed-car fields don't reliably follow camera switches.)*
2. **Given** SharedMemory is available, **When** the bridge reads session fields, **Then** `state.session` contains `track_name` (from `mTrackLocation`), `world_fastest_lap` (from `mWorldFastestLapTime`), `world_fastest_sectors[3]` (from `mWorldFastestSector1/2/3Time`), and `enforced_pit_stop_lap` (from `mEnforcedPitStopLap`). *(SharedMemory preferred — these are global session fields, not per-viewed-car. UDP `sRaceData` used as fallback.)*
3. **Given** SharedMemory is available, **When** the bridge reads weather fields, **Then** `state.weather` contains `ambient_temp` (from `mAmbientTemperature`), `track_temp` (from `mTrackTemperature`), `rain_density` (from `mRainDensity`), `snow_density` (from `mSnowDensity`), `wind_speed` (from `mWindSpeed`). *(SharedMemory preferred — these are global fields. UDP `sGameStateData` used as fallback.)*
4. **Given** SharedMemory is available, **When** the bridge reads the per-participant timing arrays, **Then** each leaderboard entry contains `fastest_lap` (from `mFastestLapTimes[64]`), `last_lap` (from `mLastLapTimes[64]`), `fastest_sector1/2/3` (from `mFastestSector1/2/3Times[64]`), and `current_sector1/2/3` (from `mCurrentSector1/2/3Times[64]`). *(SharedMemory is the only source for current-lap sector breakdowns — UDP `sTimeStatsData` only has `lastSectorTime`, not the full S1/S2/S3 for the current lap. UDP used as fallback for fastest/last lap.)*
5. **Given** a 1136-byte `sParticipantsData` packet is received, **When** processed, **Then** nationality data is parsed and available per driver.

---

### User Story 2 — Monolithic HTML Overlay Renders in OBS (Priority: P1)

A single HTML file (`f1tv_overlay.html`) connects to the bridge WebSocket and renders all enabled overlays as transparent 1920×1080 graphics suitable for OBS Browser Source.

**Why this priority**: Core deliverable — the consolidated overlay page.

**Acceptance Scenarios**:

1. **Given** the bridge is running, **When** the user opens `http://localhost:8765/f1tv_overlay.html` in a browser, **Then** all enabled overlays render with live data from the WebSocket.
2. **Given** the page is added as an OBS Browser Source at 1920×1080, **When** the game is running, **Then** overlays display with transparent background over the game feed.
3. **Given** the user presses a hotkey (Tab), **When** the settings panel opens, **Then** individual overlays can be toggled on/off.

---

### User Story 3 — Cockpit-View-Only Overlays (Priority: P2)

Some overlays (Speedometer, Halo HUD, Car Damage) should only display when the Auto Director has most recently commanded a cockpit camera view. Other overlays (Driver Name badge) should hide in cockpit mode.

**Why this priority**: Prevents visual clutter and matches broadcast conventions.

**Acceptance Scenarios**:

1. **Given** the Auto Director last sent a camera switch to cockpit view, **When** the bridge broadcasts `director.camera_type == "cockpit"`, **Then** cockpit-only overlays are visible and broadcast-only overlays are hidden.
2. **Given** the camera type is `"tv_cam"`, **When** the overlay renders, **Then** broadcast overlays are visible and cockpit overlays are hidden.

---

### User Story 4 — Pit Timer Overlay (Priority: P2)

When any driver enters the pits, a pit timer overlay shows the driver name, elapsed pit time (calculated from `pit_mode` state transitions), their total pit stop count for the session, and laps completed since their last pit stop.

**Acceptance Scenarios**:

1. **Given** a driver's `pit_mode` transitions from 0 → 1 (entering pits), **When** the bridge detects this, **Then** the pit entry time is recorded.
2. **Given** the same driver's `pit_mode` transitions to 3 → 0 (exiting pits), **When** detected, **Then** the pit duration is calculated and broadcast.
3. **Given** the pit timer is active, **When** the overlay renders, **Then** the driver name, running pit time (or final duration), total pit count, and laps since last pit are displayed.
4. **Given** a driver has completed 2 prior pit stops and is now pitting on lap 35 (last pit was on lap 22), **When** the pit event is created, **Then** `pit_count` is 3 and `laps_since_last_pit` is 13.

---

### Edge Cases

- What happens when the bridge has no UDP data yet? Overlays show placeholder state (dashes) until data arrives.
- What happens when a driver disconnects mid-race? They are removed from overlays that reference active drivers.
- What happens when multiple drivers pit simultaneously? All pit events are tracked independently.
- What happens when the Auto Director is not running (manual camera control)? Camera type defaults to `"tv_cam"` (broadcast mode). User can still manually toggle overlays via the settings panel.

## Requirements *(mandatory)*

### Functional Requirements

**Bridge Extensions:**
- **FR-001**: Bridge MUST parse the 556-byte `sTelemetryData` UDP packet to extract viewed car telemetry: brake, throttle, maxRpm, numGears, crashState, aeroDamage, engineDamage, suspensionDamage[4], brakeDamage[4], tyreWear[4], tyreCompound[4].
- **FR-002**: Bridge MUST parse the 308-byte `sRaceData` UDP packet to extract: trackName, trackVariation, worldFastestLapTime, worldFastestSector1/2/3Time, enforcedPitStopLap.
- **FR-003**: Bridge MUST parse the 24-byte `sGameStateData` UDP packet to extract: ambientTemperature, trackTemperature, rainDensity, snowDensity, windSpeed.
- **FR-004**: Bridge MUST parse the 1040-byte `sTimeStatsData` UDP packet to extract per-driver: fastestLap, lastLap, lastSectorTime, fastestSector1/2/3.
- **FR-005**: Bridge MUST parse nationality data from the 1136-byte `sParticipantsData` packet.
- **FR-006**: Bridge MUST compute a `behind` object (mirror of `ahead`) with the driver immediately behind the viewed participant.
- **FR-007**: Bridge MUST track pit_mode transitions per driver to calculate pit entry/exit times and durations.
- **FR-008**: Bridge MUST expose a `director.camera_type` field inferred from the last camera key press command.
- **FR-009**: Bridge MUST extend each leaderboard entry with: fastest_lap, last_lap, fastest_sectors[3], nationality, car_name, car_class.

**Overlay HTML:**
- **FR-010**: A single `f1tv_overlay.html` file MUST render all enabled overlay components in a 1920×1080 transparent canvas.
- **FR-011**: Each overlay MUST be independently togglable via a settings panel (hotkey: Tab).
- **FR-012**: Overlays MUST automatically switch between cockpit and broadcast visibility modes based on `director.camera_type`.
- **FR-013**: The overlay MUST support URL parameter presets (`?preset=broadcast` or `?preset=cockpit`).
- **FR-014**: F1TV fonts MUST be served from the `dashboard/_SHFonts/` directory.

**Static Data:**
- **FR-015**: A static `team_lookup.json` MUST map car class names to team identity (name + hex colour).

### Key Entities

- **BridgeState**: The full JSON state object broadcast via WebSocket at ~60Hz.
- **ViewedTelemetry**: Extended telemetry for the currently viewed participant (brake, throttle, damage, tyres).
- **WeatherState**: Current ambient conditions (temp, rain, wind).
- **TimeStats**: Per-driver timing statistics (fastest/last lap, sector times).
- **PitEvent**: A tracked pit stop instance with entry time, exit time, duration, driver name.
- **DirectorState**: Camera type inference and auto-directing status.
- **TeamLookup**: Static mapping from car class name → team name + colour.

## Assumptions

- AMS2 UDP protocol follows the `SMS_UDP_Definitions_AMS2_RR.hpp` specification (the RangeyRover-modified version is authoritative).
- The bridge already runs a WebSocket server on port 8765 with an HTTP file server for the `dashboard/` directory.
- UDP listener is already implemented in `telemetry_provider.py` and buffers packets by size in `_packet_buffer`.
- The bridge already parses 556-byte (speed, rpm, gear), 1063-byte (timings, splits), and partially 1040-byte (last lap) packets.
- The bridge already constructs a `leaderboard[]` from the main app's `_participants` dict.
- Camera type inference is limited to when the Auto Director is actively controlling cameras. When not auto-directing, defaults to broadcast mode.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 15 in-scope overlays render correctly with live AMS2 data in an OBS Browser Source.
- **SC-002**: Bridge unit tests verify correct parsing of all 6 UDP packet types with mock data.
- **SC-003**: Pit timer accurately tracks pit duration within ±1 tick (~16ms) of actual pit_mode transition.
- **SC-004**: Cockpit/broadcast mode switching occurs within 1 bridge tick of camera type change.
- **SC-005**: All existing bridge and telemetry tests continue to pass (anti-regression).
- **SC-006**: Overlay renders at 60fps in OBS with negligible CPU overhead.
