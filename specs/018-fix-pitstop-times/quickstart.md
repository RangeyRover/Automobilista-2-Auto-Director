# Quickstart Guide: Standalone Server Flywheel Pitstop Times

This guide outlines how to execute tests and verify that the standalone leaderboard server calculates pit times using the flywheel-stabilized clock.

## Verification Checklist

### 1. Run Automated Unit Tests
Verify that all unit tests, including new stabilized pitstop checks, pass successfully:
```bash
python -m pytest tests/test_shm_dump_tool.py
```

### 2. Run Standalone WS Server
Start the standalone leaderboard WS server:
```bash
python tools/shm_leaderboard_server.py
```

### 3. Run Replay Verification
1. Connect to Automobilista 2 or run a replay memory dump.
2. Trigger a pitstop.
3. Switch cameras (forcing raw game time jumps).
4. Verify that `_pit_time` in the output JSON remains stable and matches the stabilized master clock rather than the raw `mCurrentTime` jumps.
