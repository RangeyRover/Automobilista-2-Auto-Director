import socket
import struct
import os
import pandas as pd
import keyboard
import time
from shared_memory_struct import SharedMemory, SHARED_MEMORY_VERSION
from pyKey import pressKey, releaseKey
import ctypes
import mmap
import wx
import wx.grid as gridlib
import threading
import traceback
from collections import defaultdict, deque

# Buffers to store raw UDP packets
packet_buffer = defaultdict(deque)

# Store the timestamp of the last processed set
last_processed_time = None

# Threading locks
data_lock = threading.Lock()

# User choice between UDP and Shared Memory
mode = None
while mode not in ["1", "2"]:
    mode = input("Select data source:\n1. UDP\n2. Shared Memory\nEnter 1 or 2: ").strip()

# Prompt for the interval between camera changes in seconds
camera_change_interval_input = input("Enter the interval between camera changes in seconds (press Enter for default 7): ")

# Set the camera change interval based on user input, or use the default if none is provided
AUTO_DIRECTOR_INTERVAL = int(camera_change_interval_input) if camera_change_interval_input.strip() else 7

# Prompt for the race position bonus factor
race_position_bonus_input = input("Enter the race position bonus factor, (press Enter for default 12): ")

# Set the race position bonus factor based on user input, or use the default if none is provided
RACE_POSITION_BONUS_FACTOR = int(race_position_bonus_input) if race_position_bonus_input.strip() else 12

# Set up for the selected mode
if mode == "1":
    # Prompt the user to enter the port number or press Enter for the default
    port_input = input("Enter UDP port to listen on (press Enter for default 5606): ")
    # Set the UDP port based on user input, or use the default if none is provided
    UDP_PORT = int(port_input) if port_input.strip() else 5606

# Set score history record
scores_dict = {i: 0 for i in range(32)}  # Initialize scores_dict with default scores of 0


# Initialize variables
BUFFER_SIZE = 1500
PACKET_SIZE_LEADERBOARD = 1040
PACKET_SIZE_EXTENDED = 1063
PACKET_SIZE_TRACK_INFO = 308
SAMPLE_PERIOD = 15  # Number of samples to average
UPDATE_INTERVAL = 1  # Update screen every 1 second
SCREEN_CLEAR_INTERVAL = 15  # Clear screen every 15 seconds to handle potential aberrations
# Define multipliers for scoring components
PIT_MODE_PENALTY_MULTIPLIER = -10
SPEED_PENALTY_MULTIPLIER = -5
LEADER_CARS_AHEAD_MULTIPLIER = 2
OTHER_CARS_AHEAD_MULTIPLIER = 2
CLOSE_RACING_BONUS_DIVISOR = 5
CLOSE_RACING_MAX_GAP = 50

# Initialize dictionaries to store participants' data and track length
participants_data_dict = {i: {} for i in range(32)}
previous_data_dict = {i: {'distances': deque(maxlen=SAMPLE_PERIOD), 'timestamps': deque(maxlen=SAMPLE_PERIOD)} for i in range(32)}
gap_history = {i: deque(maxlen=SAMPLE_PERIOD) for i in range(32)}  # New: to store gap history
track_length = None
previous_track_info = {}
last_update_time = time.time()
last_director_time = time.time()
last_screen_clear_time = time.time()
last_shared_memory_read_time = time.time()  # Add this to track the last shared memory read time
last_UDP_read_time = time.time()  # Add this to track the last shared memory read time

# Required packet sizes for identification
REQUIRED_PACKET_TYPES = {
    PACKET_SIZE_LEADERBOARD: "leaderboard",
    PACKET_SIZE_EXTENDED: "extended",
    PACKET_SIZE_TRACK_INFO: "track_info",
}

# Control variables
auto_director_enabled = False
current_focus_position = None
last_focus_position = None
dev_mode_enabled = False

def read_shared_memory():
    try:
        # Open the memory-mapped file
        file_handle = mmap.mmap(-1, ctypes.sizeof(SharedMemory), "$pcars2$", access=mmap.ACCESS_READ)
        
        # Create an instance of the shared memory structure
        data = SharedMemory()
        
        # Read the shared memory into the structure
        file_handle.seek(0)
        ctypes.memmove(ctypes.addressof(data), file_handle.read(ctypes.sizeof(data)), ctypes.sizeof(data))
        
        return data
    except Exception as e:
        #print(f"Error reading shared memory: {e}")
        return None

