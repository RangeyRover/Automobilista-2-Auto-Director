# Feature Specification: Configurable Raw JSON Telemetry Dumps

**Feature Branch**: `feature/9-raw-json-telemetry`  
**Created**: 2026-05-12  
**Status**: Draft  
**Input**: User description: "a configurable raw json every second for all shared memory features and a seperate one for all UDP features, where there are structs break them down so we can see the output, im tired of guessing."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configurable Raw Dumps (Priority: P1)

As a developer debugging telemetry, I want the system to output raw JSON dumps of all Shared Memory and UDP structures to a file every second, so that I can inspect exactly what values the simulation is sending without guessing.

**Why this priority**: Without visibility into the raw structures, diagnosing hybrid telemetry synchronization issues is currently impossible.

**Independent Test**: Can be tested by enabling the dump feature, running the game, and inspecting the output JSON file.

**Acceptance Scenarios**:

1. **Given** the telemetry logger is enabled, **When** the game runs in Shared Memory mode, **Then** a JSON file is created containing the fully unrolled C-structs of the Shared Memory.
2. **Given** the telemetry logger is enabled, **When** the game runs in UDP mode, **Then** a JSON file is created containing the fully parsed UDP packets.
3. **Given** the system is running, **When** one second elapses, **Then** the JSON files are overwritten/appended with the latest snapshot of the state.

---

### User Story 2 - Struct Breakdown (Priority: P2)

As a developer, I want all nested C-structs (e.g., ParticipantInfo) to be fully expanded into JSON arrays/objects, so that I can see every field clearly.

**Why this priority**: C-structs in memory are opaque; expanding them is necessary to read the telemetry data.

**Independent Test**: Can be tested by looking at the output JSON and confirming that complex structs are serialized completely.

**Acceptance Scenarios**:

1. **Given** a raw memory struct, **When** the JSON dump occurs, **Then** all internal structs, bytes, and arrays are recursively serialized to standard JSON primitives.

---

### Edge Cases

- What happens if the file is locked by a viewer?
- How large do the JSON files grow over time? (Should it be a single snapshot file that overwrites every second, or a log file that grows?)
- How is the configuration toggled on/off?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST output a raw JSON dump of the Shared Memory structure every 1 second when active.
- **FR-002**: System MUST output a raw JSON dump of the active UDP packets every 1 second when active.
- **FR-003**: System MUST recursively expand nested structs into JSON objects.
- **FR-004**: System MUST convert `bytes` and `c_char` arrays into readable string representations.
- **FR-005**: System MUST provide a configuration toggle to enable/disable the telemetry dump.
- **FR-006**: System MUST overwrite a static snapshot file (`shm_dump.json` and `udp_dump.json`) rather than creating infinitely growing logs to prevent disk exhaustion.

### Key Entities *(include if feature involves data)*

- **TelemetryDumper**: The component responsible for deep-copying and serializing the memory structures to JSON.
- **DumpConfiguration**: The configuration setting to toggle this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developer can view the raw output of Shared Memory and UDP within 1 second of it happening in the game.
- **SC-002**: JSON dumps contain 100% of the structurally defined fields in `shared_memory_struct.py` and the UDP parsers.
