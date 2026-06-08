# Tasks: Streamline OBS Performance

**Input**: Design documents from `specs/015-streamline-obs-performance/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, quickstart.md

**Tests**: This project uses a strict Test-Driven Development (TDD) approach. The test tasks below MUST be written and run to verify failure before implementing the corresponding features.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Includes exact file paths in descriptions

## Path Conventions

- Paths assume single project structure starting under `AMS2_Auto_Director4.0/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Test framework and diagnostic initialization

- [x] T001 Create performance and concurrency TDD test file `tests/test_performance.py`
- [x] T002 Initialize performance diagnostic logging variables in `core/telemetry_provider.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core synchronization locks and packet buffer structures

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T003 Implement `PacketSlot` struct/class in `core/telemetry_provider.py`
- [x] T004 Introduce `self._packet_buffer_lock` in `core/telemetry_provider.py` and update `_add_packet_to_buffer` to write to `PacketSlot`
- [x] T005 Implement thread-safe `get_packet_buffer_snapshot` in `core/telemetry_provider.py` under `_packet_buffer_lock`
- [x] T006 Introduce `self._lock` in `core/telemetry_provider.py` to protect splines, histories, and poll states, updating properties to make list copies under lock
- [x] T007 Introduce `self._state_lock` in `main.py` and expose thread-safe properties `participants_snapshot` and `scores_snapshot`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Stutter-Free OBS Overlay Rendering (Priority: P1) 🎯 MVP

**Goal**: Decouple broadcasting loop and optimize iteration rates to eliminate micro-stutters.

**Independent Test**: Simulate 32 drivers and verify 4Hz broadcast loop rate with <5% CPU usage.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T008 [P] [US1] Write test `test_broadcast_loop_frequency` in `tests/test_performance.py` asserting that the WebSocket broadcast loop executes at 4Hz

### Implementation for User Story 1

- [x] T009 [US1] Modify `_broadcast_loop` in `dashboard/bridge.py` to run at a stable 4Hz by setting sleep interval to 0.25s
- [x] T010 [US1] Refactor `parse_packets` in `dashboard/payload_builder.py` to fetch state snapshots via the thread-safe `participants_snapshot` and `scores_snapshot` properties of `main.py`

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Non-Blocking, Thread-Safe Telemetry Workstreams (Priority: P2)

**Goal**: Thread-safe telemetry collection and state scoring without race conditions or thread hangs.

**Independent Test**: Simulate a slow WebSocket client and verify the UDP/SHM collector continues broadcasting updates without delay.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US2] Write test `test_thread_safe_telemetry_polling` in `tests/test_performance.py` validating concurrent read/write operations to telemetry caches and spline data
- [x] T012 [P] [US2] Introduce `self._udp_lock` in `core/udp_parser.py` protecting participant names, nationalities, and car data caches
- [x] T013 [US2] Refactor `_parse_udp_participants` and public getters in `core/telemetry_provider.py` to read metadata caches under `_udp_lock`
- [x] T014 [US2] Update `_tick` in `main.py` to acquire `_state_lock` when writing to `_participants` and `_scores`, preventing GUI vs WebSocket write races

**Checkpoint**: User Stories 1 and 2 both work independently and concurrently without race conditions.

---

## Phase 5: User Story 3 - Resilient UDP Input Queue Handling (Priority: P3)

**Goal**: Non-blocking UDP queue design that drops stale/excess packets to avoid timings latency.

**Independent Test**: Inject a UDP packet storm at 100Hz and verify Timing matches latest game state within 250ms.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T015 [P] [US3] Write test `test_udp_packet_drop_on_starvation` in `tests/test_performance.py` asserting that high-frequency packet overwrites increment the dropped counter and preserve only the newest payload
- [x] T016 [P] [US3] Write test `test_udp_socket_timeout` in `tests/test_performance.py` verifying that starting/stopping the UDP socket thread exits within 0.5s

### Implementation for User Story 3

- [x] T017 [US3] Configure `self._udp_socket.settimeout(0.5)` and handle timeouts in `_listen_udp_loop` in `core/udp_parser.py`
- [x] T018 [US3] Update `parse_packets` in `dashboard/payload_builder.py` to read packets via the thread-safe `get_packet_buffer_snapshot` property of `core/telemetry_provider.py`

**Checkpoint**: All user stories are independently functional and resilient.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Performance diagnostics reporting and final validation

- [x] T019 Add 10-second diagnostics logging to stdout in `core/telemetry_provider.py` printing actual loop frequencies, latencies, and packet stats
- [x] T020 Run entire test suite `pytest tests` to verify zero regressions
- [x] T021 Perform manual validation steps documented in `specs/015-streamline-obs-performance/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - Proceed sequentially in priority order (P1 → P2 → P3) to ensure incremental TDD validation
- **Polish (Phase 6)**: Depends on all user stories being complete

### Parallel Opportunities

- Setup tasks T001 and T002 can run in parallel
- Foundational tasks T003, T004, and T005 can run in parallel
- Concurrency test tasks T008, T011, T015, and T016 can be written in parallel
- Model/structure lock implementations T012 and T014 can be written in parallel

---

## Parallel Example: User Story 3

```bash
# Launch test creation tasks for US3 together:
Task: "Write test_udp_packet_drop_on_starvation in tests/test_performance.py"
Task: "Write test_udp_socket_timeout in tests/test_performance.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Verify that the 4Hz broadcast loop runs smoothly without memory leaks or stutters

### Incremental Delivery

1. Setup + Foundation -> Core locks ready
2. Add User Story 1 -> Verify stutters eliminated (MVP)
3. Add User Story 2 -> Verify thread safety under concurrent load
4. Add User Story 3 -> Verify high-frequency packet drop resiliency
5. Add Polish -> Active performance monitoring dashboard
