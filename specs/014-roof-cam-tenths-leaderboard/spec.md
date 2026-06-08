# Feature Specification: Roof Camera Session Info Overlay & Tenths Leaderboard Format

**Feature Branch**: `014-roof-cam-tenths-leaderboard`  
**Created**: 2026-06-08  
**Status**: Draft  
**Input**: User description: "When going to roof camera/halo hud it will not show the session info even if it is enabled. I tried clicking it as well and no dice. I tried to make the leaderboard go to tenths via Ai but didn't have any luck. Is there any chance that is something you might be able to do? I think it will clean up the look and will hide the pauses/gaps in data much better. Is it possible for that text to be bigger overall or is it maxed out for the leaderboard?"

## Clarifications

### Session 2026-06-08

- Q: When "Tenths Timing" is enabled, should the bottom-center viewed driver's lap timer and active sector times also be formatted to tenths of a second, or should they always remain in thousandths (milliseconds)? → A: Keep bottom-center viewed driver timings always in thousandths.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Session Info Visibility on Roof Camera (Priority: P1)

When using the Auto Director, the camera switches between trackside cameras (broadcast) and roof/cockpit cameras (cockpit/halo HUD). The session info overlay (which displays track name, current weather icon, leader lap / total laps, and time remaining) should remain visible when switching to the roof camera or cockpit camera if it is enabled in the control settings. It must obey the user's manual checklist selection and preset buttons (Broadcast vs Cockpit).

**Why this priority**: High value. During race broadcasts, session information (e.g. weather, laps remaining) is critical context that shouldn't disappear when the camera angle switches to a driver's onboard view.

**Independent Test**:
1. Open the F1TV Overlay and Control Panel.
2. Ensure the "Session Info" component is enabled (checked) in the settings.
3. Trigger a camera change to "roof" or "cockpit".
4. Verify that the Session Info panel remains visible on the screen.
5. In the control panel, click the "Cockpit" preset button (which disables Session Info by default) and verify it hides.
6. Manually toggle the "Session Info" checkbox off and on to verify it hides and shows as expected.

**Acceptance Scenarios**:

1. **Given** Session Info is enabled, **When** camera type is "tv_cam", **Then** Session Info is visible.
2. **Given** Session Info is enabled, **When** camera type is "roof", **Then** Session Info remains visible.
3. **Given** Session Info is disabled (via checkbox or Cockpit preset), **When** camera type is "roof", **Then** Session Info is hidden.

---

### User Story 2 - Selectable Leaderboard Timing in Tenths (Priority: P2)

To clean up the broadcast look and hide small pauses/gaps in telemetry data, the time gaps in the mini and full leaderboards, and the last lap times in the full leaderboard, should be formatted to tenths of a second (1 decimal place) instead of thousandths (3 decimal places). This formatting option must be selectable via a "Tenths Timing" checkbox in the settings, defaulting to enabled (tenths).

**Why this priority**: Improves overall presentation and hides minor timing jitter or data gaps, while maintaining flexibility for users who prefer precise thousandths.

**Independent Test**:
1. Run the Auto Director and view the overlay leaderboard.
2. Verify that "Tenths Timing" is enabled by default, and gaps/lap times are shown to 1 decimal place (e.g. `+1.2s`, `1:23.4`).
3. Toggle "Tenths Timing" off in the settings/control panel.
4. Verify that the timings instantly revert to thousandths (3 decimal places, e.g. `+1.234s`, `1:23.456`).

**Acceptance Scenarios**:

1. **Given** "Tenths Timing" is enabled, **When** the mini or full leaderboard renders, **Then** gaps are displayed as `+X.Ys` and lap times as `M:SS.T`.
2. **Given** "Tenths Timing" is disabled, **When** the mini or full leaderboard renders, **Then** gaps are displayed as `+X.YYYs` and lap times as `M:SS.TTT`.
3. **Given** a driver has status "PIT" or "OUT", **When** leaderboard renders, **Then** the status string is displayed unmodified regardless of the Tenths Timing setting.

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

- **FR-001**: The session-info overlay component MUST NOT be hidden automatically when the camera type is "roof" or "cockpit". It MUST be classified as an `always-visible` component.
- **FR-002**: The session-info overlay component MUST obey user configuration toggles (checkboxes) and preset actions (Broadcast vs Cockpit) in all camera modes.
- **FR-003**: A user-selectable toggle option "Tenths Timing" MUST be added to the control panel and settings, defaulting to enabled (true).
- **FR-004**: When "Tenths Timing" is enabled, leaderboard gaps in both mini-leaderboard and full-leaderboard MUST be formatted to 1 decimal place (tenths of a second) when they are numeric values.
- **FR-005**: When "Tenths Timing" is enabled, last lap times in the full-leaderboard MUST be formatted to 1 decimal place (tenths of a second) when they are valid times.
- **FR-006**: When "Tenths Timing" is disabled, leaderboard gaps and lap times MUST revert to their original millisecond (3 decimal places) formatting.
- **FR-007**: Lap times and sector times in the viewed driver's lap-timer MUST retain their original millisecond (3 decimal places) formatting regardless of the Tenths Timing setting.
- **FR-008**: Leaderboard font sizes MUST be increased from 13px to 15px.
- **FR-009**: Leaderboard layout container width and row height MUST be expanded proportionally to accommodate the larger font size.

### Key Entities

- **Overlay Component**: A visual block of the F1TV dashboard with visibility settings.
- **Leaderboard Driver Row**: An entry in the leaderboard containing position, team color, driver name, tyre info, and timing data (gap/lap time).
- **Tenths Timing Setting**: A boolean configuration that determines whether leaderboard timing details use 1 or 3 decimal places.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Switching camera to "roof" or "cockpit" maintains the visibility of the Session Info component if it is enabled.
- **SC-002**: Applying the "Cockpit" preset turns off the Session Info component, and manually checking it turns it back on, regardless of the active camera.
- **SC-003**: Toggling "Tenths Timing" instantly switches leaderboard timing displays between 1 decimal place and 3 decimal places.
- **SC-004**: All leaderboard gaps are formatted to tenths (1 decimal place) and render correctly when Tenths Timing is enabled.
- **SC-005**: Full leaderboard lap times are formatted to tenths (1 decimal place) and render correctly when Tenths Timing is enabled.
- **SC-006**: The default leaderboard font size is 15px, and layout remains clean with no overlapping text.