def update_participants_data_dict(data, participants_data_dict):
    """
    Update participants data and ensure 'Gap to Player Ahead' and 'Cars Ahead' are calculated
    before updating participants_data_dict. Clears and initializes on track change.
    """
    global previous_track_info
    global track_length

    # Extract current track info
    current_track_info = {
        "Track Location": data.mTrackLocation.decode('utf-8').strip(),
        "Track Variation": data.mTrackVariation.decode('utf-8').strip(),
        "Track Length": data.mTrackLength,
    }

    # Check for track changes
    if current_track_info != previous_track_info:
        participants_data_dict.clear()  # Reset participants data on track change
        previous_track_info = current_track_info

    track_length = data.mTrackLength  # Update global track length from shared memory

    max_participants = 32  # Get the maximum number of participants

    # Ensure all participant indices exist in the dictionary
    for i in range(max_participants):
        if i not in participants_data_dict:
            participants_data_dict[i] = {}  # Initialize an empty dictionary for each participant

    # Prepare a list to store True Distance Traveled
    true_distances = []

    # Calculate True Distance Traveled for each participant
    for i in range(max_participants):
        if data.mParticipantInfo[i].mIsActive:
            laps_completed = data.mParticipantInfo[i].mLapsCompleted
            current_lap_distance = data.mParticipantInfo[i].mCurrentLapDistance
            true_distance_traveled = laps_completed * track_length + current_lap_distance if track_length else None
            true_distances.append((i, true_distance_traveled, laps_completed))
        else:
            true_distances.append((i, None, None))

    # Calculate Cars Ahead
    cars_ahead = [0] * max_participants  # Initialize the cars ahead count for all participants
    for current_idx, current_distance, current_lap in true_distances:
        if current_distance is None or current_lap is None:
            continue
        count = 0
        for other_idx, other_distance, other_lap in true_distances:
            if current_idx == other_idx or other_distance is None or other_lap is None:
                continue

            lap_difference = other_lap - current_lap
            effective_distance = other_distance + (lap_difference * track_length)
            distance_ahead = (effective_distance - current_distance + track_length) % track_length

            if 0 < distance_ahead <= 250:  # Check if within 250 meters
                count += 1

        cars_ahead[current_idx] = count

    # Calculate Gap to Player Ahead
    gaps_to_player_ahead = [None] * max_participants  # Initialize gaps to None
    sorted_distances = sorted(
        [t for t in true_distances if t[1] is not None], key=lambda x: x[1]
    )  # Sort only active participants with valid distances

    for idx in range(len(sorted_distances)):
        if idx == 0:
            # First place has no one ahead
            gaps_to_player_ahead[sorted_distances[idx][0]] = 0
        else:
            # Gap is calculated as the difference between current and previous in the sorted list
            current = sorted_distances[idx]
            previous = sorted_distances[idx - 1]
            gaps_to_player_ahead[previous[0]] = current[1] - previous[1]

    # Process and update participant data
    for i in range(max_participants):
        if data.mParticipantInfo[i].mIsActive:
            participant_data = {
                "Race Position": data.mParticipantInfo[i].mRacePosition,
                "Is Active": data.mParticipantInfo[i].mIsActive,
                "Lap Distance": data.mParticipantInfo[i].mCurrentLapDistance,
                "Current Sector": data.mParticipantInfo[i].mCurrentSector,
                "Current Lap": data.mParticipantInfo[i].mLapsCompleted,
                "FastestLapTime": data.mFastestLapTimes[i],
                "LastLapTime": data.mLastLapTimes[i],
                "Speed": data.mSpeeds[i],
                "Pit Mode": data.mPitModes[i],
                "Highest Flag Colours": data.mHighestFlagColours[i],
				"Highest Flag Reasons": data.mHighestFlagReasons[i],
                "Race State": data.mRaceStates[i],
                "True Distance Traveled": true_distances[i][1],
                "Cars Ahead": cars_ahead[i],  # Add Cars Ahead
                "Gap to Player Ahead": gaps_to_player_ahead[i],  # Add Gap to Player Ahead
            }

            # Update the participant's dictionary
            participants_data_dict[i].update(participant_data)

    # Debug: Print updated participants data
    # print_participants_data(participants_data_dict)

