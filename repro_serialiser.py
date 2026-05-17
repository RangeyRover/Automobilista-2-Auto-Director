import ctypes
from shared_memory_struct import SharedMemory

shm = SharedMemory.from_buffer(bytearray(ctypes.sizeof(SharedMemory)))
val = shm.mCarNames[0]
print(f"type(val): {type(val)}, is bytes? {isinstance(val, bytes)}")
print(f"val.value: {type(val.value)}")
