"""Shared test fixtures for AMS2 Auto Director V4.0 test suite."""
import pytest


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
        self.mTranslatedTrackLocation = kwargs.get('mTranslatedTrackLocation', b'')
        self.mTrackVariation = kwargs.get('mTrackVariation', b'GP\x00')
        self.mTrackLength = kwargs.get('mTrackLength', 4309.0)
        self.mCurrentTime = kwargs.get('mCurrentTime', 0.0)

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


@pytest.fixture
def mock_shared_memory():
    """Factory fixture: returns a MockSharedMemory with overridable fields."""
    def _factory(**kwargs):
        return MockSharedMemory(**kwargs)
    return _factory
