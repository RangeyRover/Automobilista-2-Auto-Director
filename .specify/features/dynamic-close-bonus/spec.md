# Feature Specification: Dynamic Close Bonus & Session Time

## 1. Feature Description
Modify the Auto Director scoring engine to evaluate "close racing" based on an asymptotic/logarithmic proximity curve and the driver's closing speed. This guarantees that cars actively reeling in the driver ahead receive a massive camera priority spike, while static gaps provide minimal priority. Additionally, expose the session's elapsed or remaining time to the GUI.

## 2. User Scenarios
1. **Closing for an Overtake**: A driver is 0.5s behind and rapidly closing under braking. Their `Close` bonus spikes asymptotically, forcing the Auto Director to snap the camera to them right before the overtake.
2. **Drafting (No Delta)**: Two drivers are 0.5s apart but matching speed on a straight. Their bonus remains moderate because their closing speed is 0.
3. **Session Awareness**: The user glances at the Auto Director GUI and sees "Time Left: 15:30", allowing them to sync their broadcast commentary without looking at the game screen.

## 3. Functional Requirements
- **FR-1**: Telemetry Provider must track previous gaps over time to compute `closing_speed`.
- **FR-2**: Telemetry Provider must apply an Exponential Moving Average (EMA) to smooth the `closing_speed` over the polling interval.
- **FR-3**: Scoring Engine must calculate the base close bonus using the original linear curve: `(max_gap - gap) / divisor`.
- **FR-4**: Scoring Engine must apply the closing speed as an additive modifier directly to the base bonus: `bonus = base + closing_speed`. Negative closing speeds (falling behind) are retained, reducing the overall score.
- **FR-5**: Telemetry Provider must extract `mEventTimeRemaining` and `mCurrentTime` from shared memory.
- **FR-6**: The Main GUI must display the formatted session time in the top status bar.
- **FR-7**: The Main GUI treeview must include a `CloseSpd` column to observe the calculated closing speed metric.

## 4. Success Criteria
- **SC-1**: The `Close` bonus awards linear points based on gap, but drivers closing the gap receive an additive boost to their score, while those falling behind receive a penalty relative to their base gap score.
- **SC-2**: The GUI continuously displays accurate session time, explicitly showing "Rem: null" if time remaining is unavailable.
- **SC-3**: TDD test coverage remains at or above current baseline levels, specifically validating the asymptotic curve boundaries and EMA smoothing logic.

## 5. Assumptions
- The telemetry polling rate (200ms) provides sufficient fidelity to calculate closing speeds without extreme aliasing.
- The closing speed formula uses meters per second.
