# Technical Research - Roof Camera Session Info Overlay & Tenths Leaderboard Format

This document details the technical research, architectural decisions, and alternatives evaluated for feature 014.

## Decided Solutions

### Decision 1: Client-Side Timing Formatting (JavaScript)
- **Decision**: Perform all rounding and formatting to tenths of a second in `f1tv_overlay.js` rather than modifying `payload_builder.py` or the Python shared memory/UDP telemetry provider.
- **Rationale**: 
  1. Hides telemetry pauses/gaps on the client display side only, preserving raw high-precision telemetry data in the backend database, logs, and WebSocket payload.
  2. Simplifies development by keeping changes localized to the frontend.
  3. Avoids rebuilding the compiled Python binaries (via PyInstaller) for timing-only changes.
- **Alternatives Considered**: 
  - *Formatting in `payload_builder.py`*: Rejected because it restricts other dashboard pages (like diagnostics or telemetry analyzers) from accessing precise millisecond values.

### Decision 2: Node.js VM Sandbox Unit Testing for Frontend TDD
- **Decision**: Implement a unit test suite using Node.js's built-in `vm` module to run `f1tv_overlay.js` in a mocked DOM/WebSocket context.
- **Rationale**:
  1. Allows direct execution of frontend code from the command line without setting up full browser automation (Playwright/Selenium) or installing massive NPM node modules (Jest/Vitest).
  2. Zero-dependency setup that runs extremely fast (under 100ms).
  3. Provides a clean way to write assertions for `formatGapTenths`, `formatTimeTenths`, `updateVisibilityMode`, and the HTML visibility state changes.
- **Alternatives Considered**:
  - *Playwright/Puppeteer*: Rejected for unit testing because of slow startup times and package installation overhead, but will be used for final manual/verification checks.
  - *Jest/Vitest*: Rejected as it would require initializing a package.json and running npm installations in the project which is currently pure static frontend assets.

### Decision 3: CSS Custom Property for Font Size Configuration
- **Decision**: Define a CSS custom property `--leaderboard-font-size` in the stylesheet to control the leaderboard row scaling.
- **Rationale**:
  1. Keeps sizing values centralized at the top of the CSS file.
  2. Simplifies adjustments if the user wants to tweak the font size later.
- **Alternatives Considered**:
  - *Hardcoded CSS rules*: Rejected because it scatters the sizing values and makes scaling components more error-prone.
