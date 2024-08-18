import ctypes

# Constants
STRING_LENGTH_MAX = 64
STORED_PARTICIPANTS_MAX = 64
TYRE_MAX = 4
VEC_MAX = 3
TYRE_COMPOUND_NAME_LENGTH_MAX = 40

# Enumerations and structures
class GameState(ctypes.c_uint):
    GAME_EXITED = 0
    GAME_FRONT_END = 1
    GAME_INGAME_PLAYING = 2
    GAME_INGAME_PAUSED = 3
    GAME_INGAME_INMENU_TIME_TICKING = 4
    GAME_INGAME_RESTARTING = 5
    GAME_INGAME_REPLAY = 6
    GAME_FRONT_END_REPLAY = 7

class SessionState(ctypes.c_uint):
    SESSION_INVALID = 0
    SESSION_PRACTICE = 1
    SESSION_TEST = 2
    SESSION_QUALIFY = 3
    SESSION_FORMATION_LAP = 4
    SESSION_RACE = 5
    SESSION_TIME_ATTACK = 6

class RaceState(ctypes.c_uint):
    RACESTATE_INVALID = 0
    RACESTATE_NOT_STARTED = 1
    RACESTATE_RACING = 2
    RACESTATE_FINISHED = 3
    RACESTATE_DISQUALIFIED = 4
    RACESTATE_RETIRED = 5
    RACESTATE_DNF = 6

class FlagColour(ctypes.c_uint):
    FLAG_COLOUR_NONE = 0
    FLAG_COLOUR_GREEN = 1
    FLAG_COLOUR_BLUE = 2
    FLAG_COLOUR_WHITE_SLOW_CAR = 3
    FLAG_COLOUR_WHITE_FINAL_LAP = 4
    FLAG_COLOUR_RED = 5
    FLAG_COLOUR_YELLOW = 6
    FLAG_COLOUR_DOUBLE_YELLOW = 7
    FLAG_COLOUR_BLACK_AND_WHITE = 8
    FLAG_COLOUR_BLACK_ORANGE_CIRCLE = 9
    FLAG_COLOUR_BLACK = 10
    FLAG_COLOUR_CHEQUERED = 11

class FlagReason(ctypes.c_uint):
    FLAG_REASON_NONE = 0
    FLAG_REASON_SOLO_CRASH = 1
    FLAG_REASON_VEHICLE_CRASH = 2
    FLAG_REASON_VEHICLE_OBSTRUCTION = 3

class PitMode(ctypes.c_uint):
    PIT_MODE_NONE = 0
    PIT_MODE_DRIVING_INTO_PITS = 1
    PIT_MODE_IN_PIT = 2
    PIT_MODE_DRIVING_OUT_OF_PITS = 3
    PIT_MODE_IN_GARAGE = 4
    PIT_MODE_DRIVING_OUT_OF_GARAGE = 5

class PitSchedule(ctypes.c_uint):
    PIT_SCHEDULE_NONE = 0
    PIT_SCHEDULE_PLAYER_REQUESTED = 1
    PIT_SCHEDULE_ENGINEER_REQUESTED = 2
    PIT_SCHEDULE_DAMAGE_REQUESTED = 3
    PIT_SCHEDULE_MANDATORY = 4
    PIT_SCHEDULE_DRIVE_THROUGH = 5
    PIT_SCHEDULE_STOP_GO = 6
    PIT_SCHEDULE_PITSPOT_OCCUPIED = 7

class CarFlags(ctypes.c_uint):
    CAR_HEADLIGHT = 1 << 0
    CAR_ENGINE_ACTIVE = 1 << 1
    CAR_ENGINE_WARNING = 1 << 2
    CAR_SPEED_LIMITER = 1 << 3
    CAR_ABS = 1 << 4
    CAR_HANDBRAKE = 1 << 5
    CAR_TCS = 1 << 6
    CAR_SCS = 1 << 7

