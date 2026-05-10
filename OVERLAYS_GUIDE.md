# AMS2 Auto Director Overlays Guide

Welcome to the AMS2 Auto Director dynamic overlays system! This system provides highly accurate, zero-latency HTML/CSS overlays for your live streams or replays. By running a local Websocket server, it injects Automobilista 2 telemetry data directly into your browser or OBS without the need for heavy middleware like SimHub.

## How to Access

When the **AMS2 Auto Director 4.0** is running, it automatically hosts a local web server on port `8765`.

1. Open your browser or OBS Browser Source.
2. Navigate to: `http://localhost:8765/`
3. You will be greeted with the main **Dashboard Portal**, which lists all available overlays.

## How to Add Overlays to OBS Studio

Adding these overlays to your livestream or recording is very simple:

1. In OBS, go to the **Sources** dock and click the **+** button.
2. Select **Browser**. Name it something like "F1TV Leaderboard".
3. In the properties window, check the box for **Local file** to FALSE (leave it unchecked).
4. Set the **URL** to the specific overlay address (e.g., `http://localhost:8765/f1tv_overlay.html`).
5. Set the Width and Height to match your canvas (usually `1920`x`1080`).
6. **CRITICAL:** Delete all text in the "Custom CSS" box, except for this: `body { background-color: rgba(0, 0, 0, 0); margin: 0px auto; overflow: hidden; }` to ensure the background is completely transparent!
7. Click OK. The overlay will now appear perfectly on top of your gameplay!

---

## 1. F1TV Leaderboard Overlay (`f1tv_overlay.html`)

A highly polished, dynamic F1TV-style broadcast graphic that automatically reacts to the game state.

**Features:**
* **Dynamic Mini & Full Leaderboards:** Displays driver positions, gaps, tyre compound colors, and stint ages.
* **Fastest Lap/Sector Triggers:** Automatically flashes and highlights when a driver sets a fastest sector or lap.
* **Pit Tracker:** Tracks and displays an animated, rotating pit stop timer when cars enter the pit lane.
* **Smart Auto-Hide:** When the Auto Director switches to a "Cockpit" camera, the broadcast elements (like the leaderboard) can automatically slide off-screen to make room for the Halo HUD. (Note: You can override this using the Control Panel).

---

## 2. F1TV Overlay Control Panel (`f1tv_control.html`)

Because interacting with overlays inside OBS is difficult, we built a dedicated Remote Control Panel. 

**How to use:**
1. Add `http://localhost:8765/f1tv_overlay.html` as a Browser Source in OBS.
2. On a second monitor, or even a smartphone connected to your local network, navigate to `http://localhost:8765/f1tv_control.html`.
3. You will see a live control board. Clicking any toggle (e.g., turning off the Mini Leaderboard) will instantly trigger a Websocket command that hides the element on your OBS stream with a smooth animation.
4. **Presets:** Use the "Broadcast" or "Cockpit" preset buttons to quickly configure the overlay for your current scene.

---

## 3. F1TV Halo HUD (`F1TV - Halo HUD/f1_hud.html`)

An exact, 1:1 replica of the modern F1TV Halo Graphic used for onboard shots. 

**Features:**
* **Authentic Styling:** Replicated using offset-shadow styling, exact F1 fonts, and layered SVGs.
* **Dynamic RPM Bar:** The RPM stroke scales precisely against the maximum RPM of the specific car you are viewing.
* **Live Telemetry:** Throttle and Brake meters, exact Speed (MPH/KMH), and immediate Gear shifts.
* **ERS Deployment:** Fully mapped ERS radial glow ring that responds to deployment.

*Pro-Tip: Run this as a transparent Browser Source directly over your AMS2 Cockpit/T-Cam views.*

---

## 4. MM Dash (SimHub Conversion) (`mmdash/index.html`)

A transparent overlay designed to highlight close battles, originally converted from a SimHub dashboard.

**Features:**
* **Ahead/Behind Indicators:** Shows the driver immediately ahead and behind the currently focused car, including their live gaps.
* **Red/Green Triangles:** Easy-to-read dynamic arrows showing if the gap is closing or expanding.
* **Custom Team Colors & Logos:** Powered by an external JSON configuration file!

**How to customize teams:**
Open `dashboard/mmdash/drivers_teams.json` in any text editor. You can map exact driver names to specific teams, assign Hex color codes, and assign team logos. The overlay fetches this file automatically, meaning you can update team colors mid-race without touching any code!

---

## 5. Now Watching / Battle For (`now_watching.html`)

A lightweight, streamlined overlay that sits at the bottom of the screen.

**Features:**
* **Current Focus:** Displays the name of the driver the Auto Director is currently watching.
* **Live Gaps:** Shows immediate gaps to the cars in front and behind.
* **Unobtrusive:** Perfect for minimalist streams that don't want heavy TV-style graphics covering the screen.

---

## 6. Replay Logger & Analyser (`replay_logger.html`)

A completely browser-based tool that silently monitors your live race and generates the exact Timeline Log file the Auto Director needs.

**Features:**
* **Zero Setup:** Open the page, set your close battle gap, and click "Start Capture".
* **Smart Logic:** Tracks exactly what the Python `race_analyser` script used to track: overtakes, accidents, close battles, and leader laps.
* **Easy Export:** When the race finishes, click "Stop & Download" and your browser will save a `.txt` log perfectly formatted for the Auto Director's Replay mode!

---

## 7. Diagnostic & Data Feed (`diagnostic.html`)

A raw technical viewer for developers and curious users.

**Features:**
* **Raw JSON Stream:** Watch the 60Hz websocket payload scroll in real-time.
* **State Verification:** A great tool to check if the Auto Director is properly hooked into the AMS2 Shared Memory or UDP feed. If graphics aren't updating, check this page first!
