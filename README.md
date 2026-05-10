# AMS2 Auto Director V4.0

Real-time telemetry-driven broadcast camera controller for Automobilista 2.

## Architecture

```
main.py                    ← Thin tkinter GUI shell (no business logic)
core/
  scoring_engine.py        ← Stateless per-tick interest scoring (FR-3)
  telemetry_provider.py    ← SharedMemory/UDP data extraction (FR-1, FR-2)
  camera_controller.py     ← pyKey injection with delta navigation (FR-4)
tests/
  conftest.py              ← Shared fixtures (make_participant, MockSharedMemory)
  test_fixtures.py         ← Fixture smoke tests
  test_scoring_engine.py   ← 29 tests (SE-01 to SE-29)
  test_telemetry_provider.py ← 26 tests (TP-01 to TP-26)
  test_camera_controller.py  ← 13 tests (CC-01 to CC-13)
```

## Quick Start

```bash
# Run with Shared Memory (default)
python main.py

# Run with UDP
python main.py --mode udp

# Run tests
python -m pytest tests/ -v
```

## Requirements

- Python 3.11+
- AMS2 running (for live telemetry)
- `pyKey` (for camera control key injection)

## Key Controls

| Key | Action |
|---|---|
| **Space** | Toggle Auto Director ON/OFF |

## Test Suite

| Module | Tests | Coverage |
|---|---|---|
| Scoring Engine | 29 | Pit/Speed penalties, Cars Ahead, Close Racing, Position Bonus, Focus Selection |
| Telemetry Provider | 26 | SharedMemory extraction, True Distance, Gaps, Cars Ahead, Speed, UDP, Connection State |
| Camera Controller | 13 | Delta navigation, Fallback, Key timing, Edge cases |
| **Total** | **68** | All business logic fully tested in isolation |

## Strangler Refactor

This V4.0 was extracted from the V3.0 monolith (`AMS2AutoDirector.py`, 902 lines)
using the Strangler Pattern. The legacy file is preserved but never imported.
All logic was decomposed into three testable `core/` modules.

## Web Overlays & HUDs

V4.0 includes a powerful, zero-latency Web Overlay system served locally on port `8765`. It includes F1TV-style broadcast graphics, a Halo HUD, and remote control panels for OBS integration.

**👉 Please see the [Overlays Guide](OVERLAYS_GUIDE.md) for full documentation on how to use and customize the graphics.**
