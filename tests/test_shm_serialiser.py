"""Tests for the Shared Memory Serialiser (core/shm_serialiser.py)."""
import pytest
import ctypes
import copy
from shared_memory_struct import SharedMemory
from core.shm_serialiser import serialise_shm, annotate_enums

@pytest.fixture
def zero_shm():
    """Returns a zero-initialised SharedMemory instance using ctypes.from_buffer."""
    return SharedMemory.from_buffer(bytearray(ctypes.sizeof(SharedMemory)))

def test_serialise_returns_all_fields(zero_shm):
    result = serialise_shm(zero_shm)
    expected_keys = [f[0] for f in SharedMemory._fields_ if not f[0].startswith('_')]
    for key in expected_keys:
        assert key in result

def test_serialise_scalar_int(zero_shm):
    zero_shm.mVersion = 14
    result = serialise_shm(zero_shm)
    assert result["mVersion"] == 14
    assert isinstance(result["mVersion"], int)

def test_serialise_scalar_float(zero_shm):
    zero_shm.mTrackLength = 5803.09
    result = serialise_shm(zero_shm)
    assert isinstance(result["mTrackLength"], float)
    assert abs(result["mTrackLength"] - 5803.09) < 0.01

def test_serialise_scalar_bool(zero_shm):
    zero_shm.mAntiLockActive = True
    result = serialise_shm(zero_shm)
    assert result["mAntiLockActive"] is True

def test_serialise_string_car_name(zero_shm):
    zero_shm.mCarName = b"Formula Ultimate\x00"
    result = serialise_shm(zero_shm)
    assert result["mCarName"] == "Formula Ultimate"
    assert isinstance(result["mCarName"], str)

def test_serialise_string_track_location(zero_shm):
    zero_shm.mTrackLocation = b"Kansai\x00"
    result = serialise_shm(zero_shm)
    assert result["mTrackLocation"] == "Kansai"
    assert isinstance(result["mTrackLocation"], str)

def test_serialise_participant_array_length_64(zero_shm):
    result = serialise_shm(zero_shm)
    assert len(result["mParticipantInfo"]) == 64

def test_serialise_participant_struct_keys(zero_shm):
    result = serialise_shm(zero_shm)
    entry = result["mParticipantInfo"][0]
    expected_keys = ["mIsActive", "mName", "mWorldPosition", "mCurrentLapDistance", 
                     "mRacePosition", "mLapsCompleted", "mCurrentLap", "mCurrentSector"]
    for key in expected_keys:
        assert key in entry

def test_serialise_participant_name_decoded(zero_shm):
    zero_shm.mParticipantInfo[0].mName = b"TestDriver\x00"
    result = serialise_shm(zero_shm)
    assert result["mParticipantInfo"][0]["mName"] == "TestDriver"

def test_serialise_participant_world_position_vec3(zero_shm):
    result = serialise_shm(zero_shm)
    pos = result["mParticipantInfo"][0]["mWorldPosition"]
    assert isinstance(pos, list)
    assert len(pos) == 3
    assert all(isinstance(x, float) for x in pos)

def test_serialise_tyre_array_length_4(zero_shm):
    result = serialise_shm(zero_shm)
    assert len(result["mTyreFlags"]) == 4
    assert len(result["mTyreTemp"]) == 4

def test_serialise_participant_flat_array_length_64(zero_shm):
    result = serialise_shm(zero_shm)
    assert len(result["mCurrentSector1Times"]) == 64
    assert len(result["mSpeeds"]) == 64
    assert len(result["mFastestLapTimes"]) == 64

def test_serialise_orientations_reshaped(zero_shm):
    result = serialise_shm(zero_shm)
    assert isinstance(result["mOrientations"], list)
    assert len(result["mOrientations"]) == 64
    assert isinstance(result["mOrientations"][0], list)
    assert len(result["mOrientations"][0]) == 3

def test_serialise_car_names_list_of_strings(zero_shm):
    zero_shm.mCarNames[0].value = b"Car1"
    result = serialise_shm(zero_shm)
    assert isinstance(result["mCarNames"], list)
    assert len(result["mCarNames"]) == 64
    assert result["mCarNames"][0] == "Car1"
    assert isinstance(result["mCarNames"][1], str)

