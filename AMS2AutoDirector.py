import socket
import struct
import os
import pandas as pd
import keyboard
import time
from shared_memory_struct import SharedMemory, SHARED_MEMORY_VERSION
from collections import deque
from pyKey import pressKey, releaseKey
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
import ctypes
import mmap
import wx
import wx.grid as gridlib
import threading
import traceback

# Initialize the Rich console
console = Console()

# Threading locks
data_lock = threading.Lock()

# User choice between UDP and Shared Memory
mode = None
while mode not in ["1", "2"]:
    mode = input("Select data source:\n1. UDP\n2. Shared Memory\nEnter 1 or 2: ").strip()

# Prompt for the interval between camera changes in seconds
camera_change_interval_input = input("Enter the interval between camera changes in seconds (press Enter for default 5): ")

# Set the camera change interval based on user input, or use the default if none is provided
AUTO_DIRECTOR_INTERVAL = int(camera_change_interval_input) if camera_change_interval_input.strip() else 5

# Prompt for the race position bonus factor
race_position_bonus_input = input("Enter the race position bonus factor, lower is more bonus (press Enter for default 10): ")

# Set the race position bonus factor based on user input, or use the default if none is provided
RACE_POSITION_BONUS_FACTOR = int(race_position_bonus_input) if race_position_bonus_input.strip() else 10

# Set up for the selected mode
if mode == "1":
    # Prompt the user to enter the port number or press Enter for the default
    port_input = input("Enter UDP port to listen on (press Enter for default 5606): ")
    # Set the UDP port based on user input, or use the default if none is provided
    UDP_PORT = int(port_input) if port_input.strip() else 5606

# Set score history record
score_history = {i: deque(maxlen=20) for i in range(32)}

# Initialize variables
BUFFER_SIZE = 1500
PACKET_SIZE_LEADERBOARD = 1040
PACKET_SIZE_EXTENDED = 1063
PACKET_SIZE_TRACK_INFO = 308
SAMPLE_PERIOD = 15  # Number of samples to average
UPDATE_INTERVAL = 1  # Update screen every 1 second
SCREEN_CLEAR_INTERVAL = 15  # Clear screen every 15 seconds to handle potential aberrations

# Initialize dictionaries to store participants' data and track length
participants_data_dict = {i: {} for i in range(32)}
previous_data_dict = {i: {'distances': deque(maxlen=SAMPLE_PERIOD), 'timestamps': deque(maxlen=SAMPLE_PERIOD)} for i in range(32)}
gap_history = {i: deque(maxlen=SAMPLE_PERIOD) for i in range(32)}  # New: to store gap history
track_length = None
last_update_time = time.time()
last_director_time = time.time()
last_screen_clear_time = time.time()
last_shared_memory_read_time = time.time()  # Add this to track the last shared memory read time


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
        print(f"Error reading shared memory: {e}")
        return None

def update_participants_data_dict(data):
    global track_length
    current_timestamp = time.time()
    track_length = data.mTrackLength  # Update track length from shared memory
    
    for i in range(32):  # Assuming there can be up to 32 participants
        if data.mParticipantInfo[i].mIsActive:
            participant_data = {
                "Race Position": data.mParticipantInfo[i].mRacePosition,
                "Is Active": data.mParticipantInfo[i].mIsActive,
                "Lap Distance": data.mParticipantInfo[i].mCurrentLapDistance,
                "Current Sector": data.mParticipantInfo[i].mCurrentSector,
                "Current Lap": data.mParticipantInfo[i].mLapsCompleted,
                "FastestLapTime": data.mFastestLapTimes[i],  # Extract fastest lap time for participant i
                "LastLapTime": data.mLastLapTimes[i],  # Extract last lap time for participant i
            }

            # Add current distance and timestamp to deque
            previous_data_dict[i]['distances'].append(data.mParticipantInfo[i].mCurrentLapDistance)
            previous_data_dict[i]['timestamps'].append(current_timestamp)

            # Calculate speed over the sample period
            if len(previous_data_dict[i]['distances']) > 1:
                total_distance = previous_data_dict[i]['distances'][-1] - previous_data_dict[i]['distances'][0]
                total_time = previous_data_dict[i]['timestamps'][-1] - previous_data_dict[i]['timestamps'][0]
                speed = total_distance / total_time if total_time > 0 else 0
            else:
                speed = 0  # Not enough data to calculate speed yet

            participant_data['Speed'] = speed

            # Calculate true distance traveled
            if track_length is not None:
                if data.mParticipantInfo[i].mLapsCompleted > 0:
                    true_distance_traveled = (data.mParticipantInfo[i].mLapsCompleted - 1) * track_length + data.mParticipantInfo[i].mCurrentLapDistance
                else:
                    true_distance_traveled = data.mParticipantInfo[i].mCurrentLapDistance
            else:
                true_distance_traveled = None

            participant_data['True Distance Traveled'] = true_distance_traveled

            # Update the participant's data in the dictionary
            participants_data_dict[i].update(participant_data)

