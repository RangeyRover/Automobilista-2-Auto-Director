"""Standalone WebSocket server and pure functions for the SHM Leaderboard Test Tool."""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared_memory_struct import SharedMemory

from core.shm_serialiser import serialise_shm, annotate_enums

from core.spline import DistanceTimeSpline, compute_total_distance, compute_time_gap


from core.physics_flywheel import PhysicsFlywheel

def correlate_drivers(data: dict, active_only: bool = False, spline: DistanceTimeSpline = None, pit_entry_times: dict = None, flywheel: PhysicsFlywheel = None) -> list:
    """Bundle indexed data arrays into a sorted list of driver dictionaries."""
    if not data or "mNumParticipants" not in data:
        return []
        
    num = data["mNumParticipants"]
    participants = data.get("mParticipantInfo", [])
    track_len = data.get("mTrackLength", 0.0)
    
    drivers = []
    
    for i in range(min(num, len(participants))):
        p_info = participants[i]
        driver = dict(p_info)
        
        if active_only and not driver.get("mIsActive", False):
            continue
            
        for key, value in data.items():
            if key == "mParticipantInfo":
                continue
            if isinstance(value, list) and len(value) >= num:
                out_key = key
                if key.endswith("_labels"):
                    out_key = key[:-1]
                driver[out_key] = value[i]
                
        current_lap = driver.get("mCurrentLap", 1)
        dist = driver.get("mCurrentLapDistance", 0.0)
        driver["_total_dist"] = compute_total_distance(current_lap, track_len, dist)
        
        current_time = data.get("mCurrentTime", 0.0)
        pit_mode = driver.get("mPitModes", 0)
        driver_name = driver.get("mName")
        
        driver["_in_pits"] = False
        driver["_pit_time"] = None
        
        if pit_mode > 0:
            driver["_in_pits"] = True
            if pit_entry_times is not None and driver_name:
                if driver_name not in pit_entry_times:
                    pit_entry_times[driver_name] = current_time
                driver["_pit_time"] = current_time - pit_entry_times[driver_name]
        else:
            if pit_entry_times is not None and driver_name in pit_entry_times:
                del pit_entry_times[driver_name]
        
        drivers.append(driver)
        
    def sort_key(d):
        pos = d.get("mRacePosition", 0)
        return pos if pos > 0 else 99999
        
    drivers.sort(key=sort_key)
    
    if drivers:
        current_time = data.get("mCurrentTime", 0.0)
        leader_dist = max(d["_total_dist"] for d in drivers)
        
        # Physics Flywheel: stabilize mCurrentTime before downstream consumers
        if flywheel is not None:
            current_time = flywheel.process(current_time, leader_dist)
        
        for i, d in enumerate(drivers):
            d["_gap"] = leader_dist - d["_total_dist"]
            
            if i == 0 or d["_gap"] <= 0.0:
                d["_time_gap"] = 0.0
            else:
                d["_time_gap"] = compute_time_gap(d["_total_dist"], current_time, spline)
            
    return drivers

def process_shm(shm: SharedMemory, active_only: bool = False, spline: DistanceTimeSpline = None, pit_entry_times: dict = None, flywheel: PhysicsFlywheel = None) -> dict:
    """Process the raw ctypes struct into the final WebSocket payload."""
    raw_data = serialise_shm(shm)
    annotated = annotate_enums(raw_data)
    leaderboard = correlate_drivers(annotated, active_only, spline, pit_entry_times, flywheel)
    payload = {
        "raw": annotated,
        "leaderboard": leaderboard
    }
    
    if spline is not None:
        payload["spline"] = {
            "distances": spline.distances,
            "times": spline.times
        }
        
    return payload

import json
import asyncio

def should_reset_spline(prev_state: int | None, curr_state: int, prev_participants: int, curr_participants: int) -> bool:
    """Determine if session state implies we should flush the splines."""
    if curr_participants == 0:
        return True
    if prev_state == 5 and curr_state != 5: # SESSION_RACE is 5
        return True
    return False

