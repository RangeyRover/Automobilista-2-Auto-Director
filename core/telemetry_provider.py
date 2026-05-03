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
        self._last_poll_time = time.time()
        self._packet_buffer: dict[int, bytes] = {}  # keyed by packet size
        
        # UDP State
        self._udp_port = 5606
        self._udp_running = False
        self._udp_thread: threading.Thread | None = None
        self._udp_socket: socket.socket | None = None
        self._udp_participant_names: dict[int, str] = {}

    # ── Public API ──────────────────────────────────────────────────────────

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

        # Calculate derived fields
        track_length = track_info.get('track_length', 1.0)
        for idx, p in participants.items():
            p['true_distance'] = self._calc_true_distance(
                p['current_lap'], p['lap_distance'], track_length
            )

        self._calc_gaps(participants)
        self._calc_cars_ahead(participants, track_length)

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
            is_active = bool(getattr(info, 'mIsActive', False)) and i < num

            # Decode name — handle bytes with null terminator
            raw_name = getattr(info, 'mName', b'')
            if isinstance(raw_name, bytes):
                name = raw_name.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
            else:
                name = str(raw_name).strip()

            participants[i] = {
                'name': name,
                'race_position': info.mRacePosition if hasattr(info, 'mRacePosition') else 0,
                'is_active': is_active,
                'lap_distance': info.mCurrentLapDistance if hasattr(info, 'mCurrentLapDistance') else 0.0,
                'current_lap': info.mLapsCompleted if hasattr(info, 'mLapsCompleted') else 0,
                'current_sector': info.mCurrentSector if hasattr(info, 'mCurrentSector') else 0,
                'speed': sm.mSpeeds[i] if hasattr(sm, 'mSpeeds') else 0.0,
                'pit_mode': sm.mPitModes[i] if hasattr(sm, 'mPitModes') else 0,
                'race_state': sm.mRaceStates[i] if hasattr(sm, 'mRaceStates') else 0,
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
                
                # DEBUG: Output to console
                print(f"[UDP DEBUG] Received packet of size {packet_size} from {addr}")
                
                # Proactively parse string packets to populate name cache
                if packet_size in (1136, 1367):
                    print(f"[UDP DEBUG] Parsing name strings from {packet_size}-byte packet")
                    self._parse_udp_names(data)
            except Exception as e:
                if not self._udp_running:
                    break  # Socket closed gracefully
                print(f"[UDP DEBUG] Receive Error: {e}")
                continue

    def _add_packet_to_buffer(self, packet: bytes):
        """Add a UDP packet to the buffer, keyed by packet size."""
        self._packet_buffer[len(packet)] = packet

    def _parse_udp_names(self, packet: bytes):
        """Parse 1367-byte strings packet to cache driver names."""
        # Offset 16 is where 16 names of 64 bytes each start
        for i in range(16):
            offset = 16 + (i * 64)
            if offset + 64 <= len(packet):
                raw_name = packet[offset:offset+64]
                name = raw_name.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                if name:
                    self._udp_participant_names[i] = name
                    
        # If this is a PCars2 1367 packet, there are 16 names. 
        # PCars2 uses an additional packet (PacketType 2) for names 16-31.
        # But for testing, caching them correctly keyed by index is sufficient.

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
        info = {'event_time_remaining': 0.0, 'laps_in_event': 0}
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
                    info['event_time_remaining'] = 0.0  # Or keep as -1.0 depending on GUI preference
                # print(f"[UDP DEBUG] Parsed Session Info: Event Time Remaining = {val:.2f}s")
            except struct.error as e:
                print(f"[UDP DEBUG] Error unpacking session time: {e}")
                
        # sRaceData (308 bytes) holds total laps
        packet_race = self._packet_buffer.get(308)
        if packet_race and len(packet_race) >= 308:
            try:
                # unsigned short sLapsTimeInEvent (304)
                laps_time = struct.unpack_from('<H', packet_race, 304)[0]
                is_timed = bool(laps_time & 0x8000)
                actual_laps = laps_time & 0x7FFF
                print(f"[UDP DEBUG] 308 Packet: sLapsTimeInEvent = {actual_laps} (Timed={is_timed})")
                if not is_timed:
                    info['laps_in_event'] = actual_laps
            except struct.error as e:
                print(f"[UDP DEBUG] Error unpacking laps: {e}")
                
        return info

    def _parse_udp_participants(self, packet: bytes | None) -> dict[int, dict] | None:
        """Parse a UDP extended packet into participant dicts."""
        if packet is None or len(packet) < 1063:
            return None

        try:
            participants: dict[int, dict] = {}
            for i in range(32):
                race_position_offset = 31 + i * 32 + 16
                lap_distance_offset = 31 + i * 32 + 14
                current_sector_offset = 31 + i * 32 + 17
                current_lap_offset = 31 + i * 32 + 23
                race_state_offset = 31 + i * 32 + 22
                pit_mode_offset = 31 + i * 32 + 19

                # Safely parse bytes
                race_pos_byte = packet[race_position_offset]
                race_position = race_pos_byte & 0x7F
                is_active = (race_pos_byte & 0x80) != 0
                lap_distance = int.from_bytes(packet[lap_distance_offset:lap_distance_offset + 2], byteorder='little')
                current_sector = packet[current_sector_offset] & 0x0F
                current_lap = packet[current_lap_offset]
                race_state = packet[race_state_offset] & 0x07
                pit_mode_byte = packet[pit_mode_offset]
                pit_mode = pit_mode_byte & 0x07

                # Lookup name from cache
                name = self._udp_participant_names.get(i, f"Driver {i}")

                participants[i] = {
                    'name': name,
                    'race_position': race_position,
                    'is_active': is_active,
                    'lap_distance': float(lap_distance),
                    'current_lap': current_lap,
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
