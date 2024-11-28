// static/script.js

var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
var ws_path = ws_scheme + '://' + window.location.host + "/ws";
var ws = new WebSocket(ws_path);

var currentActivityStartTime = null;
var activityDurationInterval = null;

ws.onopen = function() {
    console.log("WebSocket connection established");
};

ws.onmessage = function(event) {
    var data = JSON.parse(event.data);
    updateDashboard(data);
};

ws.onerror = function(error) {
    console.error('WebSocket Error: ', error);
};

function updateDashboard(data) {
    // Update current activity
    updateCurrentActivity(data.current_activity);

    // Update character stats
    updateStats(data.state);

    // Update activity history
    updateHistoryTable(data.activity_history);
}

function updateCurrentActivity(activity) {
    if (!activity) return;

    document.getElementById("activity-name").textContent = capitalizeFirstLetter(activity.name || 'None');
    document.getElementById("activity-id").textContent = activity.activity_id || 'N/A';
    document.getElementById("activity-source").textContent = activity.source || 'N/A';

    // Update activity timing
    if (activity.start_time) {
        currentActivityStartTime = activity.start_time;
        var startTime = new Date(currentActivityStartTime * 1000);
        document.getElementById("activity-start-time").textContent = startTime.toLocaleTimeString();

        if (!activityDurationInterval) {
            activityDurationInterval = setInterval(updateActivityDuration, 1000);
        }
    } else {
        resetActivityTiming();
    }
}

function resetActivityTiming() {
    currentActivityStartTime = null;
    document.getElementById("activity-start-time").textContent = 'N/A';
    document.getElementById("activity-duration").textContent = '0s';

    if (activityDurationInterval) {
        clearInterval(activityDurationInterval);
        activityDurationInterval = null;
    }
}

function updateStats(state) {
    updateStatWithAnimation('energy', state.energy);
    updateStatWithAnimation('happiness', state.happiness);
    updateStatWithAnimation('xp', state.xp);
}

function updateStatWithAnimation(elementId, newValue) {
    const element = document.getElementById(elementId);
    const oldValue = parseInt(element.textContent);

    if (oldValue !== newValue) {
        element.textContent = newValue;
        element.classList.remove('highlight');
        void element.offsetWidth; // Trigger reflow
        element.classList.add('highlight');
    }
}

function updateHistoryTable(history) {
    var historyBody = document.getElementById("history-body");
    historyBody.innerHTML = '';

    history.forEach(function(item) {
        var row = document.createElement('tr');

        // Format timestamp
        var timestamp = new Date(item.timestamp).toLocaleString();

        // Format state changes
        var stateChanges = formatStateChanges(item.state_changes);

        // Create table cells
        row.innerHTML = `
            <td>${timestamp}</td>
            <td><span class="activity-tag">${capitalizeFirstLetter(item.activity)}</span></td>
            <td>${item.result || 'N/A'}</td>
            <td>${formatDuration(item.duration)}</td>
            <td><span class="source-tag">${item.source || 'system'}</span></td>
            <td><div class="state-changes">${stateChanges}</div></td>
        `;

        historyBody.appendChild(row);
    });
}

function formatStateChanges(changes) {
    if (!changes || Object.keys(changes).length === 0) return 'None';

    return Object.entries(changes).map(([key, value]) => {
        const changeClass = value > 0 ? 'positive' : value < 0 ? 'negative' : '';
        const sign = value > 0 ? '+' : '';
        return `<span class="state-change ${changeClass}">${key}: ${sign}${value}</span>`;
    }).join('');
}

function formatDuration(seconds) {
    if (!seconds) return 'N/A';

    var hrs = Math.floor(seconds / 3600);
    var mins = Math.floor((seconds % 3600) / 60);
    var secs = Math.floor(seconds % 60);

    var parts = [];
    if (hrs > 0) parts.push(hrs + 'h');
    if (mins > 0 || hrs > 0) parts.push(mins + 'm');
    parts.push(secs + 's');

    return parts.join(' ');
}

function updateActivityDuration() {
    if (currentActivityStartTime) {
        var now = Date.now() / 1000;
        var elapsedSeconds = Math.floor(now - currentActivityStartTime);
        document.getElementById("activity-duration").textContent = formatDuration(elapsedSeconds);
    }
}

function capitalizeFirstLetter(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
}