# Function to check if required packets (track info and extended) are available
def required_packets_received():
    return (
        len(packet_buffer["track_info"]) > 0 and
        len(packet_buffer["extended"]) > 0
    )

def initialize_previous_data():
    """Initialize the previous_data_dict with fixed-size deques for each participant."""
    global previous_data_dict
    previous_data_dict = {}
    for i in range(32):
        previous_data_dict[i] = {
            'distances': deque(maxlen=2),  # Keep only last 2 measurements
            'timestamps': deque(maxlen=2)   # Keep only last 2 timestamps
        }

def calculate_speed(distances, timestamps):
    """Calculate speed in meters per second from two distance/timestamp pairs."""
    if len(distances) < 2 or len(timestamps) < 2:
        return None
        
    distance_delta = distances[-1] - distances[-2]
    time_delta = timestamps[-1] - timestamps[-2]
    
    # Handle crossing start/finish line
    if distance_delta < -track_length/2:
        distance_delta += track_length
    elif distance_delta > track_length/2:
        distance_delta -= track_length
        
    if time_delta > 0:
        return abs(distance_delta / time_delta)  # m/s
    return None

def process_packets():
    """Process track info and extended packets and update participants_data_dict."""
    global participants_data_dict, track_length, last_processed_time, previous_track_info
    if not required_packets_received():
        #print("Not all required packets received")
        return  # Exit if not all required packets are available
    
    current_timestamp = time.time()
    
    # Access and process the track info packet without removing it
    if packet_buffer["track_info"]:
        track_info_packet = packet_buffer["track_info"][0]
        track_length, track_location = decode_track_info_packet(track_info_packet)
    
    # Check for track changes
    current_track_info = {
        "Track Location": track_location,
        "Track Length": track_length,
    }
    if current_track_info != previous_track_info:
        #print("[DEBUG] Track changed, clearing participants data")
        participants_data_dict.clear()
        initialize_previous_data()  # Reset the deques
        previous_track_info = current_track_info
    
    # Access and process the extended packet without removing it
    if packet_buffer["extended"]:
        extended_packet = packet_buffer["extended"][0]
    
    # First pass: collect all participant data and true distances
    participant_info = {}
    true_distances = []
    
    for i in range(32):
        race_position_offset = 31 + i * 32 + 16
        lap_distance_offset = 31 + i * 32 + 14
        current_sector_offset = 31 + i * 32 + 17
        current_lap_offset = 31 + i * 32 + 23
        race_state_offset = 31 + i * 32 + 22
        pit_mode_offset = 31 + i * 32 + 19
        
        race_position, is_active = parse_race_position(extended_packet[race_position_offset])
        lap_distance = parse_lap_distance(extended_packet, lap_distance_offset)
        current_sector = parse_current_sector(extended_packet[current_sector_offset])
        current_lap = parse_current_lap(extended_packet[current_lap_offset])
        race_state = parse_race_state(extended_packet[race_state_offset])
        pit_mode_byte = extended_packet[pit_mode_offset]
        pit_mode, pit_schedule = parse_pit_mode_schedule(pit_mode_byte)
        
        # Add current distance and timestamp to deque (now size-limited)
        previous_data_dict[i]['distances'].append(lap_distance)
        previous_data_dict[i]['timestamps'].append(current_timestamp)
        
        # Calculate speed
        speed = calculate_speed(
            list(previous_data_dict[i]['distances']),
            list(previous_data_dict[i]['timestamps'])
        )
        
        participant_info[i] = {
            'Race Position': race_position,
            'Is Active': is_active,
            'Lap Distance': lap_distance,
            'Current Sector': current_sector,
            'Current Lap': current_lap,
            'Track Location': track_location,
            'Track Length': track_length,
            'Pit Mode': pit_mode,
            'Race State': race_state,
            'Speed': speed
        }
        
        # Calculate True Distance Traveled
        if is_active and track_length is not None:
            true_distance_traveled = (current_lap-1) * track_length + lap_distance
            participant_info[i]['True Distance Traveled'] = true_distance_traveled
            true_distances.append((i, true_distance_traveled))
        else:
            participant_info[i]['True Distance Traveled'] = None

    # [Rest of the function remains the same...]
    # Sort active participants by true distance traveled (descending order)
    true_distances.sort(key=lambda x: x[1], reverse=True)
    
    # Calculate gaps to player ahead
    gaps_dict = {}
    for idx in range(len(true_distances)):
        current_player = true_distances[idx]
        if idx > 0:
            player_ahead = true_distances[idx - 1]
            gap = player_ahead[1] - current_player[1]
            gaps_dict[current_player[0]] = gap
        else:
            gaps_dict[current_player[0]] = 0.0
    
    # Calculate cars ahead within 250m for each participant
    cars_ahead_within_250m = {}
    for i in range(32):
        if participant_info[i]['True Distance Traveled'] is not None and track_length is not None:
            current_distance = participant_info[i]['Lap Distance']
            count = 0
            
            for other_id, other_total_distance in [(p[0], p[1]) for p in true_distances]:
                if other_id != i:
                    other_lap_distance = participant_info[other_id]['Lap Distance']
                    relative_distance = other_lap_distance - current_distance
                    
                    if relative_distance < -track_length/2:
                        relative_distance += track_length
                    elif relative_distance > track_length/2:
                        relative_distance -= track_length
                    
                    if 0 < relative_distance <= 250:
                        count += 1
            
            cars_ahead_within_250m[i] = count
        else:
            cars_ahead_within_250m[i] = None
    
    # Update participants_data_dict with all data
    for i in range(32):
        participants_data_dict[i] = participant_info[i].copy()
        participants_data_dict[i]['Gap to Player Ahead'] = gaps_dict.get(i, None)
        participants_data_dict[i]['Cars Ahead'] = cars_ahead_within_250m.get(i, None)
    
    last_processed_time = current_timestamp
    #print("[DEBUG] Processed track info and extended packets")
    # Debug: Print updated participants data
    #display_leaderboard(participants_data_dict)
 
