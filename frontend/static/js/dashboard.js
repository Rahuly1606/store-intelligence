/**
 * Dashboard JavaScript
 * Handles real-time data updates and chart rendering
 */

let funnelChart = null;
let heatmapChart = null;
let refreshTimer = null;

$(document).ready(function() {
    // Initial load
    loadDashboardData();
    
    // Auto-refresh
    startAutoRefresh();
    
    // Manual refresh button
    $('#refreshBtn').on('click', function() {
        loadDashboardData();
    });
});

function loadDashboardData() {
    showLoading();
    
    $.ajax({
        url: `/api/dashboard-data/${STORE_ID}`,
        type: 'GET',
        success: function(response) {
            if (response.success) {
                updateMetrics(response.data.metrics);
                updateFunnelChart(response.data.funnel);
                updateHeatmapChart(response.data.heatmap);
                updateDwellTimes(response.data.metrics.dwell_times);
            } else {
                showError('Failed to load dashboard data');
            }
        },
        error: function(xhr) {
            showError('Backend API unavailable. Please ensure FastAPI is running on port 8000.');
        },
        complete: function() {
            hideLoading();
        }
    });
}

function updateMetrics(metrics) {
    $('#uniqueVisitors').text(metrics.unique_visitors);
    $('#conversionRate').text(metrics.conversion_rate + '%');
    $('#queueDepth').text(metrics.queue_depth);
    $('#abandonmentRate').text(metrics.abandonment_rate + '%');
}

function updateFunnelChart(funnel) {
    const ctx = document.getElementById('funnelChart').getContext('2d');
    
    const data = {
        labels: ['Entry', 'Zone Visit', 'Billing Queue', 'Conversion'],
        datasets: [{
            label: 'Visitors',
            data: [funnel.entry, funnel.zone_visit, funnel.billing_queue, funnel.conversion],
            backgroundColor: [
                'rgba(54, 162, 235, 0.8)',
                'rgba(75, 192, 192, 0.8)',
                'rgba(255, 206, 86, 0.8)',
                'rgba(75, 192, 75, 0.8)'
            ],
            borderColor: [
                'rgba(54, 162, 235, 1)',
                'rgba(75, 192, 192, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 75, 1)'
            ],
            borderWidth: 1
        }]
    };
    
    if (funnelChart) {
        funnelChart.data = data;
        funnelChart.update();
    } else {
        funnelChart = new Chart(ctx, {
            type: 'bar',
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
}

function updateHeatmapChart(heatmap) {
    const ctx = document.getElementById('heatmapChart').getContext('2d');
    
    const zones = Object.keys(heatmap.zone_visits);
    const visits = Object.values(heatmap.zone_visits);
    
    const data = {
        labels: zones,
        datasets: [{
            label: 'Visits',
            data: visits,
            backgroundColor: 'rgba(255, 99, 132, 0.8)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 1
        }]
    };
    
    if (heatmapChart) {
        heatmapChart.data = data;
        heatmapChart.update();
    } else {
        heatmapChart = new Chart(ctx, {
            type: 'bar',
            data: data,
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

function updateDwellTimes(dwellTimes) {
    const container = $('#dwellTimesContainer');
    
    // Handle null/undefined dwell times
    if (!dwellTimes || Object.keys(dwellTimes).length === 0) {
        container.html('<p class="text-muted">No dwell time data available</p>');
        return;
    }
    
    let html = '<div class="row g-3">';
    for (const [zone, time] of Object.entries(dwellTimes)) {
        html += `
            <div class="col-md-3">
                <div class="card">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">${zone}</h6>
                        <h4 class="card-title mb-0">${time}</h4>
                    </div>
                </div>
            </div>
        `;
    }
    html += '</div>';
    
    container.html(html);
}

function startAutoRefresh() {
    refreshTimer = setInterval(function() {
        loadDashboardData();
    }, REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
}

function showLoading() {
    $('#loadingOverlay').show();
}

function hideLoading() {
    $('#loadingOverlay').hide();
}

function showError(message) {
    alert(message);
}

// Stop auto-refresh when page is hidden
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh();
    }
});