class TyreFlags(ctypes.c_uint):
    TYRE_ATTACHED = 1 << 0
    TYRE_INFLATED = 1 << 1
    TYRE_IS_ON_GROUND = 1 << 2

class TerrainMaterials(ctypes.c_uint):
    TERRAIN_ROAD = 0
    TERRAIN_LOW_GRIP_ROAD = 1
    TERRAIN_BUMPY_ROAD1 = 2
    TERRAIN_BUMPY_ROAD2 = 3
    TERRAIN_BUMPY_ROAD3 = 4
    TERRAIN_MARBLES = 5
    TERRAIN_GRASSY_BERMS = 6
    TERRAIN_GRASS = 7
    TERRAIN_GRAVEL = 8
    TERRAIN_BUMPY_GRAVEL = 9
    TERRAIN_RUMBLE_STRIPS = 10
    TERRAIN_DRAINS = 11
    TERRAIN_TYREWALLS = 12
    TERRAIN_CEMENTWALLS = 13
    TERRAIN_GUARDRAILS = 14
    TERRAIN_SAND = 15
    TERRAIN_BUMPY_SAND = 16
    TERRAIN_DIRT = 17
    TERRAIN_BUMPY_DIRT = 18
    TERRAIN_DIRT_ROAD = 19
    TERRAIN_BUMPY_DIRT_ROAD = 20
    TERRAIN_PAVEMENT = 21
    TERRAIN_DIRT_BANK = 22
    TERRAIN_WOOD = 23
    TERRAIN_DRY_VERGE = 24
    TERRAIN_EXIT_RUMBLE_STRIPS = 25
    TERRAIN_GRASSCRETE = 26
    TERRAIN_LONG_GRASS = 27
    TERRAIN_SLOPE_GRASS = 28
    TERRAIN_COBBLES = 29
    TERRAIN_SAND_ROAD = 30
    TERRAIN_BAKED_CLAY = 31
    TERRAIN_ASTROTURF = 32
    TERRAIN_SNOWHALF = 33
    TERRAIN_SNOWFULL = 34
    TERRAIN_DAMAGED_ROAD1 = 35
    TERRAIN_TRAIN_TRACK_ROAD = 36
    TERRAIN_BUMPYCOBBLES = 37
    TERRAIN_ARIES_ONLY = 38
    TERRAIN_ORION_ONLY = 39
    TERRAIN_B1RUMBLES = 40
    TERRAIN_B2RUMBLES = 41
    TERRAIN_ROUGH_SAND_MEDIUM = 42
    TERRAIN_ROUGH_SAND_HEAVY = 43
    TERRAIN_SNOWWALLS = 44
    TERRAIN_ICE_ROAD = 45
    TERRAIN_RUNOFF_ROAD = 46
    TERRAIN_ILLEGAL_STRIP = 47
    TERRAIN_PAINT_CONCRETE = 48
    TERRAIN_PAINT_CONCRETE_ILLEGAL = 49
    TERRAIN_RALLY_TARMAC = 50

class CrashState(ctypes.c_uint):
    CRASH_DAMAGE_NONE = 0
    CRASH_DAMAGE_OFFTRACK = 1
    CRASH_DAMAGE_LARGE_PROP = 2
    CRASH_DAMAGE_SPINNING = 3
    CRASH_DAMAGE_ROLLING = 4

class DrsState(ctypes.c_uint):
    DRS_INSTALLED = 1 << 0
    DRS_ZONE_RULES = 1 << 1
    DRS_AVAILABLE_NEXT = 1 << 2
    DRS_AVAILABLE_NOW = 1 << 3
    DRS_ACTIVE = 1 << 4

class ErsDeploymentMode(ctypes.c_uint):
    ERS_DEPLOYMENT_MODE_NONE = 0
    ERS_DEPLOYMENT_MODE_OFF = 1
    ERS_DEPLOYMENT_MODE_BUILD = 2
    ERS_DEPLOYMENT_MODE_BALANCED = 3
    ERS_DEPLOYMENT_MODE_ATTACK = 4
    ERS_DEPLOYMENT_MODE_QUAL = 5

