# Technical Research: Non-Blocking Camera Switches

This document outlines the technical research, decisions, and design choices for implementing non-blocking camera switches in the AMS2 Auto Director.

## Concurrency Mechanisms Evaluation

To prevent camera keypress sequences (which require `time.sleep` delays) from blocking the main Tkinter thread, we evaluated three approach alternatives:

### 1. Dedicated Concurrency Thread (Chosen)
- **Design**: Wrap the sequence of key presses (UP, DOWN, ENTER, and camera select key) inside a background daemon thread (`threading.Thread`). Use a thread-safe boolean flag `self._switching_in_progress` to ignore any concurrent switch requests.
- **Pros**:
  - Extremely simple to implement.
  - Zero dependencies on GUI packages or event loops. Keeps `CameraController` clean of Tkinter references.
  - Highly testable using standard Python test tools and mocks.
  - `pyKey` keyboard injection via Windows `SendInput` is system-level and fully thread-safe.
- **Cons**: Spawns a thread per camera switch. However, since camera switches happen at most once every few seconds, the overhead of creating a short-lived daemon thread is negligible.

### 2. Tkinter `.after()` Scheduled Chains (Rejected)
- **Design**: Deconstruct keypress sequences into individual key-down, wait, key-up, and gap events, scheduling each step using `root.after()`.
- **Pros**: Run entirely on the single Tkinter thread without multi-threading overhead.
- **Cons**: 
  - Violates separation of concerns: `core/camera_controller.py` would need direct access to the Tkinter `root` instance, breaking the architectural rule "No GUI imports or widgets in core/".
  - Makes unit testing extremely complex since tests would require a running Tkinter mainloop.

### 3. Asyncio Event Loop Integration (Rejected)
- **Design**: Run the key injection sequences as asynchronous tasks inside an event loop.
- **Pros**: Clean cooperative concurrency.
- **Cons**: 
  - The main GUI thread is synchronous Tkinter. Mixing synchronous Tkinter with a main-thread asyncio loop is complex, requiring libraries like `asyncio-tkinter` or nested loops.
  - Although the bridge thread runs an asyncio event loop, the `CameraController` belongs to the main app, and cross-thread event loop dispatching introduces unnecessary synchronization overhead.

---

## Decision & Rationale

* **Decision**: Implement a background thread runner in `CameraController` for keypress sequence execution.
* **Concurrency Lock**: Use a `threading.Lock` to protect the state of `self._switching_in_progress`.
* **State Updates**: String attributes like `self.current_camera_type` will be updated atomically at the end of the background thread sequence, making them safe for concurrent reads by the main and bridge threads.

---

## Verification & Testing Strategy (TDD)

We will implement Test-Driven Development (TDD) by writing tests *before* modifying the implementation:
1. **Mock Keypress Execution**: Override `_press_key` and `_release_key` to verify correct key sequences are sent.
2. **Timing Verification**: Assert that calling `move_to_position` or `select_random_camera` returns immediately (< 5ms) on the calling thread, even though the mock keypress sequences are executing.
3. **Concurrency Test**: Trigger multiple switches in rapid succession and assert that only the first one starts execution, while subsequent requests are discarded.
