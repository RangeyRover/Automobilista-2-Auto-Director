import struct
import time

class PayloadBuilder:
    def __init__(self, bridge):
        self.bridge = bridge

    def parse_packets(self) -> bool:
        b = self.bridge
        if b.packet_buffer is None or not hasattr(b, 'main_app'):
            return False
            
        changed = False

        # Fetch a thread-safe snapshot of all packet buffers in a single lock acquisition
        if hasattr(b, 'provider') and b.provider and hasattr(b.provider, 'get_packet_buffer_snapshot'):
            snapshot = b.provider.get_packet_buffer_snapshot(client='bridge')
        else:
            snapshot = b.packet_buffer

        # --- Viewed Index Debouncing ---
        raw_viewed_index = b.state["viewed_index"]
        p559 = snapshot.get(559) or snapshot.get(556)
        
        # Get thread-safe shared memory snapshot if in hybrid mode
        shm = None
        effective_source = getattr(b.main_app, '_effective_source', 'hybrid')
        if effective_source == 'hybrid':
            shm = getattr(b.main_app, 'shm_snapshot', None) or getattr(b.main_app, '_shm', None)
            if shm is not None:
                current_time = getattr(shm, 'mCurrentTime', 0.0)
                if current_time != getattr(b, '_last_shm_time', -1.0):
                    b._last_shm_time = current_time
                    changed = True
        
        if p559:
            raw_viewed_index = p559[12]
        elif shm is not None:
            raw_viewed_index = getattr(shm, 'mViewedParticipantIndex', b.state["viewed_index"])

        if raw_viewed_index != b.state["viewed_index"]:
            if raw_viewed_index == getattr(b, '_viewed_idx_candidate', -1):
                b._viewed_idx_count += 1
                if b._viewed_idx_count >= 10:
                    b.state["viewed_index"] = raw_viewed_index
                    b._last_camera_change_time = time.time()
                    b._viewed_idx_count = 0
                    changed = True
            else:
                b._viewed_idx_candidate = raw_viewed_index
                b._viewed_idx_count = 1
        else:
            b._viewed_idx_candidate = -1
            b._viewed_idx_count = 0
        # -------------------------------

        # 559 bytes - Telemetry (AMS2 uses 559, PCars2 used 556)
        if p559 and p559 != b.last_packets.get(559):
            b.last_packets[559] = p559
            changed = True
            b.state["viewed"]["speed_kph"] = struct.unpack_from('<f', p559, 36)[0] * 3.6
            b.state["viewed"]["rpm"] = struct.unpack_from('<H', p559, 40)[0]
            b.state["viewed"]["gear"] = p559[45] & 0x0F
            
            b.state["viewed"]["brake"] = p559[29] / 255.0
            b.state["viewed"]["throttle"] = p559[30] / 255.0
            b.state["viewed"]["max_rpm"] = struct.unpack_from('<H', p559, 42)[0]
            b.state["viewed"]["num_gears"] = (p559[45] >> 4) & 0x0F
            b.state["viewed"]["crash_state"] = p559[47]
            
            if len(p559) >= 538:
                b.state["viewed"]["aero_damage"] = p559[371] / 255.0
                b.state["viewed"]["engine_damage"] = p559[372] / 255.0
                b.state["viewed"]["suspension_damage"] = [p559[204+i] / 255.0 for i in range(4)]
                b.state["viewed"]["brake_damage"] = [p559[200+i] / 255.0 for i in range(4)]
                b.state["viewed"]["tyre_wear"] = [p559[196+i] / 255.0 for i in range(4)]
                compounds = []
                for i in range(4):
                    raw = p559[378+i*40:378+(i+1)*40]
                    compounds.append(raw.split(b'\x00')[0].decode('utf-8', errors='replace').strip())
                b.state["viewed"]["tyre_compound"] = compounds
                if b.state.get("viewed_index", -1) >= 0 and time.time() - getattr(b, '_last_camera_change_time', 0.0) > 1.0:
                    b._tyre_compound_cache[b.state["viewed_index"]] = compounds[0]

        # 308 bytes - RaceData
        p308 = snapshot.get(308)
        if p308 and p308 != b.last_packets.get(308):
            b.last_packets[308] = p308
            changed = True
            try:
                b.state["session"]["world_fastest_lap"] = struct.unpack_from('<f', p308, 12)[0]
                b.state["session"]["world_fastest_sectors"] = [
                    struct.unpack_from('<f', p308, 32)[0],
                    struct.unpack_from('<f', p308, 36)[0],
                    struct.unpack_from('<f', p308, 40)[0]
                ]
                b.state["session"]["track_name"] = struct.unpack_from('64s', p308, 48)[0].split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                b.state["session"]["track_variation"] = struct.unpack_from('64s', p308, 112)[0].split(b'\x00')[0].decode('utf-8', errors='replace').strip()
                b.state["session"]["enforced_pit_stop_lap"] = struct.unpack_from('<b', p308, 306)[0]
            except Exception:
                pass

        # 24 bytes - GameState
        p24 = snapshot.get(24)
        if p24 and p24 != b.last_packets.get(24):
            b.last_packets[24] = p24
            changed = True
            try:
                b.state["weather"]["ambient_temp"] = struct.unpack_from('<b', p24, 16)[0]
                b.state["weather"]["track_temp"] = struct.unpack_from('<b', p24, 17)[0]
                b.state["weather"]["rain_density"] = p24[18] / 255.0
                b.state["weather"]["snow_density"] = p24[19] / 255.0
                b.state["weather"]["wind_speed"] = struct.unpack_from('<b', p24, 20)[0] * 3.6
            except Exception:
                pass

        # 1136 bytes - Participants
        p1136 = snapshot.get(1136)
        if p1136 and p1136 != b.last_packets.get(1136):
            b.last_packets[1136] = p1136
            changed = True

        # 1063 bytes - Timings
        p1063 = snapshot.get(1063)
        if p1063 and p1063 != b.last_packets.get(1063):
            b.last_packets[1063] = p1063
            changed = True
            try:
                split_ahead = struct.unpack_from('<f', p1063, 21)[0]
                split_behind = struct.unpack_from('<f', p1063, 25)[0]
                b.state["split_ahead"] = split_ahead
                b.state["split_behind"] = split_behind
            except Exception:
                pass

        # 1040 bytes - TimeStats
        p1040 = snapshot.get(1040)
        if p1040 and p1040 != b.last_packets.get(1040):
            b.last_packets[1040] = p1040
            changed = True
            try:
                viewed_idx = b.state["viewed_index"]
                if viewed_idx >= 0 and viewed_idx < 32:
                    offset = 16 + viewed_idx * 32 + 4
                    last_lap = struct.unpack_from('<f', p1040, offset)[0]
                    if last_lap > 0:
                        b.state["viewed"]["last_lap"] = last_lap
            except Exception:
                pass

        # Post-processing updates using main_app participants snapshot
        participants = getattr(b.main_app, 'participants_snapshot', None) or getattr(b.main_app, '_participants', {})
            
        if participants:
            viewed_idx = b.state["viewed_index"]
            if viewed_idx in participants:
                vp = participants[viewed_idx]
                b.state["viewed"]["position"] = vp.get("race_position", 0)
                b.state["viewed"]["name"] = vp.get("name", "Unknown Driver")
                
                target_pos = vp.get("race_position", 0) - 1
                if target_pos > 0:
                    ahead_name = "Unknown Driver"
                    for idx, p in participants.items():
                        if p.get("race_position") == target_pos:
                            ahead_name = p.get("name", "Unknown Driver")
                            break
                    b.state["ahead"]["name"] = ahead_name
                    b.state["ahead"]["position"] = target_pos
                    b.state["ahead"]["gap_seconds"] = b.state.get("split_ahead", 0.0)
                else:
                    b.state["ahead"]["name"] = ""
                    b.state["ahead"]["position"] = 2
                    b.state["ahead"]["gap_seconds"] = b.state.get("split_behind", 0.0)

                behind_pos = vp.get("race_position", 0) + 1
                behind_name = ""
                found_behind = False
                for idx, p in participants.items():
                    if p.get("race_position") == behind_pos:
                        behind_name = p.get("name", "Unknown Driver")
                        found_behind = True
                        break
                
                if found_behind:
                    b.state["behind"]["name"] = behind_name
                    b.state["behind"]["position"] = behind_pos
                    b.state["behind"]["gap_seconds"] = b.state.get("split_behind", 0.0)
                else:
                    b.state["behind"]["name"] = ""
                    b.state["behind"]["position"] = 0
                    b.state["behind"]["gap_seconds"] = 0.0

        # Session Info Update
        if shm is not None:
            # SHM only provides RPM/Gear/Brake/Throttle for the LOCAL player (which is 0 when spectating).
            # UDP provides it for the VIEWED player. Only use SHM if UDP is not available.
            if not b.last_packets.get(559) and not b.last_packets.get(556):
                b.state["viewed"]["speed_kph"] = getattr(shm, 'mSpeed', 0.0) * 3.6
                b.state["viewed"]["rpm"] = int(getattr(shm, 'mRpm', 0.0))
                b.state["viewed"]["max_rpm"] = int(getattr(shm, 'mMaxRPM', 10000.0))
                b.state["viewed"]["gear"] = getattr(shm, 'mGear', 0)
                b.state["viewed"]["num_gears"] = getattr(shm, 'mNumGears', 0)
                b.state["viewed"]["brake"] = getattr(shm, 'mBrake', 0.0)
                b.state["viewed"]["throttle"] = getattr(shm, 'mThrottle', 0.0)
                b.state["viewed"]["crash_state"] = getattr(shm, 'mCrashState', 0)
                b.state["viewed"]["aero_damage"] = getattr(shm, 'mAeroDamage', 0.0)
                b.state["viewed"]["engine_damage"] = getattr(shm, 'mEngineDamage', 0.0)
                
                try:
                    b.state["viewed"]["suspension_damage"] = list(shm.mSuspensionDamage)
                    b.state["viewed"]["brake_damage"] = list(shm.mBrakeDamage)
                    b.state["viewed"]["tyre_wear"] = list(shm.mTyreWear)
                    compounds = []
                    for i in range(4):
                        compounds.append(bytes(shm.mTyreCompound[i]).split(b'\x00')[0].decode('utf-8', errors='replace').strip())
                    b.state["viewed"]["tyre_compound"] = compounds
                    if b.state.get("viewed_index", -1) >= 0 and time.time() - getattr(b, '_last_camera_change_time', 0.0) > 1.0:
                        b._tyre_compound_cache[b.state["viewed_index"]] = compounds[0]
                except Exception:
                    pass

            b.state["session"]["world_fastest_lap"] = getattr(shm, 'mWorldFastestLapTime', 0.0)
            b.state["session"]["world_fastest_sectors"] = [
                getattr(shm, 'mWorldFastestSector1Time', 0.0),
                getattr(shm, 'mWorldFastestSector2Time', 0.0),
                getattr(shm, 'mWorldFastestSector3Time', 0.0)
            ]
            b.state["session"]["track_name"] = getattr(shm, 'mTranslatedTrackLocation', b'').split(b'\x00')[0].decode('utf-8', errors='replace').strip()
            b.state["session"]["track_variation"] = getattr(shm, 'mTranslatedTrackVariation', b'').split(b'\x00')[0].decode('utf-8', errors='replace').strip()
            b.state["session"]["enforced_pit_stop_lap"] = getattr(shm, 'mEnforcedPitStopLap', -1)
            b.state["weather"]["ambient_temp"] = getattr(shm, 'mAmbientTemperature', 0)
            b.state["weather"]["track_temp"] = getattr(shm, 'mTrackTemperature', 0)
            b.state["weather"]["rain_density"] = getattr(shm, 'mRainDensity', 0.0)
            b.state["weather"]["snow_density"] = getattr(shm, 'mSnowDensity', 0.0)
            b.state["weather"]["wind_speed"] = getattr(shm, 'mWindSpeed', 0) * 3.6
            
        session_info = b.provider.get_session_info(shm) if hasattr(b, 'provider') and b.provider else {}
        if session_info:
            time_remaining = session_info.get("event_time_remaining", 0.0)
            cur_time = session_info.get("current_time", 0.0)
            
            # Time-Travel Rewind Detection
            if cur_time < getattr(b, '_last_current_time', 0.0) - 5.0:
                b.pit_manager.process_rewind(cur_time)
                
                # Prune fastest laps
                b._fastest_lap_events = [ev for ev in b._fastest_lap_events if ev.get("timestamp", 0.0) <= cur_time]
                
            b._last_current_time = cur_time
            laps = session_info.get("laps_in_event", 0)
            
            # Replay Log Fallbacks
            scorer = getattr(b.main_app, 'scorer', None)
            if scorer:
                if laps <= 0:
                    laps = scorer.timeline_laps_in_event
                
                if time_remaining <= 0 and scorer.timeline_session_time > 0:
                    time_remaining = max(0.0, scorer.timeline_session_time - cur_time)
            
            b.state["session"]["time_remaining"] = time_remaining
            b.state["session"]["laps_in_event"] = laps
            b.state["session"]["leader_lap"] = session_info.get("leader_lap", 0)

        camera_ctrl = getattr(b.main_app, 'camera', None)
        if camera_ctrl:
            b.state["director"]["camera_type"] = camera_ctrl.current_camera_type
            b.state["director"]["is_auto_directing"] = getattr(b.main_app, '_director_enabled', False)
        
        if session_info:
            b.state["session"]["state"] = session_info.get("game_state", 0)
            b.state["session"]["session_state"] = session_info.get("session_state", 0)
            b.state["session"]["yellow_flag_state"] = session_info.get("yellow_flag_state", 0)
            
            participants_dict = getattr(b.main_app, 'participants_snapshot', None) or getattr(b.main_app, '_participants', {})
            
            b.pit_manager.update(participants_dict, getattr(b, '_last_current_time', 0.0))
            b.state["pit_events"] = b.pit_manager.pit_events
            
            b.state["session"]["total_drivers"] = len([p for p in participants_dict.values() if p.get('is_active', False)])
            # Find leader lap
            leader_lap = 0
            for p in participants_dict.values():
                if p.get('race_position') == 1:
                    # In AMS2, current_lap starts at 1 usually, but let's just expose what the telemetry provides
                    leader_lap = p.get('current_lap', 0)
                    break
            b.state["session"]["leader_lap"] = leader_lap
            
            # Leaderboard (sorted by race_position)
            from dashboard.state_engine.telemetry_builder import TelemetryBuilder
            leaderboard = TelemetryBuilder.build_leaderboard(
                shm, participants_dict, b.pit_manager, b._sector_manager,
                b._tyre_compound_cache, b.last_packets, b.driver_lookup,
                effective_source, b.provider
            )
            b.state["leaderboard"] = leaderboard
            
            # Calculate actual session fastest lap from active drivers
            session_fastest, session_sectors = TelemetryBuilder.calculate_session_bests(
                leaderboard, b._fastest_lap_events, getattr(b, '_last_current_time', 0.0)
            )
            
            # Ignore 0.0 times or the very first packet (cur_time < 5.0) to prevent initial floods
            if session_fastest > 0:
                b.state["session"]["world_fastest_lap"] = session_fastest

            
            if b._fastest_lap_events:
                b.state["events"]["fastest_lap"] = b._fastest_lap_events[-1]
                
            if any(s > 0 for s in session_sectors):
                b.state["session"]["world_fastest_sectors"] = session_sectors
            
            changed = True

        if getattr(b, 'provider', None):
            b.state["spline"] = b.provider.spline_data
            b.state["flywheel_active"] = b.provider.flywheel_active
            b.state["time_history"] = b.provider.time_history

        return changed
