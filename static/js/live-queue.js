/* QueueLess AI — live-queue.js */

class LiveQueueMonitor {
  constructor(branchSelectId, counterSelectId) {
    this.branchSelect = document.getElementById(branchSelectId);
    this.counterSelect = document.getElementById(counterSelectId);
    this.intervalId = null;
    this.POLL_INTERVAL = 10000; // 10 seconds
  }

  start() {
    this.stop(); // clear any existing interval
    this.refresh();
    this.intervalId = setInterval(() => this.refresh(), this.POLL_INTERVAL);
  }

  stop() {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  async refresh() {
    const branchId = this.branchSelect ? this.branchSelect.value : '';
    if (!branchId) return;

    const counterId = this.counterSelect ? this.counterSelect.value : '';
    let url = `/api/queue/status?branch_id=${branchId}`;
    if (counterId) url += `&counter_id=${counterId}`;

    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Update DOM
      const currentTokenEl = document.getElementById('current-token');
      if (currentTokenEl) {
        if (data.current_token) {
          currentTokenEl.textContent = data.current_token;
          currentTokenEl.classList.remove('empty');
        } else {
          currentTokenEl.textContent = '—';
          currentTokenEl.classList.add('empty');
        }
      }

      const peopleAheadEl = document.getElementById('people-ahead');
      if (peopleAheadEl) {
        // If user entered their token, still show global people_ahead count
        peopleAheadEl.textContent = data.people_ahead ?? '—';
      }

      const servedTodayEl = document.getElementById('served-today');
      if (servedTodayEl) servedTodayEl.textContent = data.served_today ?? '—';

      const totalTodayEl = document.getElementById('total-today');
      if (totalTodayEl) totalTodayEl.textContent = data.total_today ?? '—';

      const progressBar = document.getElementById('queue-progress');
      if (progressBar) progressBar.style.width = `${data.progress_percent ?? 0}%`;

      const progressLabel = document.getElementById('progress-label');
      if (progressLabel) progressLabel.textContent = `${data.progress_percent ?? 0}% complete`;

      const lastUpdated = document.getElementById('last-updated');
      if (lastUpdated) lastUpdated.textContent = new Date().toLocaleTimeString();

      // Hide connectivity warning on success
      const warn = document.getElementById('connectivity-warning');
      if (warn) warn.classList.remove('visible');

    } catch (_err) {
      // Show connectivity warning, retain last known values
      const warn = document.getElementById('connectivity-warning');
      if (warn) warn.classList.add('visible');
    }
  }
}

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const branchSelect = document.getElementById('branch-select');
  const counterSelect = document.getElementById('counter-select');

  // Populate branches
  try {
    const res = await fetch('/api/branches');
    if (res.ok) {
      const branches = await res.json();
      branches.forEach(b => {
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = `${b.name} — ${b.location}`;
        branchSelect.appendChild(opt);
      });
    }
  } catch (_) {
    // silently ignore — user can still select manually if branches load later
  }

  const monitor = new LiveQueueMonitor('branch-select', 'counter-select');

  // On branch change: restart monitor
  branchSelect.addEventListener('change', () => {
    monitor.start();
  });

  // On counter change: restart monitor
  counterSelect.addEventListener('change', () => {
    if (branchSelect.value) monitor.start();
  });

  monitor.start();
});
