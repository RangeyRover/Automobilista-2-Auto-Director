const fs = require('fs');
const vm = require('vm');
const path = require('path');
const assert = require('assert');

console.log("Setting up TDD mock environment...");

// Mock DOM elements and environment
const mockElements = {};
const mockDocument = {
    getElementById: (id) => {
        if (!mockElements[id]) {
            mockElements[id] = {
                id: id,
                style: {},
                classList: {
                    classes: new Set(),
                    add: function(c) { this.classes.add(c); },
                    remove: function(c) { this.classes.delete(c); },
                    contains: function(c) { return this.classes.has(c); }
                },
                appendChild: () => {},
                innerText: '',
                innerHTML: '',
                addEventListener: () => {},
                checked: true
            };
        }
        return mockElements[id];
    },
    createElement: (tag) => {
        return {
            appendChild: () => {},
            style: {},
            classList: {
                classes: new Set(),
                add: function(c) { this.classes.add(c); },
                remove: function(c) { this.classes.delete(c); },
                contains: function(c) { return this.classes.has(c); }
            },
            appendChildNode: () => {},
            addEventListener: () => {},
            checked: true
        };
    },
    createTextNode: (text) => {
        return { text: text };
    },
    addEventListener: () => {},
    querySelectorAll: () => []
};

const mockLocalStorage = {
    store: {},
    getItem: function(key) { return this.store[key] || null; },
    setItem: function(key, val) { this.store[key] = String(val); }
};

const mockLocation = { host: 'localhost:8765', search: '' };
class MockWebSocket {
    constructor(url) {
        this.url = url;
    }
}

// VM context sandbox
const context = {
    document: mockDocument,
    localStorage: mockLocalStorage,
    location: mockLocation,
    WebSocket: MockWebSocket,
    console: console,
    setTimeout: setTimeout,
    setInterval: setInterval,
    Math: Math,
    parseFloat: parseFloat,
    parseInt: parseInt,
    fetch: () => Promise.resolve({ ok: false }), // mock fetch
    URLSearchParams: URLSearchParams, // pass global URLSearchParams
    window: {}
};
context.window = context;

vm.createContext(context);

// Load the overlay JS file and expose const/let variables/functions to context
const jsCode = fs.readFileSync(path.join(__dirname, '../dashboard/js/f1tv_overlay.js'), 'utf8');
const exposingCode = `
;
if (typeof components !== 'undefined') window.components = components;
if (typeof presets !== 'undefined') window.presets = presets;
if (typeof formatGapTenths !== 'undefined') window.formatGapTenths = formatGapTenths;
if (typeof formatTimeTenths !== 'undefined') window.formatTimeTenths = formatTimeTenths;
if (typeof updateVisibilityMode !== 'undefined') window.updateVisibilityMode = updateVisibilityMode;
if (typeof state !== 'undefined') {
    Object.defineProperty(window, 'state', {
        get: () => state,
        set: (v) => { state = v; }
    });
}
window.updateAll = updateAll;
window.updateVisibility = updateVisibility;

`;
vm.runInContext(jsCode + exposingCode, context);

console.log("Running TDD Test Suite...");

// ----------------------------------------------------
// Test 1: formatGapTenths Unit Test
// ----------------------------------------------------
try {
    console.log("Test: formatGapTenths exists and formats correctly...");
    assert.ok(context.formatGapTenths, "formatGapTenths function should exist");
    assert.strictEqual(context.formatGapTenths(0.123), "+0.1s");
    assert.strictEqual(context.formatGapTenths(1.289), "+1.3s");
    assert.strictEqual(context.formatGapTenths(0), "");
    assert.strictEqual(context.formatGapTenths(-0.5), "");
    assert.strictEqual(context.formatGapTenths("PIT"), "PIT");
    assert.strictEqual(context.formatGapTenths("+1 LAP"), "+1 LAP");
    console.log("✓ Test formatGapTenths passed!");
} catch (e) {
    console.error("✗ Test formatGapTenths FAILED:", e.message);
}

// ----------------------------------------------------
// Test 2: formatTimeTenths Unit Test
// ----------------------------------------------------
try {
    console.log("Test: formatTimeTenths exists and formats correctly...");
    assert.ok(context.formatTimeTenths, "formatTimeTenths function should exist");
    assert.strictEqual(context.formatTimeTenths(65.489), "1:05.5");
    assert.strictEqual(context.formatTimeTenths(9.234), "0:09.2");
    assert.strictEqual(context.formatTimeTenths(0), "--:--.-");
    assert.strictEqual(context.formatTimeTenths(-5), "--:--.-");
    console.log("✓ Test formatTimeTenths passed!");
} catch (e) {
    console.error("✗ Test formatTimeTenths FAILED:", e.message);
}

