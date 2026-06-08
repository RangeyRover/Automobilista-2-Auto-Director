# Implementation Plan: Streamline OBS Performance

**Branch**: `015-streamline-obs-performance` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/015-streamline-obs-performance/spec.md`

## Summary

This feature streamlines the telemetry collection and WebSocket broadcast loops of the Auto Director to eliminate the "sticky" overlay behavior and occasional freezes when loaded as a browser source in OBS. 

The primary technical approach is:
1. **Async & Loop Decoupling**: Decouple the WebSocket broadcast loop from the GUI thread and telemetry polling thread, and reduce the broadcast frequency from ~60Hz to a stable 4Hz (meeting `SC-001`).
2. **Snapshot Double-Buffering**: Eliminate redundant mmap reads and ctypes deserialization in the WebSocket thread by having it read thread-safe snapshots of `_participants`, `_scores`, and `_shm` generated on the GUI thread.
3. **Thread Safety & Mutex Locks**: Introduce strict thread-safe locking on the raw packet buffer (`_packet_buffer_lock`), UDP metadata string cache (`_udp_lock`), spline cache (`_lock`), and global state (`_state_lock`).
4. **Non-Blocking UDP Sockets**: Configure the UDP socket with `settimeout(0.5)` to ensure clean thread exits and non-blocking reads.
5. **Periodic Diagnostics**: Print performance statistics (actual update Hz, latencies, and dropped packet counts) to stdout/console every 10 seconds.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: `socket`, `struct`, `threading`, `asyncio`, `websockets`  
**Storage**: N/A  
**Testing**: `pytest` (Existing tests + new concurrent performance tests in `tests/test_performance.py`)  
**Target Platform**: Windows  
**Project Type**: Single project desktop application (Python GUI + WebSocket Bridge + Overlays)  
**Performance Goals**: 
  - Stable 4Hz (+/- 0.5Hz) WebSocket broadcast loop.
  - Stable 5Hz poller loop on the main GUI thread.
  - Low CPU usage (< 5% of a single core).
**Constraints**: 
  - Strict thread safety across all shared caches.
  - No blocking synchronous delays in event loops.
  - Maintain separate single-packet buffers per packet size/type to prevent starvation.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No constitution file detected; default code quality and performance principles are applied. The design strictly adheres to the TDD requirement (tests will be written first).

## Project Structure

### Documentation (this feature)

```text
specs/015-streamline-obs-performance/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Technical design decisions
├── data-model.md        # Concurrency and locking structures
├── quickstart.md        # Verification and test instructions
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
AMS2_Auto_Director4.0/
├── core/
│   ├── telemetry_provider.py    # Target for thread safety & poll locking
│   └── udp_parser.py            # Target for non-blocking socket & UDP cache locking
├── dashboard/
│   ├── bridge.py                # Target for broadcast loop Hz & thread-safe reads
│   └── payload_builder.py       # Target for thread-safe state snapshot parsing
├── main.py                      # Target for GUI thread state locking
└── tests/
    └── test_performance.py      # New TDD performance & concurrency tests
```

**Structure Decision**: Single project application. We will strictly modify the core telemetry provider, UDP parser, dashboard bridge, and main GUI tick loop files, and add new TDD tests in `tests/test_performance.py`.

## Complexity Tracking

No violations to justify.
