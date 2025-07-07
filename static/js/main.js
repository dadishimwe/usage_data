// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    Chart.defaults.color = '#888888';
    Chart.defaults.borderColor = '#333333';
    
    fetchClientData();
});

async function fetchClientData() {
    try {
        const response = await fetch('/api/clients');
        if (!response.ok) throw new Error('Network response was not ok');
        const clients = await response.json();
        
        const clientList = document.getElementById('client-list');
        clientList.innerHTML = ''; 

        if (clients.length === 0) {
            clientList.innerHTML = '<p class="loading-message">No client data found. Please run the import script.</p>';
            return;
        }

        clients.forEach(client => {
            // --- UPDATED: The card is now a link ---
            const card = document.createElement('a');
            card.className = 'client-card';
            card.href = `/client/${client.id}`; // Link to the detail page
            // --- END UPDATED ---
            
            card.innerHTML = `
                <div class="card-header">
                    <h2>${client.name}</h2>
                    <span class="usage-summary">${client.total_usage_gb} GB / ${client.monthly_limit_gb} GB</span>
                </div>
                <div class="chart-container">
                    <canvas id="chart-canvas-${client.id}"></canvas>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${client.usage_percentage}%;"></div>
                </div>
            `;
            clientList.appendChild(card);
            
            // Render the small chart for the current cycle on the dashboard
            renderDashboardChart(client.id);
        });

    } catch (error) {
        console.error('Error fetching client data:', error);
        const clientList = document.getElementById('client-list');
        clientList.innerHTML = '<p class="loading-message">Error loading data. Please check the console.</p>';
    }
}

async function renderDashboardChart(clientId) {
    try {
        // --- UPDATED: Fetch from the new 'current' usage endpoint ---
        const response = await fetch(`/api/client/${clientId}/usage/current`);
        // --- END UPDATED ---
        if (!response.ok) throw new Error('Failed to fetch usage data');
        const usageData = await response.json();
        
        const ctx = document.getElementById(`chart-canvas-${clientId}`).getContext('2d');
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: usageData.labels,
                datasets: [{
                    label: 'Daily Usage (GB)',
                    data: usageData.data,
                    backgroundColor: 'rgba(255, 255, 255, 0.1)',
                    borderColor: '#444',
                    borderWidth: 1,
                    hoverBackgroundColor: 'rgba(255, 255, 255, 0.2)',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } }, // Disable tooltips on dashboard
                scales: {
                    y: { display: false }, // Hide axes
                    x: { display: false }
                }
            }
        });

    } catch (error) {
        console.error(`Error rendering chart for client ${clientId}:`, error);
    }
}