import socket
import struct
import threading
import tkinter as tk
from tkinter import ttk
import ctypes

class PacketBase(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("mPacketNumber", ctypes.c_uint),
        ("mCategoryPacketNumber", ctypes.c_uint),
        ("mPartialPacketIndex", ctypes.c_ubyte),
        ("mPartialPacketNumber", ctypes.c_ubyte),
        ("mPacketType", ctypes.c_ubyte),
        ("mPacketVersion", ctypes.c_ubyte)
    ]

class sRaceData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("sBase", PacketBase),
        ("sWorldFastestLapTime", ctypes.c_float),
        ("sPersonalFastestLapTime", ctypes.c_float),
        ("sPersonalFastestSector1Time", ctypes.c_float),
        ("sPersonalFastestSector2Time", ctypes.c_float),
        ("sPersonalFastestSector3Time", ctypes.c_float),
        ("sWorldFastestSector1Time", ctypes.c_float),
        ("sWorldFastestSector2Time", ctypes.c_float),
        ("sWorldFastestSector3Time", ctypes.c_float),
        ("sTrackLength", ctypes.c_float),
        ("sTrackLocation", ctypes.c_char * 64),
        ("sTrackVariation", ctypes.c_char * 64),
        ("sTranslatedTrackLocation", ctypes.c_char * 64),
        ("sTranslatedTrackVariation", ctypes.c_char * 64),
        ("sLapsTimeInEvent", ctypes.c_ushort),
        ("sEnforcedPitStopLap", ctypes.c_byte),
        ("padding", ctypes.c_byte) # To make it 308 bytes
    ]

class sParticipantInfo(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("sWorldPosition", ctypes.c_short * 3),
        ("sOrientation", ctypes.c_short * 3),
        ("sCurrentLapDistance", ctypes.c_ushort),
        ("sRacePosition", ctypes.c_ubyte),
        ("sSector", ctypes.c_ubyte),
        ("sHighestFlag", ctypes.c_ubyte),
        ("sPitModeSchedule", ctypes.c_ubyte),
        ("sCarIndex", ctypes.c_ushort),
        ("sRaceState", ctypes.c_ubyte),
        ("sCurrentLap", ctypes.c_ubyte),
        ("sCurrentTime", ctypes.c_float),
        ("sCurrentSectorTime", ctypes.c_float),
        ("sMPParticipantIndex", ctypes.c_ushort)
    ]

class sTimingsData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("sBase", PacketBase),
        ("sNumParticipants", ctypes.c_char),
        ("sParticipantsChangedTimestamp", ctypes.c_uint),
        ("sEventTimeRemaining", ctypes.c_float),
        ("sSplitTimeAhead", ctypes.c_float),
        ("sSplitTimeBehind", ctypes.c_float),
        ("sSplitTime", ctypes.c_float),
        ("sParticipants", sParticipantInfo * 32),
        ("sLocalParticipantIndex", ctypes.c_ushort)
    ]

class sGameStateData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("sBase", PacketBase),
        ("mBuildVersionNumber", ctypes.c_ushort),
        ("mGameState", ctypes.c_char),
        ("sAmbientTemperature", ctypes.c_char),
        ("sTrackTemperature", ctypes.c_char),
        ("sRainDensity", ctypes.c_ubyte),
        ("sSnowDensity", ctypes.c_ubyte),
        ("sWindSpeed", ctypes.c_char),
        ("sWindDirectionY", ctypes.c_char),
        ("padding", ctypes.c_byte * 2) # Padded to 24 bytes
    ]