// ----------------------------------------------------
// Test 3: Tenths Timing Config & Preset Integration
// ----------------------------------------------------
try {
    console.log("Test: tenths-timing checkbox in components and presets...");
    const components = context.components;
    const presets = context.presets;
    
    const tenthsComp = components.find(c => c.id === 'tenths-timing');
    assert.ok(tenthsComp, "tenths-timing component should be defined in components list");
    assert.strictEqual(tenthsComp.default, true, "tenths-timing should be enabled by default");
    
    assert.ok(presets.broadcast.includes('tenths-timing'), "broadcast preset should include tenths-timing");
    assert.ok(presets.cockpit.includes('tenths-timing'), "cockpit preset should include tenths-timing");
    console.log("✓ Test Tenths Timing Config passed!");
} catch (e) {
    console.error("✗ Test Tenths Timing Config FAILED:", e.message);
}

// ----------------------------------------------------
// Test 4: Session Info Preset Alignment
// ----------------------------------------------------
try {
    console.log("Test: session-info preset alignment...");
    const presets = context.presets;
    assert.ok(presets.broadcast.includes('session-info'), "broadcast preset should include session-info");
    assert.ok(!presets.cockpit.includes('session-info'), "cockpit preset should NOT include session-info");
    console.log("✓ Test Session Info Presets passed!");
} catch (e) {
    console.error("✗ Test Session Info Presets FAILED:", e.message);
}

// ----------------------------------------------------
// Test 5: Session Info Onboard Visibility
// ----------------------------------------------------
try {
    console.log("Test: session-info visibility on onboard/roof camera...");
    const sessionInfoEl = context.document.getElementById('session-info');
    const sessionInfoCb = context.document.getElementById('toggle-session-info');
    
    // Set state camera to roof
    context.state = { director: { camera_type: 'roof' } };
    
    // Case 1: Session Info is checked (enabled)
    sessionInfoCb.checked = true;
    sessionInfoEl.classList.remove('mode-hidden');
    
    // Run visibility update
    if (context.updateVisibilityMode) context.updateVisibilityMode();
    context.updateVisibility();
    
    assert.ok(!sessionInfoEl.classList.contains('mode-hidden'), "session-info should NOT have mode-hidden class");
    assert.strictEqual(sessionInfoEl.style.display, '', "session-info should be visible when checked on roof cam");
    
    // Case 2: Session Info is unchecked (disabled)
    sessionInfoCb.checked = false;
    context.updateVisibility();
    assert.strictEqual(sessionInfoEl.style.display, 'none', "session-info should be hidden when unchecked");
    
    console.log("✓ Test Session Info Onboard Visibility passed!");
} catch (e) {
    console.error("✗ Test Session Info Onboard Visibility FAILED:", e.message);
}

// ----------------------------------------------------
// Test 6: Interval Gaps Config & Leaderboard Calculations (TDD)
// ----------------------------------------------------
try {
    console.log("Test: interval-gaps checkbox in components...");
    const components = context.components;
    const intervalComp = components.find(c => c.id === 'interval-gaps');
    assert.ok(intervalComp, "interval-gaps component should be defined in components list");
    assert.strictEqual(intervalComp.default, false, "interval-gaps should be disabled by default");

    console.log("Test: interval gap calculation in updateAll()...");
    // Setup state
    context.state = {
        viewed: { position: 1, name: 'VER' },
        leaderboard: [
            { pos: 1, name: 'VER', gap: 0.0, car_class: 'F1', nationality: 'nl', tyre_compound: 'Soft', tyre_stint_laps: 3, last_lap: 80.0 },
            { pos: 2, name: 'HAM', gap: 2.5, car_class: 'F1', nationality: 'gb', tyre_compound: 'Soft', tyre_stint_laps: 3, last_lap: 81.0 },
            { pos: 3, name: 'LEC', gap: 3.8, car_class: 'F1', nationality: 'mc', tyre_compound: 'Medium', tyre_stint_laps: 5, last_lap: 81.2 }
        ],
        weather: {},
        session: {},
        viewed_index: 0
    };

    // Enable interval gaps toggle in DOM
    const intervalCb = context.document.getElementById('toggle-interval-gaps');
    intervalCb.checked = true;

    // Run updateAll
    context.updateAll();

    const miniHtml = mockElements['mini-leaderboard'].innerHTML;
    const fullHtml = mockElements['full-leaderboard'].innerHTML;

    // HAM interval gap should be 2.5s
    assert.ok(miniHtml.includes('+2.5s'), "HAM gap of +2.5s should be rendered");
    // LEC interval gap should be 1.3s (3.8 - 2.5 = 1.3s)
    assert.ok(miniHtml.includes('+1.3s'), "LEC interval gap of +1.3s should be rendered instead of +3.8s");
    assert.ok(!miniHtml.includes('+3.8s'), "LEC leader gap of +3.8s should NOT be rendered when interval gaps are active");

    console.log("✓ Test Interval Gaps passed!");
} catch (e) {
    console.error("✗ Test Interval Gaps FAILED:", e.message);
}

console.log("TDD Test Suite execution finished.");

