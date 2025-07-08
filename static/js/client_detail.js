// static/js/client_detail.js
document.addEventListener('DOMContentLoaded', function() {
    Chart.defaults.color = '#888888';
    Chart.defaults.borderColor = '#333333';

    if (typeof CLIENT_ID !== 'undefined') {
        renderCurrentCycleChart(CLIENT_ID);
        renderHistoricalData(CLIENT_ID);
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

async function renderHistoricalData(clientId) {
    try {
        const response = await fetch(`/api/client/${clientId}/usage/historical`);
        const historicalData = await response.json();
        const container = document.getElementById('historical-data-container');
        container.innerHTML = '';

        if (historicalData.length === 0) {
            container.innerHTML = '<p>No historical data available.</p>';
            return;
        }

        const tableBody = document.getElementById('historical-table-body');
        historicalData.reverse().forEach(cycle => {
            const row = tableBody.insertRow();
            row.innerHTML = `
                <td>${cycle.cycle_label}</td>
                <td>${cycle.total_usage} GB</td>
            `;
        });
    } catch (error) {
        console.error('Error rendering historical data:', error);
    }
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
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: '#222' } },
                x: { grid: { display: false } }
            }
        }
    });
}