def decode_track_info_packet(data):
    """Decode the 308-byte track info packet to obtain track length and location."""
    track_length_offset = 44  # Offset to the sTrackLength field
    track_location_offset = 48  # Offset to the sTrackLocation field
    trackname_length_max = 64  # Maximum length for track name fields

    # Decode track length (float)
    track_length = struct.unpack('f', data[track_length_offset:track_length_offset + 4])[0]

    # Decode track location (string)
    try:
        track_location = data[track_location_offset:track_location_offset + trackname_length_max].decode('utf-8').strip('\x00')
    except UnicodeDecodeError as e:
        track_location = "Unknown Location"
        #print(f"[DEBUG] Failed to decode track location: {e}")

    # Debug prints
    #print(f"[DEBUG] Track Length: {track_length}")
    #print(f"[DEBUG] Track Location: {track_location}")

    return track_length, track_location




def parse_race_position(byte_value):
    """Extract the race position and active status from a byte."""
    race_position = byte_value & 0x7F  # Lower 7 bits
    is_active = (byte_value & 0x80) != 0  # Top bit
    return race_position, is_active

def parse_lap_distance(data, offset):
    """Extract the lap distance from two bytes."""
    lap_distance = int.from_bytes(data[offset:offset + 2], byteorder='little')
    return lap_distance

def parse_current_sector(byte_value):
    """Extract the current sector from the first 4 bits."""
    current_sector = byte_value & 0x0F  # Mask to keep only the first 4 bits
    return current_sector

def parse_current_lap(byte_value):
    """Extract the current lap from a byte."""
    return byte_value

def parse_pit_mode_schedule(byte_value):
    pit_mode = byte_value & 0x07  # Lower 3 bits for pit mode
    pit_schedule = (byte_value & 0x18) >> 3  # Next 2 bits for pit schedule
    return pit_mode, pit_schedule

def parse_race_state(byte_value):
    return byte_value & 0x07  # Mask to extract bits 0-2

