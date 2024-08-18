# Automobilista-2-Auto-Director
An auto director for AMS2 in python using UDP or AMS2 shared memory
This is a simplified Auto director that does not rely on Simhub, and uses UDP or Shared Memory.
It tracks the smallest gap and the rate of change, selecting those most likely to be racing to be in view.
It has customisable Race Position bonus.
It has customisable camera dwell.
Usage is simple:


    Start the Auto director,
    Select UDP or Shared memory.
    Select UDP port if selected.
    Enter Camera Dwell time.
    Enter Race Position Bonus.
    Click on a racer, in AMS2 leaderboard
    Press space to start Auto directing.
    The program presses up, down and enter for you to select cameras
    Press space to stop Auto directing.
<img width="615" alt="Auto Director UI" src="https://github.com/user-attachments/assets/cf658850-1328-43b5-bdab-05311b104682">

This is what chatGPT says this is, it should know, it wrote it.
# AMS2 Auto Director and Leaderboard
# Overview

This project is a custom auto-director and leaderboard system for Automobilista 2 (AMS2) racing simulator. It allows for dynamic control of the camera focus during races based on the participants' performance metrics, such as speed, gap to the next player, and racing position. The system supports both UDP data streaming and shared memory for real-time data acquisition from AMS2.
Features

    Auto Director: Automatically switches camera focus to participants with the most interesting race metrics, such as close racing gaps or significant changes in position.
    Leaderboard Display: Real-time leaderboard that displays essential race statistics like race position, lap times, speed, and gap to the player ahead.
    Data Source Flexibility: Supports both UDP and shared memory for data collection, allowing flexibility depending on your setup.
    Customizable Intervals: Adjustable intervals for camera changes and race position bonuses.
    GUI Interface: A wxPython-based graphical user interface (GUI) for real-time monitoring and control, including a grid to display the leaderboard and control elements to adjust settings on the fly.
    Rich Console Integration: Uses the Rich library to provide a visually appealing console output with tables and panels for in-depth race data.
    Dev Mode: A developer mode that can be toggled with a key combination (Ctrl+X), enabling or disabling additional console outputs.

# Usage

    Start the Application
        Launch the executable file to start the application.
        Upon running the application, you'll be prompted to select the data source:
            1 for UDP
            2 for Shared Memory
        After selecting the data source, you can configure the interval between camera changes and the race position bonus factor.

    Monitor the Race
        The auto director will dynamically focus on the most interesting participant in the race based on the calculated metrics.
        The leaderboard will be updated in real-time both in the GUI and optionally in the console (if dev mode is enabled).

    Adjust Settings On-The-Fly
        Use the wxPython GUI to adjust the auto director interval and race position bonus factor during the race.
        Toggle auto-director functionality with the spacebar.
        Enable or disable developer mode with Ctrl+X.

    Exit the Application
        Press ESC to exit the application safely.


Project Structure

    main.exe: The main executable that initializes the auto-director and leaderboard system.
    
Key Components
Main Logic Loop

    Data Handling: Handles data acquisition from AMS2 through either UDP or shared memory.
    Leaderboard Update: Processes the data and updates the leaderboard with real-time statistics.
    Auto Director: Automatically shifts the camera focus based on calculated metrics.

wxPython GUI

    Grid Display: Shows the leaderboard with real-time updates.
    Control Panel: Allows users to adjust key parameters like the auto-director interval and race position bonus factor.

Rich Console Integration

    Enhanced Display: Uses the Rich library to display race data in a visually appealing manner in the console, when CTRL-X Pressed

Troubleshooting

    Shared Memory Issues: Make sure AMS2 is running and correctly configured to share data via shared memory. Replay, and driver offer Shared memory
    UDP Issues: Make sure AMS2 is setup for UDP sharing in Project Cars 2 with a UDP frequency of 3. Using UDP only one program can access the port, so check if Simhub is using UDP too.
    GUI Display Problems: If the wxPython window appears incorrect, ensure your system supports wxPython and consider running the script in a standard desktop environment.

Contributing

Contributions are welcome! Please fork the repository and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.
License

This project is licensed under the CC0 1.0 Universal (CC0 1.0) Public Domain Dedication. See the LICENSE file for details.
Acknowledgments

    AMS2 Community: For the support and shared knowledge about accessing and utilizing AMS2's telemetry data.
    Rich Library: For providing an amazing library to enhance console output.
    wxPython: For enabling easy GUI development in Python.

By using this software, you acknowledge that it is provided "as is" without warranty of any kind, express or implied. Use at your own risk.
