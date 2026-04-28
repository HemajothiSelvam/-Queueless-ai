/* Queue Management — Admin JS */

document.addEventListener('DOMContentLoaded', () => {
    loadCounters();

    document.getElementById('action-counter-select').addEventListener('change', function () {
        const id = this.value;
        if (id) loadQueue(id);
        else document.getElementById('queue-display').innerHTML =
            '<p style="color:var(--text-muted)">Select a counter to view its queue.</p>';
    });

    document.getElementById('btn-call-next').addEventListener('click', () => {
        const id = selectedCounter();
        if (!id) return showAlert('Please select a counter first.', 'error');
        postAction('/api/admin/queue/call-next', { counter_id: id }, (data) => {
            const msg = `Served: ${data.served_token || '—'} → Now Serving: ${data.next_token || '—'}`;
            showAlert(msg, 'success');
            loadQueue(id);
        });
    });

    document.getElementById('btn-skip').addEventListener('click', () => {
        const id = selectedCounter();
        if (!id) return showAlert('Please select a counter first.', 'error');
        postAction('/api/admin/queue/skip', { counter_id: id }, (data) => {
            const msg = `Skipped: ${data.skipped_token || '—'} → Now Serving: ${data.next_token || '—'}`;
            showAlert(msg, 'success');
            loadQueue(id);
        });
    });

    document.getElementById('btn-delay').addEventListener('click', () => {
        const id = selectedCounter();
        const minutes = parseInt(document.getElementById('delay-minutes').value, 10);
        if (!id) return showAlert('Please select a counter first.', 'error');
        if (!minutes || minutes < 1) return showAlert('Enter a valid delay (min 1 minute).', 'error');
        postAction('/api/admin/queue/delay', { counter_id: id, delay_minutes: minutes }, (data) => {
            showAlert(`${data.message} — ${data.affected_tokens} token(s) affected.`, 'success');
            loadQueue(id);
        });
    });
});

function selectedCounter() {
    return parseInt(document.getElementById('action-counter-select').value, 10) || null;
}

function loadCounters() {
    fetch('/api/admin/counters')
        .then(r => r.json())
        .then(counters => {
            renderCounters(counters);
            populateSelect(counters);
        })
        .catch(() => showAlert('Failed to load counters.', 'error'));
}

function renderCounters(counters) {
    const list = document.getElementById('counters-list');
    if (!counters.length) {
        list.innerHTML = '<p style="color:var(--text-muted)">No counters found.</p>';
        return;
    }
    list.innerHTML = counters.map(c => `
        <div class="card" style="padding:1rem;">
            <div style="font-weight:700;margin-bottom:0.25rem;">${escHtml(c.name)}</div>
            <div style="font-size:0.85rem;color:var(--text-muted);margin-bottom:0.5rem;">${escHtml(c.branch_name)}</div>
            <span class="badge ${c.status === 'Active' ? 'badge-success' : 'badge-secondary'}"
                  style="margin-bottom:0.75rem;display:inline-block;">${c.status}</span>
            <div style="display:flex;gap:0.5rem;">
                <button class="btn btn-sm btn-primary" onclick="openCounter(${c.id})"
                    ${c.status === 'Active' ? 'disabled' : ''}>Open</button>
                <button class="btn btn-sm btn-secondary" onclick="closeCounter(${c.id})"
                    ${c.status === 'Inactive' ? 'disabled' : ''}>Close</button>
            </div>
        </div>
    `).join('');
}

function populateSelect(counters) {
    const sel = document.getElementById('action-counter-select');
    const current = sel.value;
    sel.innerHTML = '<option value="">— choose a counter —</option>' +
        counters.map(c => `<option value="${c.id}" ${String(c.id) === String(current) ? 'selected' : ''}>${escHtml(c.name)} (${escHtml(c.branch_name)})</option>`).join('');
}

function openCounter(id) {
    postAction(`/api/admin/counters/${id}/open`, {}, (data) => {
        showAlert(data.message, 'success');
        loadCounters();
    });
}

function closeCounter(id) {
    postAction(`/api/admin/counters/${id}/close`, {}, (data) => {
        showAlert(`${data.message} — ${data.reassigned} token(s) reassigned.`, 'success');
        loadCounters();
    });
}

function loadQueue(counterId) {
    fetch(`/api/admin/queue/waiting?counter_id=${counterId}`)
        .then(r => r.json())
        .then(data => {
            const display = document.getElementById('queue-display');
            if (!data.tokens || !data.tokens.length) {
                display.innerHTML = '<p style="color:var(--text-muted)">No waiting tokens for this counter.</p>';
                return;
            }
            display.innerHTML = `
                <table class="table" style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr>
                            <th style="text-align:left;padding:0.5rem;border-bottom:1px solid var(--border)">#</th>
                            <th style="text-align:left;padding:0.5rem;border-bottom:1px solid var(--border)">Token</th>
                            <th style="text-align:left;padding:0.5rem;border-bottom:1px solid var(--border)">Status</th>
                            <th style="text-align:left;padding:0.5rem;border-bottom:1px solid var(--border)">Est. Wait</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.tokens.map((t, i) => `
                        <tr>
                            <td style="padding:0.5rem;border-bottom:1px solid var(--border)">${i + 1}</td>
                            <td style="padding:0.5rem;border-bottom:1px solid var(--border);font-weight:600;">${escHtml(t.token_number)}</td>
                            <td style="padding:0.5rem;border-bottom:1px solid var(--border)">${escHtml(t.status)}</td>
                            <td style="padding:0.5rem;border-bottom:1px solid var(--border)">${t.estimated_wait_minutes != null ? t.estimated_wait_minutes + ' min' : '—'}</td>
                        </tr>`).join('')}
                    </tbody>
                </table>`;
        })
        .catch(() => showAlert('Failed to load queue.', 'error'));
}

function postAction(url, body, onSuccess) {
    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    })
        .then(r => r.json())
        .then(data => {
            if (data.error) showAlert(data.error, 'error');
            else onSuccess(data);
        })
        .catch(() => showAlert('Request failed. Please try again.', 'error'));
}

function showAlert(message, type) {
    const el = document.getElementById('action-alert');
    el.textContent = message;
    el.style.display = 'block';
    el.style.background = type === 'error' ? 'var(--danger, #e74c3c)' : 'var(--success, #27ae60)';
    el.style.color = '#fff';
    el.style.padding = '0.75rem 1rem';
    el.style.borderRadius = '6px';
    setTimeout(() => { el.style.display = 'none'; }, 4000);
}

function escHtml(str) {
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}
