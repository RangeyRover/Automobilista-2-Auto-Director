# Implementation Plan - Roof Camera Session Info Overlay & Tenths Leaderboard Format

**Branch**: `014-roof-cam-tenths-leaderboard` | **Date**: 2026-06-08 | **Spec**: [spec.md](file:///C:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/specs/014-roof-cam-tenths-leaderboard/spec.md)
**Input**: Feature specification from `/specs/014-roof-cam-tenths-leaderboard/spec.md`

## Summary

Implement visibility behavior updates for the session-info panel in onboard camera views, and format leaderboard timings to tenths of a second. This plan adopts a strict **System Design Document (SDD)** and **Test-Driven Development (TDD)** approach. Automated test cases verifying timing format and visibility logic will be written and validated as failing *before* any implementation code is modified.

---

## Technical Context

**Language/Version**: Python 3.11, JavaScript (ES6+), HTML5, CSS3, Node.js v22.20.0 (for local testing)  
**Primary Dependencies**: None (Standard browser APIs & Node.js built-in `vm` module for testing)  
**Storage**: Local Storage (to persist user settings checkbox states)  
**Testing**: Node.js `node tests/test_f1tv_overlay.js` unit tests, Pytest (for backend integration)  
**Target Platform**: OBS / Web Browser (1920x1080 resolution)  
**Project Type**: Single project with web dashboard assets  
**Performance Goals**: UI rendering latency <5ms per frame update, update frequency ~4Hz  
**Constraints**: Zero-dependency frontend testing (no NPM install allowed in repository), Timing format must be configurable and default to tenths  
**Scale/Scope**: 1 dashboard overlay page, 1 control page, 1 stylesheet, 1 javascript controller  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Design Simplicity**: Yes. Uses CSS variables and client-side helper functions.
- **TDD Requirement**: Yes. Tests must be written and verify-failed before code updates.
- **Platform Separation**: Yes. Frontend formatting keeps Python backend telemetry raw.

---

## Project Structure

### Documentation (this feature)

```text
specs/014-roof-cam-tenths-leaderboard/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 data structure schema
├── quickstart.md        # Quickstart instructions
├── contracts/
│   └── websocket-protocol.md # Phase 1 websocket payload contracts
└── checklists/
    └── requirements.md  # Specification quality checklist
```

### Source Code (repository root)

```text
AMS2_Auto_Director4.0/
├── dashboard/
│   ├── f1tv_overlay.html    # Overlay page (To modify: session-info class)
│   ├── f1tv_control.html    # Control panel (To modify: tenths-timing checkbox)
│   ├── css/
│   │   └── f1tv_overlay.css # Stylesheet (To modify: font sizing, dimensions)
│   └── js/
│       └── f1tv_overlay.js  # Main logic (To modify: timing helpers, presets, updateAll)
├── tests/
│   └── test_f1tv_overlay.js # [NEW] Node.js VM unit tests (written BEFORE code)
└── main.py                  # Core backend (unchanged)
```

**Structure Decision**: Single project. Static overlay assets are located in `/dashboard/`, and automated tests are located in `/tests/`. We will add a new Node.js test script `tests/test_f1tv_overlay.js` to execute frontend tests.

---

## Test-Driven Development (TDD) Design

Before modifying the overlay files, we will create the unit test file [test_f1tv_overlay.js](file:///C:/Users/markn/OneDrive/Documents/0-1Python/Auto%20Director%20Analyser/AMS2_Auto_Director4.0/tests/test_f1tv_overlay.js) which loads `f1tv_overlay.js` in a virtual context and runs the following test suites:

### 1. Timing Format Unit Tests
- Assert `formatGapTenths(gap)`:
  - `0.123` $\rightarrow$ `"+0.1s"`
  - `1.289` $\rightarrow$ `"+1.3s"`
  - `0` or `-1` $\rightarrow$ `""`
  - `"PIT"` or `"+1 LAP"` $\rightarrow$ `"PIT"`, `"+1 LAP"`
- Assert `formatTimeTenths(sec)`:
  - `65.489` $\rightarrow$ `"1:05.4"`
  - `9.234` $\rightarrow$ `"0:09.2"`
  - `0` or `-5` $\rightarrow$ `"--:--.-"`

### 2. Component Visibility and Preset Tests
- Verify that `session-info` visibility respects user settings and presets:
  - `applyPreset('broadcast')` $\rightarrow$ `session-info` is active/visible.
  - `applyPreset('cockpit')` $\rightarrow$ `session-info` is inactive/hidden.
  - Switches to `roof` or `cockpit` camera keep `session-info` visible if checked.

### 3. Sizing & Text Layout Tests
- Verify that all row layout dimensions have been updated to scale with the larger font.
