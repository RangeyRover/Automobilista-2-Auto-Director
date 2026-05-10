import asyncio
import time
import json
import os
import struct
import threading
import websockets
import http
import mimetypes
import logging

# Suppress websockets connection/EOF tracebacks flooding the console
logging.getLogger("websockets.server").setLevel(logging.CRITICAL)

from core.models.sector_tracker import SectorTrackerManager

class DashboardBridge:
    def __init__(self):
        self.packet_buffer = None
        self._running = False
        self._thread = None
        self._loop = None
        
        self.last_packets = {}
        self.clients = set()
        
        # Parsed state
        self.state = {
            "viewed_index": -1,
            "viewed": {
                "position": 0,
                "name": "",
                "gear": 0,
                "speed_kph": 0.0,
                "rpm": 0,
                "last_lap": 0.0,
                "brake": 0.0,
                "throttle": 0.0,
                "max_rpm": 0,
                "num_gears": 0,
                "crash_state": 0,
                "aero_damage": 0.0,
                "engine_damage": 0.0,
                "suspension_damage": [0.0, 0.0, 0.0, 0.0],
                "brake_damage": [0.0, 0.0, 0.0, 0.0],
                "tyre_wear": [0.0, 0.0, 0.0, 0.0],
                "tyre_compound": ["", "", "", ""]
            },
            "ahead": {
                "name": "",
                "gap_seconds": 0.0
            },
            "behind": {
                "name": "",
                "position": 0,
                "gap_seconds": 0.0
            },
            "weather": {
                "ambient_temp": 0,
                "track_temp": 0,
                "rain_density": 0.0,
                "snow_density": 0.0,
                "wind_speed": 0
            },
            "director": {
                "camera_type": "tv_cam",
                "is_auto_directing": False
            },
            "pit_events": [],
            "session": {
                "state": 0,
                "session_state": 0,
                "laps_in_event": 0,
                "leader_lap": 0,
                "time_remaining": 0.0,
                "yellow_flag_state": 0,
                "total_drivers": 0,
                "track_name": "",
                "track_variation": "",
                "world_fastest_lap": 0.0,
                "world_fastest_sectors": [0.0, 0.0, 0.0],
                "enforced_pit_stop_lap": -1
            },
            "leaderboard": []
        }
        self._pit_tracker = {}
        self._pit_events = []
        self._sector_manager = SectorTrackerManager()
        
        self.names = {}
        self.participants = {}
        self._tyre_compound_cache: dict[int, str] = {}
        
        # Debounce state for viewed_index changes
        self._viewed_idx_candidate = -1
        self._viewed_idx_count = 0

        # Load lookups
        self.team_lookup = {}
        lookup_path = os.path.join(os.path.dirname(__file__), "team_lookup.json")
        if os.path.exists(lookup_path):
            with open(lookup_path, 'r', encoding='utf-8') as f:
                self.team_lookup = json.load(f)
                
        self.driver_lookup = {}
        driver_lookup_path = os.path.join(os.path.dirname(__file__), "driver_lookup.json")
        if os.path.exists(driver_lookup_path):
            with open(driver_lookup_path, 'r', encoding='utf-8') as f:
                raw_lookup = json.load(f)
                self.driver_lookup = {k.lower().strip(): v for k, v in raw_lookup.items()}

    def start(self, provider, main_app):
        if self._running:
            return
        self.provider = provider
        self.main_app = main_app
        self.packet_buffer = provider._packet_buffer
        self._running = True
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def _run_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_main())

    async def _async_main(self):
        # Start WebSocket & HTTP server
        async with websockets.serve(
            self._ws_handler,
            "0.0.0.0",
            8765,
            process_request=self._process_request
        ):
            broadcast_task = asyncio.create_task(self._broadcast_loop())
            
            # Keep running until stopped
            while self._running:
                await asyncio.sleep(0.1)
                
            broadcast_task.cancel()

    async def _process_request(self, connection, request):
        """Serve HTTP requests for the dashboard directory."""
        from websockets.http11 import Response
        from websockets.datastructures import Headers
        from urllib.parse import unquote

        path = request.path
        if path == "/ws":
            return None  # Proceed to websocket handshake

        if path == "/":
            path = "/index.html"

        # URL-decode path so assets with spaces (e.g. 'Top Stroke.png')
        # resolve correctly — browsers encode spaces as %20 in HTTP requests
        path = unquote(path)
            
        web_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.abspath(os.path.join(web_dir, path.lstrip('/')))
        
        if not file_path.startswith(web_dir):
            return Response(http.HTTPStatus.FORBIDDEN, "Forbidden", Headers(), b"403 Forbidden")
            
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return Response(http.HTTPStatus.NOT_FOUND, "Not Found", Headers(), b"404 Not Found")
            
        with open(file_path, "rb") as f:
            content = f.read()
            
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = "application/octet-stream"
            
        return Response(
            http.HTTPStatus.OK, 
            "OK", 
            Headers([("Content-Type", content_type)]), 
            content
        )

    async def _ws_handler(self, websocket):
        self.clients.add(websocket)
        try:
            # Send immediate state on connect
            await websocket.send(json.dumps(self.state))
            async for message in websocket:
                # Allow control panels to bounce messages to overlays
                try:
                    data = json.loads(message)
                    if data.get("type") == "f1tv_config":
                        payload = json.dumps(data)
                        # Broadcast to all OTHER connected clients
                        websockets.broadcast([c for c in self.clients if c != websocket], payload)
                    elif data.get("type") == "save_json":
                        target_path = data.get("path", "")
                        content = data.get("content")
                        if target_path and content is not None:
                            web_dir = os.path.dirname(os.path.abspath(__file__))
                            file_path = os.path.abspath(os.path.join(web_dir, target_path.lstrip('/')))
                            if file_path.startswith(web_dir) and file_path.endswith('.json'):
                                with open(file_path, "w", encoding="utf-8") as f:
                                    json.dump(content, f, indent=2)
                                
                                # Hot reload lookups in memory
                                if "team_lookup.json" in target_path:
                                    self.team_lookup = content
                                elif "driver_lookup.json" in target_path:
                                    self.driver_lookup = {k.lower().strip(): v for k, v in content.items()}
                except Exception:
                    pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)

    async def _broadcast_loop(self):
        """Polls packet buffer at ~60Hz and broadcasts state changes."""
        while self._running:
            try:
                changed = self._parse_packets()
                if changed and self.clients:
                    payload = json.dumps(self.state)
                    # Broadcast to all connected clients
                    websockets.broadcast(self.clients, payload)
            except Exception as e:
                print(f"Broadcast Loop Error: {e}")
            
            await asyncio.sleep(0.016)  # ~60Hz

    def _update_pit_tracker(self, participants: dict):
        now = time.time()
        for idx, p in participants.items():
            if idx not in self._pit_tracker:
                self._pit_tracker[idx] = {"prev_pit_mode": 0}
                
            tracker = self._pit_tracker[idx]
            prev = tracker.get("prev_pit_mode", 0)
            current = p.get("pit_mode", 0)
            
            if prev == 0 and current == 1:
                tracker["entry_time"] = now
                tracker["entry_lap"] = p.get("current_lap", 0)
                tracker["in_progress"] = True
                tracker["pit_count"] = tracker.get("pit_count", 0) + 1
            elif prev == 3 and current == 0:
                tracker["exit_time"] = now
                if "entry_time" in tracker:
                    tracker["duration"] = now - tracker["entry_time"]
                tracker["in_progress"] = False
                tracker["exit_lap"] = p.get("current_lap", 0)
                
            tracker["prev_pit_mode"] = current

        self._pit_events = []
        for idx, tracker in self._pit_tracker.items():
            p = participants.get(idx)
            if not p:
                continue
                
            in_progress = tracker.get("in_progress", False)
            exit_time = tracker.get("exit_time")
            
            if in_progress or (exit_time and now - exit_time <= 10.0):
                exit_lap = tracker.get("exit_lap", -1)
                laps_since = p.get("current_lap", 0) - exit_lap if exit_lap >= 0 else -1
                
                duration = tracker.get("duration")
                if in_progress and "entry_time" in tracker:
                    duration = now - tracker["entry_time"]
                
                event = {
                    "driver_name": p.get("name", ""),
                    "position": p.get("race_position", 0),
                    "entry_time": tracker.get("entry_time"),
                    "exit_time": exit_time,
                    "duration": duration,
                    "in_progress": in_progress,
                    "pit_count": tracker.get("pit_count", 0),
                    "entry_lap": tracker.get("entry_lap", 0),
                    "laps_since_last_pit": laps_since
                }
                self._pit_events.append(event)
                tracker["laps_since_last_pit"] = laps_since

    def _parse_packets(self) -> bool:
        if self.packet_buffer is None or not hasattr(self, 'main_app'):
            return False
            
        changed = False

        # --- Viewed Index Debouncing ---
        raw_viewed_index = self.state["viewed_index"]
        p559 = self.packet_buffer.get(559) or self.packet_buffer.get(556)
        
        # Poll SHM at 60Hz if in shared_memory mode AND not in UDP effective source
        shm = None
        effective_source = getattr(self.main_app, '_effective_source', 'hybrid')
        if effective_source == 'hybrid' and getattr(self.main_app, '_mode', '') == 'shared_memory':
            shm = self.main_app._read_shared_memory()
            if shm is not None:
                current_time = getattr(shm, 'mCurrentTime', 0.0)
                if current_time != getattr(self, '_last_shm_time', -1.0):
                    self._last_shm_time = current_time
                    changed = True
        elif effective_source == 'hybrid':
            shm = getattr(self.main_app, '_shm', None)
        
        if p559:
            raw_viewed_index = p559[12]
        elif shm is not None:
            raw_viewed_index = getattr(shm, 'mViewedParticipantIndex', self.state["viewed_index"])

        if raw_viewed_index != self.state["viewed_index"]:
            if raw_viewed_index == self._viewed_idx_candidate:
                self._viewed_idx_count += 1
                if self._viewed_idx_count >= 10:
                    self.state["viewed_index"] = raw_viewed_index
                    self._viewed_idx_count = 0
                    changed = True
            else:
                self._viewed_idx_candidate = raw_viewed_index
                self._viewed_idx_count = 1
        else:
            self._viewed_idx_candidate = -1
            self._viewed_idx_count = 0
        # -------------------------------

        # 559 bytes - Telemetry (AMS2 uses 559, PCars2 used 556)
        if p559 and p559 != self.last_packets.get(559):
            self.last_packets[559] = p559
            changed = True
            self.state["viewed"]["speed_kph"] = struct.unpack_from('<f', p559, 36)[0] * 3.6
            self.state["viewed"]["rpm"] = struct.unpack_from('<H', p559, 40)[0]
            self.state["viewed"]["gear"] = p559[45] & 0x0F
            
            self.state["viewed"]["brake"] = p559[29] / 255.0
            self.state["viewed"]["throttle"] = p559[30] / 255.0
            self.state["viewed"]["max_rpm"] = struct.unpack_from('<H', p559, 42)[0]
            self.state["viewed"]["num_gears"] = (p559[45] >> 4) & 0x0F
            self.state["viewed"]["crash_state"] = p559[47]
            
            if len(p559) >= 538:
                self.state["viewed"]["aero_damage"] = p559[371] / 255.0
                self.state["viewed"]["engine_damage"] = p559[372] / 255.0
                self.state["viewed"]["suspension_damage"] = [p559[204+i] / 255.0 for i in range(4)]
                self.state["viewed"]["brake_damage"] = [p559[200+i] / 255.0 for i in range(4)]
                self.state["viewed"]["tyre_wear"] = [p559[196+i] / 255.0 for i in range(4)]
                compounds = []
                for i in range(4):
                    raw = p559[378+i*40:378+(i+1)*40]
                    compounds.append(raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip())
                self.state["viewed"]["tyre_compound"] = compounds
                if self.state.get("viewed_index", -1) >= 0:
                    self._tyre_compound_cache[self.state["viewed_index"]] = compounds[0]

        # 308 bytes - RaceData
        p308 = self.packet_buffer.get(308)
        if p308 and p308 != self.last_packets.get(308):
            self.last_packets[308] = p308
            changed = True
            try:
                self.state["session"]["world_fastest_lap"] = struct.unpack_from('<f', p308, 12)[0]
                self.state["session"]["world_fastest_sectors"] = [
                    struct.unpack_from('<f', p308, 32)[0],
                    struct.unpack_from('<f', p308, 36)[0],
                    struct.unpack_from('<f', p308, 40)[0]
                ]
                self.state["session"]["track_name"] = struct.unpack_from('64s', p308, 48)[0].split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                self.state["session"]["track_variation"] = struct.unpack_from('64s', p308, 112)[0].split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                self.state["session"]["enforced_pit_stop_lap"] = struct.unpack_from('<b', p308, 306)[0]
            except Exception:
                pass

        # 24 bytes - GameState
        p24 = self.packet_buffer.get(24)
        if p24 and p24 != self.last_packets.get(24):
            self.last_packets[24] = p24
            changed = True
            try:
                self.state["weather"]["ambient_temp"] = struct.unpack_from('<b', p24, 16)[0]
                self.state["weather"]["track_temp"] = struct.unpack_from('<b', p24, 17)[0]
                self.state["weather"]["rain_density"] = p24[18] / 255.0
                self.state["weather"]["snow_density"] = p24[19] / 255.0
                self.state["weather"]["wind_speed"] = struct.unpack_from('<b', p24, 20)[0]
            except Exception:
                pass

        # 1136 bytes - Participants
        p1136 = self.packet_buffer.get(1136)
        if p1136 and p1136 != self.last_packets.get(1136):
            self.last_packets[1136] = p1136
            changed = True

        # 1063 bytes - Timings
        p1063 = self.packet_buffer.get(1063)
        if p1063 and p1063 != self.last_packets.get(1063):
            self.last_packets[1063] = p1063
            changed = True
            try:
                split_ahead = struct.unpack_from('<f', p1063, 21)[0]
                split_behind = struct.unpack_from('<f', p1063, 25)[0]
                self.state["split_ahead"] = split_ahead
                self.state["split_behind"] = split_behind
            except Exception:
                pass

        # 1040 bytes - TimeStats
        p1040 = self.packet_buffer.get(1040)
        if p1040 and p1040 != self.last_packets.get(1040):
            self.last_packets[1040] = p1040
            changed = True
            try:
                viewed_idx = self.state["viewed_index"]
                if viewed_idx >= 0 and viewed_idx < 32:
                    offset = 16 + viewed_idx * 32 + 4
                    last_lap = struct.unpack_from('<f', p1040, offset)[0]
                    if last_lap > 0:
                        self.state["viewed"]["last_lap"] = last_lap
            except Exception:
                pass

        # Post-processing updates using main_app participants (from UDP or Shared Memory)
        participants = getattr(self.main_app, '_participants', {})
            
        if participants:
            viewed_idx = self.state["viewed_index"]
            if viewed_idx in participants:
                vp = participants[viewed_idx]
                self.state["viewed"]["position"] = vp.get("race_position", 0)
                self.state["viewed"]["name"] = vp.get("name", "Unknown Driver")
                
                target_pos = vp.get("race_position", 0) - 1
                if target_pos > 0:
                    ahead_name = "Unknown Driver"
                    for idx, p in participants.items():
                        if p.get("race_position") == target_pos:
                            ahead_name = p.get("name", "Unknown Driver")
                            break
                    self.state["ahead"]["name"] = ahead_name
                    self.state["ahead"]["position"] = target_pos
                    self.state["ahead"]["gap_seconds"] = self.state.get("split_ahead", 0.0)
                else:
                    self.state["ahead"]["name"] = ""
                    self.state["ahead"]["position"] = 2
                    self.state["ahead"]["gap_seconds"] = self.state.get("split_behind", 0.0)

                behind_pos = vp.get("race_position", 0) + 1
                behind_name = ""
                found_behind = False
                for idx, p in participants.items():
                    if p.get("race_position") == behind_pos:
                        behind_name = p.get("name", "Unknown Driver")
                        found_behind = True
                        break
                
                if found_behind:
                    self.state["behind"]["name"] = behind_name
                    self.state["behind"]["position"] = behind_pos
                    self.state["behind"]["gap_seconds"] = self.state.get("split_behind", 0.0)
                else:
                    self.state["behind"]["name"] = ""
                    self.state["behind"]["position"] = 0
                    self.state["behind"]["gap_seconds"] = 0.0

        # Session Info Update
        if shm is not None:
            # SHM only provides RPM/Gear/Brake/Throttle for the LOCAL player (which is 0 when spectating).
            # UDP provides it for the VIEWED player. Only use SHM if UDP is not available.
            if not self.last_packets.get(559) and not self.last_packets.get(556):
                self.state["viewed"]["speed_kph"] = getattr(shm, 'mSpeed', 0.0) * 3.6
                self.state["viewed"]["rpm"] = int(getattr(shm, 'mRpm', 0.0))
                self.state["viewed"]["max_rpm"] = int(getattr(shm, 'mMaxRPM', 10000.0))
                self.state["viewed"]["gear"] = getattr(shm, 'mGear', 0)
                self.state["viewed"]["num_gears"] = getattr(shm, 'mNumGears', 0)
                self.state["viewed"]["brake"] = getattr(shm, 'mBrake', 0.0)
                self.state["viewed"]["throttle"] = getattr(shm, 'mThrottle', 0.0)
                self.state["viewed"]["crash_state"] = getattr(shm, 'mCrashState', 0)
                self.state["viewed"]["aero_damage"] = getattr(shm, 'mAeroDamage', 0.0)
                self.state["viewed"]["engine_damage"] = getattr(shm, 'mEngineDamage', 0.0)
                
                try:
                    self.state["viewed"]["suspension_damage"] = list(shm.mSuspensionDamage)
                    self.state["viewed"]["brake_damage"] = list(shm.mBrakeDamage)
                    self.state["viewed"]["tyre_wear"] = list(shm.mTyreWear)
                    compounds = []
                    for i in range(4):
                        compounds.append(bytes(shm.mTyreCompound[i]).split(b'\x00')[0].decode('utf-8', errors='replace').strip())
                    self.state["viewed"]["tyre_compound"] = compounds
                    if getattr(shm, 'mViewedParticipantIndex', -1) >= 0:
                        self._tyre_compound_cache[getattr(shm, 'mViewedParticipantIndex', -1)] = compounds[0]
                except Exception:
                    pass

            self.state["session"]["world_fastest_lap"] = getattr(shm, 'mWorldFastestLapTime', 0.0)
            self.state["session"]["world_fastest_sectors"] = [
                getattr(shm, 'mWorldFastestSector1Time', 0.0),
                getattr(shm, 'mWorldFastestSector2Time', 0.0),
                getattr(shm, 'mWorldFastestSector3Time', 0.0)
            ]
            self.state["session"]["track_name"] = getattr(shm, 'mTranslatedTrackLocation', b'').split(b'\x00')[0].decode('utf-8', errors='replace').strip()
            self.state["session"]["track_variation"] = getattr(shm, 'mTranslatedTrackVariation', b'').split(b'\x00')[0].decode('utf-8', errors='replace').strip()
            self.state["session"]["enforced_pit_stop_lap"] = getattr(shm, 'mEnforcedPitStopLap', -1)
            self.state["weather"]["ambient_temp"] = getattr(shm, 'mAmbientTemperature', 0)
            self.state["weather"]["track_temp"] = getattr(shm, 'mTrackTemperature', 0)
            self.state["weather"]["rain_density"] = getattr(shm, 'mRainDensity', 0.0)
            self.state["weather"]["snow_density"] = getattr(shm, 'mSnowDensity', 0.0)
            self.state["weather"]["wind_speed"] = getattr(shm, 'mWindSpeed', 0)
        session_info = self.provider.get_session_info(shm)
        if session_info:
            time_remaining = session_info.get("event_time_remaining", 0.0)
            cur_time = session_info.get("current_time", 0.0)
            laps = session_info.get("laps_in_event", 0)
            
            # Replay Log Fallbacks
            scorer = getattr(self.main_app, 'scorer', None)
            if scorer:
                if laps <= 0:
                    laps = scorer.timeline_laps_in_event
                
                if time_remaining <= 0 and scorer.timeline_session_time > 0:
                    time_remaining = max(0.0, scorer.timeline_session_time - cur_time)
            
            self.state["session"]["time_remaining"] = time_remaining
            self.state["session"]["laps_in_event"] = laps
            self.state["session"]["leader_lap"] = session_info.get("leader_lap", 0)

        camera_ctrl = getattr(self.main_app, 'camera', None)
        if camera_ctrl:
            self.state["director"]["camera_type"] = camera_ctrl.current_camera_type
            self.state["director"]["is_auto_directing"] = getattr(self.main_app, '_director_enabled', False)
        
        if session_info:
            self.state["session"]["state"] = session_info.get("game_state", 0)
            self.state["session"]["session_state"] = session_info.get("session_state", 0)
            self.state["session"]["yellow_flag_state"] = session_info.get("yellow_flag_state", 0)
            
            participants_dict = getattr(self.main_app, '_participants', {})
            
            self._update_pit_tracker(participants_dict)
            self.state["pit_events"] = self._pit_events
            
            self.state["session"]["total_drivers"] = len([p for p in participants_dict.values() if p.get('is_active', False)])
            # Find leader lap
            leader_lap = 0
            for p in participants_dict.values():
                if p.get('race_position') == 1:
                    # In AMS2, current_lap starts at 1 usually, but let's just expose what the telemetry provides
                    leader_lap = p.get('current_lap', 0)
                    break
            self.state["session"]["leader_lap"] = leader_lap
            
            # Leaderboard (sorted by race_position)
            active_drivers = [p for p in participants_dict.values() if p.get('is_active', False) and p.get('race_position', 999) > 0]
            active_drivers.sort(key=lambda x: x.get('race_position', 999))
            
            leaderboard = []
            for p in active_drivers:
                idx = -1
                for key, val in participants_dict.items():
                    if val == p:
                        idx = key
                        break

                pit_count = 0
                laps_since = -1
                if idx >= 0 and idx in self._pit_tracker:
                    pit_count = self._pit_tracker[idx].get("pit_count", 0)
                    laps_since = self._pit_tracker[idx].get("laps_since_last_pit", -1)

                gap_val = p.get("time_gap_to_leader", p.get("gap_ahead", 0.0))

                # Update Sector Tracker
                sector = p.get("current_sector", 0)
                game_time = p.get("current_time", 0.0)
                in_pits = p.get("pit_mode", 0) != 0
                if idx >= 0:
                    current_sectors = self._sector_manager.update_driver(idx, sector, game_time, in_pits)
                else:
                    current_sectors = [0.0, 0.0, 0.0]

                entry = {
                    "pos": p.get("race_position"),
                    "name": p.get("name"),
                    "lap": p.get("current_lap"),
                    "lap_distance": p.get("lap_distance", 0.0),
                    "true_distance": p.get("true_distance", 0.0),
                    "tyre_stint_laps": p.get("tyre_stint_laps", 0),
                    "tyre_compound": self._tyre_compound_cache.get(idx, ""),
                    "gap": gap_val,
                    "current_time": p.get("current_time", 0.0),
                    "current_sector_time": p.get("current_sector_time", 0.0),
                    "speed": p.get("speed"),
                    "pit": pit_count,
                    "pit_mode": p.get("pit_mode"),
                    "laps_since_last_pit": laps_since,
                    "current_sector": sector
                }

                if shm is not None and idx >= 0 and idx < len(getattr(shm, 'mFastestLapTimes', [])):
                    entry["fastest_lap"] = shm.mFastestLapTimes[idx]
                    entry["last_lap"] = shm.mLastLapTimes[idx]
                    entry["current_sectors"] = current_sectors
                    entry["fastest_sectors"] = [shm.mFastestSector1Times[idx], shm.mFastestSector2Times[idx], shm.mFastestSector3Times[idx]]
                elif self.last_packets.get(1040):
                    p1040 = self.last_packets[1040]
                    if idx >= 0 and idx < 32:
                        offset = 16 + idx * 32
                        try:
                            fl, ll, _, fs1, fs2, fs3 = struct.unpack_from('<6f', p1040, offset)
                            entry["fastest_lap"] = fl
                            entry["last_lap"] = ll
                            entry["current_sectors"] = current_sectors
                            entry["fastest_sectors"] = [fs1, fs2, fs3]
                        except Exception:
                            entry["fastest_lap"] = 0.0
                            entry["last_lap"] = 0.0
                            entry["current_sectors"] = current_sectors
                            entry["fastest_sectors"] = [0.0, 0.0, 0.0]
                    else:
                        entry["fastest_lap"] = 0.0
                        entry["last_lap"] = 0.0
                        entry["current_sectors"] = current_sectors
                        entry["fastest_sectors"] = [0.0, 0.0, 0.0]
                else:
                    entry["fastest_lap"] = 0.0
                    entry["last_lap"] = 0.0
                    entry["current_sectors"] = current_sectors
                    entry["fastest_sectors"] = [0.0, 0.0, 0.0]

                d_name = p.get("name", "")
                name_key = str(d_name).lower().strip()
                
                # 1. Manual JSON Override has highest priority
                if name_key in self.driver_lookup:
                    entry["nationality"] = self.driver_lookup[name_key]
                # 2. Live Telemetry Hash has second priority
                elif p.get("nationality"):
                    # We convert to lower here just in case the UI expects lowercase 'br' instead of 'BR'
                    entry["nationality"] = p.get("nationality").lower()
                else:
                    entry["nationality"] = ""
                
                if shm is not None and idx >= 0:
                    entry["car_name"] = bytes(shm.mCarNames[idx]).split(b'\x00')[0].decode('utf-8', errors='replace').strip() if idx < len(getattr(shm, 'mCarNames', [])) else ""
                    entry["car_class"] = bytes(shm.mCarClassNames[idx]).split(b'\x00')[0].decode('utf-8', errors='replace').strip() if idx < len(getattr(shm, 'mCarClassNames', [])) else ""
                elif effective_source in ('udp_auto', 'udp_manual'):
                    # Use UDP-parsed car data when in UDP mode
                    udp_car_names = self.provider.get_udp_car_names() if hasattr(self.provider, 'get_udp_car_names') else {}
                    udp_car_classes = self.provider.get_udp_car_classes() if hasattr(self.provider, 'get_udp_car_classes') else {}
                    entry["car_name"] = udp_car_names.get(idx, "")
                    entry["car_class"] = udp_car_classes.get(idx, "")
                else:
                    entry["car_name"] = ""
                    entry["car_class"] = ""

                leaderboard.append(entry)
            self.state["leaderboard"] = leaderboard
            
            # Calculate actual session fastest lap from active drivers (ignoring all-time track records)
            session_fastest = 0.0
            session_sectors = [0.0, 0.0, 0.0]
            
            for entry in leaderboard:
                fl = entry.get("fastest_lap", 0.0)
                if fl > 0 and (session_fastest == 0.0 or fl < session_fastest):
                    session_fastest = fl
                    
                fs = entry.get("fastest_sectors", [0.0, 0.0, 0.0])
                for i in range(3):
                    if fs[i] > 0 and (session_sectors[i] == 0.0 or fs[i] < session_sectors[i]):
                        session_sectors[i] = fs[i]
            
            if session_fastest > 0:
                self.state["session"]["world_fastest_lap"] = session_fastest
            if any(s > 0 for s in session_sectors):
                self.state["session"]["world_fastest_sectors"] = session_sectors
            
            changed = True

        return changed
