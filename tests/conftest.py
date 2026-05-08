"""Shared test fixtures for AMS2 Auto Director V4.0 test suite."""
import pytest
import struct


@pytest.fixture
def make_participant():
    """Factory fixture: returns a single participant dict with sensible defaults.
    Override any field via kwargs.
    """
    def _factory(**overrides):
        defaults = {
            'name': 'Driver',
            'race_position': 1,
            'is_active': True,
            'lap_distance': 500.0,
            'current_lap': 1,
            'current_sector': 0,
            'speed': 60.0,
            'pit_mode': 0,
            'race_state': 2,  # 2 = racing
            'true_distance': 4500.0,
            'gap_ahead': 25.0,
            'cars_ahead_250m': 1,
            'flag_colour': 0,
            'flag_reason': 0,
            'fastest_lap': 90.0,
            'last_lap': 91.0,
        }
        defaults.update(overrides)
        return defaults
    return _factory


@pytest.fixture
def make_participants(make_participant):
    """Factory fixture: returns dict[int, dict] of N participants with
    sequential positions and sensible spread distances.
    Override per-driver fields via per_driver_overrides dict keyed by index.
    """
    def _factory(count=5, track_length=4000.0, **per_driver_overrides):
        participants = {}
        for i in range(count):
            spacing = track_length / count
            lap_dist = spacing * i
            true_dist = track_length + lap_dist  # all on lap 1
            gap = spacing if i > 0 else 0.0
            cars_ahead = min(i, 3)  # cap at 3 for sensible defaults

            overrides = {
                'name': f'Driver_{i}',
                'race_position': i + 1,
                'lap_distance': lap_dist,
                'true_distance': true_dist,
                'gap_ahead': gap,
                'cars_ahead_250m': cars_ahead if spacing <= 250 else 0,
            }
            # Apply per-driver overrides if provided
            if i in per_driver_overrides:
                overrides.update(per_driver_overrides[i])

            participants[i] = make_participant(**overrides)
        return participants
    return _factory


class MockParticipantInfo:
    """Mimics SharedMemory.mParticipantInfo[i] struct."""
    def __init__(self, name=b"Driver\x00", is_active=True, race_position=0, lap_distance=0.0, laps_completed=0, current_sector=0):
        self.mName = name if isinstance(name, bytes) else name.encode('utf-8')
        self.mIsActive = is_active
        self.mRacePosition = race_position
        self.mCurrentLapDistance = lap_distance
        self.mLapsCompleted = laps_completed
        self.mCurrentSector = current_sector


class MockSharedMemory:
    """Mimics the SharedMemory ctypes Structure for testing.
    Override any field via constructor kwargs.
    """
    def __init__(self, **kwargs):
        self.mVersion = kwargs.get('mVersion', 14)
        self.mBuildVersionNumber = kwargs.get('mBuildVersionNumber', 1000)
        self.mNumParticipants = kwargs.get('mNumParticipants', 2)
        self.mTrackLocation = kwargs.get('mTrackLocation', b'Interlagos\x00')
        self.mTrackLocation = kwargs.get('mTrackLocation', b'Interlagos\x00')
        self.mTranslatedTrackLocation = kwargs.get('mTranslatedTrackLocation', b'')
        self.mTrackVariation = kwargs.get('mTrackVariation', b'GP\x00')
        self.mTrackLength = kwargs.get('mTrackLength', 4309.0)
        self.mCurrentTime = kwargs.get('mCurrentTime', 0.0)
        self.mEventTimeRemaining = kwargs.get('mEventTimeRemaining', 0.0)
        self.mLapsInEvent = kwargs.get('mLapsInEvent', 0)
        self.mViewedParticipantIndex = kwargs.get('mViewedParticipantIndex', -1)
        self.mWorldFastestLapTime = kwargs.get('mWorldFastestLapTime', 0.0)
        self.mWorldFastestSector1Time = kwargs.get('mWorldFastestSector1Time', 0.0)
        self.mWorldFastestSector2Time = kwargs.get('mWorldFastestSector2Time', 0.0)
        self.mWorldFastestSector3Time = kwargs.get('mWorldFastestSector3Time', 0.0)
        self.mAmbientTemperature = kwargs.get('mAmbientTemperature', 25.0)
        self.mTrackTemperature = kwargs.get('mTrackTemperature', 35.0)
        self.mRainDensity = kwargs.get('mRainDensity', 0.0)
        self.mSnowDensity = kwargs.get('mSnowDensity', 0.0)
        self.mWindSpeed = kwargs.get('mWindSpeed', 0.0)
        self.mTranslatedTrackVariation = kwargs.get('mTranslatedTrackVariation', b'')
        self.mEnforcedPitStopLap = kwargs.get('mEnforcedPitStopLap', -1)

        # Per-participant arrays (up to 32)
        num = 32
        self.mParticipantInfo = kwargs.get(
            'mParticipantInfo',
            [MockParticipantInfo() for _ in range(num)]
        )
        self.mRacePosition = kwargs.get('mRacePosition', [i + 1 for i in range(num)])
        self.mLapsCompleted = kwargs.get('mLapsCompleted', [0] * num)
        self.mCurrentLapDistance = kwargs.get('mCurrentLapDistance', [0.0] * num)
        self.mCurrentSector = kwargs.get('mCurrentSector', [0] * num)
        self.mSpeeds = kwargs.get('mSpeeds', [60.0] * num)
        self.mPitModes = kwargs.get('mPitModes', [0] * num)
        self.mRaceStates = kwargs.get('mRaceStates', [2] * num)
        self.mHighestFlagColours = kwargs.get('mHighestFlagColours', [0] * num)
        self.mHighestFlagReasons = kwargs.get('mHighestFlagReasons', [0] * num)
        self.mFastestLapTimes = kwargs.get('mFastestLapTimes', [0.0] * num)
        self.mLastLapTimes = kwargs.get('mLastLapTimes', [0.0] * num)
        self.mCurrentSector1Times = kwargs.get('mCurrentSector1Times', [0.0] * 64)
        self.mCurrentSector2Times = kwargs.get('mCurrentSector2Times', [0.0] * 64)
        self.mCurrentSector3Times = kwargs.get('mCurrentSector3Times', [0.0] * 64)
        self.mFastestSector1Times = kwargs.get('mFastestSector1Times', [0.0] * 64)
        self.mFastestSector2Times = kwargs.get('mFastestSector2Times', [0.0] * 64)
        self.mFastestSector3Times = kwargs.get('mFastestSector3Times', [0.0] * 64)
        self.mNationalities = kwargs.get('mNationalities', [0] * 64)
        self.mCarNames = kwargs.get('mCarNames', [b''] * 64)
        self.mCarClassNames = kwargs.get('mCarClassNames', [b''] * 64)


