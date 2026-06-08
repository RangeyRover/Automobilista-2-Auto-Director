# Feature Specification: HTML Configuration Options

**Feature Branch**: `019-html-config-options`  
**Created**: 2026-06-08  
**Status**: Draft  
**Input**: User description: "analyse the 2 most recently opened issues with a view to fixing them by making them configuration options in the html"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Leaderboard Interval Gaps Toggle (Priority: P1)

As a broadcast viewer or director, I want to toggle between displaying "Gap to Leader" and "Interval Gap" (gap to the car ahead) on the leaderboard overlays, so that I can monitor close battles more effectively.

**Why this priority**: High value for viewers as interval gaps are the standard mode of timing in professional motorsports broadcasts when cars are close on track.

**Independent Test**:
- Open the F1TV Overlay page.
- Open the timing leaderboard.
- Toggle the "Interval Gaps" setting checkbox in the overlay settings panel.
- Verify that the timing column changes from showing cumulative gap to leader (e.g., +1.2s, +2.5s) to showing interval gap to the car ahead (e.g., +1.2s, +1.3s).

**Acceptance Scenarios**:

1. **Given** the leaderboard is displaying gap to leader,  
   **When** the user checks the "Interval Gaps" option,  
   **Then** the first place driver continues to display "LEADER",  
   **And** every subsequent driver displays the time difference to the driver immediately ahead of them.
   
2. **Given** the user changes the setting on the control panel,  
   **When** the websocket updates,  
   **Then** the setting is synchronized and the overlay immediately updates its gap rendering.

---

### User Story 2 - Limit Auto-Camera Pools (Priority: P2)

As a broadcast director, I want to restrict the camera views used by the auto director to a custom subset (e.g., only Cockpit, Chase, and TV Cam), so that I can avoid undesirable camera angles during a broadcast.

**Why this priority**: Essential for broadcast quality control, allowing the director to exclude cameras that have poor visibility or setup.

**Independent Test**:
- Open the control panel HTML page.
- Select only specific cameras (e.g., Camera 1, 2, and 7) under the auto camera pool settings.
- Verify that the auto director only switches between the selected camera views.

**Acceptance Scenarios**:

1. **Given** a set of selected cameras in the settings,  
   **When** the auto director selects a new camera view,  
   **Then** it only selects from the checked camera numbers.

---

### User Story 3 - Disable Auto-Camera Switch Toggle (Priority: P3)

As a broadcast director, I want to temporarily disable auto-camera angle switching while keeping the auto director's driver tracking active, so that I can lock a specific camera angle (like the TV pod) while still tracking the battle.

**Why this priority**: Enables manual camera override while keeping the automatic driver-selection logic running.

**Independent Test**:
- Toggle the "Disable Auto Cam Switch" checkbox in the settings.
- Verify that the auto director continues to switch the viewed driver, but the camera angle does not change automatically.

**Acceptance Scenarios**:

1. **Given** "Disable Auto Cam Switch" is enabled,  
   **When** the auto director switches focus to another participant,  
   **Then** the target driver is updated, but the active camera angle remains unchanged.

---

### Edge Cases

- **No Cameras Selected**: If the user unchecks all cameras in the auto-camera pool, the system must fallback to all cameras enabled by default to prevent errors.
- **Lapped Drivers**: Interval gaps for lapped drivers must be formatted properly without showing negative values or extremely large timing gaps.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The F1TV Overlay and Control Panel MUST support an "Interval Gaps" setting that changes the leaderboard display from gap-to-leader to gap-to-car-ahead.
- **FR-002**: The interval gap calculation MUST be computed on the client side based on consecutive sorted leaderboard entries.
- **FR-003**: The Camera Controller MUST support an `enabled_cameras` list in `camera_config.json` that filters the available choices in standard and close racing camera pools.
- **FR-004**: The Camera Controller MUST support a `disable_camera_change` boolean in `camera_config.json` to inhibit auto-camera switches.
- **FR-005**: The HTML settings panels MUST read and write the `camera_config.json` settings via the existing `save_json` websocket command.

### Key Entities

- **camera_config.json**: The configuration file that holds auto-director camera pools and settings.
- **leaderboard**: The list of drivers sorted by race position.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Checking "Interval Gaps" correctly changes the timing gap column to show differences to the car ahead.
- **SC-002**: Auto camera switches are restricted strictly to the camera keys configured in `enabled_cameras`.
- **SC-003**: Existing PyInstaller build and test cases continue to compile and pass successfully.