class sTelemetryData(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("sBase", PacketBase),                          # 0 12
        ("sViewedParticipantIndex", ctypes.c_byte),    # 12 1
        ("sUnfilteredThrottle", ctypes.c_ubyte),       # 13 1
        ("sUnfilteredBrake", ctypes.c_ubyte),          # 14 1
        ("sUnfilteredSteering", ctypes.c_byte),        # 15 1
        ("sUnfilteredClutch", ctypes.c_ubyte),         # 16 1
        ("sCarFlags", ctypes.c_ubyte),                 # 17 1
        ("sOilTempCelsius", ctypes.c_short),           # 18 2
        ("sOilPressureKPa", ctypes.c_ushort),          # 20 2
        ("sWaterTempCelsius", ctypes.c_short),         # 22 2
        ("sWaterPressureKpa", ctypes.c_ushort),        # 24 2
        ("sFuelPressureKpa", ctypes.c_ushort),         # 26 2
        ("sFuelCapacity", ctypes.c_ubyte),             # 28 1
        ("sBrake", ctypes.c_ubyte),                    # 29 1
        ("sThrottle", ctypes.c_ubyte),                 # 30 1
        ("sClutch", ctypes.c_ubyte),                   # 31 1
        ("sFuelLevel", ctypes.c_float),                # 32 4
        ("sSpeed", ctypes.c_float),                    # 36 4
        ("sRpm", ctypes.c_ushort),                     # 40 2
        ("sMaxRpm", ctypes.c_ushort),                  # 42 2
        ("sSteering", ctypes.c_byte),                  # 44 1
        ("sGearNumGears", ctypes.c_ubyte),             # 45 1
        ("sBoostAmount", ctypes.c_ubyte),              # 46 1
        ("sCrashState", ctypes.c_ubyte),               # 47 1
        ("sOdometerKM", ctypes.c_float),               # 48 4
        ("sOrientation", ctypes.c_float * 3),          # 52 12
        ("sLocalVelocity", ctypes.c_float * 3),        # 64 12
        ("sWorldVelocity", ctypes.c_float * 3),        # 76 12
        ("sAngularVelocity", ctypes.c_float * 3),      # 88 12
        ("sLocalAcceleration", ctypes.c_float * 3),    # 100 12
        ("sWorldAcceleration", ctypes.c_float * 3),    # 112 12
        ("sExtentsCentre", ctypes.c_float * 3),        # 124 12
        ("sTyreFlags", ctypes.c_ubyte * 4),            # 136 4
        ("sTerrain", ctypes.c_ubyte * 4),              # 140 4
        ("sTyreY", ctypes.c_float * 4),                # 144 16
        ("sTyreRPS", ctypes.c_float * 4),              # 160 16
        ("sTyreTemp", ctypes.c_ubyte * 4),             # 176 4
        ("sTyreHeightAboveGround", ctypes.c_float * 4),# 180 16
        ("sTyreWear", ctypes.c_ubyte * 4),             # 196 4
        ("sBrakeDamage", ctypes.c_ubyte * 4),          # 200 4
        ("sSuspensionDamage", ctypes.c_ubyte * 4),     # 204 4
        ("sBrakeTempCelsius", ctypes.c_short * 4),     # 208 8
        ("sTyreTreadTemp", ctypes.c_ushort * 4),       # 216 8
        ("sTyreLayerTemp", ctypes.c_ushort * 4),       # 224 8
        ("sTyreCarcassTemp", ctypes.c_ushort * 4),     # 232 8
        ("sTyreRimTemp", ctypes.c_ushort * 4),         # 240 8
        ("sTyreInternalAirTemp", ctypes.c_ushort * 4), # 248 8
        ("sTyreTempLeft", ctypes.c_ushort * 4),        # 256 8
        ("sTyreTempCenter", ctypes.c_ushort * 4),      # 264 8
        ("sTyreTempRight", ctypes.c_ushort * 4),       # 272 8
        ("sWheelLocalPositionY", ctypes.c_float * 4),  # 280 16
        ("sRideHeight", ctypes.c_float * 4),           # 296 16
        ("sSuspensionTravel", ctypes.c_float * 4),     # 312 16
        ("sSuspensionVelocity", ctypes.c_float * 4),   # 328 16
        ("sSuspensionRideHeight", ctypes.c_ushort * 4),# 344 8
        ("sAirPressure", ctypes.c_ushort * 4),         # 352 8
        ("sEngineSpeed", ctypes.c_float),              # 360 4
        ("sEngineTorque", ctypes.c_float),             # 364 4
        ("sWings", ctypes.c_ubyte * 2),                # 368 2
        ("sHandBrake", ctypes.c_ubyte),                # 370 1
        ("sAeroDamage", ctypes.c_ubyte),               # 371 1
        ("sEngineDamage", ctypes.c_ubyte),             # 372 1
        ("sJoyPad0", ctypes.c_uint),                   # 373 4
        ("sDPad", ctypes.c_ubyte),                     # 377 1
        ("sTyreCompound", (ctypes.c_char * 40) * 4),   # 378 160
        ("sTurboBoostPressure", ctypes.c_float),       # 538 4
        ("sFullPosition", ctypes.c_float * 3),         # 542 12
        ("sBrakeBias", ctypes.c_ubyte),                # 554 1
        ("padding", ctypes.c_ubyte)                    # 555 1
    ]

def dump_struct(obj) -> str:
    lines = []
    for field in obj._fields_:
        name = field[0]
        val = getattr(obj, name)
        
        # Handle string arrays
        if hasattr(val, 'value') and isinstance(val.value, bytes):
            lines.append(f"  {name}: {val.value.decode('utf-8', 'ignore')}")
        # Handle simple arrays
        elif hasattr(val, '__len__') and not isinstance(val, (bytes, str)):
            # If array of structs, just print count
            if len(val) > 0 and hasattr(val[0], '_fields_'):
                lines.append(f"  {name}: Array[{len(val)}]")
                # Dump the first active one as an example
                if name == "sParticipants":
                    lines.append(f"    [0] -> {dump_struct_inline(val[0])}")
            # If array of char arrays (like sTyreCompound)
            elif len(val) > 0 and hasattr(val[0], 'value') and isinstance(val[0].value, bytes):
                decoded_list = [v.value.decode('utf-8', 'ignore').strip() for v in val]
                lines.append(f"  {name}: {decoded_list}")
            else:
                lines.append(f"  {name}: {list(val)}")
        elif hasattr(val, '_fields_'):
            lines.append(f"  {name}: {dump_struct_inline(val)}")
        else:
            lines.append(f"  {name}: {val}")
    return "\n".join(lines)

