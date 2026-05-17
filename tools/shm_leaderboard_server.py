"""Standalone WebSocket server and pure functions for the SHM Leaderboard Test Tool."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared_memory_struct import SharedMemory

def _serialise_struct(struct) -> dict:
    """Recursively serialise a ctypes struct to a dictionary."""
    result = {}
    for field_name, field_type in struct._fields_:
        if field_name.startswith('_'):
            continue
            
        value = getattr(struct, field_name)
        
        if isinstance(value, bytes):
            result[field_name] = value.split(b'\x00', 1)[0].decode('utf-8', errors='replace')
        elif hasattr(value, '__len__') and not isinstance(value, (str, bytes)):
            if len(value) > 0 and hasattr(value[0], 'value') and isinstance(value[0].value, bytes):
                # Array of char arrays (strings)
                if field_name == 'mTyreCompound':
                    # Special case: defined as c_char * 4 * 40, but is 4 strings of 40 chars
                    flat_bytes = bytes(value)
                    result[field_name] = [flat_bytes[i:i+40].split(b'\x00', 1)[0].decode('utf-8', errors='replace') for i in range(0, 160, 40)]
                else:
                    result[field_name] = [v.value.split(b'\x00', 1)[0].decode('utf-8', errors='replace') for v in value]
            elif len(value) > 0 and hasattr(value[0], '_fields_'):
                # Array of structs
                result[field_name] = [_serialise_struct(item) for item in value]
            elif len(value) > 0 and hasattr(value[0], '__len__') and not isinstance(value[0], (str, bytes)):
                # Multi-dimensional array of numbers
                flat = [x for row in value for x in row]
                if field_name == 'mOrientations':
                    # Special case for mOrientations due to C-layout (64x3) being defined as 3x64 in ctypes
                    result[field_name] = [flat[i:i+3] for i in range(0, len(flat), 3)]
                else:
                    result[field_name] = [list(row) for row in value]
            else:
                # Flat array of numbers
                result[field_name] = list(value)
        elif hasattr(value, '_fields_'):
            result[field_name] = _serialise_struct(value)
        else:
            result[field_name] = value
            
    return result

def serialise_shm(shm: SharedMemory) -> dict:
    """Serialise a SharedMemory ctypes struct to a JSON-compatible dictionary."""
    return _serialise_struct(shm)

ENUM_MAP = {
    "mGameState": {
        0: "GAME_EXITED", 1: "GAME_FRONT_END", 2: "GAME_INGAME_PLAYING",
        3: "GAME_INGAME_PAUSED", 4: "GAME_INGAME_INMENU_TIME_TICKING",
        5: "GAME_INGAME_RESTARTING", 6: "GAME_INGAME_REPLAY", 7: "GAME_FRONT_END_REPLAY"
    },
    "mSessionState": {
        0: "SESSION_INVALID", 1: "SESSION_PRACTICE", 2: "SESSION_TEST",
        3: "SESSION_QUALIFY", 4: "SESSION_FORMATION_LAP", 5: "SESSION_RACE",
        6: "SESSION_TIME_ATTACK"
    },
    "mRaceState": {
        0: "RACESTATE_INVALID", 1: "RACESTATE_NOT_STARTED", 2: "RACESTATE_RACING",
        3: "RACESTATE_FINISHED", 4: "RACESTATE_DISQUALIFIED", 5: "RACESTATE_RETIRED",
        6: "RACESTATE_DNF"
    },
    "mPitMode": {
        0: "PIT_MODE_NONE", 1: "PIT_MODE_DRIVING_INTO_PITS", 2: "PIT_MODE_IN_PIT",
        3: "PIT_MODE_DRIVING_OUT_OF_PITS", 4: "PIT_MODE_IN_GARAGE", 5: "PIT_MODE_DRIVING_OUT_OF_GARAGE"
    },
    "mHighestFlagColour": {
        0: "FLAG_COLOUR_NONE", 1: "FLAG_COLOUR_GREEN", 2: "FLAG_COLOUR_BLUE",
        3: "FLAG_COLOUR_WHITE_SLOW_CAR", 4: "FLAG_COLOUR_WHITE_FINAL_LAP",
        5: "FLAG_COLOUR_RED", 6: "FLAG_COLOUR_YELLOW", 7: "FLAG_COLOUR_DOUBLE_YELLOW",
        8: "FLAG_COLOUR_BLACK_AND_WHITE", 9: "FLAG_COLOUR_BLACK_ORANGE_CIRCLE",
        10: "FLAG_COLOUR_BLACK", 11: "FLAG_COLOUR_CHEQUERED"
    },
    "mHighestFlagReason": {
        0: "FLAG_REASON_NONE", 1: "FLAG_REASON_SOLO_CRASH", 2: "FLAG_REASON_VEHICLE_CRASH",
        3: "FLAG_REASON_VEHICLE_OBSTRUCTION"
    },
    "mPitSchedule": {
        0: "PIT_SCHEDULE_NONE", 1: "PIT_SCHEDULE_PLAYER_REQUESTED", 2: "PIT_SCHEDULE_ENGINEER_REQUESTED",
        3: "PIT_SCHEDULE_DAMAGE_REQUESTED", 4: "PIT_SCHEDULE_MANDATORY", 5: "PIT_SCHEDULE_DRIVE_THROUGH",
        6: "PIT_SCHEDULE_STOP_GO", 7: "PIT_SCHEDULE_PITSPOT_OCCUPIED"
    }
}

ARRAY_ENUM_MAP = {
    "mRaceStates": "mRaceState",
    "mPitModes": "mPitMode",
    "mPitSchedules": "mPitSchedule",
    "mHighestFlagColours": "mHighestFlagColour",
    "mHighestFlagReasons": "mHighestFlagReason"
}

def annotate_enums(data: dict) -> dict:
    """Inject human-readable enum labels into a serialised shared memory dictionary."""
    if data is None:
        return None
    import copy
    result = copy.copy(data)
    
    for key, mapping in ENUM_MAP.items():
        if key in result:
            val = result[key]
            result[f"{key}_label"] = mapping.get(val, f"UNKNOWN({val})")
            
    for array_key, scalar_key in ARRAY_ENUM_MAP.items():
        if array_key in result:
            mapping = ENUM_MAP[scalar_key]
            result[f"{array_key}_labels"] = [mapping.get(v, f"UNKNOWN({v})") for v in result[array_key]]
            
    return result

import bisect

class DistanceTimeSpline:
    """Maintains a history of distance-time pairs for gap interpolation."""
    def __init__(self, min_interval: float = 0.5):
        self.min_interval = min_interval
        self.distances = []
        self.times = []
        
    def reset(self):
        """Clear all recorded samples."""
        self.distances.clear()
        self.times.clear()
        
    @property
    def sample_count(self) -> int:
        return len(self.distances)
        
    @property
    def distance_range(self) -> tuple[float, float] | None:
        if not self.distances:
            return None
        return (self.distances[0], self.distances[-1])
        
    def record(self, distance: float, time: float) -> bool:
        """
        Attempt to record a new sample.
        Rejects if time since last sample < min_interval or if distance is not strictly monotonically increasing.
        Returns True if accepted, False if rejected.
        """
        if self.times:
            if time - self.times[-1] < self.min_interval:
                return False
            if distance <= self.distances[-1]:
                return False
                
        self.distances.append(distance)
        self.times.append(time)
        return True
        
    def interpolate_time(self, distance: float) -> float | None:
        """
        Interpolate the time at a given distance.
        Returns None if there are <2 samples or if the distance is < the first sample.
        Extrapolates if distance is > the last sample.
        """
        if self.sample_count < 2:
            return None
            
        if distance < self.distances[0]:
            return None
            
        if distance > self.distances[-1]:
            idx = self.sample_count - 1
        else:
            idx = bisect.bisect_right(self.distances, distance)
            if idx == 0:
                return self.times[0]
            if idx == self.sample_count:
                idx = self.sample_count - 1
                
        d0, d1 = self.distances[idx - 1], self.distances[idx]
        t0, t1 = self.times[idx - 1], self.times[idx]
        
        if d1 == d0:
            return t0
            
        if distance > d1:
            speed = (d1 - d0) / (t1 - t0) if t1 > t0 else 0.0
            # If game physics paused during camera swap, speed approaches 0.
            # We enforce a 10m/s (~36km/h) minimum speed for extrapolation to prevent crazy time spikes.
            if speed < 10.0:
                speed = 10.0
            return t1 + (distance - d1) / speed
            
        # Linear interpolation
        fraction = (distance - d0) / (d1 - d0)
        return t0 + fraction * (t1 - t0)


class PhysicsFlywheel:
    """Dead-reckoning time stabilizer for AMS2 replay telemetry.
    
    During camera transitions in replays, mCurrentTime can jump by ~40 seconds
    before snapping back. This class maintains an Internal Master Clock that
    rejects anomalous time deltas (>10.0s) and synthesizes replacement time
    using distance_delta / last_known_speed.
    
    The 10.0s threshold safely accommodates the maximum 20x replay scrub speed
    (which produces ~5.0s per 0.25s polling tick).
    """
    
    ANOMALY_THRESHOLD = 5.5   # seconds — max legitimate delta at 20x scrub is ~5s, 0.5s headroom
    FALLBACK_DT = 0.25        # seconds — used when speed is near zero
    MIN_SPEED = 1.0           # m/s — below this, use FALLBACK_DT
    DEFAULT_SPEED = 80.0      # m/s — ~288 km/h, safe racing assumption
    SPEED_DROP_TOLERANCE = 0.1  # 10% — if implied speed < 10% of last_known_speed, reject
    HEALTHY_TICK_MIN = 0.05   # seconds — minimum delta for a "healthy" game tick
    HEALTHY_TICK_MAX = 1.0    # seconds — maximum delta for a "healthy" game tick
    RESYNC_AFTER = 5          # consecutive healthy ticks before force-resync
    
    def __init__(self):
        self.internal_master_clock: float | None = None
        self.last_known_speed: float = self.DEFAULT_SPEED
        self.last_leader_distance: float | None = None
        self.is_active: bool = False
        self._last_game_time: float | None = None  # tracks raw game time for sanity check
        self._consecutive_healthy: int = 0          # consecutive healthy game-time deltas
    
    def reset(self, current_time: float, leader_dist: float) -> None:
        """Force-sync the Internal Master Clock on session reset (FR-007).
        
        Called when should_reset_spline() triggers to prevent permanent desync
        after session transitions.
        """
        self.internal_master_clock = current_time
        self.last_leader_distance = leader_dist
        self.is_active = False
        self.last_known_speed = self.DEFAULT_SPEED
        self._last_game_time = current_time
        self._consecutive_healthy = 0
    
    def _is_anomalous(self, game_time: float, distance_delta: float) -> bool:
        """Two-layer anomaly detection: time threshold AND speed lie detector."""
        time_delta = abs(game_time - self.internal_master_clock)
        
        # Layer 1: Time threshold — reject if time jumped more than 5.5s
        if time_delta > self.ANOMALY_THRESHOLD:
            return True
        
        # Layer 2: Speed lie detector — only on forward movement (distance_delta > 0)
        # Negative distance_delta (lap transitions) is NOT a speed anomaly
        actual_dt = game_time - self.internal_master_clock
        if actual_dt > 0 and distance_delta > 0 and self.last_known_speed >= self.MIN_SPEED:
            implied_speed = distance_delta / actual_dt
            if implied_speed < self.last_known_speed * self.SPEED_DROP_TOLERANCE:
                return True
        
        return False
    
    def _check_game_time_sanity(self, game_time: float) -> None:
        """Track consecutive healthy game-time deltas for self-healing resync.
        
        If 5 consecutive raw mCurrentTime samples show healthy ~0.25s deltas,
        the game clock is clearly stable and we should trust it — even if our
        internal clock has drifted far away.
        """
        if self._last_game_time is not None:
            raw_delta = game_time - self._last_game_time
            if self.HEALTHY_TICK_MIN <= raw_delta <= self.HEALTHY_TICK_MAX:
                self._consecutive_healthy += 1
            else:
                self._consecutive_healthy = 0
        self._last_game_time = game_time
    
    def process(self, game_time: float, leader_dist: float) -> float:
        """Process a telemetry frame and return the stabilized time.
        
        Returns either the real game_time (if healthy) or a synthetic time
        calculated via dead reckoning (if anomalous).
        
        Detection uses two layers:
        1. Time threshold: abs(delta) > 5.5s
        2. Speed lie detector: implied_speed < 10% of last_known_speed
        
        Self-healing: if 5 consecutive raw game-time deltas are healthy,
        force-resync regardless of internal clock drift.
        
        Args:
            game_time: Raw mCurrentTime from AMS2 shared memory.
            leader_dist: Leader's total distance (compute_total_distance output).
            
        Returns:
            Stabilized time value for downstream consumers.
        """
        # Track raw game time health independent of internal clock
        self._check_game_time_sanity(game_time)
        
        # First tick — unconditionally sync (sentinel pattern)
        if self.internal_master_clock is None:
            self.internal_master_clock = game_time
            self.last_leader_distance = leader_dist
            self.is_active = False
            return game_time
        
        distance_delta = leader_dist - self.last_leader_distance
        
        # Self-healing: if game time has been stable for 5+ ticks, trust it
        if self.is_active and self._consecutive_healthy >= self.RESYNC_AFTER:
            self.internal_master_clock = game_time
            self.last_leader_distance = leader_dist
            self.is_active = False
            self._consecutive_healthy = 0
            self.last_known_speed = self.DEFAULT_SPEED
            return game_time
        
        if not self._is_anomalous(game_time, distance_delta):
            # ACCEPT — healthy frame or legitimate scrub
            # Update speed only from valid ticks with positive time progression
            actual_dt = game_time - self.internal_master_clock
            if actual_dt > 0 and distance_delta > 0:
                self.last_known_speed = distance_delta / actual_dt
            
            self.internal_master_clock = game_time
            self.last_leader_distance = leader_dist
            self.is_active = False
            return game_time
        else:
            # REJECT — anomalous frame (camera swap bug)
            # Do NOT update last_known_speed (FR-002)
            distance_delta_clamped = max(0.0, distance_delta)
            
            if self.last_known_speed < self.MIN_SPEED:
                synthetic_dt = self.FALLBACK_DT
            else:
                synthetic_dt = distance_delta_clamped / self.last_known_speed
            
            self.internal_master_clock += synthetic_dt
            self.last_leader_distance = leader_dist
            self.is_active = True
            return self.internal_master_clock


def compute_total_distance(current_lap: int, track_length: float, lap_distance: float) -> float:
    """Calculate absolute total distance from lap metrics."""
    return (current_lap - 1) * track_length + lap_distance

def compute_time_gap(driver_total_dist: float, current_time: float, spline: DistanceTimeSpline) -> float | None:
    """
    Calculate the time gap between the leader and a driver at a given distance.
    Returns the time difference in seconds, or None if the distance cannot be interpolated.
    """
    if spline is None:
        return None
    leader_time_at_dist = spline.interpolate_time(driver_total_dist)
    if leader_time_at_dist is None:
        return None
    return max(0.0, current_time - leader_time_at_dist)

def correlate_drivers(data: dict, active_only: bool = False, spline: DistanceTimeSpline = None, previous_spline: DistanceTimeSpline = None, pit_entry_times: dict = None, flywheel: PhysicsFlywheel = None) -> list:
    """Bundle indexed data arrays into a sorted list of driver dictionaries."""
    if not data or "mNumParticipants" not in data:
        return []
        
    num = data["mNumParticipants"]
    participants = data.get("mParticipantInfo", [])
    track_len = data.get("mTrackLength", 0.0)
    
    drivers = []
    
    for i in range(min(num, len(participants))):
        p_info = participants[i]
        driver = dict(p_info)
        
        if active_only and not driver.get("mIsActive", False):
            continue
            
        for key, value in data.items():
            if key == "mParticipantInfo":
                continue
            if isinstance(value, list) and len(value) >= num:
                out_key = key
                if key.endswith("_labels"):
                    out_key = key[:-1]
                driver[out_key] = value[i]
                
        current_lap = driver.get("mCurrentLap", 1)
        dist = driver.get("mCurrentLapDistance", 0.0)
        driver["_total_dist"] = compute_total_distance(current_lap, track_len, dist)
        
        current_time = data.get("mCurrentTime", 0.0)
        pit_mode = driver.get("mPitModes", 0)
        driver_name = driver.get("mName")
        
        driver["_in_pits"] = False
        driver["_pit_time"] = None
        
        if pit_mode > 0:
            driver["_in_pits"] = True
            if pit_entry_times is not None and driver_name:
                if driver_name not in pit_entry_times:
                    pit_entry_times[driver_name] = current_time
                driver["_pit_time"] = current_time - pit_entry_times[driver_name]
        else:
            if pit_entry_times is not None and driver_name in pit_entry_times:
                del pit_entry_times[driver_name]
        
        drivers.append(driver)
        
    def sort_key(d):
        pos = d.get("mRacePosition", 0)
        return pos if pos > 0 else 99999
        
    drivers.sort(key=sort_key)
    
    if drivers:
        current_time = data.get("mCurrentTime", 0.0)
        leader_dist = max(d["_total_dist"] for d in drivers)
        
        # Physics Flywheel: stabilize mCurrentTime before downstream consumers
        if flywheel is not None:
            current_time = flywheel.process(current_time, leader_dist)
        
        for i, d in enumerate(drivers):
            d["_gap"] = leader_dist - d["_total_dist"]
            
            if i == 0 or d["_gap"] <= 0.0:
                d["_time_gap"] = 0.0
            else:
                time_gap = compute_time_gap(d["_total_dist"], current_time, spline)
                if time_gap is None and previous_spline is not None:
                    time_gap = compute_time_gap(d["_total_dist"], current_time, previous_spline)
                d["_time_gap"] = time_gap
            
    return drivers

def process_shm(shm: SharedMemory, active_only: bool = False, spline: DistanceTimeSpline = None, previous_spline: DistanceTimeSpline = None, pit_entry_times: dict = None, flywheel: PhysicsFlywheel = None) -> dict:
    """Process the raw ctypes struct into the final WebSocket payload."""
    raw_data = serialise_shm(shm)
    annotated = annotate_enums(raw_data)
    leaderboard = correlate_drivers(annotated, active_only, spline, previous_spline, pit_entry_times, flywheel)
    payload = {
        "raw": annotated,
        "leaderboard": leaderboard
    }
    
    if spline is not None:
        payload["spline"] = {
            "distances": spline.distances,
            "times": spline.times
        }
        
    return payload

import json
import asyncio

def should_reset_spline(prev_state: int | None, curr_state: int, prev_participants: int, curr_participants: int) -> bool:
    """Determine if session state implies we should flush the splines."""
    if curr_participants == 0:
        return True
    if prev_state == 5 and curr_state != 5: # SESSION_RACE is 5
        return True
    return False

def get_leader_name(leaderboard: list) -> str | None:
    """Extract the current leader's name from a correlated leaderboard."""
    if leaderboard:
        return leaderboard[0].get("mName")
    return None

