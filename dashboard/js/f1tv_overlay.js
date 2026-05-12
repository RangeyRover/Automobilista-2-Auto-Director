const components = [
            { id: 'full-leaderboard', name: 'Full Leaderboard', default: true, type: 'broadcast' },
            { id: 'mini-leaderboard', name: 'Mini Leaderboard', default: true, type: 'broadcast' },
            { id: 'driver-name', name: 'Driver Name', default: true, type: 'broadcast' },
            { id: 'lap-timer', name: 'Lap Timer', default: true, type: 'broadcast' },
            { id: 'live-speed', name: 'Live Speed', default: false, type: 'cockpit' },
            { id: 'ahead-behind', name: 'Ahead & Behind', default: true, type: 'broadcast' },
            { id: 'session-info', name: 'Session Info', default: true, type: 'broadcast' },
            { id: 'fastest-lap', name: 'Fastest Lap', default: true, type: 'broadcast' },
            { id: 'fastest-sectors', name: 'Fastest Sectors', default: true, type: 'broadcast' },
            { id: 'weather-panel', name: 'Weather', default: true, type: 'broadcast' },
            { id: 'pit-window', name: 'Pit Window', default: true, type: 'broadcast' },
            { id: 'pit-timer', name: 'Pit Timer', default: true, type: 'broadcast' },
            { id: 'connection-status', name: 'Connection Status', default: true, type: 'broadcast' }
        ];

        let state = null;
        let lastFastestLapTimestamp = 0;
        let prevFastestSectors = [0,0,0];
        let ws;

        // HALO HUD VARS
        const throttleMeter = document.getElementById('hud-throttle-meter');
        const brakeMeter = document.getElementById('hud-brake-meter');
        const rpmLine = document.getElementById('hud-rpm-line');
        const maxRpmText = document.getElementById('hud-max-rpm-text');
        const kmhMain = document.getElementById('hud-kmh-main');
        const kmhShadow = document.getElementById('hud-kmh-shadow');
        const mphMain = document.getElementById('hud-mph-main');
        const mphShadow = document.getElementById('hud-mph-shadow');
        
        const throttleConfigs = {
            10: { left: 1449.3, top: 344.8, width: 118.7, height: 39.9 },
            20: { left: 1449.3, top: 330.3, width: 121.8, height: 54.6 },
            30: { left: 1449.3, top: 316.3, width: 126.0, height: 68.3 },
            40: { left: 1449.3, top: 301.8, width: 129.2, height: 83.0 },
            50: { left: 1449.3, top: 284.8, width: 133.4, height: 99.8 },
            60: { left: 1449.4, top: 268.3, width: 136.5, height: 116.6 },
            70: { left: 1449.0, top: 251.8, width: 140.7, height: 133.4 },
            80: { left: 1449.3, top: 235.0, width: 143.9, height: 150.2 },
            90: { left: 1449.3, top: 217.3, width: 148.1, height: 168.0 },
            100: { left: 1449.6, top: 197.3, width: 151.2, height: 188.0 }
        };

        const gearConfigs = {
            0: { label: 'N', left: 1648, top: 314, width: 39.6, height: 35.4 },
            1: { label: '1', left: 1712, top: 335, width: 24.6, height: 33.6 },
            2: { label: '2', left: 1768, top: 359, width: 31.8, height: 34.8 },
            3: { label: '3', left: 1827, top: 386, width: 31.8, height: 34.2 },
            4: { label: '4', left: 1884, top: 424, width: 30.0, height: 30.6 },
            5: { label: '5', left: 1943, top: 453, width: 31.8, height: 36.0 },
            6: { label: '6', left: 2000, top: 495, width: 30.0, height: 31.8 },
            7: { label: '7', left: 2059, top: 532, width: 29.4, height: 31.8 },
            8: { label: '8', left: 2111, top: 577, width: 31.2, height: 36.6 }
        };

        let lastGear = null;
        let speedChangeCount = 0;
        let rpmChangeCount = 0;
        let lastSpeed = -1;
        let lastRpm = -1;
        let teamLookup = {};

        async function fetchTeamLookup() {
            try {
                const res = await fetch('team_lookup.json?t=' + new Date().getTime());
                if (res.ok) {
                    const data = await res.json();
                    for (const key in data) {
                        teamLookup[key] = data[key].color;
                    }
                }
            } catch (e) {
                console.error("Failed to load team_lookup.json", e);
            }
        }

        function initSettings() {
            const grid = document.getElementById('settings-checkboxes');
            components.forEach(c => {
                const label = document.createElement('label');
                const cb = document.createElement('input');
                cb.type = 'checkbox';
                cb.id = `toggle-${c.id}`;
                
                const saved = localStorage.getItem(`toggle-${c.id}`);
                if (saved !== null) {
                    cb.checked = saved === 'true';
                } else {
                    cb.checked = c.default;
                }
                
                cb.addEventListener('change', (e) => {
                    localStorage.setItem(`toggle-${c.id}`, e.target.checked);
                    updateVisibility();
                });
                
                label.appendChild(cb);
                label.appendChild(document.createTextNode(' ' + c.name));
                grid.appendChild(label);
            });

            // Parse URL params
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('preset')) {
                applyPreset(urlParams.get('preset'));
            }
            updateVisibility();
        }

        const presets = {
            'broadcast': ['full-leaderboard', 'mini-leaderboard', 'driver-name', 'lap-timer', 'ahead-behind', 'session-info', 'fastest-lap', 'fastest-sectors', 'weather-panel', 'pit-window', 'pit-timer', 'connection-status'],
            'cockpit': ['mini-leaderboard', 'fastest-lap', 'weather-panel', 'pit-window', 'pit-timer']
        };

        function applyPreset(preset) {
            components.forEach(c => {
                const cb = document.getElementById(`toggle-${c.id}`);
                if (preset === 'all') cb.checked = true;
                else if (preset === 'none') cb.checked = false;
                else cb.checked = presets[preset].includes(c.id);
                
                localStorage.setItem(`toggle-${c.id}`, cb.checked);
            });
            updateVisibility();
        }

        function updateVisibilityMode() {
            if (!state || !state.director) return;
            const camType = state.director.camera_type || "tv_cam";
            
            // Cockpit mode vs Broadcast mode
            const isCockpit = (camType === "cockpit");
            
            document.querySelectorAll('.cockpit-only').forEach(el => {
                if (isCockpit) el.classList.remove('mode-hidden');
                else el.classList.add('mode-hidden');
            });
            
            document.querySelectorAll('.broadcast-only').forEach(el => {
                if (isCockpit) el.classList.add('mode-hidden');
                else el.classList.remove('mode-hidden');
            });

            // T008: Halo HUD — cockpit-only component
            const haloHud = document.getElementById('halo-hud');
            if (haloHud) {
                if (isCockpit) haloHud.classList.remove('mode-hidden');
                else haloHud.classList.add('mode-hidden');
            }
        }

        function updateVisibility() {
            // First apply visibility mode if state is available
            updateVisibilityMode();

            // Then apply user settings (overrides mode logic if toggled OFF)
            components.forEach(c => {
                const el = document.getElementById(c.id);
                const cb = document.getElementById(`toggle-${c.id}`);
                if (cb && el) {
                    if (!cb.checked) {
                        el.style.display = 'none'; // User turned it off explicitly
                    } else {
                        // User turned it on; check if mode-hidden allows it
                        if (el.classList.contains('mode-hidden')) {
                            el.style.display = 'none';
                        } else {
                            el.style.display = '';
                        }
                    }
                }
            });
        }

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                e.preventDefault();
                toggleSettings();
            }
        });

        function toggleSettings() {
            const p = document.getElementById('settings-panel');
            p.style.display = p.style.display === 'none' ? 'block' : 'none';
        }

        function connect() {
            ws = new WebSocket('ws://' + location.host + '/ws');
            const statusEl = document.getElementById('connection-status');
            
            ws.onopen = () => {
                statusEl.innerText = "CONNECTED";
                statusEl.style.color = "var(--f1-timing-green)";
            };
            
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                
                // Handle remote config updates from f1tv_control.html
                if (data.type === "f1tv_config") {
                    for (const key in data.config) {
                        const cb = document.getElementById(`toggle-${key}`);
                        if (cb && cb.checked !== data.config[key]) {
                            cb.checked = data.config[key];
                        }
                    }
                    updateVisibility();
                    return;
                }
                
                state = data;
                updateVisibility(); // Always check mode logic when state updates
                updateAll();
                // T024: Update Halo HUD telemetry (only does work when cockpit mode active)
                updateHaloHUD(state);
            };
            
            ws.onclose = () => {
                statusEl.innerText = "DISCONNECTED";
                statusEl.style.color = "var(--f1-red)";
                setTimeout(connect, 2000);
            };
        }

        function formatTime(sec) {
            if (sec <= 0) return "--:--.---";
            const m = Math.floor(sec / 60);
            const s = Math.floor(sec % 60);
            const ms = Math.floor((sec % 1) * 1000);
            return `${m}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
        }

        function formatGap(gap) {
            if (typeof gap === 'string') return gap;
            if (gap <= 0) return "";
            return `+${gap.toFixed(3)}s`;
        }
        
        function getLastName(name) {
            if (!name) return "UNK";
            const parts = name.split(' ');
            const last = parts.length > 1 ? parts[parts.length-1] : parts[0];
            return last.toUpperCase();
        }

        function getTeamColor(driverName, carClass) {
            // First check if a specific driver is mapped in team_lookup.json
            if (teamLookup[driverName]) return teamLookup[driverName];
            // Otherwise fallback to car class mapping
            return teamLookup[carClass] || "var(--f1-dark-grey)";
        }

        function getDamageColor(val) {
            val = val || 0;
            if (val < 0.2) return "#00FF00";
            if (val < 0.6) return "#FFD700";
            return "#FF0000";
        }

        function updateAll() {
            if (!state) return;

            // Driver Name
            const dn = document.getElementById('driver-name');
            const vp = state.viewed.position;
            const vn = state.viewed.name;
            const viewedIdx = state.viewed_index;
            
            let carClass = "";
            let nationality = "";
            let viewedLb = state.leaderboard.find(x => x.name === vn);
            if (viewedLb) {
                carClass = viewedLb.car_class;
                nationality = viewedLb.nationality;
            }
            
            let flagHTML = nationality ? `<img src="https://flagcdn.com/w20/${nationality}.png" srcset="https://flagcdn.com/w40/${nationality}.png 2x" height="15" style="vertical-align:middle; margin-right:8px; margin-top:-2px; border-radius:2px;">` : "";
            
            dn.innerHTML = `
                <div class="team-strip" style="background:${getTeamColor(vn, carClass)}"></div>
                <div class="pos-box">${vp || '-'}</div>
                <div>${flagHTML}${vn || 'Waiting...'}</div>
            `;

            // Lap Timer
            const lt = document.getElementById('lap-timer');
            if (viewedLb && viewedLb.current_sectors) {
                const secs = viewedLb.current_sectors;
                const pBests = viewedLb.fastest_sectors || [0,0,0];
                const wBests = state.session.world_fastest_sectors || [0,0,0];
                
                // activeIdx represents which sector is currently ticking
                if (typeof window._activeIdx === 'undefined') window._activeIdx = -1;
                
                if (viewedLb.current_sector === 1 && secs[2] === 0) window._activeIdx = 0;
                else if (viewedLb.current_sector === 2) window._activeIdx = 1;
                else if (viewedLb.current_sector === 3) window._activeIdx = 2;
                else if (viewedLb.current_sector === 1 && secs[2] > 0) window._activeIdx = -1;
                
                let activeIdx = window._activeIdx;
                
                function getSecHtml(val, idx) {
                    if (val <= 0) return `<div style="color:var(--f1-light-grey); width:110px;">S${idx+1}: --.---</div>`;
                    
                    let isActive = (idx === activeIdx);
                    let col = "var(--f1-white)";
                    
                    if (!isActive) {
                        if (wBests[idx] > 0 && val <= wBests[idx] + 0.005) col = "var(--f1-timing-purple)";
                        else if (pBests[idx] > 0 && val <= pBests[idx] + 0.005) col = "var(--f1-timing-green)";
                        else col = "var(--f1-timing-yellow)";
                    }
                    
                    return `<div style="color:${col}; width:110px; font-weight:${isActive ? 'normal' : 'bold'}; text-shadow:${isActive ? 'none' : '0 0 8px '+col};">S${idx+1}: ${val.toFixed(3)}</div>`;
                }

                const s1Html = getSecHtml(secs[0], 0);
                const s2Html = getSecHtml(secs[1], 1);
                const s3Html = getSecHtml(secs[2], 2);
                
                const lap = state.viewed.last_lap > 0 ? formatTime(state.viewed.last_lap) : "--:--.---";
                lt.innerHTML = `
                    <div style="width:150px; font-weight:bold;">LAP: ${lap}</div>
                    ${s1Html}
                    ${s2Html}
                    ${s3Html}
                `;
            }

            // Live Speed
            const ls = document.getElementById('live-speed');
            ls.innerHTML = `${Math.round(state.viewed.speed_kph || 0)} <span style="font-size:24px">KPH</span>`;

            // Ahead & Behind
            const ab = document.getElementById('ahead-behind');
            let abHTML = "";
            let hasCloseCar = false;
            if (state.ahead && state.ahead.name) {
                abHTML += `<div>▲ ${state.ahead.name} <span class="gap-up">${formatGap(state.ahead.gap_seconds)}</span></div>`;
                if (state.ahead.gap_seconds > 0 && state.ahead.gap_seconds <= 0.5) {
                    hasCloseCar = true;
                }
            }
            if (state.behind && state.behind.name) {
                abHTML += `<div>▼ ${state.behind.name} <span class="gap-down">${formatGap(state.behind.gap_seconds)}</span></div>`;
                if (state.behind.gap_seconds > 0 && state.behind.gap_seconds <= 0.5) {
                    hasCloseCar = true;
                }
            }
            ab.innerHTML = abHTML;

            if (lt) {
                if (hasCloseCar) {
                    lt.classList.add('close-car-hidden');
                } else {
                    lt.classList.remove('close-car-hidden');
                }
            }

            // Session Info
            const si = document.getElementById('session-info');
            const rain = state.weather.rain_density || 0;
            const snow = state.weather.snow_density || 0;
            let icon = '☀️';
            if (snow > 0.1) icon = '❄️';
            else if (rain > 0.7) icon = '⛈️';
            else if (rain > 0.3) icon = '🌧️';
            else if (rain > 0.1) icon = '🌦️';
            
            const rem = state.session.time_remaining || 0;
            const h = Math.floor(rem / 3600);
            const m = Math.floor((rem % 3600) / 60);
            const s = Math.floor(rem % 60);
            const tStr = `${h}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}`;
            
            const lapsInEvent = state.session.laps_in_event || 0;
            const lapDisplay = lapsInEvent > 0 ? `Lap ${state.session.leader_lap || 0} / ${lapsInEvent}` : `Lap ${state.session.leader_lap || 0}`;
            
            si.innerHTML = `
                <div style="font-size:18px; font-weight:bold;">${state.session.track_name || 'Track'} ${icon}</div>
                <div>${lapDisplay}</div>
                <div style="font-variant-numeric:tabular-nums;">${tStr}</div>
            `;

            // Main Leaderboard
            const mlb = document.getElementById('mini-leaderboard');
            let mlbHTML = "";
            state.leaderboard.forEach(driver => {
                const isViewed = driver.name === vn;
                const tc = getTeamColor(driver.name, driver.car_class);
                
                let tCol = "#FFFFFF";
                if (driver.tyre_compound) {
                    const comp = driver.tyre_compound.toLowerCase();
                    if (comp.includes('soft')) tCol = "#E10600";
                    else if (comp.includes('medium')) tCol = "#FFD700";
                    else if (comp.includes('inter')) tCol = "#00FF00";
                    else if (comp.includes('wet')) tCol = "#0000FF";
                }

                mlbHTML += `
                    <div class="lb-row ${isViewed ? 'viewed' : ''}">
                        <div style="width:20px; text-align:right; flex-shrink:0;">${driver.pos}</div>
                        <div class="team-strip" style="background:${tc}; width:4px; height:16px; flex-shrink:0;"></div>
                        <div style="flex-grow:1; min-width:140px; display:flex; align-items:center; font-weight:bold; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
                            ${driver.nationality ? `<img src="https://flagcdn.com/w20/${driver.nationality}.png" height="11" style="margin-right:8px; border-radius:1px; flex-shrink:0;">` : ''}
                            <span style="overflow:hidden; text-overflow:ellipsis;">${getLastName(driver.name)}</span>
                        </div>
                        <div class="tyre-info">
                            <span style="color:${tCol}; margin-right: 2px; font-size: 12px;" title="${driver.tyre_compound}">●</span>${driver.tyre_stint_laps > 0 ? driver.tyre_stint_laps : 'NEW'}
                        </div>
                        <div style="text-align:right; width:65px; flex-shrink:0;">${driver.pos === 1 ? 'LEADER' : formatGap(driver.gap)}</div>
                    </div>
                `;
            });
            mlb.innerHTML = mlbHTML;

            // Full Leaderboard
            const flb = document.getElementById('full-leaderboard');
            let flbHTML = "";
            state.leaderboard.forEach(driver => {
                const isViewed = driver.name === vn;
                const tc = getTeamColor(driver.name, driver.car_class);
                
                let tCol = "#FFFFFF";
                if (driver.tyre_compound) {
                    const comp = driver.tyre_compound.toLowerCase();
                    if (comp.includes('soft')) tCol = "#E10600";
                    else if (comp.includes('medium')) tCol = "#FFD700";
                    else if (comp.includes('inter')) tCol = "#00FF00";
                    else if (comp.includes('wet')) tCol = "#0000FF";
                }

                flbHTML += `
                    <div class="flb-row ${isViewed ? 'viewed' : ''}">
                        <div style="width:20px; text-align:right; flex-shrink:0;">${driver.pos}</div>
                        <div class="team-strip" style="background:${tc}; width:4px; height:16px; flex-shrink:0;"></div>
                        <div style="flex-grow:1; min-width:140px; display:flex; align-items:center; font-weight:bold; overflow:hidden; white-space:nowrap; text-overflow:ellipsis;">
                            ${driver.nationality ? `<img src="https://flagcdn.com/w20/${driver.nationality}.png" height="11" style="margin-right:8px; border-radius:1px; flex-shrink:0;">` : ''}
                            <span style="overflow:hidden; text-overflow:ellipsis;">${getLastName(driver.name)}</span>
                        </div>
                        <div class="tyre-info" style="margin-right: 5px;">
                            <span style="color:${tCol}; margin-right: 2px; font-size: 12px;" title="${driver.tyre_compound}">●</span>${driver.tyre_stint_laps > 0 ? driver.tyre_stint_laps : 'NEW'}
                        </div>
                        <div style="width:65px; text-align:right; flex-shrink:0;">${formatTime(driver.last_lap)}</div>
                        <div style="width:65px; text-align:right; flex-shrink:0;">${driver.pos === 1 ? 'LEADER' : formatGap(driver.gap)}</div>
                        ${driver.pit > 0 ? `<div style="background:var(--f1-red); color:white; padding:0 4px; border-radius:2px; font-size:10px; flex-shrink:0;" title="${driver.laps_since_last_pit > 0 ? driver.laps_since_last_pit + ' laps since pit' : ''}">P${driver.pit}</div>` : ''}
                    </div>
                `;
            });
            flb.innerHTML = flbHTML;

            // Weather
            const wp = document.getElementById('weather-panel');
            const air = (state.weather.ambient_temp || 0).toFixed(1);
            const trk = (state.weather.track_temp || 0).toFixed(1);
            const wind = (state.weather.wind_speed || 0).toFixed(1);
            wp.innerHTML = `
                <div>AIR: <span style="display:inline-block; width:45px; text-align:right; font-variant-numeric:tabular-nums;">${air}</span>°C</div>
                <div>TRK: <span style="display:inline-block; width:45px; text-align:right; font-variant-numeric:tabular-nums;">${trk}</span>°C</div>
                <div style="grid-column: span 2">RAIN: <div style="display:inline-block; width:100px; height:8px; background:var(--f1-dark-grey);"><div style="width:${(rain*100)}%; height:100%; background:var(--f1-timing-purple);"></div></div></div>
                <div style="grid-column: span 2">WIND: <span style="display:inline-block; width:45px; text-align:right; font-variant-numeric:tabular-nums;">${wind}</span> km/h</div>
            `;

            // Pit Window
            const pw = document.getElementById('pit-window');
            if (state.session.enforced_pit_stop_lap > 0) {
                pw.style.display = '';
                const comp = (state.viewed.tyre_compound && state.viewed.tyre_compound[0]) ? state.viewed.tyre_compound[0] : 'Unknown';
                let cClass = "tyre-hard";
                if (comp.toLowerCase().includes('soft')) cClass = "tyre-soft";
                else if (comp.toLowerCase().includes('medium')) cClass = "tyre-medium";
                else if (comp.toLowerCase().includes('inter')) cClass = "tyre-inter";
                else if (comp.toLowerCase().includes('wet')) cClass = "tyre-wet";
                pw.innerHTML = `
                    <div style="font-weight:bold; color:var(--f1-red);">PIT WINDOW</div>
                    <div>Mandatory Lap: ${state.session.enforced_pit_stop_lap}</div>
                    <div>Tyre: <span class="${cClass}">●</span> ${comp}</div>
                `;
            } else {
                pw.style.display = 'none';
            }

            // Fastest Lap Animation
            const flEvent = state.events?.fastest_lap;
            if (flEvent && flEvent.timestamp > 0 && flEvent.timestamp !== lastFastestLapTimestamp) {
                if (lastFastestLapTimestamp === 0) {
                    lastFastestLapTimestamp = flEvent.timestamp; // Silent init
                } else {
                    lastFastestLapTimestamp = flEvent.timestamp;
                    const fl = document.getElementById('fastest-lap');
                    fl.innerHTML = `
                        <div style="font-size:14px; opacity:0.8;">FASTEST LAP</div>
                        <div style="font-weight:bold;">${flEvent.driver_name} - ${formatTime(flEvent.lap_time)}</div>
                    `;
                    
                    // Force animation reflow and reset CSS state
                    fl.classList.remove('hidden');
                    fl.classList.remove('fade-anim');
                    fl.style.opacity = '1';
                    void fl.offsetWidth; // trigger reflow
                    fl.style.opacity = '';
                    fl.classList.add('fade-anim');
                    
                    // Also trigger fastest sectors ONLY when a fastest lap is set
                    const newSectors = state.session.world_fastest_sectors;
                    if (newSectors && (newSectors[0] > 0 || newSectors[1] > 0 || newSectors[2] > 0)) {
                        const fs = document.getElementById('fastest-sectors');
                        fs.innerHTML = `
                            <div style="font-size:12px; opacity:0.8;">FASTEST SECTORS</div>
                            <div>S1: ${newSectors[0] > 0 ? newSectors[0].toFixed(3) : '--.---'}</div>
                            <div>S2: ${newSectors[1] > 0 ? newSectors[1].toFixed(3) : '--.---'}</div>
                            <div>S3: ${newSectors[2] > 0 ? newSectors[2].toFixed(3) : '--.---'}</div>
                        `;
                        fs.classList.remove('hidden');
                        fs.classList.remove('fade-anim-right');
                        fs.style.opacity = '1';
                        void fs.offsetWidth;
                        fs.style.opacity = '';
                        fs.classList.add('fade-anim-right');
                    }
                }
            }





            // Pit Timer
            const pt = document.getElementById('pit-timer');
            if (state.pit_events && state.pit_events.length > 0) {
                // Drop if duration > 60s
                let activePits = state.pit_events.filter(ev => (ev.duration || 0) <= 60);
                
                // Keep only the 3 most recent
                if (activePits.length > 3) {
                    activePits = activePits.slice(activePits.length - 3);
                }

                if (activePits.length > 0) {
                    pt.innerHTML = activePits.map(ev => {
                        let durStr = formatTime(ev.duration || 0);
                        if (durStr.startsWith('0:')) durStr = durStr.substring(2);
                        
                        return `
                            <div class="pit-box ${ev.in_progress ? 'pit-active' : ''}">
                                <div style="font-size:11px; opacity:0.9; font-weight:bold; letter-spacing:1px; margin-bottom:2px;">PIT STOP</div>
                                <div style="font-size:14px; font-weight:bold; margin-bottom:4px;">${ev.driver_name}</div>
                                <div style="font-size:20px; font-weight:bold; margin-bottom:4px; font-variant-numeric: tabular-nums;">${durStr}</div>
                                <div style="display:flex; gap:6px; justify-content:center; font-size:10px;">
                                    <div style="background:rgba(0,0,0,0.5); padding:2px 4px; border-radius:3px;">PIT ${ev.pit_count}</div>
                                    ${ev.laps_since_last_pit >= 0 ? `<div style="background:rgba(0,0,0,0.5); padding:2px 4px; border-radius:3px;">${ev.laps_since_last_pit} LAPS</div>` : ''}
                                </div>
                            </div>
                        `;
                    }).join('');

                    if (pt.classList.contains('mode-hidden')) {
                        pt.classList.add('hidden');
                    } else {
                        pt.classList.remove('hidden');
                    }
                } else {
                    pt.classList.add('hidden');
                    pt.innerHTML = '';
                }
            } else {
                pt.classList.add('hidden');
                pt.innerHTML = '';
            }
        }

        function updateHaloHUD(state) {
            if (!state || !state.viewed) return;
            const t = state.viewed;
            


            // Track actual data change rate
                        if (t.speed_kph !== lastSpeed) {
                            speedChangeCount++;
                            lastSpeed = t.speed_kph;
                        }
                        if (t.rpm !== lastRpm) {
                            rpmChangeCount++;
                            lastRpm = t.rpm;
                        }
                        // Throttle comes in as 0.0 to 1.0. Snap it to intervals of 10 for the PNGs: 10, 20... 100
                        let throttlePct = Math.round(t.throttle * 10) * 10;
                        if (throttlePct > 100) throttlePct = 100;
                        
                        if (throttlePct <= 0) {
                            throttleMeter.style.opacity = '0';
                        } else {
                            const conf = throttleConfigs[throttlePct];
                            throttleMeter.style.opacity = '1';
                            throttleMeter.style.backgroundImage = `url('F1TV - Halo HUD/_assets/${throttlePct}.png')`;
                            throttleMeter.style.left = conf.left + 'px';
                            throttleMeter.style.top = conf.top + 'px';
                            throttleMeter.style.width = conf.width + 'px';
                            throttleMeter.style.height = conf.height + 'px';
                        }
                        
                        // Speed updates
                        const kmh = Math.round(t.speed_kph);
                        const mph = Math.round(t.speed_kph * 0.621371);
                        
                        kmhMain.innerText = kmh;
                        kmhShadow.innerText = kmh;
                        mphMain.innerText = mph;
                        mphShadow.innerText = mph;

                        // Gear updates
                        let currentGear = t.gear;
                        if (currentGear !== lastGear) {
                            // Turn OFF all gears first
                            for (let i = 0; i <= 8; i++) {
                                const el = document.getElementById('hud-gear-' + i);
                                if (!el) continue;
                                const conf = gearConfigs[i];
                                el.style.backgroundImage = `url('F1TV - Halo HUD/_assets/${conf.label}.png')`;
                                el.style.left = conf.left + 'px';
                                el.style.top = conf.top + 'px';
                                el.style.width = conf.width + 'px';
                                el.style.height = conf.height + 'px';
                            }
                            
                            // Turn ON current gear
                            if (currentGear >= 0 && currentGear <= 8) {
                                const el = document.getElementById('hud-gear-' + currentGear);
                                const conf = gearConfigs[currentGear];
                                if (el) {
                                    el.style.backgroundImage = `url('F1TV - Halo HUD/_assets_Gears/${conf.label} on.png')`;
                                    el.style.left = (conf.left - 7.8) + 'px';
                                    el.style.top = (conf.top - 7.5) + 'px';
                                    el.style.width = (conf.width + 15.6) + 'px';
                                    el.style.height = (conf.height + 15.0) + 'px';
                                }
                            }
                            lastGear = currentGear;
                        }

                        // Brake updates (Simulated segments using exact radial projection)
                        if (t.brake <= 0) {
                            brakeMeter.style.opacity = '0';
                        } else {
                            brakeMeter.style.opacity = '0.8';
                            let brakePct = Math.round(t.brake * 10) * 10;
                            
                            if (brakePct >= 100) {
                                brakeMeter.style.clipPath = 'none';
                            } else {
                                // Relative center of speedometer to brake div
                                const Cx = 1223.1 - 855.3; // 367.8
                                const Cy = 251.8 - 214.8;  // 37.0
                                const H = 200.5;
                                const W = 130.2;
                                const X_mid = W / 2;

                                // Y height of the current segment cut (0 is top, H is bottom)
                                const Y = ((100 - brakePct) / 100) * H;

                                // Slope of the radial line from center (Cx, Cy) through (X_mid, Y)
                                const m = (Y - Cy) / (X_mid - Cx);

                                // Pixel Y coordinates at left (X=0) and right (X=W)
                                const Y_left_px = m * (0 - Cx) + Cy;
                                const Y_right_px = m * (W - Cx) + Cy;

                                // Convert to percentages
                                const Y_left_pct = (Y_left_px / H) * 100;
                                const Y_right_pct = (Y_right_px / H) * 100;

                                // Use 200% for bottom vertices so polygon never self-intersects
                                brakeMeter.style.clipPath = `polygon(0 200%, 100% 200%, 100% ${Y_right_pct}%, 0 ${Y_left_pct}%)`;
                            }
                        }

                        // Linear RPM bar under gears (scales dynamically to car's max revs)
                        const maxRpm = t.max_rpm || 15000;
                        let rpmPct = (t.rpm / maxRpm) * 100;
                        if (rpmPct < 0) rpmPct = 0;
                        if (rpmPct > 100) rpmPct = 100;
                        const insetRight = 100 - rpmPct;
                        rpmLine.style.clipPath = `inset(0 ${insetRight}% 0 0)`;
                        
                        // Update the dynamic text at the end of the RPM line
                        // Round up to a single integer (e.g. 7600 -> 8)
                        maxRpmText.innerText = Math.ceil(maxRpm / 1000);
        }


        fetchTeamLookup();
        initSettings();
        connect();
