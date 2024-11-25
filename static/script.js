// static/script.js

var ws_scheme = window.location.protocol == "https:" ? "wss" : "ws";
var ws_path = ws_scheme + '://' + window.location.host + "/ws";
var ws = new WebSocket(ws_path);

var currentActivityStartTime = null; // Store the start time
var activityDurationInterval = null; // Interval to update the duration

ws.onopen = function() {
    console.log("WebSocket connection established");
};

ws.onmessage = function(event) {
    var data = JSON.parse(event.data);

    // Update current activity
    var activityName = data.current_activity.name;
    document.getElementById("activity-name").textContent = capitalizeFirstLetter(activityName) || 'None';

    // Update activity start time
    if (data.current_activity.start_time) {
        currentActivityStartTime = data.current_activity.start_time;

        // Display start time in human-readable format
        var startTime = new Date(currentActivityStartTime * 1000); // Convert UNIX timestamp to milliseconds
        document.getElementById("activity-start-time").textContent = startTime.toLocaleTimeString();

        // Start updating the duration
        if (!activityDurationInterval) {
            activityDurationInterval = setInterval(updateActivityDuration, 1000);
        }
    } else {
        currentActivityStartTime = null;
        document.getElementById("activity-start-time").textContent = 'N/A';
        document.getElementById("activity-duration").textContent = '0s';

        // Stop updating the duration
        if (activityDurationInterval) {
            clearInterval(activityDurationInterval);
            activityDurationInterval = null;
        }
    }

    // Update stats
    document.getElementById("energy").textContent = data.state.energy;
    document.getElementById("happiness").textContent = data.state.happiness;
    document.getElementById("xp").textContent = data.state.xp;

    // Update activity history
    updateHistoryTable(data.activity_history);
};

ws.onerror = function(error) {
    console.error('WebSocket Error: ', error);
};

// Function to update the elapsed time of the current activity
function updateActivityDuration() {
    if (currentActivityStartTime) {
        var now = Date.now() / 1000; // Current time in UNIX timestamp
        var elapsedSeconds = Math.floor(now - currentActivityStartTime);
        var formattedDuration = formatDuration(elapsedSeconds);
        document.getElementById("activity-duration").textContent = formattedDuration;
    }
}

function updateHistoryTable(history) {
    var historyBody = document.getElementById("history-body");
    historyBody.innerHTML = ''; // Clear existing history

    // Reverse the history to show most recent first
    history.forEach(function(item) {
        var row = document.createElement('tr');

        // Format timestamp
        var timestamp = new Date(item.timestamp).toLocaleString();

        // State changes
        var stateChanges = '';
        if (item.state_changes) {
            for (var key in item.state_changes) {
                stateChanges += key + ': ' + item.state_changes[key] + '; ';
            }
        }

        // Create table cells
        row.innerHTML = `
            <td>${timestamp}</td>
            <td>${capitalizeFirstLetter(item.activity)}</td>
            <td>${item.result}</td>
            <td>${item.duration ? item.duration.toFixed(2) : 'N/A'}</td>
            <td>${stateChanges || 'None'}</td>
        `;

        historyBody.appendChild(row);
    });
}


// Helper function to capitalize the first letter
function capitalizeFirstLetter(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// Helper function to format duration from seconds to HH:MM:SS
function formatDuration(seconds) {
    var hrs = Math.floor(seconds / 3600);
    var mins = Math.floor((seconds % 3600) / 60);
    var secs = seconds % 60;

    var duration = '';
    if (hrs > 0) {
        duration += hrs + 'h ';
    }
    if (mins > 0 || hrs > 0) {
        duration += mins + 'm ';
    }
    duration += secs + 's';

    return duration.trim();
}