# Quickstart Guide - Roof Camera Session Info Overlay & Tenths Leaderboard Format

This guide explains how to run the automated test suite and manually verify the overlay changes for this feature.

## Running Automated Tests

To test the formatting functions and overlay visibility logic:

1. Open a terminal in the project root:
   `cd "AMS2_Auto_Director4.0"`
2. Run the Node.js unit test suite:
   `node tests/test_f1tv_overlay.js`
3. Verify that all test cases pass without assertion errors.

---

## Running the Development Server

To view and verify the changes in OBS or a browser:

1. Start the Auto Director Python server:
   `python main.py`
2. Open a browser and navigate to:
   - Overlay Page: `http://localhost:8765/f1tv_overlay.html`
   - Control Panel Page: `http://localhost:8765/f1tv_control.html`
3. Verify the layout visually:
   - Toggle the settings checkboxes on the Control Panel page.
   - Switch camera type between trackside and roof/cockpit and verify that Session Info obeys the configuration checklist.
   - Verify that timings default to tenths format and can be toggled back to milliseconds.
