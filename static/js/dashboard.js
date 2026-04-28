/* QueueLess AI — dashboard.js */

let currentTokenId = null;

const tokenSection      = document.getElementById('token-section');
const emptyState        = document.getElementById('empty-state');
const loadingState      = document.getElementById('loading-state');
const connectivityWarn  = document.getElementById('connectivity-warning');

const valTokenNumber    = document.getElementById('val-token-number');
const valWaitTime       = document.getElementById('val-wait-time');
const valPeopleAhead    = document.getElementById('val-people-ahead');
const valStatus         = document.getElementById('val-status');

const btnCancel         = document.getElementById('btn-cancel');
const btnRefresh        = document.getElementById('btn-refresh');
const btnLogout         = document.getElementById('btn-logout');

// ── Badge helper ──────────────────────────────────────────────────────────
function statusBadge(status) {
  const map = {
    'Waiting':     'badge-waiting',
    'Now Serving': 'badge-serving',
    'Served':      'badge-served',
    'Cancelled':   'badge-cancelled',
    'Skipped':     'badge-skipped',
  };
  const cls = map[status] || 'badge-waiting';
  return `<span class="badge ${cls}">${status}</span>`;
}

// ── Load dashboard ────────────────────────────────────────────────────────
async function loadDashboard() {
  try {
    const res = await fetch('/api/tokens/active');
    if (!res.ok) throw new Error('API error');

    const data = await res.json();
    connectivityWarn.classList.remove('visible');
    loadingState.style.display = 'none';

    if (!data.token) {
      tokenSection.style.display = 'none';
      emptyState.style.display = 'block';
      currentTokenId = null;
      return;
    }

    const token = data.token;
    currentTokenId = token.id;

    // Update cards
    valTokenNumber.textContent = token.token_number || '—';
    valWaitTime.textContent    = token.estimated_wait_minutes != null
      ? `${token.estimated_wait_minutes} min`
      : '— min';
    valStatus.innerHTML        = statusBadge(token.status);

    // Try to get people ahead from queue status (branch_id may not be in response)
    valPeopleAhead.textContent = '—';
    if (token.branch_id != null) {
      fetchPeopleAhead(token.branch_id);
    }

    tokenSection.style.display = 'block';
    emptyState.style.display   = 'none';

  } catch (err) {
    // Connectivity issue — show warning, keep last known values
    connectivityWarn.classList.add('visible');
    loadingState.style.display = 'none';
    // If we have no data at all yet, show empty state
    if (!currentTokenId && tokenSection.style.display === 'none') {
      emptyState.style.display = 'block';
    }
  }
}

// ── People ahead (optional — queue blueprint may not exist yet) ───────────
async function fetchPeopleAhead(branchId) {
  try {
    const res = await fetch(`/api/queue/status?branch_id=${branchId}`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.people_ahead != null) {
      valPeopleAhead.textContent = data.people_ahead;
    }
  } catch (_) {
    // Queue endpoint not available yet — silently ignore
  }
}

// ── Cancel token ──────────────────────────────────────────────────────────
async function cancelToken(tokenId) {
  if (!tokenId) return;
  if (!confirm('Are you sure you want to cancel your token?')) return;

  try {
    const res = await fetch(`/api/tokens/${tokenId}/cancel`, { method: 'POST' });
    if (res.ok) {
      await loadDashboard();
    } else {
      const data = await res.json().catch(() => ({}));
      alert(data.error || 'Failed to cancel token.');
    }
  } catch (_) {
    alert('Network error. Please try again.');
  }
}

// ── Event listeners ───────────────────────────────────────────────────────
btnCancel.addEventListener('click', () => cancelToken(currentTokenId));

btnRefresh.addEventListener('click', loadDashboard);

btnLogout.addEventListener('click', async () => {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } finally {
    window.location.href = '/login';
  }
});

// ── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', loadDashboard);
