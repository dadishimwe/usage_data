// static/js/client_detail.js
document.addEventListener('DOMContentLoaded', function() {
    Chart.defaults.color = '#888888';
    Chart.defaults.borderColor = '#333333';

    if (typeof CLIENT_ID !== 'undefined') {
        renderCurrentCycleChart(CLIENT_ID);
        // Fetch historical data once and use it for both table and charts
        fetchAndRenderHistoricalData(CLIENT_ID);
        setupReportButtons(CLIENT_ID);
    }
});

async function renderCurrentCycleChart(clientId) {
    try {
        const response = await fetch(`/api/client/${clientId}/usage/current`);
        const usageData = await response.json();

        document.getElementById('current-cycle-label').textContent = `Current Cycle: ${usageData.cycle_label}`;
        document.getElementById('forecast-value').textContent = `${usageData.forecast} GB`;

        const ctx = document.getElementById('current-cycle-chart').getContext('2d');
        createChart(ctx, usageData.labels, usageData.data, 'Daily Usage (GB)');
    } catch (error) {
        console.error('Error rendering current cycle chart:', error);
    }
}

async function fetchAndRenderHistoricalData(clientId) {
    try {
        const response = await fetch(`/api/client/${clientId}/usage/historical`);
        if (!response.ok) throw new Error('Failed to fetch historical data');
        const historicalData = await response.json();

        renderHistoricalTable(historicalData);
        renderHistoricalCharts(historicalData);

    } catch (error) {
        console.error('Error fetching historical data:', error);
        document.getElementById('historical-table-body').innerHTML = '<tr><td colspan="2">Could not load data.</td></tr>';
        document.getElementById('historical-charts-container').innerHTML = '<p class="loading-message">Could not load charts.</p>';
    }
}

function renderHistoricalTable(historicalData) {
    const tableBody = document.getElementById('historical-table-body');
    tableBody.innerHTML = ''; // Clear existing content

    if (historicalData.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="2">No historical data available.</td></tr>';
        return;
    }

    // Show most recent first
    [...historicalData].reverse().forEach(cycle => {
        const row = tableBody.insertRow();
        row.innerHTML = `
            <td>${cycle.cycle_label}</td>
            <td>${cycle.total_usage} GB</td>
        `;
    });
}

function renderHistoricalCharts(historicalData) {
    const container = document.getElementById('historical-charts-container');
    container.innerHTML = ''; // Clear loading message

    if (historicalData.length === 0) {
        container.innerHTML = '<p class="loading-message">No historical charts to display.</p>';
        return;
    }

    // Show most recent first
    [...historicalData].reverse().forEach(cycle => {
        const card = document.createElement('div');
        card.className = 'card historical-card';
        
        const chartId = `chart-cycle-${cycle.cycle_label.replace(/[^a-zA-Z0-9]/g, '')}`;
        card.innerHTML = `
            <div class="card-header">
                <h3>${cycle.cycle_label}</h3>
                <span class="usage-summary">Total: ${cycle.total_usage} GB</span>
            </div>
            <div class="chart-container" style="height: 200px;">
                <canvas id="${chartId}"></canvas>
            </div>
        `;
        container.appendChild(card);

        const ctx = document.getElementById(chartId).getContext('2d');
        createChart(ctx, cycle.labels, cycle.data, 'Daily Usage (GB)');
    });
}


function setupReportButtons(clientId) {
    const standardReportBtn = document.getElementById('standard-report-btn');
    const upgradeReportBtn = document.getElementById('upgrade-report-btn');
    const cyclesInput = document.getElementById('report-cycles');

    standardReportBtn.addEventListener('click', () => {
        const cycles = cyclesInput.value || 3;
        window.location.href = `/api/client/${clientId}/report/pdf?type=standard&cycles=${cycles}`;
    });

    upgradeReportBtn.addEventListener('click', () => {
        const cycles = cyclesInput.value || 3;
        window.location.href = `/api/client/${clientId}/report/pdf?type=upgrade&cycles=${cycles}`;
    });
}

function createChart(context, labels, data, label) {
    new Chart(context, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: 'rgba(255, 255, 255, 0.1)',
                borderColor: '#444',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#000',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    displayColors: false,
                    callbacks: {
                        label: (context) => `Usage: ${context.raw.toFixed(2)} GB`
                    }
                }
            },
            scales: {
                y: { beginAtZero: true, grid: { color: '#222' } },
                x: { grid: { display: false } }
            }
        }
    });
}