def decode_leaderboard_packet(data):
    """Decode the 1040-byte leaderboard packet."""
    participant_stats_offsets = {
        "FastestLapTime": (0, 4, 'f'),
        "LastLapTime": (4, 8, 'f'),
        "LastSectorTime": (8, 12, 'f'),
        "FastestSector1Time": (12, 16, 'f'),
        "FastestSector2Time": (16, 20, 'f'),
        "FastestSector3Time": (20, 24, 'f'),
    }

    for i in range(32):  # 32 participants
        base_offset = 16 + i * 32  # Starting offset for each participant's data
        participant_data = {}
        for key, (start, end, fmt) in participant_stats_offsets.items():
            raw_bytes = data[base_offset + start: base_offset + end]
            if fmt == 'f':  # float
                value = struct.unpack('f', raw_bytes)[0]
            participant_data[key] = value
        
        # Update the participant's data in the dictionary
        participants_data_dict[i].update(participant_data)

def decode_extended_packet(data):
    """Decode the 1063-byte extended packet."""
    current_timestamp = time.time()
    
    for i in range(32):
        race_position_offset = 31 + i * 32 + 16  # Offset to the sRacePosition byte
        lap_distance_offset = 31 + i * 32 + 14  # Offset to the CurrentLapDistance bytes
        current_sector_offset = 31 + i * 32 + 17  # Offset to the CurrentSector byte
        current_lap_offset = 31 + i * 32 + 23  # Offset to the CurrentLap byte

        # Extract race position and active status
        race_position, is_active = parse_race_position(data[race_position_offset])
        # Extract lap distance
        lap_distance = parse_lap_distance(data, lap_distance_offset)
        # Extract current sector
        current_sector = parse_current_sector(data[current_sector_offset])
        # Extract current lap
        current_lap = parse_current_lap(data[current_lap_offset])

        # Add current distance and timestamp to deque
        previous_data_dict[i]['distances'].append(lap_distance)
        previous_data_dict[i]['timestamps'].append(current_timestamp)

        # Calculate speed over the sample period
        if len(previous_data_dict[i]['distances']) > 1:
            total_distance = previous_data_dict[i]['distances'][-1] - previous_data_dict[i]['distances'][0]
            total_time = previous_data_dict[i]['timestamps'][-1] - previous_data_dict[i]['timestamps'][0]
            speed = total_distance / total_time if total_time > 0 else 0
        else:
            speed = 0  # Not enough data to calculate speed yet

        # Calculate true distance traveled
        if track_length is not None:
            if current_lap > 0:
                true_distance_traveled = (current_lap - 1) * track_length + lap_distance
            else:
                true_distance_traveled = lap_distance
        else:
            true_distance_traveled = None

        # Update the participant's data in the dictionary
        participants_data_dict[i].update({
            'Race Position': race_position,
            'Is Active': is_active,
            'Lap Distance': lap_distance,
            'Current Sector': current_sector,
            'Current Lap': current_lap,
            'Speed': speed,
            'True Distance Traveled': true_distance_traveled
        })

def decode_track_info_packet(data):
    """Decode the 308-byte track info packet to obtain track length."""
    global track_length
    track_length_offset = 44  # Offset to the sTrackLength field
    track_length = struct.unpack('f', data[track_length_offset:track_length_offset + 4])[0]

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

