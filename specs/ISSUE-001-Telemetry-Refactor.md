# Issue: Telemetry Provider Refactor - Separation of Concerns

## Background
The `telemetry_provider.py` module has grown from a simple Shared Memory reader into a monolithic God Class. It is currently responsible for:
1. Managing the memory mapped file connection (`mmap`)
2. Managing the UDP socket connection and binary unpacking (`struct.unpack`)
3. Decoding complex bitwise flags for game state, race state, and sector times
4. Calculating derived telemetry (True Distance, Closing Speeds, Laps Down)
5. Maintaining temporal state (Time-gap Splines, Tyre Stint lap tracking)

## The Bug / Problem
Because data ingestion, data parsing, and state history are all intertwined in a single class, temporary glitches in the ingestion layer (like the AMS2 camera switch SHM blackout) cause cascading temporal corruption into the state history (like the `time_gap_to_leader` spline tracking). 

While a hotfix was implemented to purge corrupted "future" points from the spline during a UDP-fallback temporal jump, the architecture remains highly fragile. Attempting to manage `game_time` synchronization between two asynchronous data sources (UDP and SHM) inside the same class that calculates the gaps is too complex and prone to edge-case bugs.

## Proposed Refactor Architecture
We need to decouple the Telemetry Provider into three distinct layers:

1. **Ingestion Layer (`readers/`)**: 
   - `SharedMemoryReader`: Only reads memory and yields a raw data struct.
   - `UDPReader`: Only reads the socket and yields a raw packet buffer.
2. **Translation Layer (`translators/`)**:
   - `AMS2TelemetryTranslator`: Takes raw SHM/UDP data and standardizes it into a single, clean, stateless Python Dictionary (no history tracking).
3. **State Engine Layer (`state/`)**:
   - `GapTracker`: Takes the stateless dictionary and manages the Splines.
   - `TyreTracker`: Tracks pit stops and tyre stints.

This refactoring will make the system highly testable, as we can inject mock dictionaries into the State Engine without needing to simulate raw binary UDP packets.

## Acceptance Criteria
- [ ] `telemetry_provider.py` is split into independent modules.
- [ ] The spline history logic is decoupled from the raw data polling loop.
- [ ] 100% of existing unit tests pass after the refactor.