def get_leader_name(leaderboard: list) -> str | None:
    """Extract the current leader's name from a correlated leaderboard."""
    if leaderboard:
        return leaderboard[0].get("mName")
    return None

async def broadcast_telemetry(connected_clients: set, payload: dict):
    """Broadcast JSON payload to all connected clients."""
    if not connected_clients:
        return
        
    message = json.dumps(payload)
    aws = [client.send(message) for client in connected_clients]
    if aws:
        await asyncio.gather(*aws, return_exceptions=True)

async def telemetry_loop(connected_clients: set, active_only: bool):
    """Poll AMS2 shared memory and broadcast updates to clients."""
    import mmap
    import ctypes
    shm_name = "$pcars2$"
    shm_file = None
    spline = DistanceTimeSpline(min_interval=0.0)  # loop cadence is the sole rate limiter
    last_session_state = None
    last_participants = 0
    pit_entry_times = {}
    time_history = []
    flywheel = PhysicsFlywheel()
    
    while True:
        try:
            if shm_file is None:
                try:
                    shm_file = mmap.mmap(0, ctypes.sizeof(SharedMemory), shm_name, access=mmap.ACCESS_READ)
                except OSError:
                    if connected_clients:
                        await broadcast_telemetry(connected_clients, {"status": "Waiting for AMS2..."})
                    await asyncio.sleep(2.0)
                    continue
            
            shm = SharedMemory.from_buffer_copy(shm_file)
            
            curr_state = shm.mSessionState
            curr_participants = shm.mNumParticipants
            
            if should_reset_spline(last_session_state, curr_state, last_participants, curr_participants):
                spline.reset()
                pit_entry_times.clear()
                flywheel.reset(shm.mCurrentTime, 0.0)
                
            last_session_state = curr_state
            last_participants = curr_participants
            
            payload = process_shm(shm, active_only=active_only, spline=spline, pit_entry_times=pit_entry_times, flywheel=flywheel)
            payload["status"] = "Connected"
            payload["flywheel_active"] = flywheel.is_active
            
            leaderboard = payload.get("leaderboard", [])
            if leaderboard:
                leader = leaderboard[0]
                leader_dist = leader.get("_total_dist")
                if leader_dist is not None:
                    # Use flywheel-stabilized time, NOT raw shm.mCurrentTime
                    stabilized_time = flywheel.internal_master_clock if flywheel.internal_master_clock is not None else shm.mCurrentTime
                    spline.record(leader_dist, stabilized_time)
            
            time_history.append(shm.mCurrentTime)
            if len(time_history) > 200: # ~50 seconds of history at 4Hz
                time_history.pop(0)
                
            payload["time_history"] = list(time_history)
            
            await broadcast_telemetry(connected_clients, payload)
            
        except Exception as e:
            if shm_file is not None:
                shm_file.close()
                shm_file = None
            if connected_clients:
                await broadcast_telemetry(connected_clients, {"status": f"Error: {str(e)}"})
                
        await asyncio.sleep(0.5) # ~2Hz — matches spline min_interval for synchronized gap calculation

async def main(host="127.0.0.1", port=8770, active_only=False):
    """Main entry point for the standalone server."""
    import websockets
    connected_clients = set()
    
    async def handler(websocket):
        connected_clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            connected_clients.remove(websocket)
            
    await websockets.serve(handler, host, port)
    print(f"SHM Leaderboard Server started on ws://{host}:{port}")
    print(f"Active Only Mode: {active_only}")
    
    asyncio.create_task(telemetry_loop(connected_clients, active_only))
    await asyncio.Future()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--active-only", action="store_true", help="Filter inactive drivers")
    parser.add_argument("--host", default="127.0.0.1", help="Host IP")
    parser.add_argument("--port", type=int, default=8770, help="Port")
    args = parser.parse_args()
    
    try:
        asyncio.run(main(host=args.host, port=args.port, active_only=args.active_only))
    except KeyboardInterrupt:
        print("Server stopped.")
