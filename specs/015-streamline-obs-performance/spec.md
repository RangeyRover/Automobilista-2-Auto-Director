# Feature Specification: Streamline OBS Performance

**Feature Branch**: `015-streamline-obs-performance`  
**Created**: 2026-06-08  
**Status**: Draft  
**Input**: User description: "an analysis of performance. when this is being used in OBS i see very sticky performance, with occasional freezes. This branch is to streamline all performance, check that there are no threading routines or sleeps that can cause performance problems, making sure we are thread safe and have independent workstreams for the various issues. I suspect it might be related to UDP packets but have no proof."

## Scope Boundaries

### In-Scope
- **Core Telemetry Loop**: Decouple and optimize UDP sockets, SHM polling, and WebSocket broadcast loops.
- **Thread Safety**: Ensure absolute thread-safe operations on all shared telemetry/participant caches.
- **Spline & Distance Math**: Profile and optimize the DistanceTimeSpline and time-gap calculation algorithms to prevent core thread execution delays.

### Out-of-Scope
- **Frontend Browser Rendering**: No changes to the browser overlay HTML/CSS/JS rendering or animations (the browser-based solution is assumed not to be freezing).
- **GUI Controls**: No changes to the control panel GUI pages.

## Clarifications

### Session 2026-06-08
- Q: What strategy should the UDP queue use to discard stale telemetry data when the parsing thread is busy? → A: Single-Packet Overwrite per packet size (separate single-packet buffer for each packet size/type).
- Q: What parts of the codebase are in-scope for optimization in this performance branch? → A: Telemetry ingestion & WebSocket broadcast pipelines (Option A) AND algorithmic spline optimization / track distance calculation routines (Option B). Frontend browser rendering and GUI controls are out-of-scope.
- Q: How should the system output performance diagnostics/metrics? → A: Periodic Console Summary (Option A) - print loop performance statistics (actual Hz, dropped packets count, execution latency) to stdout every 10 seconds.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stutter-Free OBS Overlay Rendering (Priority: P1)

The overlay must render timing updates smoothly inside OBS without stutters, lag spikes, or freezes, even during long sessions (over 2 hours) and in dense grids (up to 32 drivers).

**Why this priority**: Eliminates the visible "sticky" UI behavior that directly degrades the user/broadcast experience in OBS.

**Independent Test**: Can be verified by running the Auto Director with simulated telemetry (e.g. 32 drivers), loading the F1TV Overlay inside an OBS Browser Source, and monitoring the frame delivery consistency for zero frame drops over 1 hour.

**Acceptance Scenarios**:

1. **Given** a session with 32 active drivers, **When** the overlay is loaded in OBS, **Then** all timings update smoothly at 4Hz with zero visible stutters.
2. **Given** a running stream in OBS, **When** switching camera modes or loading/unloading panels, **Then** the overlay UI does not lock up or freeze.

---

### User Story 2 - Non-Blocking, Thread-Safe Telemetry Workstreams (Priority: P2)

Telemetry collection, WebSocket client broadcasting, and game state scoring must run in independent, decoupled, thread-safe threads or tasks. Slower network clients or database operations must not block the telemetry reception thread.

**Why this priority**: Prevents a slow WebSocket client or disk/log write from stalling the packet capture pipeline, which triggers the visual stutters.

**Independent Test**: Simulate a slow WebSocket client (introducing a 500ms delay on message receipt) and verify that the backend's UDP/SHM collector thread continues polling and broadcasting to other clients at 4Hz without delay.

**Acceptance Scenarios**:

1. **Given** multiple connected WebSocket clients, **When** one client experiences network latency, **Then** other clients continue receiving updates at the target frequency without delay.
2. **Given** active shared memory and UDP inputs, **When** accessing internal telemetry caches, **Then** data operations are fully thread-safe without race conditions.

---

### User Story 3 - Resilient UDP Input Queue Handling (Priority: P3)

The UDP collection thread must use a non-blocking queue design that drops stale or excess packets when incoming traffic exceeds parsing capacity, rather than buffering them and causing latency lag accumulation.

**Why this priority**: Protects the system against input packet storms (which occur during high-frequency multiplayer updates), ensuring the UI shows the absolute latest telemetry rather than lagging behind.

**Independent Test**: Inject a UDP packet storm at 100Hz (exceeding parsing rate) and verify that the UI timing matches the latest game state within 250ms (meaning stale packets were dropped and not queued).

**Acceptance Scenarios**:

1. **Given** a high-frequency stream of UDP packets, **When** the parsing thread is busy, **Then** the socket queue drops old packets and processes only the most recent state.

---

### Edge Cases

- **Client Disconnection/Reconnection**: A client disconnecting mid-session must not cause a thread hang or socket leak.
- **Dual Telemetry Inputs**: Simultaneous UDP and SHM data availability must be handled cleanly, ensuring the primary source dominates without thread conflicts or CPU spinlocks.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST separate UDP/SHM telemetry capture and parsing from the WebSocket broadcasting loop into independent threads or asynchronous tasks.
- **FR-002**: All shared states (e.g., telemetry caches, participant indexes, spline tracking) MUST be protected by thread-safe synchronization locks or mutexes to prevent race conditions.
- **FR-003**: The system EVENT loops and WebSocket handlers MUST NOT execute blocking synchronous delays that stall execution context.
- **FR-004**: The UDP socket MUST use non-blocking mode or be handled inside a dedicated worker thread with a small, bounded queue.
- **FR-005**: If the incoming packet buffer fills up, the system MUST drop the oldest packets and only keep the latest telemetry frame, maintaining separate single-packet buffers for each packet size/type to prevent high-frequency packets from starving other data types.
- **FR-006**: The system MUST print performance diagnostics (including actual loop update frequency, dropped packet counts, and loop execution latencies) to stdout/console every 10 seconds.

### Key Entities

- **TelemetryProvider**: The boundary worker thread that polls SHM/UDP data.
- **DashboardBridge**: The WebSocket server and broadcast worker that pushes serialized updates to clients.
- **ParticipantCache**: Thread-safe storage holding current driver positions, gaps, and timing details.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Telemetry update broadcast loop runs at a stable frequency of 4Hz +/- 0.5Hz over 2+ hour sessions.
- **SC-002**: CPU usage for telemetry collection and WebSocket server remains under 5% of a single core under normal loads.
- **SC-003**: Latency between game telemetry state change and OBS UI rendering is under 250ms.
- **SC-004**: Zero thread deadlocks or race condition crashes occur during telemetry provider restarts or client reconnect events.
