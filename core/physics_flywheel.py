"""
Provides the PhysicsFlywheel class.
Responsible for stabilising `mCurrentTime` by detecting anomalous jumps and substituting
system-clock-based synthetic time until game time recovers.
"""
import time as _time

class PhysicsFlywheel:
    """System-clock time stabilizer for AMS2 replay telemetry.
    
    During camera transitions in replays, mCurrentTime can jump by ~40 seconds
    before snapping back. This class maintains an Internal Master Clock that
    rejects anomalous time deltas (>5.5s) and substitutes system wall-clock
    elapsed time to keep the spline growing with realistic values.
    
    The 5.5s threshold safely accommodates the maximum 20x replay scrub speed
    (which produces ~5.0s per 0.25s polling tick).
    """
    
    ANOMALY_THRESHOLD = 5.5   # seconds — max legitimate delta at 20x scrub is ~5s, 0.5s headroom
    FALLBACK_DT = 0.25        # seconds — used when speed is near zero
    MIN_SPEED = 1.0           # m/s — below this, use FALLBACK_DT
    DEFAULT_SPEED = 80.0      # m/s — ~288 km/h, safe racing assumption
    SPEED_DROP_TOLERANCE = 0.1  # 10% — if implied speed < 10% of last_known_speed, reject
    HEALTHY_TICK_MIN = 0.05   # seconds — minimum delta for a "healthy" game tick
    HEALTHY_TICK_MAX = 1.0    # seconds — maximum delta for a "healthy" game tick
    RESYNC_AFTER = 20         # consecutive healthy ticks (~10s at 2Hz) before force-resync
    
    def __init__(self, clock=None):
        self.internal_master_clock: float | None = None
        self.last_known_speed: float = self.DEFAULT_SPEED
        self.last_leader_distance: float | None = None
        self.is_active: bool = False
        self.did_resync: bool = False               # flag for callers to detect resync
        self._last_game_time: float | None = None   # tracks raw game time for sanity check
        self._consecutive_healthy: int = 0           # consecutive healthy game-time deltas
        self._clock = clock or _time.monotonic       # injectable clock for testing
        self._last_system_time: float | None = None  # wall-clock time of last process() call
    
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
        self._last_system_time = self._clock()
    
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
        
        If consecutive raw mCurrentTime samples show healthy deltas,
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
        advanced by the system wall-clock delta (if anomalous).
        
        Detection uses two layers:
        1. Time threshold: abs(delta) > 5.5s
        2. Speed lie detector: implied_speed < 10% of last_known_speed
        
        During anomalies, the internal clock advances by the real elapsed
        system time (time.monotonic delta), not by distance/speed estimation.
        This keeps the spline growing with realistic time intervals.
        
        Self-healing: if consecutive raw game-time deltas are healthy,
        force-resync regardless of internal clock drift.
        
        Args:
            game_time: Raw mCurrentTime from AMS2 shared memory.
            leader_dist: Leader's total distance (compute_total_distance output).
            
        Returns:
            Stabilized time value for downstream consumers.
        """
        now = self._clock()
        
        # Track raw game time health independent of internal clock
        self._check_game_time_sanity(game_time)
        self.did_resync = False
        
        # First tick — unconditionally sync (sentinel pattern)
        if self.internal_master_clock is None:
            self.internal_master_clock = game_time
            self.last_leader_distance = leader_dist
            self.is_active = False
            self._last_system_time = now
            return game_time
        
        distance_delta = leader_dist - self.last_leader_distance
        
        # Self-healing: if game time has been stable for RESYNC_AFTER ticks, trust it
        if self.is_active and self._consecutive_healthy >= self.RESYNC_AFTER:
            self.internal_master_clock = game_time
            self.last_leader_distance = leader_dist
            self.is_active = False
            self._consecutive_healthy = 0
            self.last_known_speed = self.DEFAULT_SPEED
            self.did_resync = True
            self._last_system_time = now
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
            self._last_system_time = now
            return game_time
        else:
            # REJECT — anomalous frame (camera swap bug)
            # Advance internal clock by SYSTEM TIME delta, not distance/speed
            # Do NOT update last_known_speed (FR-002)
            system_dt = now - self._last_system_time if self._last_system_time is not None else self.FALLBACK_DT
            system_dt = max(0.0, min(system_dt, 2.0))  # clamp to [0, 2s] sanity range
            
            self.internal_master_clock += system_dt
            self.last_leader_distance = leader_dist
            self.is_active = True
            self._last_system_time = now
            return self.internal_master_clock
