// static/logs.js

var allLogs = [];

document.addEventListener('DOMContentLoaded', async function() {
    await loadLogs();
    setupFilters();
});

async function loadLogs() {
    try {
        let response = await fetch('/api/logs');
        allLogs = await response.json();
        populateFilters(allLogs);
        updateLogsTable(allLogs);
    } catch (e) {
        console.error('Error loading logs:', e);
    }
}

function setupFilters() {
    document.getElementById('search-input').addEventListener('input', applyFilters);
    document.getElementById('activity-filter').addEventListener('change', applyFilters);
    document.getElementById('source-filter').addEventListener('change', applyFilters);
}

function applyFilters() {
    var searchQuery = document.getElementById('search-input').value.toLowerCase();
    var selectedActivity = document.getElementById('activity-filter').value;
    var selectedSource = document.getElementById('source-filter').value;

    var filteredLogs = allLogs.filter(function(log) {
        var matchesSearch = !searchQuery || (
            (log.activity && log.activity.toLowerCase().includes(searchQuery)) ||
            (log.result && log.result.toLowerCase().includes(searchQuery)) ||
            (log.source && log.source.toLowerCase().includes(searchQuery)) ||
            (formatStateChanges(log.state_changes).toLowerCase().includes(searchQuery))
        );

        var matchesActivity = !selectedActivity || (log.activity && log.activity === selectedActivity);
        var matchesSource = !selectedSource || (log.source && log.source === selectedSource);

        return matchesSearch && matchesActivity && matchesSource;
    });

    updateLogsTable(filteredLogs);
}

function populateFilters(logs) {
    // Populate activity filter options
    var activitySet = new Set();
    logs.forEach(item => {
        if (item.activity) {
            activitySet.add(item.activity);
        }
    });

    var activityFilter = document.getElementById('activity-filter');
    activityFilter.innerHTML = '<option value="">All Activities</option>';
    Array.from(activitySet).sort().forEach(act => {
        var opt = document.createElement('option');
        opt.value = act;
        opt.textContent = capitalizeFirstLetter(act);
        activityFilter.appendChild(opt);
    });

    // Populate source filter options
    var sourceSet = new Set();
    logs.forEach(item => {
        if (item.source) {
            sourceSet.add(item.source);
        }
    });

    var sourceFilter = document.getElementById('source-filter');
    sourceFilter.innerHTML = '<option value="">All Sources</option>';
    Array.from(sourceSet).sort().forEach(src => {
        var opt = document.createElement('option');
        opt.value = src;
        opt.textContent = capitalizeFirstLetter(src);
        sourceFilter.appendChild(opt);
    });
}

function updateLogsTable(logs) {
    var logsBody = document.getElementById('logs-body');
    logsBody.innerHTML = '';

    logs.forEach(function(item) {
        var row = document.createElement('tr');
        row.classList.add('log-row');

        // Format timestamp
        var timestamp = new Date(item.timestamp).toLocaleString();

        // Create an expandable icon
        var expandCell = document.createElement('td');
        expandCell.classList.add('expand-cell');
        expandCell.innerHTML = `<span class="expand-toggle">▶</span>`;

        var stateChangesDetail = document.createElement('tr');
        stateChangesDetail.classList.add('detail-row');
        stateChangesDetail.style.display = 'none'; 

        var stateChangeHTML = `
            <div class="detail-content">
                <strong>State Changes:</strong><br>${formatStateChanges(item.state_changes) || 'None'}
            </div>
        `;

        stateChangesDetail.innerHTML = `<td colspan="6">${stateChangeHTML}</td>`;

        // Event for expand/collapse
        expandCell.querySelector('.expand-toggle').addEventListener('click', function() {
            if (stateChangesDetail.style.display === 'none') {
                stateChangesDetail.style.display = 'table-row';
                this.textContent = '▼';
            } else {
                stateChangesDetail.style.display = 'none';
                this.textContent = '▶';
            }
        });

        row.appendChild(expandCell);

        row.innerHTML += `
            <td>${timestamp}</td>
            <td><span class="activity-tag">${capitalizeFirstLetter(item.activity)}</span></td>
            <td>${item.result || 'N/A'}</td>
            <td>${formatDuration(item.duration)}</td>
            <td><span class="source-tag">${item.source || 'system'}</span></td>
        `;

        logsBody.appendChild(row);
        logsBody.appendChild(stateChangesDetail);
    });
}

function formatStateChanges(changes) {
    if (!changes || Object.keys(changes).length === 0) return 'None';
    return Object.entries(changes).map(([key, value]) => {
        const changeClass = value > 0 ? 'positive' : value < 0 ? 'negative' : '';
        const sign = value > 0 ? '+' : '';
        return `<span class="state-change ${changeClass}">${key}: ${sign}${value}</span>`;
    }).join(' ');
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

function capitalizeFirstLetter(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
}
