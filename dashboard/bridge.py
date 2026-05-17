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
from dashboard.payload_builder import PayloadBuilder

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
                
        self.payload_builder = PayloadBuilder(self)

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
                    elif data.get("type") == "request_debug_dump_udp":
                        if hasattr(self, 'provider') and self.provider:
                            dump = self.provider.get_debug_dump_udp()
                            await websocket.send(json.dumps({
                                "type": "debug_dump_response",
                                "data": dump
                            }))
                    elif data.get("type") == "request_debug_dump_shm":
                        if hasattr(self, 'provider') and self.provider:
                            dump = self.provider.get_debug_dump_shm()
                            await websocket.send(json.dumps({
                                "type": "debug_dump_response",
                                "data": dump
                            }))
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
        return self.payload_builder.parse_packets()
