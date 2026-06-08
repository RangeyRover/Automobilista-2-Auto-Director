const WS_URL = `ws://${location.host}/ws`;
let socket = null;
let lastData = null;
let expandAll = true;

const statusIndicator = document.getElementById('status-indicator');
const leaderboardContainer = document.getElementById('leaderboard-container');
const rawJsonContainer = document.getElementById('raw-json-container');
const searchInput = document.getElementById('inspector-search');
const toggleExpandBtn = document.getElementById('toggle-expand');
const pauseBtn = document.getElementById('pause-updates-btn');

let isPaused = false;

pauseBtn.addEventListener('click', () => {
    isPaused = !isPaused;
    if (isPaused) {
        pauseBtn.textContent = 'Resume Updates';
        pauseBtn.classList.add('paused');
    } else {
        pauseBtn.textContent = 'Pause Updates';
        pauseBtn.classList.remove('paused');
    }
});

function connect() {
    socket = new WebSocket(WS_URL);
    statusIndicator.textContent = "Connecting...";
    statusIndicator.className = "status-waiting";

    socket.onopen = () => {
        statusIndicator.textContent = "Connected";
        statusIndicator.className = "status-connected";
    };

    socket.onmessage = (event) => {
        if (isPaused) return;
        
        const data = JSON.parse(event.data);
        if (data.type === "f1tv_config") {
            if (data.config && data.config['interval-gaps'] !== undefined) {
                localStorage.setItem('toggle-interval-gaps', data.config['interval-gaps']);
                if (lastData && lastData.leaderboard) {
                    renderLeaderboard(lastData.leaderboard);
                }
            }
            return;
        }

        if (data.status && !data.leaderboard) {
            // Waiting for AMS2
            statusIndicator.textContent = data.status;
            statusIndicator.className = "status-waiting";
            return;
        }
        
        statusIndicator.textContent = data.status || "Connected";
        statusIndicator.className = "status-connected";
        lastData = data;
        
        renderLeaderboard(data.leaderboard);
        renderInspector();
    };

    socket.onclose = () => {
        statusIndicator.textContent = "Disconnected";
        statusIndicator.className = "status-disconnected";
        setTimeout(connect, 2000);
    };

    socket.onerror = () => {
        socket.close();
    };
}

function renderLeaderboard(leaderboard) {
    if (!leaderboard || leaderboard.length === 0) {
        leaderboardContainer.innerHTML = '<div style="color:var(--text-muted); text-align:center; padding:20px;">No active session or no drivers.</div>';
        return;
    }

    const useIntervalGaps = localStorage.getItem('toggle-interval-gaps') === 'true';

    let html = `
        <div class="driver-row" style="background: transparent; border-left: none; padding-bottom: 4px; border-bottom: 1px solid var(--border-color); border-radius: 0;">
            <div class="driver-pos" style="font-size: 0.9rem; color: var(--text-muted);">Pos</div>
            <div class="driver-info">
                <div class="driver-name" style="font-size: 0.9rem; color: var(--text-muted);">Driver</div>
            </div>
            <div class="driver-pits" style="font-size: 0.9rem; color: var(--text-muted);">Pits</div>
            <div class="driver-pit-time" style="font-size: 0.9rem; color: var(--text-muted);">Pit Time</div>
            <div class="driver-gap" style="font-size: 0.9rem; color: var(--text-muted);">Dist Gap</div>
            <div class="driver-dist" style="font-size: 0.9rem; color: var(--text-muted);">Total Dist</div>
            <div class="driver-time-gap" style="font-size: 0.9rem; color: var(--text-muted);">Time Gap</div>
        </div>
    `;
    
    leaderboard.forEach((driver, idx) => {
        const pos = driver.mRacePosition || '-';
        const name = driver.mName || 'Unknown';
        const car = driver.mCarNames || 'Unknown Car';
        let distGap = '';
        let dist = '';
        let timeGap = '';
        let pits = driver._in_pits ? 'P' : '';
        let pitTime = '';
        
        if (driver._pit_time !== undefined && driver._pit_time !== null) {
            pitTime = driver._pit_time.toFixed(1) + 's';
        }
        
        if (driver._total_dist !== undefined) {
            dist = driver._total_dist.toFixed(0) + 'm';
        }
        
        if (pos === 1) {
            distGap = 'Leader';
            timeGap = 'Leader';
        } else {
            if (driver._gap !== undefined) {
                distGap = `+${driver._gap.toFixed(1)}m`;
            }
            if (driver._time_gap !== undefined && driver._time_gap !== null) {
                let timeGapVal = driver._time_gap;
                if (useIntervalGaps && idx > 0) {
                    const prevDriver = leaderboard[idx - 1];
                    if (prevDriver && prevDriver._time_gap !== undefined && prevDriver._time_gap !== null) {
                        timeGapVal = driver._time_gap - prevDriver._time_gap;
                    }
                }
                timeGap = `+${timeGapVal.toFixed(3)}s`;
            } else {
                timeGap = '—';
            }
        }

        html += `
            <div class="driver-row">
                <div class="driver-pos">${pos}</div>
                <div class="driver-info">
                    <div class="driver-name">${name}</div>
                    <div class="driver-car">${car}</div>
                </div>
                <div class="driver-pits" style="color: var(--status-waiting); font-weight: bold;">${pits}</div>
                <div class="driver-pit-time">${pitTime}</div>
                <div class="driver-gap">${distGap}</div>
                <div class="driver-dist">${dist}</div>
                <div class="driver-time-gap">${timeGap}</div>
            </div>
        `;
    });
    
    leaderboardContainer.innerHTML = html;
}

function stringifyWithDepth(obj, maxDepth, currentDepth = 0, filter = '') {
    if (currentDepth > maxDepth && !expandAll) {
        if (Array.isArray(obj)) return `[Array(${obj.length})]`;
        if (typeof obj === 'object' && obj !== null) return '{Object}';
    }
    
    if (typeof obj !== 'object' || obj === null) {
        return JSON.stringify(obj);
    }

    let isArray = Array.isArray(obj);
    let result = isArray ? '[\n' : '{\n';
    let indent = '  '.repeat(currentDepth + 1);
    let keys = Object.keys(obj);
    
    // Apply filter at top level
    if (currentDepth === 0 && filter) {
        const lowerFilter = filter.toLowerCase();
        keys = keys.filter(k => k.toLowerCase().includes(lowerFilter));
    }

    let entries = keys.map(key => {
        let valStr = stringifyWithDepth(obj[key], maxDepth, currentDepth + 1, filter);
        if (isArray) return indent + valStr;
        return indent + '"' + key + '": ' + valStr;
    });

    result += entries.join(',\n');
    result += '\n' + '  '.repeat(currentDepth) + (isArray ? ']' : '}');
    return result;
}

function renderInspector() {
    if (!lastData || !lastData.raw) return;
    
    const filterText = searchInput.value;
    const depth = expandAll ? 99 : 0; // if collapsed, only show root level keys
    
    rawJsonContainer.textContent = stringifyWithDepth(lastData.raw, depth, 0, filterText);
}

searchInput.addEventListener('input', renderInspector);
toggleExpandBtn.addEventListener('click', () => {
    expandAll = !expandAll;
    toggleExpandBtn.textContent = expandAll ? "Collapse All" : "Expand All";
    renderInspector();
});

// Start connection
connect();
