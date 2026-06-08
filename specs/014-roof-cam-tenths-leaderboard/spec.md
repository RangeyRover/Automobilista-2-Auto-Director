# Feature Specification: Roof Camera Session Info Overlay & Tenths Leaderboard Format

**Feature Branch**: `014-roof-cam-tenths-leaderboard`  
**Created**: 2026-06-08  
**Status**: Draft  
**Input**: User description: "When going to roof camera/halo hud it will not show the session info even if it is enabled. I tried clicking it as well and no dice. I tried to make the leaderboard go to tenths via Ai but didn't have any luck. Is there any chance that is something you might be able to do? I think it will clean up the look and will hide the pauses/gaps in data much better. Is it possible for that text to be bigger overall or is it maxed out for the leaderboard?"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Session Info Visibility on Roof Camera (Priority: P1)

When using the Auto Director, the camera switches between trackside cameras (broadcast) and roof/cockpit cameras (cockpit/halo HUD). The session info overlay (which displays track name, current weather icon, leader lap / total laps, and time remaining) should remain visible when switching to the roof camera or cockpit camera if it is enabled in the control settings.

**Why this priority**: High value. During race broadcasts, session information (e.g. weather, laps remaining) is critical context that shouldn't disappear when the camera angle switches to a driver's onboard view.

**Independent Test**:
1. Open the F1TV Overlay and Control Panel.
2. Ensure the "Session Info" component is enabled (checked) in the settings.
3. Trigger a camera change to "roof" or "cockpit".
4. Verify that the Session Info panel remains visible on the screen.

**Acceptance Scenarios**:

1. **Given** Session Info is enabled, **When** camera type is "tv_cam", **Then** Session Info is visible.
2. **Given** Session Info is enabled, **When** camera type is "roof", **Then** Session Info remains visible.
3. **Given** Session Info is disabled, **When** camera type is "roof", **Then** Session Info is hidden.

---

### User Story 2 - Leaderboard Timing in Tenths (Priority: P2)

To clean up the broadcast look and hide small pauses/gaps in telemetry data, the time gaps in the mini and full leaderboards, and the last lap times in the full leaderboard, should be formatted to tenths of a second (1 decimal place) instead of thousandths (3 decimal places).

**Why this priority**: Improves overall presentation and hides minor timing jitter or data gaps.

**Independent Test**:
1. Run the Auto Director and view the overlay leaderboard.
2. Verify that gaps are shown in the format `+X.Ys` (e.g. `+1.2s` instead of `+1.234s`).
3. Verify that lap times in the full leaderboard are shown in the format `M:SS.T` (e.g. `1:23.4` instead of `1:23.456`).

**Acceptance Scenarios**:

1. **Given** a driver is 1.256 seconds behind the leader, **When** the mini or full leaderboard renders, **Then** their gap is displayed as `+1.3s` (or appropriate rounded value).
2. **Given** a driver's last lap time was 1 minute 24.582 seconds, **When** the full leaderboard renders, **Then** the lap time is displayed as `1:24.5`.
3. **Given** a driver has status "PIT" or "OUT", **When** leaderboard renders, **Then** the status string is displayed unmodified.

---

### User Story 3 - Larger Leaderboard Text Size (Priority: P3)

The text on both the mini-leaderboard and full-leaderboard should be larger (e.g. 15px instead of 13px) to improve legibility on stream. The layout widths and heights should scale accordingly so no text is truncated.

**Why this priority**: Enhances stream readability but is non-blocking.

**Independent Test**:
1. Load the overlay.
2. Visual check: the leaderboard text should be noticeably larger than the original 13px layout.
3. Verify that long names or status strings (like "LEADER" or "+1.2s") are fully visible and do not wrap or overlap.

**Acceptance Scenarios**:

1. **Given** a leaderboard is rendered, **When** checking the CSS rules, **Then** the font size for leaderboard rows is 15px.
2. **Given** the font size is 15px, **When** leaderboard rows render, **Then** the layout has sufficient padding and width to prevent any clipping.

---

### Edge Cases

- **Rounding of Tenths**: Standard mathematical rounding (e.g. `1.25` rounds to `1.3`, `1.24` to `1.2`) must be applied to prevent truncation errors.
- **String values**: When gaps are strings (e.g. `+1 LAP` or `LEADER`), they must not be processed as numbers and must render exactly as they are.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The session-info overlay component MUST NOT be hidden when the camera type is "roof" or "cockpit". It MUST be classified as an `always-visible` component.
- **FR-002**: Leaderboard gaps in both mini-leaderboard and full-leaderboard MUST be formatted to 1 decimal place (tenths of a second) when they are numeric values.
- **FR-003**: Last lap times in the full-leaderboard MUST be formatted to 1 decimal place (tenths of a second) when they are valid times.
- **FR-004**: Sector times in the viewed driver's lap-timer MUST retain their original millisecond (3 decimal places) formatting.
- **FR-005**: Leaderboard font sizes MUST be increased from 13px to 15px.
- **FR-006**: Leaderboard layout container width and row height MUST be expanded proportionally to accommodate the larger font size.

### Key Entities

- **Overlay Component**: A visual block of the F1TV dashboard with visibility settings.
- **Leaderboard Driver Row**: An entry in the leaderboard containing position, team color, driver name, tyre info, and timing data (gap/lap time).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Switching camera to "roof" or "cockpit" maintains the visibility of the Session Info component if it is enabled.
- **SC-002**: All leaderboard gaps are formatted to tenths (1 decimal place) and render correctly.
- **SC-003**: Full leaderboard lap times are formatted to tenths (1 decimal place) and render correctly.
- **SC-004**: The default leaderboard font size is 15px, and layout remains clean with no overlapping text.
