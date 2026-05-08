# Tasks: F1TV Overlay Suite

**Input**: `.specify/features/3-f1tv-overlay-suite/`  
**Approach**: TDD — write tests FIRST, confirm FAIL, then implement  
**Granularity**: Extremely granular for lesser agentic model execution

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1=Bridge Telemetry, US2=HTML Overlay, US3=Cockpit Mode, US4=Pit Timer

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project scaffolding, test fixtures, static data files

- [x] T001 Create empty test file `tests/test_bridge_udp.py` with docstring: `"""TDD tests for F1TV bridge UDP parsing extensions."""` and `import struct, pytest`
- [x] T002 [P] Create empty test file `tests/test_pit_tracker.py` with docstring: `"""TDD tests for pit timer state machine."""` and `import pytest`
- [x] T003 [P] Create empty test file `tests/test_camera_type.py` with docstring: `"""TDD tests for camera type inference."""` and `import pytest`
- [x] T004 [P] Create static data file `dashboard/team_lookup.json` with initial mapping: keys are common AMS2 car class names (`"Formula Ultimate Gen 2"`, `"GT3"`, `"GT4"`, `"P1"`, `"Stock Car 2024"`, `"Copa Classic B"`, `"F-Reiza"`, `"F-Trainer"`, `"Brabham BT46"`, `"M1 Procar"`), each value has `"name"` (string), `"color"` (hex string e.g. `"#E10600"`), `"short"` (3-4 char abbreviation)
- [x] T005 [P] Copy F1TV font files from `F1TV v4.2/_extracted/` subdirectories into `dashboard/_SHFonts/` if not already present. Verify at minimum `Formula1-Bold.ttf` exists in that directory. If no TTF files found in extracted dirs, create a placeholder `dashboard/_SHFonts/README.md` noting fonts need manual placement.
- [x] T006 Add new fixture `make_udp_telemetry_packet` to `tests/conftest.py` — a factory function that returns a `bytearray(556)` with configurable fields: `viewed_index` (byte@12, default 0), `brake` (byte@29, default 0), `throttle` (byte@30, default 0), `speed` (float@36, default 50.0), `rpm` (uint16@40, default 8000), `max_rpm` (uint16@42, default 13000), `gear_num_gears` (byte@45, default 0x84 meaning gear=4 numGears=8), `crash_state` (byte@47, default 0), `tyre_wear` (bytes@196-199, default [0,0,0,0]), `brake_damage` (bytes@200-203, default [0,0,0,0]), `suspension_damage` (bytes@204-207, default [0,0,0,0]), `aero_damage` (byte@371, default 0), `engine_damage` (byte@372, default 0), `tyre_compound` (4x40 char strings starting@378, default all `b"Medium"`). Use `struct.pack_into` for multi-byte fields.
- [x] T007 Add new fixture `make_udp_race_data_packet` to `tests/conftest.py` — factory returning `bytearray(308)` with: `world_fastest_lap` (float@12, default 72.5), `personal_fastest_lap` (float@16, default 73.0), `world_fastest_sector1` (float@32, default 24.0), `world_fastest_sector2` (float@36, default 24.0), `world_fastest_sector3` (float@40, default 24.5), `track_length` (float@44, default 4300.0), `track_location` (char[64]@48, default `b"Interlagos"`), `track_variation` (char[64]@112, default `b"Grand Prix"`), `enforced_pit_stop_lap` (int8@306, default -1). Use `struct.pack_into` and null-terminated byte strings.
- [x] T008 Add new fixture `make_udp_game_state_packet` to `tests/conftest.py` — factory returning `bytearray(24)` with: `game_state` (byte@14, default 2), `ambient_temp` (int8@16, default 25), `track_temp` (int8@17, default 35), `rain_density` (uint8@18, default 0), `snow_density` (uint8@19, default 0), `wind_speed` (int8@20, default 5). Use `struct.pack_into`.
- [x] T009 Add new fixture `make_udp_time_stats_packet` to `tests/conftest.py` — factory returning `bytearray(1040)` with a `stats` parameter: list of dicts (up to 32), each with `fastest_lap` (float, default 0.0), `last_lap` (float, default 0.0), `last_sector_time` (float, default 0.0), `fastest_sector1` (float, default 0.0), `fastest_sector2` (float, default 0.0), `fastest_sector3` (float, default 0.0). Pack each at offset `16 + i*32` using `struct.pack_into('<6f', buf, offset, ...)`. Fill `participant_online_rep` (uint32@+24) and `mp_index` (uint16@+28) with 0.
- [x] T010 Add new fixture `make_udp_participants_packet` to `tests/conftest.py` — factory returning `bytearray(1136)` with a `participants` parameter: list of dicts (up to 16), each with `name` (str, default `f"Driver {i}"`), `nationality` (uint32, default 0). Pack names at offset `16 + i*64` as null-terminated bytes. Pack nationalities at offset `1040 + i*4` as `<I`.
- [x] T011 Extend existing `mock_shared_memory` fixture in `tests/conftest.py` to add new attributes if not present: `mWorldFastestLapTime` (float, default 0.0), `mWorldFastestSector1Time` (float, default 0.0), `mWorldFastestSector2Time` (float, default 0.0), `mWorldFastestSector3Time` (float, default 0.0), `mAmbientTemperature` (float, default 25.0), `mTrackTemperature` (float, default 35.0), `mRainDensity` (float, default 0.0), `mSnowDensity` (float, default 0.0), `mWindSpeed` (float, default 0.0), `mTranslatedTrackLocation` (bytes, default `b"TestTrack"`), `mTranslatedTrackVariation` (bytes, default `b"GP"`), `mEnforcedPitStopLap` (int, default -1), `mCurrentSector1Times` (list of 64 floats, default all 0.0), `mCurrentSector2Times` (list of 64 floats, default all 0.0), `mCurrentSector3Times` (list of 64 floats, default all 0.0), `mFastestSector1Times` (list of 64 floats, default all 0.0), `mFastestSector2Times` (list of 64 floats, default all 0.0), `mFastestSector3Times` (list of 64 floats, default all 0.0), `mNationalities` (list of 64 ints, default all 0)
- [x] T012 Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/ -x -q"` to verify all existing tests still pass with the new fixtures (anti-regression checkpoint)