def next_focus(df):
    """Determine the next focus and update scores_dict with detailed scoring components."""
    global current_focus_position

    # Define required columns
    required_columns = ["Race Position", "Pit Mode", "Gap to Player Ahead", "Cars Ahead", "Speed"]

    # Check for missing columns
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        #print(f"Warning: Missing required columns in next_focus: {', '.join(missing_columns)}")
        #print("Skipping next_focus due to missing data.")
        current_focus_position = None
        return

    # Check for empty DataFrame
    if df.empty:
        #print("Warning: DataFrame is empty. Skipping next_focus.")
        current_focus_position = None
        return

    # Sort by Race Position
    df.sort_values(by="Race Position", ascending=True, inplace=True)
    
    # Initialize scores_dict with default structures if necessary
    for idx in df.index:
        if idx not in scores_dict or not isinstance(scores_dict[idx], dict):
            scores_dict[idx] = {
                "Pit Mode Penalty": 0,
                "Speed Penalty": 0,
                "Cars Ahead Bonus": 0,
                "Close Racing Bonus": 0,
                "Race Position Bonus": 0,
                "Total Score": 0,
            }

    # Calculate scoring components
    for idx, row in df.iterrows():
        # Penalty for pit mode (ensure pit mode is not None)
        pit_mode = 0 if pd.isna(row["Pit Mode"]) else row["Pit Mode"]
        pit_mode_penalty = PIT_MODE_PENALTY_MULTIPLIER if pit_mode != 0 else 0

        # Penalty for speeds less than 5 m/s
        speed = row["Speed"] if pd.notnull(row["Speed"]) else 0
        speed_penalty = SPEED_PENALTY_MULTIPLIER if speed < 5 else 0

        # Bonus for cars ahead (adjustable multipliers)
        cars_ahead = 0 if pd.isna(row["Cars Ahead"]) else row["Cars Ahead"]
        if pit_mode == 0:
            if row["Race Position"] == 1:  # Leader
                cars_ahead_bonus = cars_ahead * LEADER_CARS_AHEAD_MULTIPLIER
            else:  # Other participants
                cars_ahead_bonus = cars_ahead * OTHER_CARS_AHEAD_MULTIPLIER / 5
        else:
            cars_ahead_bonus = 0

        # Bonus for close racing
        gap = row["Gap to Player Ahead"] if pd.notnull(row["Gap to Player Ahead"]) else float('inf')
        close_racing_bonus = (
            (CLOSE_RACING_MAX_GAP - gap) / CLOSE_RACING_BONUS_DIVISOR
            if 0 < gap <= CLOSE_RACING_MAX_GAP
            else 0
        )

        # Race position bonus
        def calculate_race_position_bonus(pos, max_cars=32):

            try:
                base_bonus = RACE_POSITION_BONUS_FACTOR
                if pos > 0 and pos <= max_cars:
                    return base_bonus * (1 - (pos - 1) / max_cars)
                return 0  # No bonus for invalid positions
            except (ZeroDivisionError, TypeError):
                return 0

        race_position = row["Race Position"] if pd.notnull(row["Race Position"]) else 0
        race_position_bonus = calculate_race_position_bonus(race_position)

        # Aggregate score
        total_score = (
            close_racing_bonus
            + race_position_bonus
            + pit_mode_penalty
            + cars_ahead_bonus
            + speed_penalty
        )

        # Update scores_dict with detailed components
        scores_dict[idx] = {
            "Pit Mode Penalty": pit_mode_penalty,
            "Speed Penalty": speed_penalty,
            "Cars Ahead Bonus": cars_ahead_bonus,
            "Close Racing Bonus": close_racing_bonus,
            "Race Position Bonus": race_position_bonus,
            "Total Score": total_score,
        }

    # Determine next focus
    valid_scores = {
        k: v["Total Score"]
        for k, v in scores_dict.items()
        if k in df.index and not pd.isna(v["Total Score"])
    }

    if valid_scores:
        # Get the participant index with the highest score
        next_focus_idx = max(valid_scores, key=valid_scores.get)
        # Retrieve the race position of the participant
        current_focus_position = df.loc[next_focus_idx, "Race Position"]
    else:
        #print("Warning: No valid participants to focus on.")
        current_focus_position = None


def auto_director():
    """Automatically switch the camera to the participant with the smallest gap and highest rate of change."""
    global current_focus_position
    global last_focus_position  # Store the last selected position
    #print(f"Current Focus Position: {current_focus_position}")
    #print(f"last Focus Position: {last_focus_position}")
    #Check if the current focus position is the same as the last one
    if current_focus_position == 0:
        current_focus_position = 4

    if current_focus_position is not None:
        # Simulate key presses to move focus to the desired position
        num_participants = len(participants_data_dict)

        # Move up to the top of the participant list
        for _ in range(num_participants):
            pressKey('UP')
            time.sleep(0.005)
            releaseKey('UP')
            time.sleep(0.005)

        # Navigate to the participant with the smallest gap
        for _ in range(current_focus_position - 1):
            pressKey('DOWN')
            time.sleep(0.005)
            releaseKey('DOWN')
            time.sleep(0.005)

        # Confirm selection
        pressKey('ENTER')
        time.sleep(0.005)
        releaseKey('ENTER')
        

    # Update the last focus position
    last_focus_position = current_focus_position