def display_leaderboard():
    """Display the leaderboard with the combined data, sorted by Race Position."""
    global current_focus_position  # Make current_focus_position a global variable
    global last_screen_clear_time
    global score_history  # Use the score_history from next_focus

    df = pd.DataFrame(participants_data_dict).transpose()

    # Check if the 'Is Active' column exists
    if 'Is Active' in df.columns:
        # Filter out inactive participants
        df = df[df['Is Active'] == True]

        # Sort by Race Position
        df = df.sort_values(by='Race Position', ascending=True)

        # Calculate gap to player ahead and convert it to a positive value
        df['Gap to Player Ahead'] = None  # Initialize the column with None
        for i in range(1, len(df)):
            if df.iloc[i]['True Distance Traveled'] is not None and df.iloc[i-1]['True Distance Traveled'] is not None:
                distance_gap = abs(df.iloc[i]['True Distance Traveled'] - df.iloc[i-1]['True Distance Traveled'])
                df.at[df.index[i], 'Gap to Player Ahead'] = distance_gap

        # Set the gap for the race leader (position 1) to None
        df.at[df.index[0], 'Gap to Player Ahead'] = None

        # Ensure all expected columns are present in the DataFrame and round them appropriately
        rounding_map = {
            'FastestLapTime': 2,
            'LastLapTime': 2,
            'Speed': 2,
            'True Distance Traveled': 1,
            'Gap to Player Ahead': 1,
            'Rolling Score': 2
        }

        for column, decimals in rounding_map.items():
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors='coerce').round(decimals)
            else:
                df[column] = None  # Use None instead of a string to represent missing values

        # Calculate and display the rolling scores
        df['Rolling Score'] = df.index.map(lambda i: sum(score_history[i]) if i in score_history else 0)

        # Round 'Rolling Score' after calculating it
        df['Rolling Score'] = df['Rolling Score'].round(2)

        # Now that we have used 'Lap Distance' for calculations, we can safely drop it
        df = df.drop(columns=['Lap Distance'])

        # Create a Rich Table to display the leaderboard
        table = Table(title="Leaderboard", show_header=True, header_style="bold magenta")
        table.add_column("Race Position", justify="center")
        table.add_column("Fastest Lap Time", justify="right")
        table.add_column("Last Lap Time", justify="right")
        table.add_column("Speed", justify="right")
        table.add_column("Current Sector", justify="center")
        table.add_column("Current Lap", justify="center")
        table.add_column("True Distance Traveled", justify="right")
        table.add_column("Gap to Player Ahead", justify="right")
        table.add_column("Rolling Score", justify="right")  # New column for rolling scores

        for _, row in df.iterrows():
            table.add_row(
                str(int(row['Race Position'])),
                f"{row['FastestLapTime']:.2f}" if pd.notnull(row['FastestLapTime']) else "N/A",
                f"{row['LastLapTime']:.2f}" if pd.notnull(row['LastLapTime']) else "N/A",
                f"{row['Speed']:.2f}" if pd.notnull(row['Speed']) else "N/A",
                str(int(row['Current Sector'])),
                str(int(row['Current Lap'])),
                f"{row['True Distance Traveled']:.1f}" if pd.notnull(row['True Distance Traveled']) else "N/A",
                f"{row['Gap to Player Ahead']:.1f}" if pd.notnull(row['Gap to Player Ahead']) else "N/A",
                f"{row['Rolling Score']:.2f}" if pd.notnull(row['Rolling Score']) else "N/A"
            )

        # Safely handle the track length display
        track_length_display = f"{track_length:.1f} meters" if track_length is not None else "Updating... Auto Director won't work until Track length is broadcast."

        # Create the panel for race control info including track length
        control_panel = Panel.fit(
            f"Current Focus: {'None' if current_focus_position is None else f'Race Position {current_focus_position}'}\n"
            f"Auto Director is {'ENABLED' if auto_director_enabled else 'DISABLED'} (Press SPACE to toggle)\n"
            f"Track Length: {track_length_display}",
            title="Race Control",
            border_style="green",
        )

        # Combine the panel and table into a single layout
        combined_layout = Table.grid(expand=True)
        combined_layout.add_row(control_panel)
        combined_layout.add_row(table)

        # Periodic screen refresh logic
        current_time = time.time()
        if current_time - last_screen_clear_time >= SCREEN_CLEAR_INTERVAL:
            console.clear()
            last_screen_clear_time = current_time

        return combined_layout, df  # Return the combined layout and the DataFrame

    return None, None  # Return None if df['Is Active'] doesn't exist or no data is available



