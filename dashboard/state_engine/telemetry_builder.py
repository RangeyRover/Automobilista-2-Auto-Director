import struct

class TelemetryBuilder:
    @staticmethod
    def build_leaderboard(shm, participants_dict, pit_manager, sector_manager, tyre_compound_cache, 
                          last_packets, driver_lookup, effective_source, provider):
        """Build the structured leaderboard array sorted by race_position."""
        active_drivers = [p for p in participants_dict.values() if p.get('is_active', False) and p.get('race_position', 999) > 0]
        active_drivers.sort(key=lambda x: x.get('race_position', 999))
        
        leaderboard = []
        for p in active_drivers:
            idx = -1
            for key, val in participants_dict.items():
                if val == p:
                    idx = key
                    break

            pit_count = 0
            laps_since = -1
            history = pit_manager.get_driver_tracker(idx)
            if history:
                last_stop = history[-1]
                pit_count = last_stop.get("pit_count", 0)
                laps_since = last_stop.get("laps_since_last_pit", -1)

            gap_val = p.get("time_gap_to_leader", p.get("gap_ahead", 0.0))

            # Update Sector Tracker
            sector = p.get("current_sector", 0)
            game_time = p.get("current_time", 0.0)
            in_pits = p.get("pit_mode", 0) != 0
            if idx >= 0:
                current_sectors = sector_manager.update_driver(idx, sector, game_time, in_pits)
            else:
                current_sectors = [0.0, 0.0, 0.0]

            entry = {
                "pos": p.get("race_position"),
                "name": p.get("name"),
                "lap": p.get("current_lap"),
                "lap_distance": p.get("lap_distance", 0.0),
                "true_distance": p.get("true_distance", 0.0),
                "tyre_stint_laps": p.get("tyre_stint_laps", 0),
                "tyre_compound": tyre_compound_cache.get(idx, ""),
                "gap": gap_val,
                "current_time": p.get("current_time", 0.0),
                "current_sector_time": p.get("current_sector_time", 0.0),
                "speed": p.get("speed"),
                "pit": pit_count,
                "pit_mode": p.get("pit_mode"),
                "laps_since_last_pit": laps_since,
                "current_sector": sector
            }

            if shm is not None and idx >= 0 and idx < len(getattr(shm, 'mFastestLapTimes', [])):
                entry["fastest_lap"] = shm.mFastestLapTimes[idx]
                entry["last_lap"] = shm.mLastLapTimes[idx]
                entry["current_sectors"] = current_sectors
                entry["fastest_sectors"] = [shm.mFastestSector1Times[idx], shm.mFastestSector2Times[idx], shm.mFastestSector3Times[idx]]
            elif last_packets.get(1040):
                p1040 = last_packets[1040]
                if idx >= 0 and idx < 32:
                    offset = 16 + idx * 32
                    try:
                        fl, ll, _, fs1, fs2, fs3 = struct.unpack_from('<6f', p1040, offset)
                        entry["fastest_lap"] = fl
                        entry["last_lap"] = ll
                        entry["current_sectors"] = current_sectors
                        entry["fastest_sectors"] = [fs1, fs2, fs3]
                    except Exception:
                        entry["fastest_lap"] = 0.0
                        entry["last_lap"] = 0.0
                        entry["current_sectors"] = current_sectors
                        entry["fastest_sectors"] = [0.0, 0.0, 0.0]
                else:
                    entry["fastest_lap"] = 0.0
                    entry["last_lap"] = 0.0
                    entry["current_sectors"] = current_sectors
                    entry["fastest_sectors"] = [0.0, 0.0, 0.0]
            else:
                entry["fastest_lap"] = 0.0
                entry["last_lap"] = 0.0
                entry["current_sectors"] = current_sectors
                entry["fastest_sectors"] = [0.0, 0.0, 0.0]

            d_name = p.get("name", "")
            name_key = str(d_name).lower().strip()
            
            # 1. Manual JSON Override has highest priority
            if name_key in driver_lookup:
                entry["nationality"] = driver_lookup[name_key]
            # 2. Live Telemetry Hash has second priority
            elif p.get("nationality"):
                entry["nationality"] = p.get("nationality").lower()
            else:
                entry["nationality"] = ""
            
            if shm is not None and idx >= 0:
                entry["car_name"] = bytes(shm.mCarNames[idx]).split(b'\x00')[0].decode('utf-8', errors='replace').strip() if idx < len(getattr(shm, 'mCarNames', [])) else ""
                entry["car_class"] = bytes(shm.mCarClassNames[idx]).split(b'\x00')[0].decode('utf-8', errors='replace').strip() if idx < len(getattr(shm, 'mCarClassNames', [])) else ""
            elif effective_source in ('udp_auto', 'udp_manual'):
                # Use UDP-parsed car data when in UDP mode
                udp_car_names = provider.get_udp_car_names() if hasattr(provider, 'get_udp_car_names') else {}
                udp_car_classes = provider.get_udp_car_classes() if hasattr(provider, 'get_udp_car_classes') else {}
                entry["car_name"] = udp_car_names.get(idx, "")
                entry["car_class"] = udp_car_classes.get(idx, "")
            else:
                entry["car_name"] = ""
                entry["car_class"] = ""

            leaderboard.append(entry)
            
        return leaderboard

    @staticmethod
    def calculate_session_bests(leaderboard, fastest_lap_events, cur_time):
        """Calculate session fastest lap and sectors from leaderboard, managing events array."""
        session_fastest = 0.0
        best_driver = ""
        session_sectors = [0.0, 0.0, 0.0]
        
        for entry in leaderboard:
            fl = entry.get("fastest_lap", 0.0)
            if fl > 0 and (session_fastest == 0.0 or fl < session_fastest):
                session_fastest = fl
                best_driver = entry.get("name", "")
                
            fs = entry.get("fastest_sectors", [0.0, 0.0, 0.0])
            for i in range(3):
                if fs[i] > 0 and (session_sectors[i] == 0.0 or fs[i] < session_sectors[i]):
                    session_sectors[i] = fs[i]
        
        # Update history and JSON payload
        current_best_in_history = fastest_lap_events[-1].get("lap_time", 0.0) if fastest_lap_events else 0.0
        
        # Ignore 0.0 times or the very first packet (cur_time < 5.0) to prevent initial floods
        if session_fastest > 0:
            is_new_record = current_best_in_history == 0.0 or session_fastest < current_best_in_history
            if is_new_record and cur_time > 5.0:
                new_event = {
                    "driver_name": best_driver,
                    "lap_time": session_fastest,
                    "timestamp": cur_time
                }
                fastest_lap_events.append(new_event)
                
        return session_fastest, session_sectors
