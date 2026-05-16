"""Telemetry data provider for AMS2 Auto Director V4.0.

Abstracts over SharedMemory and UDP data sources, providing a unified
interface for polling participant data. Returns normalised participant
dicts including driver names.

No GUI imports. Fully testable with mock objects.
"""
import time
import socket
import threading
import struct
import json
import os
from core.utils import ctypes_serializer

UDP_NATIONALITY_HASHES = {
    933178424:  'BR', # Brazil
    1004104139: 'UY', # Uruguay
    2138617929: 'US', # USA
    1048434266: 'AR', # Argentina
    1808026356: 'ID', # Indonesia
    3222416996: 'GR', # Greece
    1789533886: 'NL', # Netherlands
    4279958873: 'CO', # Colombia
    3170477316: 'PT', # Portugal
    354033749:  'MX', # Mexico
    2858231841: 'CL', # Chile
    1972970704: 'GB', # UK
    4017120722: 'CA', # Canada
    3603110075: 'AU', # Australia
    2157389219: 'NZ'  # New Zealand
}

class TelemetryProvider:
    """Abstraction over SharedMemory and UDP data sources."""

    def __init__(self, mode: str = 'shared_memory'):
        """Initialise the provider.

        Args:
            mode: 'shared_memory' or 'udp'
        """
        self._mode = mode
        self._connected = False
        self._last_track_name = None
        self._distance_history: dict[int, list[tuple[float, float]]] = {}
        self._gap_history: dict[int, float] = {}
        self._closing_speed_ema: dict[int, float] = {}
        self._tyre_stint_start_lap: dict[int, int] = {}
        self._car_splines: dict[int, list[tuple[float, float]]] = {}  # {idx: [(true_distance, game_time)]}
        self._last_poll_time = time.time()
        self._packet_buffer: dict[int, bytes] = {}  # keyed by packet size
        
        # Telemetry Dumper
        self._dump_raw_json = True
        self._last_json_dump_time = 0.0
        self._udp_time_splits: dict[int, float] = {}
        
        # UDP State
        self._udp_port = 5606
        self._udp_running = False
        self._udp_thread: threading.Thread | None = None
        self._udp_socket: socket.socket | None = None
        self._udp_participant_names: dict[int, str] = {}
        self._udp_participant_nationalities: dict[int, str] = {}
        self._udp_car_names: dict[int, str] = {}
        self._udp_car_classes: dict[int, str] = {}

    # ── Public API ──────────────────────────────────────────────────────────

    def udp_has_track_length(self) -> bool:
        """Return True if a 308-byte packet is buffered with track_length > 0."""
        packet = self._packet_buffer.get(308)
        if not packet or len(packet) < 48:
            return False
        try:
            track_length = struct.unpack_from('f', packet, 44)[0]
            return track_length > 0.0
        except struct.error:
            return False

    def udp_has_participant_names(self) -> bool:
        """Return True if at least one participant name is cached from UDP."""
        return len(self._udp_participant_names) > 0

    def get_udp_car_names(self) -> dict[int, str]:
        """Return cached car names parsed from UDP Strings packets."""
        return dict(self._udp_car_names)

    def get_udp_car_classes(self) -> dict[int, str]:
        """Return cached car classes parsed from UDP Strings packets."""
        return dict(self._udp_car_classes)

    def poll(self, shared_memory_obj=None) -> dict[int, dict] | None:
        """Read current telemetry. Returns participants dict keyed 0-31,
        or None if data source unavailable."""
        participants = None
        track_info = {}
        
        # Primary Source: Shared Memory
        if self._mode == 'shared_memory' and shared_memory_obj is not None:
            track_info = self._extract_track_info(shared_memory_obj)
            participants = self._extract_all_participants(shared_memory_obj)
            self._update_connection_state(data_available=True)
            
        # Fallback/Exclusive Source: UDP
        elif self._mode == 'udp' or (self._mode == 'shared_memory' and shared_memory_obj is None):
            track_info_packet = self._packet_buffer.get(308)
            if track_info_packet:
                track_info = self._extract_udp_track_info(track_info_packet)
            
            participants = self._parse_udp_participants(self._packet_buffer.get(1063))
            if participants is not None:
                self._update_connection_state(data_available=True)
            else:
                self._update_connection_state(data_available=False)
                
        if participants is None:
            return None

        if self._detect_track_change(track_info):
            self._distance_history.clear()
            self._leader_spline.clear()
            self._tyre_stint_start_lap.clear()

        # Calculate derived fields
        track_length = track_info.get('track_length', 1.0)
        for idx, p in participants.items():
            laps_completed = max(0, p['current_lap'] - 1)
            p['true_distance'] = self._calc_true_distance(
                laps_completed, p['lap_distance'], track_length
            )
            
            # Track tyre stint laps (assume pitstop = new tyres)
            if p.get('pit_mode', 0) != 0:
                self._tyre_stint_start_lap[idx] = p['current_lap']
            p['tyre_stint_laps'] = max(0, p['current_lap'] - self._tyre_stint_start_lap.get(idx, 1))

        self._calc_gaps(participants)
        self._calc_cars_ahead(participants, track_length)

        game_time = time.time()
        if self._mode == 'shared_memory' and shared_memory_obj is not None:
            game_time = getattr(shared_memory_obj, 'mCurrentTime', game_time)
        else:
            udp_info = self._extract_udp_session_info()
            if udp_info.get('current_time', 0.0) > 0:
                game_time = udp_info['current_time']

        self._calc_live_time_gaps(participants, track_length, game_time)

        now = time.time()
        dt = now - self._last_poll_time
        if dt <= 0:
            dt = 0.001

        # Calculate closing speeds and true speeds
        for idx, p in participants.items():
            if p['is_active']:
                # Closing speed
                p['closing_speed'] = self._calc_closing_speed(idx, p.get('gap_ahead', 0.0), dt)
                
                # True speed (distance history)
                if idx not in self._distance_history:
                    self._distance_history[idx] = []
                self._distance_history[idx].append((now, p['lap_distance']))
                # Keep only last 5 entries
                self._distance_history[idx] = self._distance_history[idx][-5:]
                
                speed = self._calc_speed(idx, track_length)
                if speed is not None:
                    p['speed'] = speed
                elif 'speed' not in p:
                    p['speed'] = 0.0

        self._last_poll_time = now
        
        self._last_poll_time = now
        return participants

    def get_game_time(self, shared_memory_obj=None) -> float | None:
        """Return current game time from SharedMemory.mCurrentTime."""
        if shared_memory_obj is None:
            return None
        return self._extract_game_time(shared_memory_obj)

    def get_track_info(self, shared_memory_obj=None) -> dict | None:
        """Return track info dict or None."""
        if shared_memory_obj is None:
            return None
        return self._extract_track_info(shared_memory_obj)

    def get_session_info(self, shared_memory_obj=None) -> dict | None:
        """Return session info dict or None."""
        info = {
            'event_time_remaining': 0.0,
            'current_time': 0.0,
            'laps_in_event': 0
        }
        
        if shared_memory_obj is not None:
            info = self._extract_session_info(shared_memory_obj)
            
        # Hybrid UDP Fallback
        if info['event_time_remaining'] == 0.0 or info['laps_in_event'] == 0:
            udp_info = self._extract_udp_session_info()
            if udp_info['event_time_remaining'] > 0.0:
                info['event_time_remaining'] = udp_info['event_time_remaining']
            if udp_info['laps_in_event'] > 0:
                info['laps_in_event'] = udp_info['laps_in_event']
                
        return info

    def is_connected(self) -> bool:
        """True if the data source is actively providing data."""
        return self._connected

    # ── Connection State ────────────────────────────────────────────────────

    def _update_connection_state(self, data_available: bool):
        """Update the connection state flag."""
        self._connected = data_available

    # ── Shared Memory Extraction ────────────────────────────────────────────

    def _extract_all_participants(self, sm) -> dict[int, dict]:
        """Extract all 32 participant slots from shared memory."""
        participants = {}
        num = getattr(sm, 'mNumParticipants', 0)

        for i in range(32):
            info = sm.mParticipantInfo[i]
            is_active = bool(getattr(info, 'mIsActive', False))
            if num > 0:
                is_active = is_active and i < num

            # Decode name — handle bytes with null terminator
            raw_name = getattr(info, 'mName', b'')
            if isinstance(raw_name, bytes):
                name = raw_name.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
            else:
                name = str(raw_name).strip()

            if name.lower().startswith('safety car'):
                is_active = False

            participants[i] = {
                'name': name,
                'nationality': self._udp_participant_nationalities.get(i, ""),
                'race_position': info.mRacePosition if hasattr(info, 'mRacePosition') else 0,
                'is_active': is_active,
                'lap_distance': info.mCurrentLapDistance if hasattr(info, 'mCurrentLapDistance') else 0.0,
                'current_lap': info.mCurrentLap if hasattr(info, 'mCurrentLap') else 0,
                # Shared Memory provides 0, 1, 2 for sectors. Convert to 1, 2, 3 for consistency with UDP.
                'current_sector': (info.mCurrentSector + 1) if hasattr(info, 'mCurrentSector') else 1,
                'speed': sm.mSpeeds[i] if hasattr(sm, 'mSpeeds') else 0.0,
                'pit_mode': sm.mPitModes[i] if hasattr(sm, 'mPitModes') else 0,
                'race_state': sm.mRaceStates[i] if hasattr(sm, 'mRaceStates') else 0,
                'current_time': getattr(sm, 'mCurrentTime', 0.0),
                'true_distance': 0.0,
                'gap_ahead': 0.0,
                'cars_ahead_250m': 0,
                'flag_colour': sm.mHighestFlagColours[i] if hasattr(sm, 'mHighestFlagColours') else 0,
                'flag_reason': sm.mHighestFlagReasons[i] if hasattr(sm, 'mHighestFlagReasons') else 0,
                'fastest_lap': sm.mFastestLapTimes[i] if hasattr(sm, 'mFastestLapTimes') else 0.0,
                'last_lap': sm.mLastLapTimes[i] if hasattr(sm, 'mLastLapTimes') else 0.0,
            }

        return participants

    def _extract_track_info(self, sm) -> dict:
        """Extract track information from shared memory."""
        track_name_raw = getattr(sm, 'mTranslatedTrackLocation', b'')
        if not track_name_raw or track_name_raw.startswith(b'\x00'):
            track_name_raw = getattr(sm, 'mTrackLocation', b'')
            
        if isinstance(track_name_raw, bytes):
            track_name = track_name_raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
        else:
            track_name = str(track_name_raw).strip()

        return {
            'track_name': track_name,
            'track_length': getattr(sm, 'mTrackLength', 0.0),
            'num_participants': getattr(sm, 'mNumParticipants', 0),
        }

    def _extract_game_time(self, sm) -> float:
        """Extract game time from SharedMemory.mCurrentTime."""
        return getattr(sm, 'mCurrentTime', 0.0)

    def _extract_session_info(self, sm) -> dict:
        """Extract session time info."""
        return {
            'event_time_remaining': getattr(sm, 'mEventTimeRemaining', 0.0),
            'current_time': getattr(sm, 'mCurrentTime', 0.0),
            'laps_in_event': getattr(sm, 'mLapsInEvent', 0),
            'viewed_participant_index': getattr(sm, 'mViewedParticipantIndex', -1),
            'game_state': getattr(sm, 'mGameState', 0),
            'session_state': getattr(sm, 'mSessionState', 0),
            'yellow_flag_state': getattr(sm, 'mYellowFlagState', 0),
        }

    # ── Derived Calculations ────────────────────────────────────────────────

    @staticmethod
    def _calc_true_distance(laps_completed: int, lap_distance: float, track_length: float) -> float:
        """FR-2.2: True Distance = laps_completed * track_length + lap_distance."""
        return laps_completed * track_length + lap_distance

    @staticmethod
    def _calc_gaps(participants: dict):
        """FR-2.3: Calculate gap to player ahead (by true distance, descending)."""
        active = [(idx, p) for idx, p in participants.items() if p.get('is_active', False)]
        if not active:
            return

        # Sort by true_distance descending (leader first)
        active.sort(key=lambda x: x[1]['true_distance'], reverse=True)

        # Leader has gap 0
        active[0][1]['gap_ahead'] = 0.0

        # Each subsequent driver's gap is distance to the one ahead
        for i in range(1, len(active)):
            gap = active[i - 1][1]['true_distance'] - active[i][1]['true_distance']
            active[i][1]['gap_ahead'] = gap

    @staticmethod
    def _calc_cars_ahead(participants: dict, track_length: float):
        """FR-2.4: Count active participants within 250m ahead on track."""
        active = [(idx, p) for idx, p in participants.items() if p.get('is_active', False)]

        for idx, p in active:
            my_dist = p['true_distance']
            count = 0
            for other_idx, other_p in active:
                if other_idx == idx:
                    continue
                diff = other_p['true_distance'] - my_dist
                if 0 < diff <= 250:
                    count += 1
            p['cars_ahead_250m'] = count

    def _calc_speed(self, index: int, track_length: float) -> float | None:
        """Calculate speed from distance/timestamp history.

        Returns None if insufficient data (< 2 entries).
        """
        history = self._distance_history.get(index, [])
        if len(history) < 2:
            return None

        t1, d1 = history[-2]
        t2, d2 = history[-1]
        dt = t2 - t1
        if dt <= 0:
            return 0.0

        dd = d2 - d1
        # Handle S/F line crossing (distance wraps around)
        if dd < -track_length / 2:
            dd += track_length

        return abs(dd) / dt

    def _calc_closing_speed(self, idx: int, current_gap: float, dt: float) -> float:
        """Calculate closing speed (m/s) with EMA smoothing."""
        alpha = 0.3
        if idx not in self._gap_history:
            self._gap_history[idx] = current_gap
            self._closing_speed_ema[idx] = 0.0
            return 0.0

        prev_gap = self._gap_history[idx]
        raw_closing = (prev_gap - current_gap) / dt
        
        if idx not in self._closing_speed_ema or not self._closing_speed_ema:
            self._closing_speed_ema[idx] = raw_closing
        else:
            self._closing_speed_ema[idx] = alpha * raw_closing + (1 - alpha) * self._closing_speed_ema.get(idx, 0.0)

        self._gap_history[idx] = current_gap
        return self._closing_speed_ema[idx]

    def _calc_live_time_gaps(self, participants: dict, track_length: float, game_time: float):
        """US1: Calculate live time gap to leader using spline history where possible."""
        active = [(idx, p) for idx, p in participants.items() if p.get('is_active', False) and p.get('race_position', 999) > 0]
        if not active:
            return

        # Sort by race_position ascending (1st to last)
        active.sort(key=lambda x: x[1].get('race_position', 999))

        # Establish a stable average speed for interpolation (fallback)
        avg_speed = 60.0 
        
        leader = active[0][1]
        leader_idx = active[0][0]
        last_lap = leader.get('last_lap', 0.0)
        leader_dist = leader.get('true_distance', 0.0)
        
        if last_lap > 10.0 and track_length > 100.0:
            avg_speed = track_length / last_lap

        # Update splines for all active cars
        for idx, p in active:
            dist = p.get('true_distance', 0.0)
            if idx not in self._car_splines:
                self._car_splines[idx] = []
                
            spline = self._car_splines[idx]
            
            if not spline:
                spline.append((dist, game_time))
            else:
                last_dist, last_time = spline[-1]
                
                # Fix: If game_time jumps backwards (e.g., hybrid UDP fallback or replay rewind), 
                # purge all corrupted "future" points from the spline.
                if game_time < last_time - 1.0:
                    self._car_splines[idx] = [(d, t) for d, t in spline if t <= game_time]
                    spline = self._car_splines[idx]
                    if not spline:
                        spline.append((dist, game_time))
                        continue
                        
                last_dist, last_time = spline[-1]
                
                # Only record a new point every 5 meters to keep array size manageable
                if dist > last_dist + 5.0:
                    spline.append((dist, game_time))
                    # Support up to ~25km of track history for 32 cars without memory bloat
                    if len(spline) > 5000:
                        spline.pop(0)
                elif dist < last_dist - track_length:
                    # Session reset detected (e.g. true distance dropped)
                    spline.clear()
                    spline.append((dist, game_time))

        def get_spline_time_at_distance(spline: list, dist: float) -> float | None:
            if not spline or dist < spline[0][0]:
                return None
            if dist >= spline[-1][0]:
                return spline[-1][1]
            if dist == spline[0][0]:
                return spline[0][1]
                
            # Simple binary search to find the two points to interpolate between
            left, right = 0, len(spline) - 1
            while left <= right:
                mid = (left + right) // 2
                if spline[mid][0] < dist:
                    left = mid + 1
                else:
                    right = mid - 1
                    
            if left >= len(spline) or left == 0:
                return None
                
            d1, t1 = spline[left - 1]
            d2, t2 = spline[left]
            
            if d2 == d1:
                return t1
                
            # Linear interpolation
            ratio = (dist - d1) / (d2 - d1)
            return t1 + ratio * (t2 - t1)

        leader_spline = self._car_splines.get(leader_idx, [])

        for i in range(len(active)):
            idx = active[i][0]
            p = active[i][1]
            my_dist = p.get('true_distance', 0.0)
            
            # Physical distance to the overall leader
            dist_to_leader = leader_dist - my_dist
            
            # Determine actual laps down based on physical distance, not just crossing the line
            laps_down = 0
            if track_length > 100.0 and dist_to_leader > (track_length * 0.8):
                laps_down = int(dist_to_leader / track_length)
                
            p['laps_down'] = laps_down
            
            if i == 0:
                p['time_gap_to_leader'] = 0.0
            else:
                spline_time = get_spline_time_at_distance(leader_spline, my_dist)
                if spline_time is not None:
                    p['time_gap_to_leader'] = game_time - spline_time
                else:
                    # Fallback to physical if the spline hasn't recorded that far back yet
                    p['time_gap_to_leader'] = dist_to_leader / avg_speed


    # ── Track Change Detection ──────────────────────────────────────────────

    def _detect_track_change(self, track_info: dict) -> bool:
        """FR-2.5: Detect track changes. Returns True if track changed."""
        new_name = track_info.get('track_name', '')
        if self._last_track_name is not None and new_name != self._last_track_name:
            self._last_track_name = new_name
            return True
        self._last_track_name = new_name
        return False

    # ── UDP Support ─────────────────────────────────────────────────────────

    def start_udp(self):
        """Start the background UDP listener thread."""
        if self._udp_running:
            return
        self._udp_running = True
        self._udp_thread = threading.Thread(target=self._listen_udp_loop, daemon=True)
        self._udp_thread.start()

    def stop_udp(self):
        """Stop the background UDP listener thread."""
        self._udp_running = False
        if self._udp_socket:
            try:
                self._udp_socket.close()
            except Exception:
                pass
        if self._udp_thread and self._udp_thread.is_alive():
            # In python 3.13, closing the socket should unblock recvfrom
            self._udp_thread.join(timeout=0.2)

    def set_udp_port(self, port: int):
        """Change the UDP port and restart listener if running."""
        self._udp_port = port
        if self._udp_running:
            self.stop_udp()
            time.sleep(0.1) # Allow thread to gracefully exit
            self.start_udp()

    def _listen_udp_loop(self):
        """Internal daemon loop for listening to UDP packets."""
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allow port reuse
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._udp_socket.bind(("", self._udp_port))
        except Exception as e:
            print(f"Error binding UDP port {self._udp_port}: {e}")
            self._udp_running = False
            return

        while self._udp_running:
            try:
                data, addr = self._udp_socket.recvfrom(2048)
                packet_size = len(data)
                
                self._add_packet_to_buffer(data)
                
                # Proactively parse string packets to populate name cache
                if packet_size in (1136, 1367):
                    self._parse_udp_names(data)
                elif packet_size == 1063:
                    try:
                        local_index = struct.unpack_from('<H', data, 1055)[0]
                        split_ahead = struct.unpack_from('<f', data, 21)[0]
                        if split_ahead >= 0.0:
                            self._udp_time_splits[local_index] = split_ahead
                    except struct.error:
                        pass
            except Exception as e:
                if not self._udp_running:
                    break  # Socket closed gracefully
                print(f"[UDP DEBUG] Receive Error: {e}")
                continue

    def _add_packet_to_buffer(self, packet: bytes):
        """Add a UDP packet to the buffer, keyed by packet size."""
        self._packet_buffer[len(packet)] = packet

    def _parse_udp_names(self, packet: bytes):
        """Parse Strings packet to cache driver names, car names, and car classes.

        Handles two packet sizes:
        - 1367 bytes: 16-byte header + 16×64 names + 16×(remaining for car names)
        - 1136 bytes: 12-byte header + 4-byte timestamp + 16×64 names + nationality(64) + sIndex(32)
        """
        pkt_len = len(packet)
        if pkt_len == 1136:
            print(f"[UDP NAT DEBUG] Parsing 1136-byte Strings Packet...")

        if pkt_len >= 1367:
            # 1367-byte layout: header(12) + timestamp(4) + 16×64 names(1024) + 16×64 car names(starts at 1040)
            name_block_start = 16
            name_stride = 64
            car_name_block_start = 1040
            car_name_stride = 64
            car_class_block_start = 2064  # Beyond 1367 — not available in this packet size
            car_class_stride = 64
            nationality_block_start = -1
            nationality_stride = -1
        elif pkt_len >= 1136:
            # 1136-byte layout: header(12) + timestamp(4) + 16×64 names(1024) + nationality(64) + sIndex(32)
            name_block_start = 16
            name_stride = 64
            car_name_block_start = -1
            car_name_stride = -1
            car_class_block_start = -1
            car_class_stride = -1
            nationality_block_start = 1040
            nationality_stride = 4
        else:
            return  # Unknown packet size

        # The PacketBase header is the first 12 bytes. Offset 8 is mPartialPacketIndex (1-based).
        partial_idx = packet[8]
        base_idx = (partial_idx - 1) * 16 if partial_idx > 0 else 0

        # Parse participant names
        for i in range(16):
            offset = name_block_start + (i * name_stride)
            if offset + name_stride <= pkt_len:
                raw_name = packet[offset:offset + name_stride]
                name = raw_name.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                if name:
                    abs_idx = base_idx + i
                    self._udp_participant_names[abs_idx] = name

        # Parse nationalities
        if nationality_block_start != -1:
            for i in range(16):
                offset = nationality_block_start + (i * nationality_stride)
                if offset + nationality_stride <= pkt_len:
                    try:
                        nat_hash = struct.unpack_from('<I', packet, offset)[0]
                        abs_idx = base_idx + i
                        found_nat = UDP_NATIONALITY_HASHES.get(nat_hash, "")
                        self._udp_participant_nationalities[abs_idx] = found_nat
                        
                        if self._udp_participant_names.get(abs_idx):
                            print(f"[UDP NAT DEBUG] Player Index {abs_idx} ({self._udp_participant_names[abs_idx]}) | Raw Hash from AMS2: {nat_hash} | Resolved To: '{found_nat}'")
                            
                    except struct.error:
                        pass

        # Parse car names
        if car_name_block_start != -1:
            for i in range(16):
                offset = car_name_block_start + (i * car_name_stride)
                if offset + car_name_stride <= pkt_len:
                    raw = packet[offset:offset + car_name_stride]
                    car_name = raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                    if car_name:
                        self._udp_car_names[i] = car_name

        # Parse car classes (if within packet bounds)
        if car_class_block_start != -1:
            for i in range(16):
                offset = car_class_block_start + (i * car_class_stride)
                if offset + car_class_stride <= pkt_len:
                    raw = packet[offset:offset + car_class_stride]
                    car_class = raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                    if car_class:
                        self._udp_car_classes[i] = car_class

    def _extract_udp_track_info(self, packet: bytes | None) -> dict:
        """Extract track info from 308-byte UDP packet."""
        info = {'track_name': '', 'track_length': 0.0, 'num_participants': 0}
        if not packet or len(packet) != 308:
            return info
        try:
            info['track_length'] = struct.unpack_from('f', packet, 44)[0]
        except struct.error:
            pass
        return info

    def _extract_udp_session_info(self) -> dict:
        """Extract session info from UDP packet buffer (Fallback)."""
        info = {
            'event_time_remaining': 0.0,
            'current_time': 0.0,
            'laps_in_event': 0,
            'game_state': 0,
            'session_state': 0,
            'yellow_flag_state': 0
        }
        # In PCars2 UDP, EventTimeRemaining and LapsInEvent are found in GameState or RaceData packet.
        # Note: PCars2 RaceData (308 bytes) does not contain EventTimeRemaining directly.
        # If the specific GameState packet (24 bytes) or TimingsData (1063 bytes) contains it, we parse it.
        # For the sake of the TDD fallback, we assume it's stored in a specific format or we just mock the return if we can't find it.
        # We will parse 1063 byte packet offset 14 (float, event time remaining) - this is an approximation for PCars2 protocol.
        packet = self._packet_buffer.get(1063)
        if packet and len(packet) >= 1063:
            try:
                # Based on SMS_UDP_Definitions_AMS2_RR.hpp:
                # sTimingsData (1063 bytes):
                #   PacketBase sBase; (0..11)
                #   signed char sNumParticipants; (12)
                #   unsigned int sParticipantsChangedTimestamp; (13..16)
                #   float sEventTimeRemaining; (17..20)
                val = struct.unpack_from('<f', packet, 17)[0]
                if val != -1.0:
                    info['event_time_remaining'] = val
                else:
                    info['event_time_remaining'] = 0.0
            except struct.error:
                pass
                
        packet_race = self._packet_buffer.get(308)
        if packet_race and len(packet_race) >= 308:
            try:
                laps_time = struct.unpack_from('<H', packet_race, 304)[0]
                is_timed = bool(laps_time & 0x8000)
                actual_laps = laps_time & 0x7FFF
                if not is_timed:
                    info['laps_in_event'] = actual_laps
                else:
                    duration_secs = actual_laps * 5 * 60
                    if info['event_time_remaining'] > 0:
                        info['current_time'] = max(0.0, duration_secs - info['event_time_remaining'])
            except struct.error:
                pass
                
        packet_game_state = self._packet_buffer.get(24)
        if packet_game_state and len(packet_game_state) >= 24:
            try:
                game_state_raw = struct.unpack_from('<B', packet_game_state, 14)[0]
                # Lower 4 bits = GameState, Upper 4 bits = SessionState
                info['game_state'] = game_state_raw & 0x0F
                info['session_state'] = (game_state_raw >> 4) & 0x0F
            except struct.error as e:
                print(f"[UDP DEBUG] Error unpacking game state: {e}")

        return info

    def _parse_udp_participants(self, packet: bytes | None) -> dict[int, dict] | None:
        """Parse a UDP extended packet into participant dicts."""
        if packet is None or len(packet) < 1063:
            return None

        try:
            num_participants = struct.unpack_from('<b', packet, 12)[0]
            if num_participants < 0 or num_participants > 32:
                num_participants = 32

            participants: dict[int, dict] = {}
            for i in range(32):
                race_position_offset = 31 + i * 32 + 16
                lap_distance_offset = 31 + i * 32 + 14
                current_sector_offset = 31 + i * 32 + 17
                current_lap_offset = 31 + i * 32 + 23
                current_time_offset = 31 + i * 32 + 24
                current_sector_time_offset = 31 + i * 32 + 28
                race_state_offset = 31 + i * 32 + 22
                pit_mode_offset = 31 + i * 32 + 19

                # Safely parse bytes
                race_pos_byte = packet[race_position_offset]
                race_position = race_pos_byte & 0x7F
                is_active = (race_pos_byte & 0x80) != 0
                
                # Strict active check using num_participants (removes disconnected ghosts)
                if num_participants > 0:
                    is_active = is_active and (i < num_participants)
                    
                lap_distance = int.from_bytes(packet[lap_distance_offset:lap_distance_offset + 2], byteorder='little')
                # AMS2 UDP sector is 0, 1, 2. Add 1 to match Shared Memory logic (1, 2, 3).
                current_sector = (packet[current_sector_offset] & 0x0F) + 1
                current_lap = packet[current_lap_offset]
                
                try:
                    current_time = struct.unpack_from('<f', packet, current_time_offset)[0]
                    current_sector_time = struct.unpack_from('<f', packet, current_sector_time_offset)[0]
                except struct.error:
                    current_time = 0.0
                    current_sector_time = 0.0

                race_state = packet[race_state_offset] & 0x07
                pit_mode_byte = packet[pit_mode_offset]
                pit_mode = pit_mode_byte & 0x07

                # Lookup name and nationality from cache
                name = self._udp_participant_names.get(i, f"Driver {i}")
                nationality = self._udp_participant_nationalities.get(i, "")

                if name.lower().startswith('safety car'):
                    is_active = False

                participants[i] = {
                    'name': name,
                    'nationality': nationality,
                    'race_position': race_position,
                    'is_active': is_active,
                    'lap_distance': float(lap_distance),
                    'current_lap': current_lap,
                    'current_time': current_time,
                    'current_sector_time': current_sector_time,
                    'current_sector': current_sector,
                    'speed': 0.0, # Will be calculated manually in poll()
                    'pit_mode': pit_mode,
                    'race_state': race_state,
                    'true_distance': 0.0,
                    'gap_ahead': 0.0,
                    'cars_ahead_250m': 0,
                    'flag_colour': 0,
                    'flag_reason': 0,
                    'fastest_lap': 0.0,
                    'last_lap': 0.0,
                }
            return participants
        except Exception:
            return None

    def get_debug_dump_shm(self) -> dict:
        """FR-001/002: Generate raw struct data JSON on-demand."""
        dump_data = {}
        try:
            import mmap
            shm = mmap.mmap(0, ctypes.sizeof(shared_memory_struct.SharedMemory), "$pcars2$")
            shared_memory_obj = shared_memory_struct.SharedMemory.from_buffer_copy(shm)
            shm.close()
            dump_data["shm"] = ctypes_serializer.struct_to_dict(shared_memory_obj)
        except Exception as e:
            dump_data["shm"] = {"error": f"Shared Memory not found or unavailable: {e}"}
        return dump_data

    def get_debug_dump_udp(self) -> dict:
        """FR-001/002: Generate raw struct data JSON on-demand."""
        udp_dump = {}
        for size, packet in self._packet_buffer.items():
            udp_dump[f"packet_{size}_hex"] = packet.hex()
            
        if self._packet_buffer.get(1063):
            udp_dump["parsed_participants"] = self._parse_udp_participants(self._packet_buffer.get(1063))
        if self._packet_buffer.get(308):
            udp_dump["parsed_track_info"] = self._extract_udp_track_info(self._packet_buffer.get(308))
            
        udp_dump["parsed_session_info"] = self._extract_udp_session_info()
        
        # Include internal string caches
        udp_dump["parsed_names"] = self._udp_participant_names
        udp_dump["parsed_nationalities"] = self._udp_participant_nationalities
        udp_dump["parsed_car_names"] = self._udp_car_names
        udp_dump["parsed_car_classes"] = self._udp_car_classes
        udp_dump["parsed_time_splits"] = self._udp_time_splits
            
        return {"udp": udp_dump}