def next_focus(df):
    """Continuously track rate of change and determine the next focus based on accumulated scores."""
    global current_focus_position
    
    # Sort by Race Position
    df = df.sort_values(by='Race Position', ascending=True)

    # Calculate the gap and update the history for each participant
    df['Gap to Player Ahead'] = pd.to_numeric(df['Gap to Player Ahead'], errors='coerce')
    
    # Update gap history for each participant
    for i, row in df.iterrows():
        gap_history[i].append(row['Gap to Player Ahead'])

    # Calculate the rate of change of the gap for each participant
    rate_of_change = []
    for i, row in df.iterrows():
        if len(gap_history[i]) > 1:
            # Calculate rate of change as the difference between the most recent and the oldest stored gap
            roc = (gap_history[i][-1] - gap_history[i][0]) / (len(gap_history[i]) - 1)
        else:
            roc = None  # Not enough data to calculate rate of change
        rate_of_change.append(roc)
    
    df['Rate of Change'] = rate_of_change

    # Filter out participants where Rate of Change is None, Gap is zero, or Race Position is 1
    df_filtered = df.dropna(subset=['Rate of Change'])
    df_filtered = df_filtered[(df_filtered['Gap to Player Ahead'] > 0) & (df_filtered['Race Position'] != 1)]

    # Calculate a close racing bonus: (10 - Gap)/10, but only if Gap <= 10
    df_filtered['Close Racing Bonus'] = df_filtered['Gap to Player Ahead'].apply(lambda gap: (10 - gap) / 10 if gap <= 10 else 0)

    # Calculate a race position bonus: higher positions (closer to 1st place) get a higher bonus
    # The bonus is calculated as 1 / (Race Position)
    def calculate_race_position_bonus(pos):
        try:
            if pos > 0:
                return 1 / (RACE_POSITION_BONUS_FACTOR * pos)
            else:
                return 0  # Return 0 or another default value if position is zero
        except ZeroDivisionError:
            return 0  # In case of any unexpected division by zero, return 0

    df_filtered['Race Position Bonus'] = df_filtered['Race Position'].apply(calculate_race_position_bonus)

    # Calculate the score based on the rate of change, gap size, close racing bonus, and race position bonus
    df_filtered['Score'] = (
        df_filtered['Rate of Change'].abs() / df_filtered['Gap to Player Ahead']
        - (df_filtered['Gap to Player Ahead'] / 300)
        + df_filtered['Close Racing Bonus']  # Add the close racing bonus to the score
        + df_filtered['Race Position Bonus']  # Add the race position bonus to the score
    )

    # Update the rolling score history for each participant
    for i, row in df_filtered.iterrows():
        score_history[i].append(row['Score'])

    # Calculate the accumulated score over the last 20 scores for each participant
    accumulated_scores = {i: sum(score_history[i]) for i in score_history if len(score_history[i]) > 0}

    if accumulated_scores:
        # Find the participant with the highest accumulated score
        highest_score_position = max(accumulated_scores, key=accumulated_scores.get)
        current_focus_position = df.loc[highest_score_position, 'Race Position']

        # Ensure that the leader (Race Position 1) is never selected
        if current_focus_position == 1:
            del accumulated_scores[highest_score_position]
            if accumulated_scores:
                highest_score_position = max(accumulated_scores, key=accumulated_scores.get)
                current_focus_position = df.loc[highest_score_position, 'Race Position']

def auto_director():
    """Automatically switch the camera to the participant with the smallest gap and highest rate of change."""
    global current_focus_position
    global last_focus_position  # Store the last selected position

    # Check if the current focus position is the same as the last one
    if current_focus_position == last_focus_position:
        return  # If the position hasn't changed, do nothing

    if current_focus_position is not None:
        # Simulate key presses to move focus to the desired position
        num_participants = len(participants_data_dict)

        # Move up to the top of the participant list
        for _ in range(num_participants):
            pressKey('UP')
            time.sleep(0.001)
            releaseKey('UP')

        # Navigate to the participant with the smallest gap
        for _ in range(current_focus_position - 1):
            pressKey('DOWN')
            time.sleep(0.001)
            releaseKey('DOWN')

        # Confirm selection
        pressKey('ENTER')
        time.sleep(0.003)
        releaseKey('ENTER')

    # Update the last focus position
    last_focus_position = current_focus_position