@pytest.fixture
def mock_shared_memory():
    """Factory fixture: returns a MockSharedMemory with overridable fields."""
    def _factory(**kwargs):
        return MockSharedMemory(**kwargs)
    return _factory

@pytest.fixture
def make_udp_telemetry_packet():
    def _factory(viewed_index=0, brake=0, throttle=0, speed=50.0, rpm=8000, max_rpm=13000,
                 gear_num_gears=0x84, crash_state=0, tyre_wear=(0,0,0,0), brake_damage=(0,0,0,0),
                 suspension_damage=(0,0,0,0), aero_damage=0, engine_damage=0,
                 tyre_compound=(b"Medium", b"Medium", b"Medium", b"Medium")):
        buf = bytearray(556)
        buf[12] = viewed_index
        buf[29] = brake
        buf[30] = throttle
        struct.pack_into('<f', buf, 36, speed)
        struct.pack_into('<H', buf, 40, rpm)
        struct.pack_into('<H', buf, 42, max_rpm)
        buf[45] = gear_num_gears
        buf[47] = crash_state
        for i in range(4):
            buf[196+i] = tyre_wear[i]
            buf[200+i] = brake_damage[i]
            buf[204+i] = suspension_damage[i]
        buf[371] = aero_damage
        buf[372] = engine_damage
        for i in range(4):
            comp_bytes = tyre_compound[i]
            buf[378 + i*40 : 378 + i*40 + len(comp_bytes)] = comp_bytes
        return buf
    return _factory

@pytest.fixture
def make_udp_race_data_packet():
    def _factory(world_fastest_lap=72.5, personal_fastest_lap=73.0,
                 world_fastest_sector1=24.0, world_fastest_sector2=24.0, world_fastest_sector3=24.5,
                 track_length=4300.0, track_location=b"Interlagos", track_variation=b"Grand Prix",
                 enforced_pit_stop_lap=-1):
        buf = bytearray(308)
        struct.pack_into('<f', buf, 12, world_fastest_lap)
        struct.pack_into('<f', buf, 16, personal_fastest_lap)
        struct.pack_into('<f', buf, 32, world_fastest_sector1)
        struct.pack_into('<f', buf, 36, world_fastest_sector2)
        struct.pack_into('<f', buf, 40, world_fastest_sector3)
        struct.pack_into('<f', buf, 44, track_length)
        buf[48 : 48 + len(track_location)] = track_location
        buf[112 : 112 + len(track_variation)] = track_variation
        struct.pack_into('<b', buf, 306, enforced_pit_stop_lap)
        return buf
    return _factory

@pytest.fixture
def make_udp_game_state_packet():
    def _factory(game_state=2, ambient_temp=25, track_temp=35,
                 rain_density=0, snow_density=0, wind_speed=5):
        buf = bytearray(24)
        buf[14] = game_state
        struct.pack_into('<b', buf, 16, ambient_temp)
        struct.pack_into('<b', buf, 17, track_temp)
        buf[18] = rain_density
        buf[19] = snow_density
        struct.pack_into('<b', buf, 20, wind_speed)
        return buf
    return _factory

@pytest.fixture
def make_udp_time_stats_packet():
    def _factory(stats=None):
        if stats is None:
            stats = []
        buf = bytearray(1040)
        struct.pack_into('<I', buf, 24, 0) # participant_online_rep
        struct.pack_into('<H', buf, 28, 0) # mp_index
        for i, s in enumerate(stats):
            offset = 16 + i * 32
            struct.pack_into('<6f', buf, offset,
                             s.get('fastest_lap', 0.0),
                             s.get('last_lap', 0.0),
                             s.get('last_sector_time', 0.0),
                             s.get('fastest_sector1', 0.0),
                             s.get('fastest_sector2', 0.0),
                             s.get('fastest_sector3', 0.0))
        return buf
    return _factory

@pytest.fixture
def make_udp_participants_packet():
    def _factory(participants=None):
        if participants is None:
            participants = []
        buf = bytearray(1136)
        for i, p in enumerate(participants):
            name_bytes = p.get('name', f"Driver {i}").encode('utf-8')
            buf[16 + i*64 : 16 + i*64 + len(name_bytes)] = name_bytes
            struct.pack_into('<I', buf, 1040 + i*4, p.get('nationality', 0))
        return buf
    return _factory
