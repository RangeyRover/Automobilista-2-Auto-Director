let socket;
const statusIndicator = document.getElementById("status-indicator");
const flywheelIndicator = document.getElementById("flywheel-indicator");
const tableBody = document.getElementById("spline-table-body");
const timeTableBody = document.getElementById("time-table-body");
const pauseBtn = document.getElementById("pause-updates-btn");

let isPaused = false;
let lastData = null;

pauseBtn.addEventListener("click", () => {
    isPaused = !isPaused;
    if (isPaused) {
        pauseBtn.textContent = "Resume Updates";
        pauseBtn.classList.add("paused");
    } else {
        pauseBtn.textContent = "Pause Updates";
        pauseBtn.classList.remove("paused");
        if (lastData) {
            renderSpline(lastData.spline);
            renderTimeHistory(lastData.time_history);
        }
    }
});

function connect() {
    socket = new WebSocket("ws://127.0.0.1:8770");

    socket.onopen = () => {
        statusIndicator.textContent = "Connected";
        statusIndicator.className = "status-connected";
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.status && !data.spline) {
            statusIndicator.textContent = data.status;
            statusIndicator.className = "status-waiting";
            return;
        }
        
        statusIndicator.textContent = data.status || "Connected";
        statusIndicator.className = "status-connected";
        
        if (!isPaused) {
            lastData = data;
            renderSpline(data.spline);
            renderTimeHistory(data.time_history);
            // Toggle flywheel status badge
            if (flywheelIndicator) {
                flywheelIndicator.style.display = data.flywheel_active ? "inline-block" : "none";
            }
        }
    };

    socket.onclose = () => {
        statusIndicator.textContent = "Disconnected";
        statusIndicator.className = "status-disconnected";
        setTimeout(connect, 2000);
    };
}

function renderSpline(spline) {
    if (!spline || !spline.distances || spline.distances.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 20px;">No spline data available</td></tr>';
        return;
    }

    let html = '';
    const distances = spline.distances;
    const times = spline.times;
    
    // Reverse loop to show newest at the top
    for (let i = distances.length - 1; i >= 0; i--) {
        const d = distances[i];
        const t = times[i];
        
        let speed = 'N/A';
        if (i > 0) {
            const d0 = distances[i-1];
            const t0 = times[i-1];
            const ds = d - d0;
            const dt = t - t0;
            if (dt > 0) {
                speed = (ds / dt).toFixed(2);
            }
        }
        
        html += `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 8px;">${i}</td>
                <td style="padding: 8px; color: var(--accent);">${d.toFixed(3)}</td>
                <td style="padding: 8px;">${t.toFixed(3)}</td>
                <td style="padding: 8px; color: ${speed !== 'N/A' && parseFloat(speed) < 10.0 ? 'var(--status-disconnected)' : 'var(--text-muted)'};">${speed}</td>
            </tr>
        `;
    }
    
    tableBody.innerHTML = html;
}

function renderTimeHistory(history) {
    if (!history || history.length === 0) {
        timeTableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding: 20px;">No time data available</td></tr>';
        return;
    }

    let html = '';
    // Reverse loop to show newest at the top
    for (let i = history.length - 1; i >= 0; i--) {
        const t = history[i];
        let delta = 'N/A';
        
        if (i > 0) {
            const dt = t - history[i-1];
            delta = dt.toFixed(4);
        }
        
        // Highlight huge jumps or negative time changes
        let color = 'inherit';
        if (delta !== 'N/A') {
            const val = parseFloat(delta);
            if (val < 0.0 || val > 1.0) {
                color = 'var(--status-disconnected)';
            }
        }
        
        html += `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 8px;">${i}</td>
                <td style="padding: 8px; color: var(--accent);">${t.toFixed(4)}</td>
                <td style="padding: 8px; color: ${color};">${delta}</td>
            </tr>
        `;
    }
    
    timeTableBody.innerHTML = html;
}

connect();