def populate_grid_from_df(grid, df, race_control_panel, current_focus_position, auto_director_enabled, track_length):
    """Populate wxPython grid dynamically with scores_dict merged if available."""
    with data_lock:
        if df is None or df.empty:
            #print("Dataframe 'df' is empty or not available. Skipping grid population.")
            return

        # Attempt to merge scores_dict if available
        if scores_dict:
            try:
                # Convert scores_dict to a DataFrame
                scores_df = pd.DataFrame.from_dict(scores_dict, orient="index")
                scores_df.index.name = "Participant Index"
                df.index.name = "Participant Index"

                # Align indices of both DataFrames before joining
                scores_df = scores_df.reindex(df.index, fill_value=0)

                # Merge scores into the main DataFrame
                df = df.join(scores_df, how="left")
            except Exception as e:
                #print(f"Error merging scores_dict: {e}")
                #print("Continuing with original DataFrame.")
                return

        # Filter out rows where the driver is not active
        if "Is Active" in df.columns:
            df = df[df["Is Active"] == True]

        # Check if the DataFrame is still valid
        if df.empty:
            #print("No active participants to display. Skipping grid population.")
            return

        # Round numerical values for cleaner display
        df = df.apply(lambda col: col.map(lambda x: round(x, 1) if isinstance(x, (int, float)) else x))

        # Check if the grid needs to be reinitialized (different columns or rows)
        current_cols = grid.GetNumberCols()
        current_rows = grid.GetNumberRows()

        # Reset the grid if the structure does not match
        if current_cols != df.shape[1] or current_rows != df.shape[0]:
            if current_cols > 0:
                grid.DeleteCols(0, current_cols, True)
            if current_rows > 0:
                grid.DeleteRows(0, current_rows, True)
            grid.AppendCols(df.shape[1])
            grid.AppendRows(df.shape[0])

            # Set new column headers
            for col_index, column_name in enumerate(df.columns):
                grid.SetColLabelValue(col_index, column_name)

        # Populate the grid with data
        for row_index in range(df.shape[0]):
            for col_index in range(df.shape[1]):
                value = df.iloc[row_index, col_index]
                grid.SetCellValue(row_index, col_index, str(value) if pd.notnull(value) else "N/A")

                # Style alternating rows
                grid.SetCellBackgroundColour(
                    row_index, col_index,
                    wx.Colour(0, 0, 0) if row_index % 2 == 0 else wx.Colour(64, 64, 64)
                )

        grid.SetDefaultCellTextColour(wx.Colour(255, 255, 255))  # White text
        grid.ForceRefresh()

        # Update race control information
        current_focus = "None" if current_focus_position is None else f"Race Position {current_focus_position}"
        track_length_display = f"{track_length:.1f} meters" if track_length is not None else "Updating..."
        race_control_panel.SetLabel(
            f"Current Focus: {current_focus}\n"
            f"Auto Director: {'ENABLED' if auto_director_enabled else 'DISABLED'}\n"
            f"Track Length: {track_length_display}\n"
            f"Ensure AMS2 is in focus and any driver clicked,\n"
            f"then press Space to toggle Auto Director.\n"
        )