def dump_struct_inline(obj) -> str:
    parts = []
    for field in obj._fields_:
        name = field[0]
        val = getattr(obj, name)
        if hasattr(val, '__len__') and not isinstance(val, (bytes, str)):
            parts.append(f"{name}=[{list(val)}]")
        else:
            parts.append(f"{name}={val}")
    return "{ " + ", ".join(parts) + " }"


class UDPInspector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UDP Packet Inspector")
        self.geometry("800x600")
        
        self.btn_frame = ttk.Frame(self)
        self.btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.btn_308 = ttk.Button(self.btn_frame, text="Capture 308 (Race Data)", command=lambda: self.capture_target(308))
        self.btn_308.pack(side=tk.LEFT, padx=5)
        
        self.btn_1063 = ttk.Button(self.btn_frame, text="Capture 1063 (Timings Data)", command=lambda: self.capture_target(1063))
        self.btn_1063.pack(side=tk.LEFT, padx=5)

        self.btn_24 = ttk.Button(self.btn_frame, text="Capture 24 (Game State)", command=lambda: self.capture_target(24))
        self.btn_24.pack(side=tk.LEFT, padx=5)

        self.btn_556 = ttk.Button(self.btn_frame, text="Capture 556 (Telemetry)", command=lambda: self.capture_target(556))
        self.btn_556.pack(side=tk.LEFT, padx=5)

        self.btn_559 = ttk.Button(self.btn_frame, text="Capture 559 (Telemetry+)", command=lambda: self.capture_target(559))
        self.btn_559.pack(side=tk.LEFT, padx=5)
        
        self.text_area = tk.Text(self, wrap=tk.NONE, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4")
        self.scroll_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text_area.yview)
        self.scroll_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.text_area.xview)
        self.text_area.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)
        
        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.target_size = None
        self.running = True
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allow multiple apps to listen to the same broadcast port
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", 5606))
        
        self.thread = threading.Thread(target=self.listen_loop, daemon=True)
        self.thread.start()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def capture_target(self, size):
        self.target_size = size
        self.text_area.insert(tk.END, f"\n=== Waiting for packet of size {size}... ===\n")
        self.text_area.see(tk.END)
        
    def listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(2048)
                if len(data) == self.target_size:
                    self.target_size = None  # Reset so we only capture one
                    self.after(0, self.decode_packet, data)
            except:
                pass
                
    def decode_packet(self, data):
        size = len(data)
        out = [f"=== CAPTURED PACKET SIZE: {size} ==="]
        try:
            if size == 308:
                obj = sRaceData.from_buffer_copy(data)
                out.append(dump_struct(obj))
                # Bitwise breakdown of sLapsTimeInEvent
                is_timed = bool(obj.sLapsTimeInEvent & 0x8000)
                actual_laps = obj.sLapsTimeInEvent & 0x7FFF
                out.append(f"\n  >> Computed Laps in Event: {actual_laps} (Timed={is_timed})")
                
            elif size == 1063:
                obj = sTimingsData.from_buffer_copy(data)
                out.append(dump_struct(obj))
            elif size == 24:
                obj = sGameStateData.from_buffer_copy(data)
                out.append(dump_struct(obj))
            elif size in (556, 559):
                # Both PCars2 (556) and AMS2 (559) share the same base structure
                obj = sTelemetryData.from_buffer_copy(data[:556])
                out.append(dump_struct(obj))
                
                # Print the AMS2-specific tail if size is 559
                if size == 559:
                    out.append("\n  [AMS2 Extra Bytes (556-558)]")
                    tail = " ".join([f"{b:02x}" for b in data[556:]])
                    out.append(f"  {tail}")
            else:
                out.append("Struct mapping not implemented for this size. Raw hex:")
                hex_dump = " ".join([f"{b:02x}" for b in data])
                out.append(hex_dump)
        except Exception as e:
            out.append(f"Error decoding: {e}")
            
        out.append("====================================\n")
        
        self.text_area.insert(tk.END, "\n".join(out))
        self.text_area.see(tk.END)
        
    def on_close(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass
        self.destroy()

if __name__ == "__main__":
    app = UDPInspector()
    app.mainloop()
