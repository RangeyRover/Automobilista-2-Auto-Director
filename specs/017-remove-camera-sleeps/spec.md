# Feature Specification: Non-Blocking Camera Switches

**Feature Branch**: `017-remove-camera-sleeps`  
**Created**: 2026-06-08  
**Status**: Draft  
**Input**: User description: "ok the camera sleeps have to go if they affect the overall program."

## Clarifications

### Session 2026-06-08

- Q: How should the camera controller handle new switch requests while a sequence is already in progress? → A: Ignore/Discard: Silently ignore any new switch requests until the current sequence completes.
- Q: What level of logging should be implemented for the asynchronous camera switches? → A: High-Level Events Only: Log sequence start, sequence completion, final camera choice, and overall duration to standard output.
- Q: Are any other performance optimizations or threading changes in other system modules in-scope for this branch? → A: Camera Controller Only: Focus exclusively on CameraController key tap/gap/stabilization sleeps. All other modules remain out of scope.

## Scope Boundaries

- **In Scope**: Refactoring the keypress injection and stabilization sleeps in `CameraController` to execute asynchronously, ensuring the Tkinter event loop remains responsive.
- **Out of Scope**: Performance tuning or threading modifications in any other systems, including the Scoring Engine, Telemetry Ingestion (UDP/SHM), Dashboard Bridge, or file I/O operations (such as loading replay logs).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smooth Auto-Directing without GUI Freezes (Priority: P1)

As an overlay broadcaster, I want the camera switches to happen asynchronously so that the scoring calculations, connection diagnostics, and user interface do not freeze or lag during a switch.

**Why this priority**: Highly critical because the current 0.4s to 0.6s synchronous freeze halts scoring updates and blocks UI redrawing, making the application appear unresponsive.

**Independent Test**: Can be verified by running the Auto Director, triggering camera changes, and checking that the GUI remains interactive and diagnostics show stable telemetry loop frequency (5Hz).

**Acceptance Scenarios**:

1. **Given** the Auto Director is active and telemetry is polling at 5Hz (200ms tick),  
   **When** a camera switch is triggered (requiring UP/DOWN/ENTER sequences),  
   **Then** the GUI remains responsive, connection status keeps updating, and the next `_tick` runs without delay.
2. **Given** a camera switch is running in the background,  
   **When** the user moves or clicks elements on the Tkinter GUI,  
   **Then** the GUI processes the user events instantly without lag.

---

### User Story 2 - Real-Time Dashboard Broadcasting during Switches (Priority: P2)

As a viewer watching the F1TV Overlay, I want telemetry updates (RPM, Speed, Throttle, Brake) to remain smooth at 60Hz during camera switches so that the HUD looks premium and responsive.

**Why this priority**: The HUD overlay is the main visual output of the application. Eliminating stutter during switches is key to a premium feel.

**Independent Test**: Verify that the WebSocket bridge continues broadcasting packets and that the client overlay animations do not stutter during a camera switch.

**Acceptance Scenarios**:

1. **Given** the Dashboard Bridge is broadcasting at 60Hz,  
   **When** a camera switch sequence is executing,  
   **Then** the WebSocket loop continues broadcasting telemetry packets without lag spikes or pauses.

---

### User Story 3 - Non-Blocking Manual Camera Switches (Priority: P3)

As a user pressing camera hotkeys (e.g. 1-7, 9), I want the keystroke injection to run asynchronously so that my manual input does not block the main application.

**Why this priority**: Consistency in the camera controller. All keystroke injection sequences should share the same non-blocking path.

**Independent Test**: Press a camera hotkey (e.g., '7') and check that the application remains responsive during the key tap sequence.

**Acceptance Scenarios**:

1. **Given** the application is running,  
   **When** the user presses a manual camera hotkey,  
   **Then** the key tap sequence runs in a non-blocking manner and the camera changes successfully.

---

### Edge Cases

- **Concurrent Switches**: If a camera switch is already executing in the background and another switch is triggered, the new switch request must be silently ignored and discarded until the active sequence completes to prevent overlapping/corrupted keypress injections.
- **Automobilista 2 Not Focused**: If the game loses focus during an asynchronous sequence, the remaining key presses in that sequence must be aborted to avoid injecting keys into other applications.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST execute camera keystroke injection sequences (UP, DOWN, ENTER, and camera selection keys) asynchronously.
- **FR-002**: The camera controller's sleeps (key hold time, key gap time, and post-ENTER stabilization delay) MUST NOT block the Tkinter main event loop.
- **FR-003**: Telemetry polling and scoring calculations MUST continue executing at their regular interval (5Hz / 200ms) during camera switches.
- **FR-004**: All existing camera configurations, including key bindings, key timings (`key_hold_ms`, `key_gap_ms`), trackside anchors, and selection pools, MUST be preserved.
- **FR-005**: If a new camera switch is requested while one is already in progress, the system MUST silently ignore and discard the request until the active sequence finishes to ensure thread safety and prevent keystroke corruption.
- **FR-006**: The system MUST log high-level switch events (sequence start with target position, sequence completion, final camera type, and overall duration) to stdout, keeping console logs uncluttered.

### Key Entities

- **CameraController**: Manages keystroke injection and camera status.
- **AutoDirectorApp**: Directs focus and triggers the camera controller.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The Tkinter GUI event loop remains responsive with zero lag spikes exceeding 50ms during camera switches.
- **SC-002**: Telemetry poll frequency stays stable at 5.0Hz (tolerance ±0.5Hz) during camera switches, with no drops.
- **SC-003**: The Dashboard Bridge WebSocket broadcast loop maintains a steady 60Hz frequency (approx. 16ms interval) during camera switches.
- **SC-004**: All 306 existing unit tests pass, and new tests confirm that camera switching occurs asynchronously without blocking the calling thread.
