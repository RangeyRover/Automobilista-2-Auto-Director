# Research: Streamline OBS Performance

## Technical Decisions

### 1. Decoupled Architecture & Event Loop Optimization
- **Decision**: Decouple the WebSocket broadcast loop from the GUI thread and telemetry polling thread, and reduce the broadcast loop frequency from ~60Hz to 4Hz (matching `SC-001`).
- **Rationale**: 
  - The OBS overlays and control panels do not need 60Hz updates since telemetry only changes at 4Hz (or at most 20Hz under game-specific high-frequency settings). 
  - Serializing a large nested state JSON and broadcasting it via WebSockets at 60Hz consumes up to 15-20% CPU on a single core and blocks the event loop. By running at 4Hz, we reduce CPU usage by **15 times** (meeting `SC-002`).
  - By removing mmap reads and ctypes deserialization from the WebSocket thread, we eliminate major lock contention on `self._shm_lock` between the GUI tick thread and the WebSocket broadcast thread.
- **Alternatives Considered**: 
  - *Keep 60Hz but optimize serialization*: Rejected because the browser overlay rendering performance is capped by OBS's browser source refresh rate, and high-frequency redundant websocket packets degrade OBS network performance.

### 2. Thread-Safe Packet Buffer & Queue Handling
- **Decision**: Implement a thread-safe dict of packet slots (`PacketSlot`), protected by `_packet_buffer_lock`. Maintain a sequence number and read-status flags (`read_by_poll`, `read_by_bridge`) for each slot.
- **Rationale**:
  - Direct concurrent access to `_packet_buffer` from the UDP thread, GUI thread, and WebSocket thread is a data race.
  - Using a `PacketSlot` containing sequence numbers and read tracking ensures that:
    1. If a new packet of size S arrives, it overwrites the old one (FR-005: single-packet overwrite buffer per size).
    2. We can detect if a packet was overwritten before being read by either consumer, incrementing a dropped packet counter.
    3. Multiple independent consumer threads can read the same packet safely.
- **Alternatives Considered**:
  - *`queue.Queue`*: Bounded FIFO queue. Rejected because high-frequency packet types (e.g. 559 bytes telemetry) would fill the queue and cause latency lag/starvation of low-frequency packets (e.g. 1136 bytes participants names). The user explicitly requested a separate buffer for each packet size.

### 3. Non-Blocking UDP Socket
- **Decision**: Configure the UDP socket with `settimeout(0.5)` to make socket operations non-blocking and ensure clean shutdown, or run in a non-blocking mode using `select.select`.
- **Rationale**:
  - Prevents the UDP listener thread from hanging indefinitely on `recvfrom` when the application closes or restarts.
- **Alternatives Considered**:
  - *Spin-wait non-blocking loop*: Rejected due to high CPU usage.

### 4. Performance Diagnostics
- **Decision**: Implement a periodic (10-second) performance diagnostics print to stdout/console.
- **Rationale**:
  - Tracks actual loop frequencies, average loop latencies (poll execution and broadcast execution), received packets, and dropped packets. Allows easy profiling and verification of success criteria.

## Verification & Profiling Plan
- We will inject mock UDP packet streams at high frequencies (e.g., 100Hz) to verify the dropped packet counter and guarantee that the newest packets are processed without lag.
- We will measure execution times of `poll()` and `_broadcast_loop()` and print the metrics every 10 seconds.
