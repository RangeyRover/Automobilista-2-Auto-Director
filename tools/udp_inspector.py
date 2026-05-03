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
        ("sWindDirectionX", ctypes.c_char),
        ("sWindDirectionY", ctypes.c_char),
        ("padding", ctypes.c_byte * 2) # Padded to 24 bytes
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