**Checkpoint**: All test fixtures created, existing tests pass, static data files in place.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure changes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T013 Add `self.current_camera_type = "tv_cam"` attribute to `CameraController.__init__()` in `core/camera_controller.py` (line ~14, after `self.key_gap_ms`). This is a simple string property, no logic yet.
- [x] T014 Add initial empty state keys to `DashboardBridge.__init__()` in `dashboard/bridge.py`. In `self.state` dict (line ~21), add: `"behind": {"name": "", "position": 0, "gap_seconds": 0.0}`, `"weather": {"ambient_temp": 0, "track_temp": 0, "rain_density": 0.0, "snow_density": 0.0, "wind_speed": 0}`, `"director": {"camera_type": "tv_cam", "is_auto_directing": false}`, `"pit_events": []`. Also extend `"session"` dict to include: `"track_name": ""`, `"track_variation": ""`, `"world_fastest_lap": 0.0`, `"world_fastest_sectors": [0.0, 0.0, 0.0]`, `"enforced_pit_stop_lap": -1`. Also extend `"viewed"` dict to include: `"brake": 0.0`, `"throttle": 0.0`, `"max_rpm": 0`, `"num_gears": 0`, `"crash_state": 0`, `"aero_damage": 0.0`, `"engine_damage": 0.0`, `"suspension_damage": [0.0, 0.0, 0.0, 0.0]`, `"brake_damage": [0.0, 0.0, 0.0, 0.0]`, `"tyre_wear": [0.0, 0.0, 0.0, 0.0]`, `"tyre_compound": ["", "", "", ""]`.
- [x] T015 Add `self._pit_tracker = {}` dict to `DashboardBridge.__init__()` in `dashboard/bridge.py` (after `self.participants = {}`). This will track per-driver pit state. Also add `self._pit_events = []` for recent completed/in-progress pit events.
- [x] T016 Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/ -x -q"` to verify all existing tests still pass after init changes (anti-regression checkpoint)

**Checkpoint**: Bridge state schema extended, camera controller has camera_type property, pit tracker initialised. All existing tests pass.

---

## Phase 3: User Story 1 — Bridge Delivers Extended Telemetry (Priority: P1) 🎯 MVP

**Goal**: Bridge parses all required UDP/SharedMemory fields and broadcasts extended state JSON via WebSocket.

**Independent Test**: Mock packets with known byte values → verify `bridge.state` dict contains correct parsed values.

### 3A: TDD Tests — 556-byte Telemetry Parsing (write FIRST, must FAIL) ⚠️

