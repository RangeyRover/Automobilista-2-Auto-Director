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
            "events": {
                "fastest_lap": {
                    "driver_name": "",
                    "lap_time": 0.0,
                    "timestamp": 0.0
                }
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
        from dashboard.state_engine.pit_tracker import PitTracker
        self.pit_manager = PitTracker()
        self._sector_manager = SectorTrackerManager()
        self._last_current_time = 0.0
        self._fastest_lap_events = []
        
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
        if '?' in path:
            path = path.split('?')[0]
            
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
            
        if file_path.endswith('.css'):
            content_type = "text/css"
        elif file_path.endswith('.js'):
            content_type = "application/javascript"
        else:
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
                    self._last_camera_change_time = time.time()
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
                if self.state.get("viewed_index", -1) >= 0 and time.time() - getattr(self, '_last_camera_change_time', 0.0) > 1.0:
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
                self.state["weather"]["wind_speed"] = struct.unpack_from('<b', p24, 20)[0] * 3.6
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
                    if self.state.get("viewed_index", -1) >= 0 and time.time() - getattr(self, '_last_camera_change_time', 0.0) > 1.0:
                        self._tyre_compound_cache[self.state["viewed_index"]] = compounds[0]
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
            self.state["weather"]["wind_speed"] = getattr(shm, 'mWindSpeed', 0) * 3.6
        session_info = self.provider.get_session_info(shm)
        if session_info:
            time_remaining = session_info.get("event_time_remaining", 0.0)
            cur_time = session_info.get("current_time", 0.0)
            
            # Time-Travel Rewind Detection
            if cur_time < self._last_current_time - 5.0:
                self.pit_manager.process_rewind(cur_time)
                
                # Prune fastest laps
                self._fastest_lap_events = [ev for ev in self._fastest_lap_events if ev.get("timestamp", 0.0) <= cur_time]
                
            self._last_current_time = cur_time
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
            
            self.pit_manager.update(participants_dict, cur_time)
            self.state["pit_events"] = self.pit_manager.pit_events
            
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
            from dashboard.state_engine.telemetry_builder import TelemetryBuilder
            leaderboard = TelemetryBuilder.build_leaderboard(
                shm, participants_dict, self.pit_manager, self._sector_manager,
                self._tyre_compound_cache, self.last_packets, self.driver_lookup,
                effective_source, self.provider
            )
            self.state["leaderboard"] = leaderboard
            
            # Calculate actual session fastest lap from active drivers
            session_fastest, session_sectors = TelemetryBuilder.calculate_session_bests(
                leaderboard, self._fastest_lap_events, cur_time
            )
            
            # Update history and JSON payload
            current_best_in_history = self._fastest_lap_events[-1].get("lap_time", 0.0) if self._fastest_lap_events else 0.0
            
            # Ignore 0.0 times or the very first packet (cur_time < 5.0) to prevent initial floods
            if session_fastest > 0:
                self.state["session"]["world_fastest_lap"] = session_fastest

            
            if self._fastest_lap_events:
                self.state["events"]["fastest_lap"] = self._fastest_lap_events[-1]
                
            if any(s > 0 for s in session_sectors):
                self.state["session"]["world_fastest_sectors"] = session_sectors
            
            changed = True

        return changed
