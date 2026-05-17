import mmap
import ctypes
from shared_memory_struct import SharedMemory
import time

shm = SharedMemory()
shm.mVersion = 14
shm.mGameState = 2
shm.mNumParticipants = 3
shm.mTrackLength = 5000.0

shm.mParticipantInfo[0].mIsActive = True
shm.mParticipantInfo[0].mName = b"Lewis Hamilton\x00"
shm.mParticipantInfo[0].mRacePosition = 1
shm.mParticipantInfo[0].mCurrentLapDistance = 2500.0
shm.mParticipantInfo[0].mLapsCompleted = 5
shm.mCarNames[0].value = b"Mercedes W14"

shm.mParticipantInfo[1].mIsActive = True
shm.mParticipantInfo[1].mName = b"Max Verstappen\x00"
shm.mParticipantInfo[1].mRacePosition = 2
shm.mParticipantInfo[1].mCurrentLapDistance = 2450.0
shm.mParticipantInfo[1].mLapsCompleted = 5
shm.mCarNames[1].value = b"Red Bull RB19"

shm.mParticipantInfo[2].mIsActive = True
shm.mParticipantInfo[2].mName = b"Fernando Alonso\x00"
shm.mParticipantInfo[2].mRacePosition = 3
shm.mParticipantInfo[2].mCurrentLapDistance = 2000.0
shm.mParticipantInfo[2].mLapsCompleted = 5
shm.mCarNames[2].value = b"Aston Martin AMR23"

shm_file = mmap.mmap(-1, ctypes.sizeof(SharedMemory), "$pcars2$")
shm_file.write(bytes(shm))
shm_file.seek(0)

print("Dummy AMS2 Shared Memory created.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
