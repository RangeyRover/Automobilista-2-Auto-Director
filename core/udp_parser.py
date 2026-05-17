"""UDP parser mixin for TelemetryProvider."""
import socket
import threading
import struct
import time

UDP_NATIONALITY_HASHES = {
    933178424:  'BR', # Brazil
    1004104139: 'UY', # Uruguay
    2138617929: 'US', # USA
    1048434266: 'AR', # Argentina
    1808026356: 'ID', # Indonesia
    3222416996: 'GR', # Greece
    1789533886: 'NL', # Netherlands
    4279958873: 'CO', # Colombia
    3170477316: 'PT', # Portugal
    354033749:  'MX', # Mexico
    2858231841: 'CL', # Chile
    1972970704: 'GB', # UK
    4017120722: 'CA', # Canada
    3603110075: 'AU', # Australia
    2157389219: 'NZ'  # New Zealand
}

class UDPParserMixin:
    def start_udp(self):
        """Start the background UDP listener thread."""
        if self._udp_running:
            return
        self._udp_running = True
        self._udp_thread = threading.Thread(target=self._listen_udp_loop, daemon=True)
        self._udp_thread.start()

    def stop_udp(self):
        """Stop the background UDP listener thread."""
        self._udp_running = False
        if self._udp_socket:
            try:
                self._udp_socket.close()
            except Exception:
                pass
        if self._udp_thread and self._udp_thread.is_alive():
            # In python 3.13, closing the socket should unblock recvfrom
            self._udp_thread.join(timeout=0.2)

    def set_udp_port(self, port: int):
        """Change the UDP port and restart listener if running."""
        self._udp_port = port
        if self._udp_running:
            self.stop_udp()
            time.sleep(0.1) # Allow thread to gracefully exit
            self.start_udp()

    def _listen_udp_loop(self):
        """Internal daemon loop for listening to UDP packets."""
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Allow port reuse
        self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._udp_socket.bind(("", self._udp_port))
        except Exception as e:
            print(f"Error binding UDP port {self._udp_port}: {e}")
            self._udp_running = False
            return

        while self._udp_running:
            try:
                data, addr = self._udp_socket.recvfrom(2048)
                packet_size = len(data)
                
                self._add_packet_to_buffer(data)
                
                # Proactively parse string packets to populate name cache
                if packet_size in (1136, 1367):
                    self._parse_udp_names(data)
                elif packet_size == 1063:
                    try:
                        local_index = struct.unpack_from('<H', data, 1055)[0]
                        split_ahead = struct.unpack_from('<f', data, 21)[0]
                        if split_ahead >= 0.0:
                            self._udp_time_splits[local_index] = split_ahead
                    except struct.error:
                        pass
            except Exception as e:
                if not self._udp_running:
                    break  # Socket closed gracefully
                print(f"[UDP DEBUG] Receive Error: {e}")
                continue

    def _add_packet_to_buffer(self, packet: bytes):
        """Add a UDP packet to the buffer, keyed by packet size."""
        self._packet_buffer[len(packet)] = packet

    def _parse_udp_names(self, packet: bytes):
        """Parse Strings packet to cache driver names, car names, and car classes.

        Handles two packet sizes:
        - 1367 bytes: 16-byte header + 16×64 names + 16×(remaining for car names)
        - 1136 bytes: 12-byte header + 4-byte timestamp + 16×64 names + nationality(64) + sIndex(32)
        """
        pkt_len = len(packet)
        if pkt_len == 1136:
            print(f"[UDP NAT DEBUG] Parsing 1136-byte Strings Packet...")

        if pkt_len >= 1367:
            # 1367-byte layout: header(12) + timestamp(4) + 16×64 names(1024) + 16×64 car names(starts at 1040)
            name_block_start = 16
            name_stride = 64
            car_name_block_start = 1040
            car_name_stride = 64
            car_class_block_start = 2064  # Beyond 1367 — not available in this packet size
            car_class_stride = 64
            nationality_block_start = -1
            nationality_stride = -1
        elif pkt_len >= 1136:
            # 1136-byte layout: header(12) + timestamp(4) + 16×64 names(1024) + nationality(64) + sIndex(32)
            name_block_start = 16
            name_stride = 64
            car_name_block_start = -1
            car_name_stride = -1
            car_class_block_start = -1
            car_class_stride = -1
            nationality_block_start = 1040
            nationality_stride = 4
        else:
            return  # Unknown packet size

        # The PacketBase header is the first 12 bytes. Offset 8 is mPartialPacketIndex (1-based).
        partial_idx = packet[8]
        base_idx = (partial_idx - 1) * 16 if partial_idx > 0 else 0

        # Parse participant names
        for i in range(16):
            offset = name_block_start + (i * name_stride)
            if offset + name_stride <= pkt_len:
                raw_name = packet[offset:offset + name_stride]
                name = raw_name.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                if name:
                    abs_idx = base_idx + i
                    self._udp_participant_names[abs_idx] = name

        # Parse nationalities
        if nationality_block_start != -1:
            for i in range(16):
                offset = nationality_block_start + (i * nationality_stride)
                if offset + nationality_stride <= pkt_len:
                    try:
                        nat_hash = struct.unpack_from('<I', packet, offset)[0]
                        abs_idx = base_idx + i
                        found_nat = UDP_NATIONALITY_HASHES.get(nat_hash, "")
                        self._udp_participant_nationalities[abs_idx] = found_nat
                        
                        if self._udp_participant_names.get(abs_idx):
                            print(f"[UDP NAT DEBUG] Player Index {abs_idx} ({self._udp_participant_names[abs_idx]}) | Raw Hash from AMS2: {nat_hash} | Resolved To: '{found_nat}'")
                            
                    except struct.error:
                        pass

        # Parse car names
        if car_name_block_start != -1:
            for i in range(16):
                offset = car_name_block_start + (i * car_name_stride)
                if offset + car_name_stride <= pkt_len:
                    raw = packet[offset:offset + car_name_stride]
                    car_name = raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                    if car_name:
                        self._udp_car_names[i] = car_name

        # Parse car classes (if within packet bounds)
        if car_class_block_start != -1:
            for i in range(16):
                offset = car_class_block_start + (i * car_class_stride)
                if offset + car_class_stride <= pkt_len:
                    raw = packet[offset:offset + car_class_stride]
                    car_class = raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                    if car_class:
                        self._udp_car_classes[i] = car_class

    def _extract_udp_track_info(self, packet: bytes | None) -> dict:
        """Extract track info from 308-byte UDP packet."""
        info = {'track_name': '', 'track_length': 0.0, 'num_participants': 0}
        if not packet or len(packet) != 308:
            return info
        try:
            info['track_length'] = struct.unpack_from('f', packet, 44)[0]
        except struct.error:
            pass
        return info

    def _extract_udp_session_info(self) -> dict:
        """Extract session info from UDP packet buffer (Fallback)."""
        info = {
            'event_time_remaining': 0.0,
            'current_time': 0.0,
            'laps_in_event': 0,
            'game_state': 0,
            'session_state': 0,
            'yellow_flag_state': 0
        }
        # In PCars2 UDP, EventTimeRemaining and LapsInEvent are found in GameState or RaceData packet.
        # Note: PCars2 RaceData (308 bytes) does not contain EventTimeRemaining directly.
        # If the specific GameState packet (24 bytes) or TimingsData (1063 bytes) contains it, we parse it.
        # For the sake of the TDD fallback, we assume it's stored in a specific format or we just mock the return if we can't find it.
        # We will parse 1063 byte packet offset 14 (float, event time remaining) - this is an approximation for PCars2 protocol.
        packet = self._packet_buffer.get(1063)
        if packet and len(packet) >= 1063:
            try:
                # Based on SMS_UDP_Definitions_AMS2_RR.hpp:
                # sTimingsData (1063 bytes):
                #   PacketBase sBase; (0..11)
                #   signed char sNumParticipants; (12)
                #   unsigned int sParticipantsChangedTimestamp; (13..16)
                #   float sEventTimeRemaining; (17..20)
                val = struct.unpack_from('<f', packet, 17)[0]
                if val != -1.0:
                    info['event_time_remaining'] = val
                else:
                    info['event_time_remaining'] = 0.0
            except struct.error:
                pass
                
        packet_race = self._packet_buffer.get(308)
        if packet_race and len(packet_race) >= 308:
            try:
                laps_time = struct.unpack_from('<H', packet_race, 304)[0]
                is_timed = bool(laps_time & 0x8000)
                actual_laps = laps_time & 0x7FFF
                if not is_timed:
                    info['laps_in_event'] = actual_laps
                else:
                    duration_secs = actual_laps * 5 * 60
                    if info['event_time_remaining'] > 0:
                        info['current_time'] = max(0.0, duration_secs - info['event_time_remaining'])
            except struct.error:
                pass
                
        packet_game_state = self._packet_buffer.get(24)
        if packet_game_state and len(packet_game_state) >= 24:
            try:
                game_state_raw = struct.unpack_from('<B', packet_game_state, 14)[0]
                # Lower 4 bits = GameState, Upper 4 bits = SessionState
                info['game_state'] = game_state_raw & 0x0F
                info['session_state'] = (game_state_raw >> 4) & 0x0F
            except struct.error as e:
                print(f"[UDP DEBUG] Error unpacking game state: {e}")

        return info

    def _parse_udp_participants(self, packet: bytes | None) -> dict[int, dict] | None:
        """Parse a UDP extended packet into participant dicts."""
        if packet is None or len(packet) < 1063:
            return None

        try:
            num_participants = struct.unpack_from('<b', packet, 12)[0]
            if num_participants < 0 or num_participants > 32:
                num_participants = 32

            participants: dict[int, dict] = {}
            for i in range(32):
                race_position_offset = 31 + i * 32 + 16
                lap_distance_offset = 31 + i * 32 + 14
                current_sector_offset = 31 + i * 32 + 17
                current_lap_offset = 31 + i * 32 + 23
                current_time_offset = 31 + i * 32 + 24
                current_sector_time_offset = 31 + i * 32 + 28
                race_state_offset = 31 + i * 32 + 22
                pit_mode_offset = 31 + i * 32 + 19

                # Safely parse bytes
                race_pos_byte = packet[race_position_offset]
                race_position = race_pos_byte & 0x7F
                is_active = (race_pos_byte & 0x80) != 0
                
                # Strict active check using num_participants (removes disconnected ghosts)
                if num_participants > 0:
                    is_active = is_active and (i < num_participants)
                    
                lap_distance = int.from_bytes(packet[lap_distance_offset:lap_distance_offset + 2], byteorder='little')
                # AMS2 UDP sector is 0, 1, 2. Add 1 to match Shared Memory logic (1, 2, 3).
                current_sector = (packet[current_sector_offset] & 0x0F) + 1
                current_lap = packet[current_lap_offset]
                
                try:
                    current_time = struct.unpack_from('<f', packet, current_time_offset)[0]
                    current_sector_time = struct.unpack_from('<f', packet, current_sector_time_offset)[0]
                except struct.error:
                    current_time = 0.0
                    current_sector_time = 0.0

                race_state = packet[race_state_offset] & 0x07
                pit_mode_byte = packet[pit_mode_offset]
                pit_mode = pit_mode_byte & 0x07

                # Lookup name and nationality from cache
                name = self._udp_participant_names.get(i, f"Driver {i}")
                nationality = self._udp_participant_nationalities.get(i, "")

                if name.lower().startswith('safety car'):
                    is_active = False

                participants[i] = {
                    'name': name,
                    'nationality': nationality,
                    'race_position': race_position,
                    'is_active': is_active,
                    'lap_distance': float(lap_distance),
                    'current_lap': current_lap,
                    'current_time': current_time,
                    'current_sector_time': current_sector_time,
                    'current_sector': current_sector,
                    'speed': 0.0, # Will be calculated manually in poll()
                    'pit_mode': pit_mode,
                    'race_state': race_state,
                    'true_distance': 0.0,
                    'gap_ahead': 0.0,
                    'cars_ahead_250m': 0,
                    'flag_colour': 0,
                    'flag_reason': 0,
                    'fastest_lap': 0.0,
                    'last_lap': 0.0,
                }
            return participants
        except Exception:
            return None

