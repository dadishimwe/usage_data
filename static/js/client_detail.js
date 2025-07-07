// static/js/client_detail.js
document.addEventListener('DOMContentLoaded', function() {
    Chart.defaults.color = '#888888';
    Chart.defaults.borderColor = '#333333';

    // The CLIENT_ID is passed from the HTML template
    if (typeof CLIENT_ID !== 'undefined') {
        renderCurrentCycleChart(CLIENT_ID);
        renderHistoricalCharts(CLIENT_ID);
    }
});

/**
 * Renders the main chart for the current billing cycle.
 */
async function renderCurrentCycleChart(clientId) {
    try {
        const response = await fetch(`/api/client/${clientId}/usage/current`);
        if (!response.ok) throw new Error('Failed to fetch current usage data');
        const usageData = await response.json();

        document.getElementById('current-cycle-label').textContent = `Current Cycle: ${usageData.cycle_label}`;

        const ctx = document.getElementById('current-cycle-chart').getContext('2d');
        createChart(ctx, usageData.labels, usageData.data, 'Daily Usage (GB)');

    } catch (error) {
        console.error('Error rendering current cycle chart:', error);
    }
}

/**
 * Fetches and renders all historical monthly charts.
 */
async function renderHistoricalCharts(clientId) {
    try {
        const response = await fetch(`/api/client/${clientId}/usage/historical`);
        if (!response.ok) throw new Error('Failed to fetch historical data');
        const historicalData = await response.json();

        const container = document.getElementById('historical-charts-container');
        container.innerHTML = ''; // Clear loading message

        if (historicalData.length === 0) {
            container.innerHTML = '<p>No historical data available for this client.</p>';
            return;
        }

        // Reverse the data to show the most recent months first
        historicalData.reverse().forEach(cycle => {
            const card = document.createElement('div');
            card.className = 'card historical-card';
            
            const totalUsage = cycle.total_usage;
            card.innerHTML = `
                <div class="card-header">
                    <h3>${cycle.cycle_label}</h3>
                    <span class="usage-summary">Total: ${totalUsage} GB</span>
                </div>
                <div class="chart-container" style="height: 200px;">
                    <canvas id="chart-cycle-${cycle.cycle_label.replace(/[^a-zA-Z0-9]/g, '')}"></canvas>
                </div>
            `;
            container.appendChild(card);

            const ctx = document.getElementById(`chart-cycle-${cycle.cycle_label.replace(/[^a-zA-Z0-9]/g, '')}`).getContext('2d');
            createChart(ctx, cycle.labels, cycle.data, 'Daily Usage (GB)');
        });

    } catch (error) {
        console.error('Error rendering historical charts:', error);
        document.getElementById('historical-charts-container').innerHTML = '<p>Could not load historical data.</p>';
    }
}

/**
 * A helper function to create a consistent Chart.js chart.
 */
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
                borderWidth: 1,
                hoverBackgroundColor: 'rgba(255, 255, 255, 0.2)',
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
                        label: (context) => `Usage: ${context.raw} GB`
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