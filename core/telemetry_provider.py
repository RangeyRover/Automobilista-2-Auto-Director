"""Telemetry data provider for AMS2 Auto Director V4.0.

Abstracts over SharedMemory and UDP data sources, providing a unified
interface for polling participant data. Returns normalised participant
dicts including driver names.

No GUI imports. Fully testable with mock objects.
"""
import time


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
        self._packet_buffer: dict[int, bytes] = {}  # keyed by packet size

    # ── Public API ──────────────────────────────────────────────────────────

    def poll(self, shared_memory_obj=None) -> dict[int, dict] | None:
        """Read current telemetry. Returns participants dict keyed 0-31,
        or None if data source unavailable."""
        if self._mode == 'shared_memory':
            if shared_memory_obj is None:
                self._update_connection_state(data_available=False)
                return None

            track_info = self._extract_track_info(shared_memory_obj)
            if self._detect_track_change(track_info):
                self._distance_history.clear()

            participants = self._extract_all_participants(shared_memory_obj)

            # Calculate derived fields
            track_length = track_info.get('track_length', 1.0)
            for idx, p in participants.items():
                p['true_distance'] = self._calc_true_distance(
                    p['current_lap'], p['lap_distance'], track_length
                )

            self._calc_gaps(participants)
            self._calc_cars_ahead(participants, track_length)

            # Calculate speeds
            now = time.time()
            for idx, p in participants.items():
                if p['is_active']:
                    if idx not in self._distance_history:
                        self._distance_history[idx] = []
                    self._distance_history[idx].append((now, p['lap_distance']))
                    # Keep only last 5 entries
                    self._distance_history[idx] = self._distance_history[idx][-5:]
                    speed = self._calc_speed(idx, track_length)
                    if speed is not None:
                        p['speed'] = speed

            self._update_connection_state(data_available=True)
            return participants

        elif self._mode == 'udp':
            # UDP mode — uses packet buffer
            result = self._parse_udp_participants(self._packet_buffer.get(1063))
            if result is not None:
                self._update_connection_state(data_available=True)
            else:
                self._update_connection_state(data_available=False)
            return result

        return None

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

    def _add_packet_to_buffer(self, packet: bytes):
        """Add a UDP packet to the buffer, keyed by packet size."""
        self._packet_buffer[len(packet)] = packet

    def _parse_udp_participants(self, packet: bytes | None) -> dict[int, dict] | None:
        """Parse a UDP extended packet into participant dicts.

        Returns None if packet is None or invalid.
        """
        if packet is None:
            return None

        # UDP extended packet (1063 bytes) parsing
        # This is the V3.0 format — retained for backwards compatibility
        # Actual parsing uses hardcoded byte offsets from the original
        try:
            participants: dict[int, dict] = {}
            # Basic validation
            if len(packet) < 100:
                return None

            # Placeholder: full UDP parsing to be implemented
            # when we have captured packet samples to validate against
            return participants
        except Exception:
            return None