# Function to populate the wxPython grid while retaining styling
def populate_grid_from_df(grid, df, race_control_panel, current_focus_position, auto_director_enabled, track_length):
    """Populate the wxPython grid with data from the DataFrame, retaining the styling, and update race control info."""
    with data_lock:
        # Save current column widths
        column_widths = [grid.GetColSize(col_index) for col_index in range(grid.GetNumberCols())]

        # Clear the grid and set the number of rows and columns
        grid.ClearGrid()
        grid.AppendRows(df.shape[0] - grid.GetNumberRows())
        grid.AppendCols(df.shape[1] - grid.GetNumberCols())

        # Set the column headers with purple text
        for col_index, column_name in enumerate(df.columns):
            grid.SetColLabelValue(col_index, column_name)
        grid.SetLabelTextColour(wx.Colour(128, 0, 128))  # Purple header text
        grid.SetLabelBackgroundColour(wx.Colour(0, 0, 0))  # Black background for headers

        # Populate the grid with data and retain styling
        for row_index in range(df.shape[0]):
            for col_index in range(df.shape[1]):
                grid.SetCellValue(row_index, col_index, str(df.iloc[row_index, col_index]))

                # Style alternating rows
                if row_index % 2 == 0:
                    grid.SetCellBackgroundColour(row_index, col_index, wx.Colour(0, 0, 0))  # Black for even rows
                else:
                    grid.SetCellBackgroundColour(row_index, col_index, wx.Colour(64, 64, 64))  # Dark grey for odd rows

        grid.SetDefaultCellTextColour(wx.Colour(255, 255, 255))  # White text for all cells

        # Reapply the saved column widths
        for col_index, width in enumerate(column_widths):
            if col_index < grid.GetNumberCols():
                grid.SetColSize(col_index, width)

        grid.ForceRefresh()  # Apply changes immediately

        # Update race control information
        current_focus = "None" if current_focus_position is None else f"Race Position {current_focus_position}"
        track_length_display = f"{track_length:.1f} meters" if track_length is not None else "Updating..."

        # Update the race control panel label with additional text for space toggle
        race_control_panel.SetLabel(
            f"Current Focus: {current_focus}\n"
            f"Auto Director: {'ENABLED' if auto_director_enabled else 'DISABLED'}\n"
            f"Track Length: {track_length_display}\n"
            f"Ensure AMS2 is in focus and racer clicked,\n"
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
    race_control_panel = wx.StaticText(panel, label="Press space to toggle Auto Director")
    race_control_panel.SetForegroundColour(wx.Colour(255, 255, 255))  # White text
    race_control_panel.SetBackgroundColour(wx.Colour(0, 0, 0))  # Black background
    race_control_panel.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

    # Vertical box for the controls to the right of Race Control
    vbox_controls = wx.BoxSizer(wx.VERTICAL)

    # Buttons and labels for AUTO_DIRECTOR_INTERVAL
    hbox_ad_interval = wx.BoxSizer(wx.HORIZONTAL)
    label_ad_interval = wx.StaticText(panel, label=f"AUTO_DIRECTOR_INTERVAL: {AUTO_DIRECTOR_INTERVAL}")
    label_ad_interval.SetForegroundColour(wx.Colour(255, 255, 255))
    btn_ad_interval_up = wx.Button(panel, label="▲", size=(30, 30))
    btn_ad_interval_down = wx.Button(panel, label="▼", size=(30, 30))

    # Buttons and labels for RACE_POSITION_BONUS_FACTOR
    hbox_race_bonus = wx.BoxSizer(wx.HORIZONTAL)
    label_race_bonus = wx.StaticText(panel, label=f"RACE_POSITION_BONUS_FACTOR: {RACE_POSITION_BONUS_FACTOR}")
    label_race_bonus.SetForegroundColour(wx.Colour(255, 255, 255))
    btn_race_bonus_up = wx.Button(panel, label="▲", size=(30, 30))
    btn_race_bonus_down = wx.Button(panel, label="▼", size=(30, 30))

    # Define button click event handlers
    def on_ad_interval_up(event):
        global AUTO_DIRECTOR_INTERVAL, auto_director_enabled
        auto_director_enabled = False  # Disable auto director when adjusting values
        AUTO_DIRECTOR_INTERVAL += 1
        label_ad_interval.SetLabel(f"AUTO_DIRECTOR_INTERVAL: {AUTO_DIRECTOR_INTERVAL}")

    def on_ad_interval_down(event):
        global AUTO_DIRECTOR_INTERVAL, auto_director_enabled
        auto_director_enabled = False  # Disable auto director when adjusting values
        if AUTO_DIRECTOR_INTERVAL > 1:
            AUTO_DIRECTOR_INTERVAL -= 1
            label_ad_interval.SetLabel(f"AUTO_DIRECTOR_INTERVAL: {AUTO_DIRECTOR_INTERVAL}")

    def on_race_bonus_up(event):
        global RACE_POSITION_BONUS_FACTOR, auto_director_enabled
        auto_director_enabled = False  # Disable auto director when adjusting values
        RACE_POSITION_BONUS_FACTOR += 1
        label_race_bonus.SetLabel(f"RACE_POSITION_BONUS_FACTOR: {RACE_POSITION_BONUS_FACTOR}")

    def on_race_bonus_down(event):
        global RACE_POSITION_BONUS_FACTOR, auto_director_enabled
        auto_director_enabled = False  # Disable auto director when adjusting values
        if RACE_POSITION_BONUS_FACTOR > 1:
            RACE_POSITION_BONUS_FACTOR -= 1
            label_race_bonus.SetLabel(f"RACE_POSITION_BONUS_FACTOR: {RACE_POSITION_BONUS_FACTOR}")

    # Bind the buttons to their respective event handlers
    btn_ad_interval_up.Bind(wx.EVT_BUTTON, on_ad_interval_up)
    btn_ad_interval_down.Bind(wx.EVT_BUTTON, on_ad_interval_down)
    btn_race_bonus_up.Bind(wx.EVT_BUTTON, on_race_bonus_up)
    btn_race_bonus_down.Bind(wx.EVT_BUTTON, on_race_bonus_down)

    # Arrange the AUTO_DIRECTOR_INTERVAL controls horizontally
    hbox_ad_interval.Add(label_ad_interval, 1, wx.EXPAND | wx.ALL, border=5)
    hbox_ad_interval.Add(btn_ad_interval_up, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
    hbox_ad_interval.Add(btn_ad_interval_down, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

    # Arrange the RACE_POSITION_BONUS_FACTOR controls horizontally
    hbox_race_bonus.Add(label_race_bonus, 1, wx.EXPAND | wx.ALL, border=5)
    hbox_race_bonus.Add(btn_race_bonus_up, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)
    hbox_race_bonus.Add(btn_race_bonus_down, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, border=5)

    # Add the controls to the vertical box sizer
    vbox_controls.Add(hbox_ad_interval, 0, wx.EXPAND | wx.ALL, border=5)
    vbox_controls.Add(hbox_race_bonus, 0, wx.EXPAND | wx.ALL, border=5)

    # Create a horizontal box to combine race control info and controls
    hbox_top_controls = wx.BoxSizer(wx.HORIZONTAL)
    hbox_top_controls.Add(race_control_panel, 1, wx.EXPAND | wx.ALL, border=5)
    hbox_top_controls.Add(vbox_controls, 0, wx.ALIGN_TOP | wx.ALL, border=5)

    # Grid for displaying the leaderboard
    grid = gridlib.Grid(panel)
    grid.CreateGrid(0, 0)

    # Ensure grid lines are enabled and visible
    grid.EnableGridLines(True)
    grid.SetGridLineColour(wx.Colour(128, 128, 128))  # Set to a visible grey color

    # Ensure the left side outline of the first column is visible
    grid.SetColMinimalAcceptableWidth(5)  # Adjust if necessary
    grid.SetMargins(5, 5)

    # Set the initial grid styling
    grid.SetRowLabelSize(0)  # Hide row labels
    grid.SetBackgroundColour(wx.Colour(0, 0, 0))
    grid.SetDefaultCellBackgroundColour(wx.Colour(0, 0, 0))
    grid.SetLabelBackgroundColour(wx.Colour(0, 0, 0))  # Black background
    grid.SetLabelTextColour(wx.Colour(128, 0, 128))  # Purple header text
    grid.SetDefaultCellTextColour(wx.Colour(255, 255, 255))  # White text

    # Layout for the grid and top controls
    vbox.Add(hbox_top_controls, flag=wx.EXPAND | wx.ALL, border=10)
    vbox.Add(grid, 1, wx.EXPAND | wx.ALL, border=10)

    panel.SetSizer(vbox)
    frame.SetBackgroundColour(wx.Colour(0, 0, 0))  # Ensure the frame itself has a black background
    frame.SetSize((1000, 600))
    frame.Show()

    def on_close(event):
        print("Closing wxPython window...")
        frame.Destroy()  # Destroy the wxPython window
        os._exit(0)  # Terminate the whole script, including the console window, without error messages

    # Bind the close event to the on_close function
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




# Start the wxPython GUI thread
wx_thread = threading.Thread(target=start_wx_app)
wx_thread.start()

# Main logic loop for updating the console and the wxPython grid
with Live(console=console, refresh_per_second=2) as live:
    current_time = time.time()
    if mode == "1":
        # Setup UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", UDP_PORT))
        print(f"Listening for UDP packets on port {UDP_PORT}. Press 'Esc' to stop.")

    try:
        while True:
            if mode == "1":
                # UDP Mode: Receive data via UDP
                data, addr = sock.recvfrom(BUFFER_SIZE)
                packet_size = len(data)
                if packet_size == PACKET_SIZE_LEADERBOARD:
                    decode_leaderboard_packet(data)
                elif packet_size == PACKET_SIZE_EXTENDED:
                    decode_extended_packet(data)
                elif packet_size == PACKET_SIZE_TRACK_INFO:
                    decode_track_info_packet(data)

            elif mode == "2" and current_time - last_shared_memory_read_time >= 0.5:
                # Shared Memory Mode: Read data from shared memory (rate-limited to twice per second)
                data = read_shared_memory()
                if data is not None:
                    update_participants_data_dict(data)
                last_shared_memory_read_time = current_time  # Update the last read time

            # Update the leaderboard display every 1 second
            current_time = time.time()
            if current_time - last_update_time >= UPDATE_INTERVAL:
                combined_layout, df = display_leaderboard()
                if combined_layout is not None:
                    if dev_mode_enabled:
                        live.update(combined_layout)
                    if df is not None and 'wx_grid' in globals():
                        wx.CallAfter(populate_grid_from_df, wx_grid, df, wx_race_control_panel, current_focus_position, auto_director_enabled, track_length)  # Call wx update using wx.CallAfter to avoid threading issues
                last_update_time = current_time

                # Perform the next focus calculation with the updated DataFrame
                if df is not None:
                    next_focus(df)

            # Clear the screen periodically to avoid lingering artifacts
            if dev_mode_enabled and current_time - last_screen_clear_time >= SCREEN_CLEAR_INTERVAL:
                console.clear()
                last_screen_clear_time = current_time

            # Perform auto-director action only if it's enabled and the interval has passed
            if auto_director_enabled and current_time - last_director_time >= AUTO_DIRECTOR_INTERVAL:
                auto_director()
                last_director_time = current_time

            # Toggle auto-director with the space key
            if keyboard.is_pressed('space'):
                auto_director_enabled = not auto_director_enabled
                current_focus_position = None  # Reset focus when toggling auto-director
                time.sleep(0.5)  # Add a short delay to prevent rapid toggling

            # Toggle dev mode with Ctrl+X
            if keyboard.is_pressed('ctrl+x'):
                dev_mode_enabled = not dev_mode_enabled
                if dev_mode_enabled:
                    print("Dev mode enabled.")
                else:
                    print("Dev mode disabled.")
                time.sleep(0.5)  # Add a short delay to prevent rapid toggling

                # Add a small sleep to reduce CPU usage
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Stopped listening.")
    except Exception:
        print("An error occurred:")
        traceback.print_exc()
    finally:
        if mode == "1":
            sock.close()
            print("Socket closed.")
