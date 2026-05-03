---
name: fix-gui-regressions
version: 1.0.0
---

# Feature Specification: Fix GUI Regressions

## Clarifications
### Session 2026-05-03
- Q: Global binding of spacebar may interfere with tuning input fields. → A: Use `Ctrl+Spacebar` as the toggle shortcut instead to avoid overlap.

## 1. Goal Description

Address two critical regressions introduced during the V4.0 Strangler Refactor:
1. **Telemetry Data Mapping**: The leaderboard table displays zeroes for all numeric participant fields (race position, speed, gap, cars ahead) and is missing the track name. This is due to incorrect referencing of nested properties within the `ParticipantInfo` struct array instead of the top-level `SharedMemory` struct.
2. **Global Keybinding**: The spacebar fails to toggle the Auto Director when the `Treeview` widget has focus, as it consumes the key event. 

## 2. User Scenarios & Testing

### Scenario 1: Connecting to AMS2 Shared Memory
- **Given** the AMS2 Auto Director is running and connected to the game
- **When** the game is in an active session
- **Then** the leaderboard must correctly populate with non-zero values for active drivers (P, Speed, Gap, Cars, penalties, and bonuses).
- **And** the track name must accurately reflect the loaded circuit (e.g. "Interlagos").

### Scenario 2: Toggling Auto Director
- **Given** the director is running and the user has clicked inside the driver grid
- **When** the user presses the `Spacebar`
- **Then** the Auto Director status must toggle between OFF and ON.

## 3. Functional Requirements

### FR-1: Correct Struct Data Extraction
- **FR-1.1**: The system must extract `mRacePosition`, `mCurrentLapDistance`, `mLapsCompleted`, `mCurrentLap`, and `mCurrentSector` from the nested `mParticipantInfo` structure.
- **FR-1.2**: The system must extract `mSpeeds`, `mPitModes`, `mRaceStates`, `mHighestFlagColours`, `mHighestFlagReasons`, `mFastestLapTimes`, and `mLastLapTimes` from the top-level `SharedMemory` structure.
- **FR-1.3**: The system must decode `mTrackLocation` correctly, falling back to legacy byte-offset extraction if the ctypes array fails to decode natively.

### FR-2: Global Keyboard Shortcuts
- **FR-2.1**: The shortcut for toggling the Auto Director must be bound globally (`<Control-space>`) to `Ctrl+Spacebar` so it works safely without interfering with text entry fields.

## 4. Success Criteria

- The leaderboard matches the data fidelity of the V3.0 original version.
- Toggling the director works reliably from any UI state.

## 5. Assumptions & Exclusions
- The underlying `shared_memory_struct.py` mappings are correct and unchanged from V3.0.
