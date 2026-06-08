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
from core.utils import ctypes_serializer
from core.spline import DistanceTimeSpline
from core.physics_flywheel import PhysicsFlywheel
from core.udp_parser import UDPParserMixin, PacketBuffer

class TelemetryProvider(UDPParserMixin):
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
        self._lock = threading.Lock()
        self._udp_lock = threading.Lock()
        self._packet_buffer_lock = threading.RLock()
        self._packet_buffer = PacketBuffer(self)
        self._last_num_participants = 0
        self._leader_spline = DistanceTimeSpline()
        self._flywheel = PhysicsFlywheel()
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
        # Diagnostics
        self._time_history: list[dict] = []
        self._dropped_packets_counter = 0
        self._received_packets_counter = 0
        self._poll_count = 0
        self._poll_latencies: list[float] = []
        self._last_diag_time = time.time()
    # ── Public API ──────────────────────────────────────────────────────────
    def get_packet_buffer_snapshot(self, client: str = 'bridge') -> dict[int, bytes]:
        """Return a snapshot of raw bytes for all buffered packets, marking them read by client."""
        snapshot = {}
        with self._packet_buffer_lock:
            for size, slot in self._packet_buffer.items():
                if slot.packet is not None:
                    snapshot[size] = slot.packet
                    if client == 'poll':
                        slot.read_by_poll = True
                    elif client == 'bridge':
                        slot.read_by_bridge = True
        return snapshot
    def udp_has_track_length(self) -> bool:
        """Return True if a 308-byte packet is buffered with track_length > 0."""
        with self._packet_buffer_lock:
            slot = self._packet_buffer.get(308)
            packet = slot.packet if slot else None
        if not packet or len(packet) < 48:
            return False
        try:
            track_length = struct.unpack_from('f', packet, 44)[0]
            return track_length > 0.0
        except struct.error:
            return False
    def udp_has_participant_names(self) -> bool:
        """Return True if at least one participant name is cached from UDP."""
        with self._udp_lock:
            return len(self._udp_participant_names) > 0
    def get_udp_car_names(self) -> dict[int, str]:
        """Return cached car names parsed from UDP Strings packets."""
        with self._udp_lock:
            return dict(self._udp_car_names)
    def get_udp_car_classes(self) -> dict[int, str]:
        """Return cached car classes parsed from UDP Strings packets."""
        with self._udp_lock:
            return dict(self._udp_car_classes)
    def poll(self, shared_memory_obj=None) -> dict[int, dict] | None:
        """Read current telemetry. Returns participants dict keyed 0-31,
        or None if data source unavailable."""
        t_start = time.time()
        self._lock.acquire()
        try:
            participants = None
            track_info = {}
            # Primary Source: Shared Memory
            if self._mode == 'shared_memory' and shared_memory_obj is not None:
                track_info = self._extract_track_info(shared_memory_obj)
                self._extract_session_info(shared_memory_obj)
                participants = self._extract_all_participants(shared_memory_obj)
                self._update_connection_state(data_available=True)
            # Fallback/Exclusive Source: UDP
            elif self._mode == 'udp' or (self._mode == 'shared_memory' and shared_memory_obj is None):
                snapshot = self.get_packet_buffer_snapshot(client='poll')
                track_info_packet = snapshot.get(308)
                if track_info_packet:
                    track_info = self._extract_udp_track_info(track_info_packet)
                self._extract_udp_session_info()
                participants = self._parse_udp_participants(snapshot.get(1063))
                if participants is not None:
                    self._update_connection_state(data_available=True)
                else:
                    self._update_connection_state(data_available=False)
            if participants is None:
                return None
            curr_participants = len(participants) if participants else 0
            # Session Boundary Detection
            if curr_participants != self._last_num_participants:
                self._distance_history.clear()
                self._car_splines.clear()
                self._tyre_stint_start_lap.clear()
            self._last_num_participants = curr_participants
            if participants is None:
                return None
            if self._detect_track_change(track_info):
                self._distance_history.clear()
                self._car_splines.clear()
                self._tyre_stint_start_lap.clear()
                self._leader_spline.reset()
                self._flywheel.reset(0.0, 0.0)
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
            # Get leader info
            active_list = [(idx, p) for idx, p in participants.items() if p.get('is_active', False) and p.get('race_position', 999) > 0]
            leader_dist = 0.0
            if active_list:
                active_list.sort(key=lambda x: x[1].get('race_position', 999))
                leader_dist = active_list[0][1].get('true_distance', 0.0)
            # 1. Flywheel Stabilization
            stable_time = self._flywheel.process(game_time, leader_dist)
            # 2. Trimming triggers (US1 & US2)
            if self._leader_spline.times:
                if stable_time < self._leader_spline.times[-1] or self._flywheel.did_resync:
                    self._leader_spline.trim_future_points(stable_time)
            # 3. Leader Spline Recording
            if active_list:
                self._leader_spline.record(leader_dist, stable_time)
            # 4. Gap Calculation using spline
            self._calc_live_time_gaps(participants, track_length, stable_time)
            now = time.time()
            dt = now - self._last_poll_time
            if dt <= 0:
                dt = 0.001
            # Calculate speeds with time delay protection
            if dt >= 0.05:
                for idx, p in participants.items():
                    if 'true_distance' in p:
                        self._distance_history.setdefault(idx, []).append((now, p['true_distance']))
                        # keep last 5
                        self._distance_history[idx] = self._distance_history[idx][-5:]
                        speed = self._calc_speed(idx, track_length)
                        if speed is not None:
                            p['speed'] = speed
                        p['closing_speed'] = self._calc_closing_speed(idx, p.get('gap_ahead', 0.0), dt)
                self._last_poll_time = now
            return participants
        finally:
            self._lock.release()
            t_end = time.time()
            self._poll_count += 1
            self._poll_latencies.append(t_end - t_start)
            if t_end - self._last_diag_time >= 10.0:
                self._print_diagnostics(t_end)

    def _print_diagnostics(self, current_time: float):
        """Prints performance diagnostics (loop frequencies, latencies, packet stats)."""
        duration = current_time - self._last_diag_time
        if duration <= 0:
            duration = 1.0
        poll_hz = self._poll_count / duration
        avg_latency_ms = (sum(self._poll_latencies) / len(self._poll_latencies) * 1000) if self._poll_latencies else 0.0
        with self._packet_buffer_lock:
            received = self._received_packets_counter
            dropped = self._dropped_packets_counter
        print(f"[PERF DIAGNOSTICS] Duration: {duration:.1f}s | "
              f"Poll Frequency: {poll_hz:.2f} Hz | "
              f"Average Poll Latency: {avg_latency_ms:.2f} ms | "
              f"UDP Packets: Received={received}, Dropped={dropped}")
        # Reset counters/history
        self._poll_count = 0
        self._poll_latencies.clear()
        self._last_diag_time = current_time
    @property
    def spline_data(self) -> dict:
        with self._lock:
            return {
                "distances": list(self._leader_spline.distances) if hasattr(self, '_leader_spline') else [],
                "times": list(self._leader_spline.times) if hasattr(self, '_leader_spline') else [],
            }
    @property
    def flywheel_active(self) -> bool:
        return self._flywheel.is_active if hasattr(self, '_flywheel') else False
    @property
    def time_history(self) -> list:
        return self._time_history if hasattr(self, '_time_history') else []
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
                
        # Override with stabilized time if available to prevent glitch-induced rewinds
        if hasattr(self, '_flywheel') and self._flywheel.internal_master_clock is not None:
            info['current_time'] = self._flywheel.internal_master_clock
            
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
        last_lap = leader.get('last_lap', 0.0)
        leader_dist = leader.get('true_distance', 0.0)
        if last_lap > 10.0 and track_length > 100.0:
            avg_speed = track_length / last_lap
        for i in range(len(active)):
            active[i][0]
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
                spline_time = self._leader_spline.interpolate_time(my_dist)
                if spline_time is not None:
                    p['time_gap_to_leader'] = max(0.0, game_time - spline_time)
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
    def get_debug_dump_shm(self) -> dict:
        """FR-001/002: Generate raw struct data JSON on-demand."""
        dump_data = {}
        try:
            import mmap
            import ctypes
            import shared_memory_struct
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
        with self._packet_buffer_lock:
            # Create a local copy of raw packet bytes under lock
            packets_copy = {size: slot.packet for size, slot in self._packet_buffer.items() if slot.packet}
            
        for size, packet in packets_copy.items():
            udp_dump[f"packet_{size}_hex"] = packet.hex()
        if packets_copy.get(1063):
            udp_dump["parsed_participants"] = self._parse_udp_participants(packets_copy.get(1063))
        if packets_copy.get(308):
            udp_dump["parsed_track_info"] = self._extract_udp_track_info(packets_copy.get(308))
        udp_dump["parsed_session_info"] = self._extract_udp_session_info()
        # Include internal string caches
        with self._udp_lock:
            udp_dump["parsed_names"] = dict(self._udp_participant_names)
            udp_dump["parsed_nationalities"] = dict(self._udp_participant_nationalities)
            udp_dump["parsed_car_names"] = dict(self._udp_car_names)
            udp_dump["parsed_car_classes"] = dict(self._udp_car_classes)
            udp_dump["parsed_time_splits"] = dict(self._udp_time_splits)
        return {"udp": udp_dump}