- [ ] T017 [US1] In `tests/test_bridge_udp.py`, write test `test_parse_556_brake_throttle`: Create a `DashboardBridge` instance. Set `bridge.packet_buffer = {556: make_udp_telemetry_packet(brake=128, throttle=255)}`. Call `bridge._parse_packets()`. Assert `bridge.state["viewed"]["brake"] == pytest.approx(128/255)` and `bridge.state["viewed"]["throttle"] == pytest.approx(1.0)`. This test MUST FAIL (method doesn't parse these fields yet).
- [ ] T018 [P] [US1] In `tests/test_bridge_udp.py`, write test `test_parse_556_max_rpm_num_gears`: Create bridge, set packet with `max_rpm=13000, gear_num_gears=0x86` (gear=6, numGears=8). Call `_parse_packets()`. Assert `state["viewed"]["max_rpm"] == 13000` and `state["viewed"]["num_gears"] == 8`. Must FAIL.
- [ ] T019 [P] [US1] In `tests/test_bridge_udp.py`, write test `test_parse_556_damage_fields`: Create bridge, set packet with `aero_damage=128, engine_damage=64, suspension_damage=[50,100,150,200], brake_damage=[25,50,75,100]`. Call `_parse_packets()`. Assert `state["viewed"]["aero_damage"] == pytest.approx(128/255)`, `state["viewed"]["engine_damage"] == pytest.approx(64/255)`, `state["viewed"]["suspension_damage"][0] == pytest.approx(50/255)`, etc. Must FAIL.
- [ ] T020 [P] [US1] In `tests/test_bridge_udp.py`, write test `test_parse_556_tyre_wear`: Create bridge, set packet with `tyre_wear=[30,40,50,60]`. Call `_parse_packets()`. Assert `state["viewed"]["tyre_wear"] == [pytest.approx(30/255), pytest.approx(40/255), pytest.approx(50/255), pytest.approx(60/255)]`. Must FAIL.
- [ ] T021 [P] [US1] In `tests/test_bridge_udp.py`, write test `test_parse_556_tyre_compound`: Create bridge, set packet with `tyre_compound=[b"Soft", b"Soft", b"Medium", b"Medium"]` (custom fixture values). Call `_parse_packets()`. Assert `state["viewed"]["tyre_compound"] == ["Soft", "Soft", "Medium", "Medium"]`. Must FAIL.
- [ ] T022 [P] [US1] In `tests/test_bridge_udp.py`, write test `test_parse_556_crash_state`: Create bridge, set packet with `crash_state=3`. Call `_parse_packets()`. Assert `state["viewed"]["crash_state"] == 3`. Must FAIL.
- [ ] T023 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — confirm all 6 tests FAIL (TDD red phase).

### 3B: Implementation — 556-byte Telemetry Parsing

- [ ] T024 [US1] In `dashboard/bridge.py` method `_parse_packets()`, inside the `if p559` block (line ~157), after the existing `self.state["viewed"]["gear"]` line, add parsing for: `self.state["viewed"]["brake"] = p559[29] / 255.0`, `self.state["viewed"]["throttle"] = p559[30] / 255.0`, `self.state["viewed"]["max_rpm"] = struct.unpack_from('<H', p559, 42)[0]`, `self.state["viewed"]["num_gears"] = (p559[45] >> 4) & 0x0F`, `self.state["viewed"]["crash_state"] = p559[47]`, `self.state["viewed"]["aero_damage"] = p559[371] / 255.0` (if len(p559) > 371), `self.state["viewed"]["engine_damage"] = p559[372] / 255.0`, `self.state["viewed"]["suspension_damage"] = [p559[204+i] / 255.0 for i in range(4)]`, `self.state["viewed"]["brake_damage"] = [p559[200+i] / 255.0 for i in range(4)]`, `self.state["viewed"]["tyre_wear"] = [p559[196+i] / 255.0 for i in range(4)]`. For tyre compound: loop `for i in range(4): raw = p559[378+i*40:378+(i+1)*40]; compounds.append(raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip())` and set `self.state["viewed"]["tyre_compound"] = compounds`. Guard with `if len(p559) >= 538:` to handle 556 vs 559 byte packets.
- [ ] T025 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — confirm all 6 telemetry tests now PASS (TDD green phase).
- [ ] T026 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/ -x -q"` — anti-regression: ALL tests pass.

### 3C: TDD Tests — Session Data from SharedMemory (write FIRST, must FAIL) ⚠️

- [ ] T027 [US1] In `tests/test_bridge_udp.py`, write test `test_session_world_fastest_from_shm`: Create bridge with mock `main_app` that has `_shm = mock_shared_memory(mWorldFastestLapTime=72.341, mWorldFastestSector1Time=24.1, mWorldFastestSector2Time=23.9, mWorldFastestSector3Time=24.3)`. Call `_parse_packets()`. Assert `state["session"]["world_fastest_lap"] == pytest.approx(72.341)` and `state["session"]["world_fastest_sectors"] == [pytest.approx(24.1), pytest.approx(23.9), pytest.approx(24.3)]`. Must FAIL.
- [ ] T028 [P] [US1] In `tests/test_bridge_udp.py`, write test `test_session_track_name_from_shm`: Mock `_shm` with `mTranslatedTrackLocation=b"Interlagos\x00..."` and `mTranslatedTrackVariation=b"Grand Prix\x00..."`. Call `_parse_packets()`. Assert `state["session"]["track_name"] == "Interlagos"` and `state["session"]["track_variation"] == "Grand Prix"`. Must FAIL.
- [ ] T029 [P] [US1] In `tests/test_bridge_udp.py`, write test `test_session_enforced_pit_stop_from_shm`: Mock `_shm` with `mEnforcedPitStopLap=15`. Call `_parse_packets()`. Assert `state["session"]["enforced_pit_stop_lap"] == 15`. Must FAIL.
- [ ] T030 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py::test_session -x -q"` — confirm 3 session tests FAIL.

### 3D: Implementation — Session Data from SharedMemory

- [ ] T031 [US1] In `dashboard/bridge.py` method `_parse_packets()`, in the "Session Info Update" block (line ~218), after `shm = getattr(self.main_app, '_shm', None)`, add: `if shm is not None:` block that reads `self.state["session"]["world_fastest_lap"] = getattr(shm, 'mWorldFastestLapTime', 0.0)`, `self.state["session"]["world_fastest_sectors"] = [getattr(shm, 'mWorldFastestSector1Time', 0.0), getattr(shm, 'mWorldFastestSector2Time', 0.0), getattr(shm, 'mWorldFastestSector3Time', 0.0)]`, track name from `getattr(shm, 'mTranslatedTrackLocation', b'')` decoded and stripped, track variation similarly, and `self.state["session"]["enforced_pit_stop_lap"] = getattr(shm, 'mEnforcedPitStopLap', -1)`.
- [ ] T032 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — all session tests PASS.

### 3E: TDD Tests — Weather from SharedMemory (write FIRST, must FAIL) ⚠️

- [ ] T033 [US1] In `tests/test_bridge_udp.py`, write test `test_weather_from_shm`: Mock `_shm` with `mAmbientTemperature=29.0, mTrackTemperature=42.0, mRainDensity=0.5, mSnowDensity=0.0, mWindSpeed=8.0`. Call `_parse_packets()`. Assert `state["weather"]["ambient_temp"] == pytest.approx(29.0)`, `state["weather"]["track_temp"] == pytest.approx(42.0)`, `state["weather"]["rain_density"] == pytest.approx(0.5)`, `state["weather"]["wind_speed"] == pytest.approx(8.0)`. Must FAIL.
- [ ] T034 [US1] Run test — confirm FAIL.

### 3F: Implementation — Weather from SharedMemory

- [ ] T035 [US1] In `dashboard/bridge.py`, inside the `if shm is not None:` block added in T031, add: `self.state["weather"]["ambient_temp"] = getattr(shm, 'mAmbientTemperature', 0.0)`, `self.state["weather"]["track_temp"] = getattr(shm, 'mTrackTemperature', 0.0)`, `self.state["weather"]["rain_density"] = getattr(shm, 'mRainDensity', 0.0)`, `self.state["weather"]["snow_density"] = getattr(shm, 'mSnowDensity', 0.0)`, `self.state["weather"]["wind_speed"] = getattr(shm, 'mWindSpeed', 0.0)`.
- [ ] T036 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — weather test PASSES.

### 3G: TDD Tests — Per-Driver Timing Stats from SharedMemory (write FIRST, must FAIL) ⚠️

- [ ] T037 [US1] In `tests/test_bridge_udp.py`, write test `test_leaderboard_timing_stats_from_shm`: Mock `_shm` with `mFastestLapTimes[0]=72.5, mLastLapTimes[0]=73.1, mCurrentSector1Times[0]=24.2, mCurrentSector2Times[0]=24.0, mFastestSector1Times[0]=23.9, mFastestSector2Times[0]=23.8, mFastestSector3Times[0]=24.1`. Set up `main_app._participants` with one active driver at index 0. Call `_parse_packets()`. Assert leaderboard[0] contains `"fastest_lap": pytest.approx(72.5)`, `"last_lap": pytest.approx(73.1)`, `"current_sectors": [pytest.approx(24.2), pytest.approx(24.0), pytest.approx(0.0)]`, `"fastest_sectors": [pytest.approx(23.9), pytest.approx(23.8), pytest.approx(24.1)]`. Must FAIL.
- [ ] T038 [US1] Run test — confirm FAIL.

### 3H: Implementation — Per-Driver Timing Stats from SharedMemory

- [ ] T039 [US1] In `dashboard/bridge.py`, inside the leaderboard construction loop (line ~256, `for p in active_drivers:`), after the existing `"pit": p.get("pit_mode")` line, add new fields to the leaderboard dict: look up the participant's index (find the key from `participants_dict` where value is `p`), then read `shm.mFastestLapTimes[idx]`, `shm.mLastLapTimes[idx]`, `shm.mCurrentSector1Times[idx]` / `2` / `3`, `shm.mFastestSector1Times[idx]` / `2` / `3`. Add to each entry: `"fastest_lap"`, `"last_lap"`, `"current_sectors": [s1, s2, s3]`, `"fastest_sectors": [s1, s2, s3]`. Guard with `if shm is not None and idx < len(shm.mFastestLapTimes):`. Use 0.0 defaults if shm is None.
- [ ] T040 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — timing stats test PASSES.

### 3I: TDD Tests — Behind Driver (write FIRST, must FAIL) ⚠️

- [ ] T041 [US1] In `tests/test_bridge_udp.py`, write test `test_behind_driver_populated`: Set up bridge with `main_app._participants` containing 3 drivers at positions 1, 2, 3. Set `viewed_index` to the driver at position 2. Set `split_behind` to 1.5. Call `_parse_packets()`. Assert `state["behind"]["name"]` equals the P3 driver's name, `state["behind"]["position"] == 3`, `state["behind"]["gap_seconds"] == pytest.approx(1.5)`. Must FAIL.
- [ ] T042 [P] [US1] In `tests/test_bridge_udp.py`, write test `test_behind_driver_empty_for_last_place`: Set up bridge with viewed driver at last position. Call `_parse_packets()`. Assert `state["behind"]["name"] == ""`. Must FAIL.
- [ ] T043 [US1] Run tests — confirm FAIL.

### 3J: Implementation — Behind Driver

- [ ] T044 [US1] In `dashboard/bridge.py`, in the post-processing block (line ~196), after the `ahead` computation block, add mirror logic for `behind`: find the driver with `race_position == viewed_position + 1`. If found, set `state["behind"]["name"]`, `state["behind"]["position"]`, `state["behind"]["gap_seconds"] = self.state.get("split_behind", 0.0)`. If no driver behind (last place), set `state["behind"]["name"] = ""`, position 0, gap 0.0.
- [ ] T045 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — behind tests PASS.

### 3K: TDD Tests — Nationality + Vehicle Names Extensions (write FIRST, must FAIL) ⚠️

- [ ] T046 [US1] In `tests/test_bridge_udp.py`, write test `test_leaderboard_has_nationality_and_car_info`: Set up bridge with `main_app._participants` and mock SharedMemory with `mNationalities[0]=81` (British), `mCarNames[0]=b"Formula Ultimate Gen 2"`, `mCarClassNames[0]=b"Formula Ultimate Gen 2"`. Call `_parse_packets()`. Assert `leaderboard[0]["nationality"] == 81`, `"car_name" == "Formula Ultimate Gen 2"`, and `"car_class" == "Formula Ultimate Gen 2"`. Must FAIL.
- [ ] T047 [US1] Run test — confirm FAIL.

### 3L: Implementation — Nationality + Vehicle Names in Leaderboard

- [ ] T048 [US1] In `dashboard/bridge.py`, in the leaderboard construction loop, add: `"nationality": shm.mNationalities[idx] if shm and idx < len(getattr(shm, 'mNationalities', [])) else 0`, `"car_name": shm.mCarNames[idx].split(b'\x00')[0].decode('utf-8', errors='replace').strip() if shm and idx < len(getattr(shm, 'mCarNames', [])) else ""`, and `"car_class": shm.mCarClassNames[idx].split(b'\x00')[0].decode('utf-8', errors='replace').strip() if shm and idx < len(getattr(shm, 'mCarClassNames', [])) else ""` to each entry dict.
- [ ] T049 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — nationality test PASSES.

### 3M: TDD Tests — Director State (write FIRST, must FAIL) ⚠️

- [ ] T050 [US1] In `tests/test_bridge_udp.py`, write test `test_director_state_broadcast`: Set up bridge with `main_app.camera_controller.current_camera_type = "cockpit"` and `main_app.is_enabled = True`. Call `_parse_packets()`. Assert `state["director"]["camera_type"] == "cockpit"` and `state["director"]["is_auto_directing"] == True`. Must FAIL.
- [ ] T051 [US1] Run test — confirm FAIL.

### 3N: Implementation — Director State

- [ ] T052 [US1] In `dashboard/bridge.py` method `_parse_packets()`, before `return changed`, add: `cam_ctrl = getattr(self.main_app, 'camera_controller', None)`, `self.state["director"]["camera_type"] = getattr(cam_ctrl, 'current_camera_type', 'tv_cam') if cam_ctrl else 'tv_cam'`, `self.state["director"]["is_auto_directing"] = getattr(self.main_app, 'is_enabled', False)`.
- [ ] T053 [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/ -x -q"` — ALL tests pass (full anti-regression).

**Checkpoint**: Bridge state JSON now contains all extended telemetry from SharedMemory.

### 3O: TDD Tests — UDP Fallbacks (write FIRST, must FAIL) ⚠️

- [ ] T053a [US1] In `tests/test_bridge_udp.py`, write test `test_udp_fallback_session_data`: Create bridge with `main_app._shm = None` and `packet_buffer = {308: make_udp_race_data_packet()}`. Call `_parse_packets()`. Assert `state["session"]["world_fastest_lap"]`, `world_fastest_sectors`, `track_name`, `track_variation`, and `enforced_pit_stop_lap` match the 308b mock values. Must FAIL.
- [ ] T053b [US1] In `tests/test_bridge_udp.py`, write test `test_udp_fallback_weather`: Create bridge with `main_app._shm = None` and `packet_buffer = {24: make_udp_game_state_packet()}`. Call `_parse_packets()`. Assert `state["weather"]["ambient_temp"]`, etc. match the 24b mock values. Must FAIL.
- [ ] T053c [US1] In `tests/test_bridge_udp.py`, write test `test_udp_fallback_timing_stats`: Create bridge with `main_app._shm = None`, a mocked participant at index 0, and `packet_buffer = {1040: make_udp_time_stats_packet(stats=[{"fastest_lap": 72.5, "last_lap": 73.1, ...}])}`. Call `_parse_packets()`. Assert `leaderboard[0]["fastest_lap"] == 72.5` and `fastest_sectors` match the 1040b mock. Must FAIL.
- [ ] T053d [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — confirm 3 fallback tests FAIL.

### 3P: Implementation — UDP Fallbacks

- [ ] T053e [US1] In `dashboard/bridge.py` method `_parse_packets()`, add an `else:` block after `if shm is not None:` (from T031) to parse the 308-byte packet (`p308 = self.packet_buffer.get(308)`) and populate the session fields. Use `struct.unpack_from` and decode strings safely.
- [ ] T053f [US1] In `dashboard/bridge.py`, add an `else:` block after `if shm is not None:` (from T035) to parse the 24-byte packet (`p24 = self.packet_buffer.get(24)`) and populate the weather fields.
- [ ] T053g [US1] In `dashboard/bridge.py`, add an `else:` block after `if shm is not None:` (from T039) inside the leaderboard loop to parse the 1040-byte packet (`p1040 = self.packet_buffer.get(1040)`) for `fastest_lap`, `last_lap`, and `fastest_sectors` (using `struct.unpack_from('<6f', p1040, 16 + idx*32)`).
- [ ] T053h [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_bridge_udp.py -x -q"` — all fallback tests PASS.
- [ ] T053i [US1] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/ -x -q"` — ALL tests pass (full anti-regression).

**Checkpoint**: Bridge state JSON now correctly handles both SharedMemory (primary) and UDP fallbacks. US1 complete and independently testable.

---

## Phase 4: User Story 2 — Monolithic HTML Overlay (Priority: P1)

**Goal**: Single `f1tv_overlay.html` connects to bridge WebSocket and renders all overlay components at 1920×1080 with transparent background.

**Independent Test**: Open in browser → verify components render with mock/live data, toggle panel works.

> **Note**: HTML/CSS/JS is not pytest-testable. Verification is via browser subagent visual checks after each component group.

### 4A: HTML Shell + WebSocket Connection

- [x] T054 [US2] Create `dashboard/f1tv_overlay.html` with: `<!DOCTYPE html>`, viewport meta 1920×1080, `<style>` block with `body { margin:0; background:transparent; overflow:hidden; width:1920px; height:1080px; font-family:'Formula1',sans-serif; }`, `@font-face` loading `Formula1-Bold.ttf` from `_SHFonts/Formula1-Bold.ttf`. Add empty `<div id="overlay-container">` and a `<script>` block.
- [x] T055 [US2] In the `<script>` block of `f1tv_overlay.html`, add WebSocket connection logic: `const ws = new WebSocket('ws://' + location.host + '/ws');`, `let state = {};`, `ws.onmessage = (e) => { state = JSON.parse(e.data); updateAll(); };`, `ws.onclose = () => setTimeout(connect, 2000);`. Wrap in a `function connect()` and call on load. Add empty `function updateAll() {}`.
- [x] T056 [US2] Add a `<div id="connection-status">` at top-left showing "CONNECTED" (green) or "DISCONNECTED" (red) based on WebSocket state. Style: `position:absolute; top:4px; left:4px; font-size:10px; opacity:0.5; z-index:9999;`.

### 4B: CSS Design System

- [x] T057 [US2] In the `<style>` block, add CSS variables (`:root`): `--f1-red: #E10600;`, `--f1-white: #FFFFFF;`, `--f1-black: #15151E;`, `--f1-dark-grey: #38383F;`, `--f1-light-grey: #949498;`, `--f1-timing-green: #00FF00;`, `--f1-timing-purple: #A020F0;`, `--f1-timing-yellow: #FFD700;`, `--panel-bg: rgba(21,21,30,0.85);`, `--panel-border: rgba(255,255,255,0.1);`, `--transition-speed: 0.3s;`.
- [x] T058 [US2] Add base overlay component class: `.overlay-component { position:absolute; transition: opacity var(--transition-speed), transform var(--transition-speed); }`, `.overlay-component.hidden { opacity:0; pointer-events:none; }`, `.overlay-component.slide-left { transform:translateX(-100%); }`, `.overlay-component.slide-right { transform:translateX(100%); }`, `.overlay-component.slide-up { transform:translateY(-100%); }`.

### 4C: Settings Panel

- [x] T059 [US2] Add `<div id="settings-panel">` with style: `position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); background:var(--panel-bg); border:1px solid var(--panel-border); border-radius:12px; padding:24px; z-index:10000; display:none; backdrop-filter:blur(10px); min-width:320px; color:var(--f1-white); font-size:14px;`. Title: `<h3>F1TV Overlay Settings</h3>`.
- [x] T060 [US2] Inside settings panel, add a checkbox for each overlay component: `Full Leaderboard`, `Mini Leaderboard`, `Driver Name`, `Lap Timer`, `Live Speed`, `Ahead & Behind`, `Session Info`, `Fastest Lap`, `Fastest Sectors`, `Speedometer`, `Car Damage`, `Pit Window`, `Weather`, `Data Channel`, `Pit Timer`. Each checkbox has `id="toggle-{component-name}"` and `checked` by default. Style checkboxes with F1 red accent.
- [x] T061 [US2] Add preset buttons row below checkboxes: `Broadcast` (enables broadcast overlays, disables cockpit), `Cockpit` (enables cockpit overlays, disables broadcast), `All On`, `All Off`. Style as pill buttons with `background:var(--f1-dark-grey); border-radius:20px; padding:6px 16px; color:white; cursor:pointer;`.
- [x] T062 [US2] Add JavaScript: `document.addEventListener('keydown', (e) => { if(e.key === 'Tab') { e.preventDefault(); toggleSettings(); }});`. `function toggleSettings() { const p = document.getElementById('settings-panel'); p.style.display = p.style.display === 'none' ? 'block' : 'none'; }`. Save toggle states to `localStorage` on change, restore on page load.
- [x] T063 [US2] Add URL parameter handling: on page load, parse `?preset=broadcast` or `?preset=cockpit` or `?preset=all`. Apply preset by programmatically setting checkboxes accordingly. Broadcast preset: all broadcast overlays ON, cockpit overlays OFF. Cockpit preset: cockpit overlays ON, broadcast overlays OFF.

### 4D: Overlay Component — Driver Name Badge (bottom-center)

- [x] T064 [US2] Add `<div id="driver-name" class="overlay-component">` positioned at `bottom:60px; left:50%; transform:translateX(-50%);`. Inner HTML: position number box (colored bg), driver name text, team colour strip. Style: `background:var(--panel-bg); border-radius:4px; padding:8px 20px; display:flex; align-items:center; gap:12px; font-size:22px; color:white;`.
- [x] T065 [US2] In `updateAll()`, add: `const dn = document.getElementById('driver-name');` Set position number from `state.viewed.position`, name from `state.viewed.name`. Look up team colour from `teamLookup[state.leaderboard[viewedIdx]?.car_class]` if available, else use `var(--f1-dark-grey)`.

### 4E: Overlay Component — Lap Timer (top-center)

- [x] T066 [US2] Add `<div id="lap-timer" class="overlay-component">` at `top:20px; left:50%; transform:translateX(-50%);`. Shows current lap time, sector splits (S1/S2/S3) with colour coding (green=personal best, purple=session best, yellow=normal). Style: `background:var(--panel-bg); border-radius:4px; padding:8px 16px; display:flex; gap:16px; font-size:18px; color:white;`.
- [x] T067 [US2] In `updateAll()`, populate lap timer from `state.leaderboard[viewedIdx].current_sectors` and compare against `state.leaderboard[viewedIdx].fastest_sectors` and `state.session.world_fastest_sectors` for colour coding.

### 4F: Overlay Component — Live Speed (bottom-right)

- [x] T068 [US2] Add `<div id="live-speed" class="overlay-component">` at `bottom:60px; right:40px;`. Shows speed as large number with "KPH" label. Style: `font-size:48px; font-weight:bold; color:white; text-shadow:0 2px 8px rgba(0,0,0,0.8);`.
- [x] T069 [US2] In `updateAll()`, set speed text from `Math.round(state.viewed.speed_kph)`.

### 4G: Overlay Component — Ahead & Behind (bottom-center, below driver name)

- [x] T070 [US2] Add `<div id="ahead-behind" class="overlay-component">` at `bottom:20px; left:50%; transform:translateX(-50%);`. Two rows: ahead driver (name + gap with green arrow up) and behind driver (name + gap with red arrow down). Style: `background:var(--panel-bg); border-radius:4px; padding:6px 16px; font-size:14px; display:flex; gap:24px;`.
- [x] T071 [US2] In `updateAll()`, populate from `state.ahead` and `state.behind`. Format gap as `+X.XXXs`. Hide if name is empty.

### 4H: Overlay Component — Session Info (top-right)

- [x] T072 [US2] Add `<div id="session-info" class="overlay-component">` at `top:20px; right:20px;`. Shows track name, lap count (`Lap X/Y`), time remaining (formatted as `H:MM:SS`), weather icon (sun/rain/snow based on density). Style: `background:var(--panel-bg); border-radius:4px; padding:10px 16px; text-align:right; font-size:14px; color:white;`.
- [x] T073 [US2] In `updateAll()`, populate track name from `state.session.track_name`, laps from `state.session.leader_lap` / `state.session.laps_in_event`, time from `state.session.time_remaining` (format as countdown). Show weather emoji: ☀️ if rain<0.1, 🌧️ if rain>0.3, ⛈️ if rain>0.7, ❄️ if snow>0.1.

### 4I: Overlay Component — Mini Leaderboard (top-left)

- [x] T074 [US2] Add `<div id="mini-leaderboard" class="overlay-component">` at `top:20px; left:20px;`. Shows top 5 drivers: position, name (abbreviated to 3-letter code), gap to leader. Each row styled with alternating `var(--f1-black)` / `var(--f1-dark-grey)` backgrounds. Viewed driver row highlighted with team colour left border. Style: `border-radius:4px; overflow:hidden; font-size:13px; min-width:200px;`.
- [x] T075 [US2] In `updateAll()`, populate from first 5 entries of `state.leaderboard`. Create 3-letter codes from driver names (first 3 chars of surname). Highlight viewed driver's row. Format gap as "+X.XXXs" or "LEADER" for P1.

### 4J: Overlay Component — Fastest Lap (event-driven, animated)

- [x] T076 [US2] Add `<div id="fastest-lap" class="overlay-component hidden">` at `top:150px; left:50%; transform:translateX(-50%);`. Shows "FASTEST LAP" header, driver name, lap time. Style: `background:linear-gradient(135deg, var(--f1-timing-purple), #6B0F9E); border-radius:8px; padding:16px 32px; text-align:center; font-size:20px; color:white;`.
- [x] T077 [US2] In `updateAll()`, track `prevFastestLap` variable. When `state.session.world_fastest_lap` changes to a new valid value, show the element with CSS animation (fade in, hold 5s, fade out). Find who set it by scanning `state.leaderboard` for matching `fastest_lap`.

### 4K: Overlay Component — Weather Panel (top-right, below session info)

- [x] T078 [US2] Add `<div id="weather-panel" class="overlay-component">` at `top:100px; right:20px;`. Shows: Air temp (`state.weather.ambient_temp` °C), Track temp (`state.weather.track_temp` °C), rain density as bar, wind speed. Style: compact grid, `background:var(--panel-bg); border-radius:4px; padding:8px 12px; font-size:12px; color:var(--f1-light-grey);`.
- [x] T079 [US2] In `updateAll()`, populate from `state.weather.*`. Show rain bar as percentage filled div.

### 4L: Overlay Component — Pit Window (left-bottom)

- [x] T080 [US2] Add `<div id="pit-window" class="overlay-component">` at `bottom:120px; left:20px;`. Shows: "PIT WINDOW" label, mandatory pit lap number, current tyre compound for viewed driver. Style: `background:var(--panel-bg); border-radius:4px; padding:8px 16px; font-size:14px;`.
- [x] T081 [US2] In `updateAll()`, populate pit lap from `state.session.enforced_pit_stop_lap` (hide if -1), tyre compound from `state.viewed.tyre_compound[0]`. Colour-code compound: red=Soft, yellow=Medium, white=Hard, green=Inter, blue=Wet.

### 4M: Overlay Component — Full Leaderboard (left edge)

- [x] T082 [US2] Add `<div id="full-leaderboard" class="overlay-component hidden">` at `top:20px; left:20px; bottom:20px;`. Scrollable list of all drivers. Each row: position number, team colour bar, 3-letter name code, last lap time, gap to leader, pit indicator (P icon if in pits). Style rows at `height:32px;` with `font-size:13px;`. Alternate row backgrounds.
- [x] T083 [US2] In `updateAll()`, rebuild leaderboard rows from `state.leaderboard`. Highlight viewed driver. Show pit icon for `pit > 0`. Format times as `M:SS.mmm`.

### 4N: Overlay Component — Fastest Sectors (event-driven)

- [x] T084 [US2] Add `<div id="fastest-sectors" class="overlay-component hidden">` at `top:150px; right:20px;`. Shows S1/S2/S3 session best times. Style similar to fastest lap but smaller. Appears when any sector record changes, holds 4s, fades out.
- [x] T085 [US2] In `updateAll()`, track `prevFastestSectors[]`. On change, animate in/out.

### 4O: Browser Verification

- [x] T086 [US2] Open `http://localhost:8765/f1tv_overlay.html` in browser. Verify: page loads, WebSocket connects (connection status shows green), settings panel opens on Tab press, all overlay divs exist in DOM. If bridge is not running, verify page loads without errors and shows "DISCONNECTED".
- [x] T087 [US2] Verify all toggle checkboxes in settings panel work: toggling each hides/shows the corresponding overlay div. Verify `localStorage` persistence: toggle some off, refresh page, verify they remain off.

**Checkpoint**: All broadcast-mode overlays render. Settings panel toggles work. US2 complete and independently testable.

---

## Phase 5: User Story 3 — Cockpit-View-Only Overlays (Priority: P2)

**Goal**: Overlays auto-switch visibility based on `director.camera_type`. Cockpit overlays (Speedometer, Car Damage) show only in cockpit### 5A: TDD Tests — Camera Type Tracking (write FIRST, must FAIL) ⚠️

- [x] T088 [US3] In `tests/test_camera_type.py`, write test `test_camera_type_default_is_tv_cam`: Create `CameraController()`. Assert `controller.current_camera_type == "tv_cam"`. This should PASS already (set in T013).
- [x] T089 [US3] In `tests/test_camera_type.py`, write test `test_camera_type_updates_on_set`: Create `CameraController()`. Call `controller.current_camera_type = "cockpit"`. Assert `controller.current_camera_type == "cockpit"`. Should PASS (it's a plain attribute).
- [x] T090 [US3] In `tests/test_camera_type.py`, write test `test_camera_set_mappings`: Write a test that validates a mapping dict `CAMERA_SET_MAP` exists in `camera_controller.py` mapping AMS2 camera set names to types: `{"Cockpit": "cockpit", "Helmet": "cockpit", "TV Pod": "cockpit", "TV Cam 1": "tv_cam", "TV Cam 2": "tv_cam", "TV Cam 3": "tv_cam", "Chase Near": "chase", "Chase Far": "chase", "Chase Bumper": "chase"}`. Import and assert keys exist. Must FAIL (constant doesn't exist yet).
- [x] T091 [US3] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_camera_type.py -x -q"` — confirm T090 FAILS.

### 5B: Implementation — Camera Type Tracking

- [x] T092 [US3] In `core/camera_controller.py`, add module-level constant `CAMERA_SET_MAP` (dict) mapping camera set names to camera types: `"Cockpit": "cockpit"`, `"Helmet": "cockpit"`, `"TV Pod": "cockpit"`, `"TV Cam 1": "tv_cam"`, `"TV Cam 2": "tv_cam"`, `"TV Cam 3": "tv_cam"`, `"Chase Near": "chase"`, `"Chase Far": "chase"`, `"Chase Bumper": "chase"`. Add method `def update_camera_type(self, camera_set_name: str):` that looks up the name in `CAMERA_SET_MAP` and sets `self.current_camera_type`. Default to `"tv_cam"` if name not found.
- [x] T093 [US3] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_camera_type.py -x -q"` — all PASS.

### 5C: Cockpit-Only HTML Overlay Components

- [x] T094 [US3] In `dashboard/f1tv_overlay.html`, add `<div id="speedometer" class="overlay-component cockpit-only hidden">` at `bottom:200px; left:50%; transform:translateX(-50%);`. Circular or horizontal gauge showing speed (large number), RPM bar (filled proportional to `rpm/max_rpm`), gear number (large centered), brake bar (red, left), throttle bar (green, right). Style: `width:300px; height:200px; background:var(--panel-bg); border-radius:8px; padding:16px;`.
- [x] T095 [US3] In `updateAll()`, populate speedometer: speed from `state.viewed.speed_kph`, RPM bar width as `(state.viewed.rpm / state.viewed.max_rpm) * 100%`, gear from `state.viewed.gear`, brake bar height from `state.viewed.brake * 100%` (red fill), throttle bar height from `state.viewed.throttle * 100%` (green fill).
- [x] T096 [US3] Add `<div id="car-damage" class="overlay-component cockpit-only hidden">` at `right:40px; top:50%; transform:translateY(-50%);`. Shows car silhouette outline with 4 corner indicators (FL/FR/RL/RR) for suspension and brake damage (coloured green→yellow→red based on damage value 0→1), plus aero and engine damage bars. Style: `width:180px; background:var(--panel-bg); border-radius:8px; padding:12px;`.
- [x] T097 [US3] In `updateAll()`, populate car damage: read `state.viewed.suspension_damage[0-3]`, `state.viewed.brake_damage[0-3]`, `state.viewed.aero_damage`, `state.viewed.engine_damage`. Map 0.0=green (#00FF00), 0.5=yellow (#FFD700), 1.0=red (#FF0000) using HSL interpolation or stepped thresholds.

### 5D: Visibility Mode Logic (JavaScript)

- [x] T098 [US3] In `f1tv_overlay.html` script, add a `function updateVisibilityMode()` that reads `state.director.camera_type`. If `"cockpit"`: show all elements with class `cockpit-only`, hide elements with class `broadcast-only`. If `"tv_cam"` or `"chase"`: show `broadcast-only`, hide `cockpit-only`. Call this from `updateAll()`.
- [x] T099 [US3] Add CSS class `broadcast-only` to these existing overlay divs: `#driver-name`, `#ahead-behind`. Add class `cockpit-only` to: `#speedometer`, `#car-damage`. All other overlays have class `always-visible` (no mode filtering).
- [x] T100 [US3] Ensure settings panel toggles still override visibility mode: if user has manually toggled an overlay OFF, it stays off regardless of camera mode. Implement as: `if checkbox unchecked → always hidden; if checked → follow visibility mode rules`.
- [x] T101 [US3] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/ -x -q"` — anti-regression: all tests pass.

**Checkpoint**: Cockpit/broadcast mode auto-switching works. Speedometer and car damage display in cockpit view. US3 complete.

---

## Phase 6: User Story 4 — Pit Timer Overlay (Priority: P2)

**Goal**: Track pit_mode state transitions per driver, calculate pit durations, display animated pit timer overlay with pit count and laps since last pit.

**Independent Test**: Simulate pit_mode transitions via mock data → verify pit events tracked with correct durations.

### 6A: TDD Tests — Pit Tracker State Machine (write FIRST, must FAIL) ⚠️

- [x] T102 [US4] In `tests/test_pit_tracker.py` (create file), write test `test_pit_entry_recorded`: Mock telemetry participants dict with `driver_0: pit_mode=1`. Call `_update_pit_tracker(participants)`. Assert `driver_0` in tracker, `entry_time` set, `in_progress=True`, `pit_count=1`.
- [x] T103 [US4] In `tests/test_pit_tracker.py`, write test `test_pit_exit_calculates_duration`: Mock telemetry with `driver_0: pit_mode=0`, but tracker previously had `prev_pit_mode=3` (exiting). Assert `duration` calculated correctly, `in_progress=False`.
- [x] T104 [US4] In `tests/test_pit_tracker.py`, write test `test_pit_count_increments`: Simulate two full pit cycles. Assert `pit_count=2`.
- [x] T105 [US4] In `tests/test_pit_tracker.py`, write test `test_laps_since_last_pit`: Mock `current_lap=23`, last `exit_lap=10`. Assert `laps_since_last_pit=13`.
- [x] T106 [US4] In `tests/test_pit_tracker.py`, write test `test_multiple_drivers_pit_simultaneously`: Ensure tracker handles 2 drivers in pit lane simultaneously.
- [x] T107 [US4] In `tests/test_pit_tracker.py`, write test `test_pit_events_list_contains_recent`: Ensure `bridge._pit_events` list only returns drivers currently `in_progress`, or exited within the last 10 seconds.
- [x] T108 [US4] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_pit_tracker.py -x -q"` — confirm they FAIL.

### 6B: Implementation — Pit Tracker State Machine

- [x] T109 [US4] In `dashboard/bridge.py`, add method `def _update_pit_tracker(self, participants: dict):`. Logic: iterate over participants. For each driver index, compare current `pit_mode` with `self._pit_tracker.get(idx, {}).get("prev_pit_mode", 0)`. State transitions: if prev=0 and current=1 → record `entry_time=time.time()`, `entry_lap=p["current_lap"]`, `in_progress=True`, increment `pit_count`. If prev=3 and current=0 → record `exit_time=time.time()`, calculate `duration=exit_time-entry_time`, set `in_progress=False`, record `exit_lap=p["current_lap"]`. Always update `prev_pit_mode=current`. Store per-driver in `self._pit_tracker[idx]`.
- [x] T110 [US4] In `_update_pit_tracker()`, after processing transitions, build `self._pit_events` list: collect all entries from `self._pit_tracker` where `in_progress == True` OR `exit_time` was set within last 10 seconds. Each event dict: `{"driver_name": str, "position": int, "entry_time": float, "exit_time": float|None, "duration": float|None, "in_progress": bool, "pit_count": int, "entry_lap": int, "laps_since_last_pit": int}`. Calculate `laps_since_last_pit = p["current_lap"] - last_exit_lap` (or -1 if first pit).
- [x] T111 [US4] In `_parse_packets()`, call `self._update_pit_tracker(participants_dict)` after the participants dict is available (line ~195), and set `self.state["pit_events"] = self._pit_events`.
- [x] T112 [US4] Add `import time` at top of `dashboard/bridge.py` if not already present.
- [x] T113 [US4] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/test_pit_tracker.py -x -q"` — confirm all PASS.
- [x] T114 [US4] Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/ -x -q"` — anti-regression: all tests pass.

### 6C: Pit Timer HTML Overlay Component

- [x] T115 [US4] In `dashboard/f1tv_overlay.html`, add `<div id="pit-timer" class="overlay-component hidden">` at `top:50%; left:50%; transform:translate(-50%,-50%);`. Shows: "PIT STOP" header, driver name, running timer (MM:SS.m format), pit count badge ("PIT 2"), laps since last pit ("12 LAPS SINCE LAST"). Style: `background:linear-gradient(135deg, var(--f1-red), #8B0000); border-radius:8px; padding:20px 40px; text-align:center; font-size:24px; color:white; min-width:280px;`.
- [x] T116 [US4] In `updateAll()`, check `state.pit_events`. For each event with `in_progress == true`, show the pit-timer div with animated running time (use `Date.now()` or receive dynamic duration). For recently completed events (within last 5 seconds), show final duration briefly then fade out. If multiple active, stack vertically or show the most recent.
- [x] T117 [US4] Add CSS animation for pit timer: `@keyframes pit-pulse { 0% { box-shadow: 0 0 0 0 rgba(225,6,0,0.7); } 70% { box-shadow: 0 0 0 20px rgba(225,6,0,0); } 100% { box-shadow: 0 0 0 0 rgba(225,6,0,0); } }`. Apply to active pit timer: `.pit-active { animation: pit-pulse 1.5s infinite; }`.
- [x] T118 [US4] Add pit count and laps-since-pit to leaderboard entries in `f1tv_overlay.html`: in the full leaderboard, append a small "P1" / "P2" badge showing `pit_count` if > 0, and show `laps_since_last_pit` as a tooltip or small text.

**Checkpoint**: Animated pit timer displays when a car pits, capturing total duration accurately. US4 complete.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final integration, OBS configuration notes, documentation.

- [ ] T119 Add `data-mode` attributes to all overlay component divs: `data-mode="broadcast"`, `data-mode="cockpit"`, or `data-mode="always"`. Use these in `updateVisibilityMode()` instead of CSS classes for cleaner logic.
- [ ] T120 [P] Add CSS micro-animations: slide-in from edges for leaderboard (left), session info (right), driver name (bottom). Use `@keyframes slideInLeft`, `slideInRight`, `slideInUp` with `transform` transitions triggered on first data arrival.
- [ ] T121 [P] Add a `function formatLapTime(seconds)` utility in JS that formats `92.341` as `1:32.341`. If `seconds` is 0.0, null, or undefined, it MUST return `"--:--.---"` as a placeholder. Use this throughout all time and sector displays.
- [ ] T122 [P] Add a `function formatSpeed(kph)` utility that returns `Math.round(kph)` or `"--"` if 0.0. Use for speed displays.
- [ ] T122a [P] Add a `function getDriverCode(fullName)` utility that extracts 3-letter code from surname: split by space, take last word, uppercase first 3 chars. E.g. "Max Verstappen" → "VER".
- [ ] T123 [P] Load `team_lookup.json` via fetch on page load: `fetch('team_lookup.json').then(r => r.json()).then(data => { teamLookup = data; });`. Use throughout for team colour lookups.
- [ ] T124 [P] Add OBS integration notes as an HTML comment at top of `f1tv_overlay.html`: `<!-- OBS Browser Source: URL=http://localhost:8765/f1tv_overlay.html, Width=1920, Height=1080, Custom CSS: body{background:transparent;} -->`.
- [ ] T125 [P] Add `?debug=true` URL parameter support: when active, show faint grid lines at 1920×1080, component bounding boxes, and log all WebSocket messages to console.
- [ ] T126 Run `cmd /c "cd AMS2_Auto_Director4.0 && python -m pytest tests/ -x -q"` — final anti-regression: ALL tests pass.
- [ ] T127 Open `http://localhost:8765/f1tv_overlay.html` in browser for final visual verification: all overlays positioned correctly, settings panel works, no JS console errors.

**Checkpoint**: Full F1TV overlay suite complete. All overlays functional, OBS-ready, tests passing.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
- **US1 Bridge Telemetry (Phase 3)**: Depends on Phase 2
- **US2 HTML Overlay (Phase 4)**: Depends on Phase 3 (needs bridge data)
- **US3 Cockpit Mode (Phase 5)**: Depends on Phase 3 + Phase 4
- **US4 Pit Timer (Phase 6)**: Depends on Phase 3
- **Polish (Phase 7)**: Depends on all above

### Within Each User Story (TDD)

1. Write test → confirm FAIL
2. Implement minimum code to make test PASS
3. Next test → confirm FAIL
4. Implement → PASS
5. Repeat until story complete

## Notes

- [P] tasks = different files, no dependencies
- TDD: ALL tests written and FAILING before implementation code
- Commit after each task or logical group
- Stop at any checkpoint to validate