def test_serialise_car_class_names_list_of_strings(zero_shm):
    zero_shm.mCarClassNames[0].value = b"Class1"
    result = serialise_shm(zero_shm)
    assert isinstance(result["mCarClassNames"], list)
    assert len(result["mCarClassNames"]) == 64
    assert result["mCarClassNames"][0] == "Class1"

def test_serialise_tyre_compound_list_of_4_strings(zero_shm):
    zero_shm.mTyreCompound[0].value = b"Soft"
    result = serialise_shm(zero_shm)
    assert isinstance(result["mTyreCompound"], list)
    assert len(result["mTyreCompound"]) == 4
    assert result["mTyreCompound"][0] == "Soft"

def test_serialise_wings_length_2(zero_shm):
    result = serialise_shm(zero_shm)
    assert len(result["mWings"]) == 2

def test_serialise_vec3_arrays(zero_shm):
    result = serialise_shm(zero_shm)
    vec3_keys = ["mOrientation", "mLocalVelocity", "mWorldVelocity", "mAngularVelocity", 
                 "mLocalAcceleration", "mWorldAcceleration", "mExtentsCentre"]
    for key in vec3_keys:
        val = result[key]
        assert isinstance(val, list)
        assert len(val) == 3

def test_serialise_skips_padding_fields(zero_shm):
    result = serialise_shm(zero_shm)
    for key in result.keys():
        assert not key.startswith('_')

# --- Phase 4: Enum Annotation Tests ---

def test_annotate_game_state_known():
    result = annotate_enums({"mGameState": 2})
    assert result["mGameState_label"] == "GAME_INGAME_PLAYING"

def test_annotate_session_state():
    result = annotate_enums({"mSessionState": 5})
    assert result["mSessionState_label"] == "SESSION_RACE"

def test_annotate_race_state():
    result = annotate_enums({"mRaceState": 3})
    assert result["mRaceState_label"] == "RACESTATE_FINISHED"

def test_annotate_pit_mode():
    result = annotate_enums({"mPitMode": 2})
    assert result["mPitMode_label"] == "PIT_MODE_IN_PIT"

def test_annotate_flag_colour():
    result = annotate_enums({"mHighestFlagColour": 11})
    assert result["mHighestFlagColour_label"] == "FLAG_COLOUR_CHEQUERED"

def test_annotate_unknown_enum_value():
    result = annotate_enums({"mGameState": 99})
    assert result["mGameState_label"] == "UNKNOWN(99)"

def test_annotate_per_participant_race_states():
    result = annotate_enums({"mRaceStates": [2, 3, 0]})
    assert result["mRaceStates_labels"] == ["RACESTATE_RACING", "RACESTATE_FINISHED", "RACESTATE_INVALID"]

def test_annotate_per_participant_pit_modes():
    result = annotate_enums({"mPitModes": [0, 1, 4]})
    assert result["mPitModes_labels"] == ["PIT_MODE_NONE", "PIT_MODE_DRIVING_INTO_PITS", "PIT_MODE_IN_GARAGE"]

def test_annotate_per_participant_pit_schedules():
    result = annotate_enums({"mPitSchedules": [0, 4]})
    assert result["mPitSchedules_labels"] == ["PIT_SCHEDULE_NONE", "PIT_SCHEDULE_MANDATORY"]

def test_annotate_per_participant_flag_colours():
    result = annotate_enums({"mHighestFlagColours": [0, 6]})
    assert result["mHighestFlagColours_labels"] == ["FLAG_COLOUR_NONE", "FLAG_COLOUR_YELLOW"]

def test_annotate_per_participant_flag_reasons():
    result = annotate_enums({"mHighestFlagReasons": [0, 2]})
    assert result["mHighestFlagReasons_labels"] == ["FLAG_REASON_NONE", "FLAG_REASON_VEHICLE_CRASH"]

def test_annotate_does_not_mutate_input():
    input_data = {"mGameState": 2, "mRaceStates": [2]}
    input_copy = copy.deepcopy(input_data)
    annotate_enums(input_data)
    assert input_data == input_copy

def test_annotate_preserves_non_enum_fields():
    result = annotate_enums({"mVersion": 14, "mSpeed": 80.0, "mGameState": 2})
    assert result["mVersion"] == 14
    assert result["mSpeed"] == 80.0