class YellowFlagState(ctypes.c_int):
    YFS_INVALID = -1
    YFS_NONE = 0
    YFS_PENDING = 1
    YFS_PITS_CLOSED = 2
    YFS_PIT_LEAD_LAP = 3
    YFS_PITS_OPEN = 4
    YFS_PITS_OPEN2 = 5
    YFS_LAST_LAP = 6
    YFS_RESUME = 7
    YFS_RACE_HALT = 8

class LaunchStage(ctypes.c_int):
    LAUNCH_INVALID = -1
    LAUNCH_OFF = 0
    LAUNCH_REV = 1
    LAUNCH_ON = 2

# ParticipantInfo struct
class ParticipantInfo(ctypes.Structure):
    _fields_ = [
        ('mIsActive', ctypes.c_bool),
        ('mName', ctypes.c_char * STRING_LENGTH_MAX),
        ('mWorldPosition', ctypes.c_float * VEC_MAX),
        ('mCurrentLapDistance', ctypes.c_float),
        ('mRacePosition', ctypes.c_uint),
        ('mLapsCompleted', ctypes.c_uint),
        ('mCurrentLap', ctypes.c_uint),
        ('mCurrentSector', ctypes.c_int)
    ]

# SharedMemory struct
class SharedMemory(ctypes.Structure):
    _fields_ = [
        ('mVersion', ctypes.c_uint),
        ('mBuildVersionNumber', ctypes.c_uint),
        ('mGameState', ctypes.c_uint),
        ('mSessionState', ctypes.c_uint),
        ('mRaceState', ctypes.c_uint),
        ('mViewedParticipantIndex', ctypes.c_int),
        ('mNumParticipants', ctypes.c_int),
        ('mParticipantInfo', ParticipantInfo * STORED_PARTICIPANTS_MAX),
        ('mUnfilteredThrottle', ctypes.c_float),
        ('mUnfilteredBrake', ctypes.c_float),
        ('mUnfilteredSteering', ctypes.c_float),
        ('mUnfilteredClutch', ctypes.c_float),
        ('mCarName', ctypes.c_char * STRING_LENGTH_MAX),
        ('mCarClassName', ctypes.c_char * STRING_LENGTH_MAX),
        ('mLapsInEvent', ctypes.c_uint),
        ('mTrackLocation', ctypes.c_char * STRING_LENGTH_MAX),
        ('mTrackVariation', ctypes.c_char * STRING_LENGTH_MAX),
        ('mTrackLength', ctypes.c_float),
        ('mNumSectors', ctypes.c_int),
        ('mLapInvalidated', ctypes.c_bool),
        ('mBestLapTime', ctypes.c_float),
        ('mLastLapTime', ctypes.c_float),
        ('mCurrentTime', ctypes.c_float),
        ('mSplitTimeAhead', ctypes.c_float),
        ('mSplitTimeBehind', ctypes.c_float),
        ('mSplitTime', ctypes.c_float),
        ('mEventTimeRemaining', ctypes.c_float),
        ('mPersonalFastestLapTime', ctypes.c_float),
        ('mWorldFastestLapTime', ctypes.c_float),
        ('mCurrentSector1Time', ctypes.c_float),
        ('mCurrentSector2Time', ctypes.c_float),
        ('mCurrentSector3Time', ctypes.c_float),
        ('mFastestSector1Time', ctypes.c_float),
        ('mFastestSector2Time', ctypes.c_float),
        ('mFastestSector3Time', ctypes.c_float),
        ('mPersonalFastestSector1Time', ctypes.c_float),
        ('mPersonalFastestSector2Time', ctypes.c_float),
        ('mPersonalFastestSector3Time', ctypes.c_float),
        ('mWorldFastestSector1Time', ctypes.c_float),
        ('mWorldFastestSector2Time', ctypes.c_float),
        ('mWorldFastestSector3Time', ctypes.c_float),
        ('mHighestFlagColour', ctypes.c_uint),
        ('mHighestFlagReason', ctypes.c_uint),
        ('mPitMode', ctypes.c_uint),
        ('mPitSchedule', ctypes.c_uint),
        ('mCarFlags', ctypes.c_uint),
        ('mOilTempCelsius', ctypes.c_float),
        ('mOilPressureKPa', ctypes.c_float),
        ('mWaterTempCelsius', ctypes.c_float),
        ('mWaterPressureKPa', ctypes.c_float),
        ('mFuelPressureKPa', ctypes.c_float),
        ('mFuelLevel', ctypes.c_float),
        ('mFuelCapacity', ctypes.c_float),
        ('mSpeed', ctypes.c_float),
        ('mRpm', ctypes.c_float),
        ('mMaxRPM', ctypes.c_float),
        ('mBrake', ctypes.c_float),
        ('mThrottle', ctypes.c_float),
        ('mClutch', ctypes.c_float),
        ('mSteering', ctypes.c_float),
        ('mGear', ctypes.c_int),
        ('mNumGears', ctypes.c_int),
        ('mOdometerKM', ctypes.c_float),
        ('mAntiLockActive', ctypes.c_bool),
        ('mLastOpponentCollisionIndex', ctypes.c_int),
        ('mLastOpponentCollisionMagnitude', ctypes.c_float),
        ('mBoostActive', ctypes.c_bool),
        ('mBoostAmount', ctypes.c_float),
        ('mOrientation', ctypes.c_float * VEC_MAX),
        ('mLocalVelocity', ctypes.c_float * VEC_MAX),
        ('mWorldVelocity', ctypes.c_float * VEC_MAX),
        ('mAngularVelocity', ctypes.c_float * VEC_MAX),
        ('mLocalAcceleration', ctypes.c_float * VEC_MAX),
        ('mWorldAcceleration', ctypes.c_float * VEC_MAX),
        ('mExtentsCentre', ctypes.c_float * VEC_MAX),
        ('mTyreFlags', ctypes.c_uint * TYRE_MAX),
        ('mTerrain', ctypes.c_uint * TYRE_MAX),
        ('mTyreY', ctypes.c_float * TYRE_MAX),
        ('mTyreRPS', ctypes.c_float * TYRE_MAX),
        ('mTyreSlipSpeed', ctypes.c_float * TYRE_MAX),
        ('mTyreTemp', ctypes.c_float * TYRE_MAX),
        ('mTyreHeightAboveGround', ctypes.c_float * TYRE_MAX),
        ('mTyreWear', ctypes.c_float * TYRE_MAX),
        ('mBrakeDamage', ctypes.c_float * TYRE_MAX),
        ('mSuspensionDamage', ctypes.c_float * TYRE_MAX),
        ('mBrakeTempCelsius', ctypes.c_float * TYRE_MAX),
        ('mTyreTreadTemp', ctypes.c_float * TYRE_MAX),
        ('mTyreLayerTemp', ctypes.c_float * TYRE_MAX),
        ('mTyreCarcassTemp', ctypes.c_float * TYRE_MAX),
        ('mTyreRimTemp', ctypes.c_float * TYRE_MAX),
        ('mTyreInternalAirTemp', ctypes.c_float * TYRE_MAX),
        ('mCrashState', ctypes.c_uint),
        ('mAeroDamage', ctypes.c_float),
        ('mEngineDamage', ctypes.c_float),
        ('mAmbientTemperature', ctypes.c_float),
        ('mTrackTemperature', ctypes.c_float),
        ('mRainDensity', ctypes.c_float),
        ('mWindSpeed', ctypes.c_float),
        ('mWindDirectionX', ctypes.c_float),
        ('mWindDirectionY', ctypes.c_float),
        ('mCloudBrightness', ctypes.c_float),
        ('mSequenceNumber', ctypes.c_uint),
        ('mWheelLocalPositionY', ctypes.c_float * TYRE_MAX),
        ('mSuspensionTravel', ctypes.c_float * TYRE_MAX),
        ('mSuspensionVelocity', ctypes.c_float * TYRE_MAX),
        ('mAirPressure', ctypes.c_float * TYRE_MAX),
        ('mEngineSpeed', ctypes.c_float),
        ('mEngineTorque', ctypes.c_float),
        ('mWings', ctypes.c_float * 2),
        ('mHandBrake', ctypes.c_float),
        ('mCurrentSector1Times', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mCurrentSector2Times', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mCurrentSector3Times', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mFastestSector1Times', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mFastestSector2Times', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mFastestSector3Times', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mFastestLapTimes', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mLastLapTimes', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mLapsInvalidated', ctypes.c_bool * STORED_PARTICIPANTS_MAX),
        ('mRaceStates', ctypes.c_uint * STORED_PARTICIPANTS_MAX),
        ('mPitModes', ctypes.c_uint * STORED_PARTICIPANTS_MAX),
        ('mOrientations', ctypes.c_float * STORED_PARTICIPANTS_MAX * VEC_MAX),
        ('mSpeeds', ctypes.c_float * STORED_PARTICIPANTS_MAX),
        ('mCarNames', ctypes.c_char * STORED_PARTICIPANTS_MAX * STRING_LENGTH_MAX),
        ('mCarClassNames', ctypes.c_char * STORED_PARTICIPANTS_MAX * STRING_LENGTH_MAX),
        ('mEnforcedPitStopLap', ctypes.c_int),
        ('mTranslatedTrackLocation', ctypes.c_char * STRING_LENGTH_MAX),
        ('mTranslatedTrackVariation', ctypes.c_char * STRING_LENGTH_MAX),
        ('mBrakeBias', ctypes.c_float),
        ('mTurboBoostPressure', ctypes.c_float),
        ('mTyreCompound', ctypes.c_char * TYRE_MAX * TYRE_COMPOUND_NAME_LENGTH_MAX),
        ('mPitSchedules', ctypes.c_uint * STORED_PARTICIPANTS_MAX),
        ('mHighestFlagColours', ctypes.c_uint * STORED_PARTICIPANTS_MAX),
        ('mHighestFlagReasons', ctypes.c_uint * STORED_PARTICIPANTS_MAX),
        ('mNationalities', ctypes.c_uint * STORED_PARTICIPANTS_MAX),
        ('mSnowDensity', ctypes.c_float),
        ('mSessionDuration', ctypes.c_float),
        ('mSessionAdditionalLaps', ctypes.c_int),
        ('mTyreTempLeft', ctypes.c_float * TYRE_MAX),
        ('mTyreTempCenter', ctypes.c_float * TYRE_MAX),
        ('mTyreTempRight', ctypes.c_float * TYRE_MAX),
        ('mDrsState', ctypes.c_uint),
        ('mRideHeight', ctypes.c_float * TYRE_MAX),
        ('mJoyPad0', ctypes.c_uint),
        ('mDPad', ctypes.c_uint),
        ('mAntiLockSetting', ctypes.c_int),
        ('mTractionControlSetting', ctypes.c_int),
        ('mErsDeploymentMode', ctypes.c_uint),
        ('mErsAutoModeEnabled', ctypes.c_bool),
        ('mClutchTemp', ctypes.c_float),
        ('mClutchWear', ctypes.c_float),
        ('mClutchOverheated', ctypes.c_bool),
        ('mClutchSlipping', ctypes.c_bool),
        ('mYellowFlagState', ctypes.c_int),
        ('mSessionIsPrivate', ctypes.c_bool),
        ('mLaunchStage', ctypes.c_int)
    ]

# Add any additional constants or enums if needed here
SHARED_MEMORY_VERSION = 14