async def broadcast_telemetry(connected_clients: set, payload: dict):
    """Broadcast JSON payload to all connected clients."""
    if not connected_clients:
        return
        
    message = json.dumps(payload)
    aws = [client.send(message) for client in connected_clients]
    if aws:
        await asyncio.gather(*aws, return_exceptions=True)

async def telemetry_loop(connected_clients: set, active_only: bool):
    """Poll AMS2 shared memory and broadcast updates to clients."""
    import mmap
    import ctypes
    shm_name = "$pcars2$"
    shm_file = None
    spline = DistanceTimeSpline()
    previous_spline = None
    last_leader_name = None
    last_session_state = None
    last_participants = 0
    pit_entry_times = {}
    time_history = []
    flywheel = PhysicsFlywheel()
    
    while True:
        try:
            if shm_file is None:
                try:
                    shm_file = mmap.mmap(0, ctypes.sizeof(SharedMemory), shm_name, access=mmap.ACCESS_READ)
                except OSError:
                    if connected_clients:
                        await broadcast_telemetry(connected_clients, {"status": "Waiting for AMS2..."})
                    await asyncio.sleep(2.0)
                    continue
            
            shm = SharedMemory.from_buffer_copy(shm_file)
            
            curr_state = shm.mSessionState
            curr_participants = shm.mNumParticipants
            
            if should_reset_spline(last_session_state, curr_state, last_participants, curr_participants):
                spline.reset()
                previous_spline = None
                last_leader_name = None
                pit_entry_times.clear()
                flywheel.reset(shm.mCurrentTime, 0.0)
                
            last_session_state = curr_state
            last_participants = curr_participants
            
            payload = process_shm(shm, active_only=active_only, spline=spline, previous_spline=previous_spline, pit_entry_times=pit_entry_times, flywheel=flywheel)
            payload["status"] = "Connected"
            payload["flywheel_active"] = flywheel.is_active
            
            leaderboard = payload.get("leaderboard", [])
            leader_name = get_leader_name(leaderboard)
            
            if leader_name and leader_name != last_leader_name:
                previous_spline = spline
                spline = DistanceTimeSpline()
                last_leader_name = leader_name
                
            if leaderboard:
                leader = leaderboard[0]
                leader_dist = leader.get("_total_dist")
                if leader_dist is not None:
                    # Use flywheel-stabilized time, NOT raw shm.mCurrentTime
                    stabilized_time = flywheel.internal_master_clock if flywheel.internal_master_clock is not None else shm.mCurrentTime
                    spline.record(leader_dist, stabilized_time)
            
            time_history.append(shm.mCurrentTime)
            if len(time_history) > 200: # ~50 seconds of history at 4Hz
                time_history.pop(0)
                
            payload["time_history"] = list(time_history)
            
            await broadcast_telemetry(connected_clients, payload)
            
        except Exception as e:
            if shm_file is not None:
                shm_file.close()
                shm_file = None
            if connected_clients:
                await broadcast_telemetry(connected_clients, {"status": f"Error: {str(e)}"})
                
        await asyncio.sleep(0.25) # ~4Hz

async def main(host="127.0.0.1", port=8770, active_only=False):
    """Main entry point for the standalone server."""
    import websockets
    connected_clients = set()
    
    async def handler(websocket):
        connected_clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            connected_clients.remove(websocket)
            
    server = await websockets.serve(handler, host, port)
    print(f"SHM Leaderboard Server started on ws://{host}:{port}")
    print(f"Active Only Mode: {active_only}")
    
    loop_task = asyncio.create_task(telemetry_loop(connected_clients, active_only))
    await asyncio.Future()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-only", action="store_true", help="Filter inactive drivers")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP")
    parser.add_argument("--port", type=int, default=8770, help="Port")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(host=args.host, port=args.port, active_only=args.active_only))
    except KeyboardInterrupt:
        print("Server stopped.")