# Start wxPython GUI in a separate thread
def start_wx_app():
    # Enable high DPI support for Windows
    if hasattr(wx, "EnableHighDPIAwareness"):
        wx.EnableHighDPIAwareness()

    app = wx.App(False)
    
    # Additional DPI settings for Windows
    if os.name == 'nt':  # Check if the OS is Windows
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # Set process DPI awareness to System-DPI aware
        except Exception as e:
            print(f"Failed to set DPI awareness: {e}")
    
    frame = wx.Frame(None, title="Race Leaderboard")
    panel = wx.Panel(frame)
    panel.SetBackgroundColour(wx.Colour(0, 0, 0))  # Black background for the panel
    vbox = wx.BoxSizer(wx.VERTICAL)

    # Race Control Information
    race_control_panel = wx.StaticText(panel, label="Waiting for Packets or Shared Memory. Track Info packet occurs at start and about every 1 min thereafter if UDP")
    race_control_panel.SetForegroundColour(wx.Colour(255, 255, 255))
    race_control_panel.SetBackgroundColour(wx.Colour(0, 0, 0))
    race_control_panel.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

    # Vertical box for controls
    vbox_controls = wx.BoxSizer(wx.VERTICAL)

    # Add controls for each variable
    def add_control(label_text, global_var_name, increment, decrement):
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, label=f"{label_text}: {globals()[global_var_name]}")
        label.SetForegroundColour(wx.Colour(255, 255, 255))
        btn_up = wx.Button(panel, label="▲", size=(30, 30))
        btn_down = wx.Button(panel, label="▼", size=(30, 30))

        def on_up(event):
            globals()[global_var_name] += increment
            label.SetLabel(f"{label_text}: {globals()[global_var_name]}")

        def on_down(event):
            globals()[global_var_name] -= decrement
            label.SetLabel(f"{label_text}: {globals()[global_var_name]}")

        btn_up.Bind(wx.EVT_BUTTON, on_up)
        btn_down.Bind(wx.EVT_BUTTON, on_down)

        hbox.Add(label, 1, wx.EXPAND | wx.ALL, border=5)
        hbox.Add(btn_up, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        hbox.Add(btn_down, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
        vbox_controls.Add(hbox, 0, wx.EXPAND | wx.ALL, border=5)

    # Add individual controls
    add_control("Auto Director Interval", "AUTO_DIRECTOR_INTERVAL", 1, 1)
    add_control("Race Position Bonus Factor", "RACE_POSITION_BONUS_FACTOR", 1, 1)
    add_control("Pit Mode Penalty", "PIT_MODE_PENALTY_MULTIPLIER", 1, 1)
    add_control("Speed Penalty", "SPEED_PENALTY_MULTIPLIER", 1, 1)
    add_control("Leader Cars Ahead Multiplier", "LEADER_CARS_AHEAD_MULTIPLIER", 1, 1)
    add_control("Other Cars Ahead Multiplier", "OTHER_CARS_AHEAD_MULTIPLIER", 1, 1)
    add_control("Close Racing Max Gap", "CLOSE_RACING_MAX_GAP", 5, 5)

    # Create a horizontal box to combine race control info and controls
    hbox_top_controls = wx.BoxSizer(wx.HORIZONTAL)
    hbox_top_controls.Add(race_control_panel, 1, wx.EXPAND | wx.ALL, border=5)
    hbox_top_controls.Add(vbox_controls, 0, wx.ALIGN_TOP | wx.ALL, border=5)

    # Grid for displaying the leaderboard
    grid = gridlib.Grid(panel)
    grid.CreateGrid(0, 0)

    grid.EnableGridLines(True)
    grid.SetGridLineColour(wx.Colour(128, 128, 128))
    grid.SetColMinimalAcceptableWidth(5)
    grid.SetRowLabelSize(0)
    grid.SetBackgroundColour(wx.Colour(0, 0, 0))
    grid.SetDefaultCellBackgroundColour(wx.Colour(0, 0, 0))
    grid.SetLabelBackgroundColour(wx.Colour(0, 0, 0))
    grid.SetLabelTextColour(wx.Colour(128, 0, 128))
    grid.SetDefaultCellTextColour(wx.Colour(255, 255, 255))

    vbox.Add(hbox_top_controls, flag=wx.EXPAND | wx.ALL, border=10)
    vbox.Add(grid, 1, wx.EXPAND | wx.ALL, border=10)

    panel.SetSizer(vbox)
    frame.SetBackgroundColour(wx.Colour(0, 0, 0))
    frame.SetSize((1000, 600))
    frame.Show()

    def on_close(event):
        frame.Destroy()
        os._exit(0)

    frame.Bind(wx.EVT_CLOSE, on_close)

    global wx_grid, wx_race_control_panel
    wx_grid = grid
    wx_race_control_panel = race_control_panel

    app.MainLoop()



def update_auto_director_interval(value):
    global AUTO_DIRECTOR_INTERVAL, auto_director_enabled
    try:
        AUTO_DIRECTOR_INTERVAL = int(value)
        auto_director_enabled = False  # Disable auto director when updating the interval
        wx_race_control_panel.SetLabel(f"Auto Director Interval set to {AUTO_DIRECTOR_INTERVAL} seconds")
    except ValueError:
        wx_race_control_panel.SetLabel("Invalid input for interval. Please enter an integer value.")

def update_race_position_bonus_factor(value):
    global RACE_POSITION_BONUS_FACTOR, auto_director_enabled
    try:
        RACE_POSITION_BONUS_FACTOR = int(value)
        auto_director_enabled = False  # Disable auto director when updating the bonus factor
        wx_race_control_panel.SetLabel(f"Race Position Bonus Factor set to {RACE_POSITION_BONUS_FACTOR}")
    except ValueError:
        wx_race_control_panel.SetLabel("Invalid input for bonus factor. Please enter an integer value.")

# Function to listen for UDP packets in a separate thread
def listen_udp():
    print(f"Attempting to listen for UDP packets on port {UDP_PORT}. Press 'Esc' to stop.")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Attempt to bind the socket to the specified port
        sock.bind(("", UDP_PORT))
        print(f"Listening for UDP packets on port {UDP_PORT}.")

        while True:
            # Receive UDP packet
            data, addr = sock.recvfrom(BUFFER_SIZE)
            packet_size = len(data)

            # Add packet to buffer
            add_packet_to_buffer(data, packet_size)

    except KeyboardInterrupt:
        print("Stopped listening.")
    except Exception as e:
        print(f"Error during UDP listening: {e}")
    finally:
        sock.close()
        print("Socket closed.")
        print(f"Error: UDP port {UDP_PORT} is already in use. Please choose a different port.")

# Function to add a packet to the buffer, ensuring at least one packet is retained
def add_packet_to_buffer(packet_data, packet_size):
    packet_type = REQUIRED_PACKET_TYPES.get(packet_size, None)
    if packet_type:
        # If the buffer already has one packet, remove the oldest one (but retain at least one)
        while len(packet_buffer[packet_type]) > 1:
            packet_buffer[packet_type].popleft()  # Remove the oldest packet
        # Add the new packet to the buffer
        packet_buffer[packet_type].append(packet_data)

# Start the wxPython GUI thread
wx_thread = threading.Thread(target=start_wx_app)
wx_thread.start()

# Start the UDP listener in a separate thread
if mode == "1":
    udp_thread = threading.Thread(target=listen_udp, daemon=True)
    udp_thread.start()
    
# Main logic loop for updating the console and wxPython grid
# Main logic loop
try:
    while True:
        current_time = time.time()

        if mode == "1":  # UDP Mode
            # Check and debug packet buffers every second
            if current_time - last_UDP_read_time >= 1.0:
                #debug_packet_buffer()  # Print the current state of the buffers
                process_packets()      # Process packets if all are available
                last_UDP_read_time = current_time

        elif mode == "2":  # Shared Memory Mode
            # Check shared memory every 200ms
            if current_time - last_shared_memory_read_time >= 0.2:
                data = read_shared_memory()
                if data is not None:
                    update_participants_data_dict(data, participants_data_dict)
                last_shared_memory_read_time = current_time

        # Update leaderboard display every UPDATE_INTERVAL seconds
        if current_time - last_update_time >= UPDATE_INTERVAL:
            df = pd.DataFrame(participants_data_dict).transpose()

            # Sort the DataFrame by race position
            if 'Race Position' in df.columns:
                df = df.sort_values(by='Race Position', ascending=True)

            # Update wxPython grid
            if df is not None and 'wx_grid' in globals():
                wx.CallAfter(
                    populate_grid_from_df,
                    wx_grid,
                    df,
                    wx_race_control_panel,
                    current_focus_position,
                    auto_director_enabled,
                    track_length if track_length else 0,
                )

            # Perform next focus calculation
            if df is not None:
                next_focus(df)

            last_update_time = current_time

        # Perform auto-director action if enabled and the interval has passed
        if auto_director_enabled and current_time - last_director_time >= AUTO_DIRECTOR_INTERVAL:
            auto_director()
            last_director_time = current_time

        # Toggle auto-director and dev mode with keyboard shortcuts
        if keyboard.is_pressed('space'):
            auto_director_enabled = not auto_director_enabled
            current_focus_position = None  # Reset focus
            time.sleep(0.5)

        # Add a small sleep to reduce CPU usage
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Stopped main loop.")
except Exception as e:
    print(f"Error in main loop: {e}")
    traceback.print_exc()
