"""Smoke tests for shared test fixtures — validates factory output shapes."""
from tests.conftest import MockSharedMemory, MockParticipantInfo


class TestMakeParticipant:
    """T009: Verify make_participant fixture returns correct schema."""

    def test_defaults_have_all_keys(self, make_participant):
        p = make_participant()
        required_keys = {
            'name', 'race_position', 'is_active', 'lap_distance',
            'current_lap', 'current_sector', 'speed', 'pit_mode',
            'race_state', 'true_distance', 'gap_ahead', 'cars_ahead_250m',
            'flag_colour', 'flag_reason', 'fastest_lap', 'last_lap',
        }
        assert set(p.keys()) == required_keys

    def test_override_applies(self, make_participant):
        p = make_participant(name='Alice', race_position=5)
        assert p['name'] == 'Alice'
        assert p['race_position'] == 5

    def test_defaults_are_sensible(self, make_participant):
        p = make_participant()
        assert p['is_active'] is True
        assert p['speed'] > 0
        assert p['pit_mode'] == 0


class TestMakeParticipants:
    """T009: Verify make_participants fixture returns correct shape."""

    def test_returns_correct_count(self, make_participants):
        ps = make_participants(count=5)
        assert len(ps) == 5

    def test_keys_are_ints(self, make_participants):
        ps = make_participants(count=3)
        assert all(isinstance(k, int) for k in ps.keys())

    def test_positions_are_sequential(self, make_participants):
        ps = make_participants(count=5)
        positions = [ps[i]['race_position'] for i in range(5)]
        assert positions == [1, 2, 3, 4, 5]


class TestMockSharedMemory:
    """T009: Verify MockSharedMemory has all required fields."""

    def test_default_fields_exist(self, mock_shared_memory):
        sm = mock_shared_memory()
        assert hasattr(sm, 'mNumParticipants')
        assert hasattr(sm, 'mTrackLocation')
        assert hasattr(sm, 'mTrackLength')
        assert hasattr(sm, 'mCurrentTime')
        assert hasattr(sm, 'mParticipantInfo')
        assert hasattr(sm, 'mRacePosition')
        assert hasattr(sm, 'mLapsCompleted')
        assert hasattr(sm, 'mCurrentLapDistance')
        assert hasattr(sm, 'mSpeeds')
        assert hasattr(sm, 'mPitModes')
        assert hasattr(sm, 'mRaceStates')
        assert hasattr(sm, 'mHighestFlagColours')
        assert hasattr(sm, 'mHighestFlagReasons')
        assert hasattr(sm, 'mFastestLapTimes')
        assert hasattr(sm, 'mLastLapTimes')

    def test_participant_info_has_name(self, mock_shared_memory):
        sm = mock_shared_memory()
        assert hasattr(sm.mParticipantInfo[0], 'mName')
        assert hasattr(sm.mParticipantInfo[0], 'mIsActive')

    def test_arrays_have_32_entries(self, mock_shared_memory):
        sm = mock_shared_memory()
        assert len(sm.mParticipantInfo) == 32
        assert len(sm.mPitModes) == 32
        assert len(sm.mSpeeds) == 32

    def test_override_works(self, mock_shared_memory):
        sm = mock_shared_memory(mTrackLength=5000.0, mCurrentTime=42.5)
        assert sm.mTrackLength == 5000.0
        assert sm.mCurrentTime == 42.5
