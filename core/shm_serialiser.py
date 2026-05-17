"""
Provides serialization logic for the AMS2 shared memory struct.
Converts ctypes structs to JSON-compatible dictionaries and injects human-readable enum labels.
"""
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
