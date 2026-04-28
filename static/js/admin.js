document.addEventListener('DOMContentLoaded', function () {
    fetch('/api/admin/dashboard')
        .then(function (res) {
            if (!res.ok) throw new Error('Failed to load dashboard data');
            return res.json();
        })
        .then(function (data) {
            // Update stat cards
            document.getElementById('stat-users').textContent = data.total_users_today;
            document.getElementById('stat-tokens').textContent = data.total_tokens;
            document.getElementById('stat-wait').textContent = data.avg_wait_time + ' min';
            document.getElementById('stat-counters').textContent = data.active_counters;

            // Hourly bar chart
            var hourlyLabels = [];
            for (var h = 0; h < 24; h++) {
                hourlyLabels.push(String(h).padStart(2, '0') + ':00');
            }
            new Chart(document.getElementById('hourly-chart'), {
                type: 'bar',
                data: {
                    labels: hourlyLabels,
                    datasets: [{
                        label: 'Tokens',
                        data: data.hourly_volume,
                        backgroundColor: '#4f46e5',
                        borderRadius: 4,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, ticks: { stepSize: 1 } }
                    }
                }
            });

            // Weekly line chart — compute last 7 day labels
            var weeklyLabels = [];
            var now = new Date();
            for (var d = 6; d >= 0; d--) {
                var day = new Date(now);
                day.setDate(now.getDate() - d);
                weeklyLabels.push(
                    day.getFullYear() + '-' +
                    String(day.getMonth() + 1).padStart(2, '0') + '-' +
                    String(day.getDate()).padStart(2, '0')
                );
            }
            new Chart(document.getElementById('weekly-chart'), {
                type: 'line',
                data: {
                    labels: weeklyLabels,
                    datasets: [{
                        label: 'Avg Wait (min)',
                        data: data.weekly_avg_wait,
                        borderColor: '#06b6d4',
                        backgroundColor: 'rgba(6,182,212,0.1)',
                        borderWidth: 2,
                        pointRadius: 4,
                        tension: 0.3,
                        fill: true,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true }
                    }
                }
            });
        })
        .catch(function (err) {
            var statsArea = document.getElementById('stats-area');
            if (statsArea) {
                statsArea.innerHTML = '<div class="alert alert-danger">Failed to load dashboard data. Please refresh the page.</div>';
            }
        });
});
