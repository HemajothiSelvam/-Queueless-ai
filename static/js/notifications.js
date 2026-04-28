/* notifications.js — Beautiful notifications UI */

document.addEventListener('DOMContentLoaded', async function() {

  // Inject page styles
  var style = document.createElement('style');
  style.textContent = `
    body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
    .notif-wrap { max-width: 680px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }
    .notif-page-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 1.5rem; padding: 1.5rem 2rem;
      background: rgba(255,255,255,0.15); backdrop-filter: blur(20px);
      border-radius: 16px; border: 1px solid rgba(255,255,255,0.2);
    }
    .notif-page-title {
      font-size: 1.6rem; font-weight: 900; color: white;
      display: flex; align-items: center; gap: 0.5rem;
    }
    .unread-pill {
      background: #ef4444; color: white; border-radius: 999px;
      font-size: 0.75rem; font-weight: 800; padding: 0.2rem 0.65rem;
      animation: pulse-red 2s infinite;
    }
    @keyframes pulse-red {
      0%,100% { box-shadow: 0 0 0 0 rgba(239,68,68,0.4); }
      50% { box-shadow: 0 0 0 6px rgba(239,68,68,0); }
    }
    .mark-read-btn {
      background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3);
      padding: 0.45rem 1rem; border-radius: 8px; font-size: 0.82rem; font-weight: 600;
      cursor: pointer; transition: all 0.2s;
    }
    .mark-read-btn:hover { background: rgba(255,255,255,0.35); }
    .notif-list { display: flex; flex-direction: column; gap: 0.75rem; }
    .notif-card {
      background: white; border-radius: 14px; padding: 1.1rem 1.25rem;
      display: flex; align-items: flex-start; gap: 1rem;
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
      border-left: 4px solid #e2e8f0;
      transition: transform 0.2s, box-shadow 0.2s;
      animation: slideIn 0.3s ease forwards;
      opacity: 0; transform: translateY(10px);
    }
    .notif-card:hover { transform: translateY(-2px); box-shadow: 0 8px 30px rgba(0,0,0,0.12); }
    .notif-card.unread { border-left-color: #6366f1; background: #fafbff; }
    .notif-card.type-turn { border-left-color: #10b981; }
    .notif-card.type-delay { border-left-color: #f59e0b; }
    .notif-card.type-general { border-left-color: #6366f1; }
    @keyframes slideIn {
      to { opacity: 1; transform: translateY(0); }
    }
    .notif-icon-wrap {
      width: 2.75rem; height: 2.75rem; border-radius: 12px;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.3rem; flex-shrink: 0;
    }
    .icon-turn { background: #d1fae5; }
    .icon-delay { background: #fef3c7; }
    .icon-general { background: #ede9fe; }
    .icon-changed { background: #dbeafe; }
    .notif-body { flex: 1; min-width: 0; }
    .notif-msg {
      font-size: 0.92rem; color: #1e293b; line-height: 1.5;
      margin-bottom: 0.35rem; font-weight: 500;
    }
    .notif-card.unread .notif-msg { font-weight: 700; color: #0f172a; }
    .notif-footer { display: flex; align-items: center; gap: 0.5rem; }
    .notif-time { font-size: 0.75rem; color: #94a3b8; }
    .notif-badge {
      font-size: 0.65rem; font-weight: 800; padding: 0.15rem 0.5rem;
      border-radius: 999px; text-transform: uppercase; letter-spacing: 0.04em;
    }
    .badge-turn { background: #d1fae5; color: #065f46; }
    .badge-delay { background: #fef3c7; color: #92400e; }
    .badge-general { background: #ede9fe; color: #4c1d95; }
    .badge-changed { background: #dbeafe; color: #1e40af; }
    .unread-dot {
      width: 7px; height: 7px; border-radius: 50%; background: #6366f1;
      display: inline-block; flex-shrink: 0;
    }
    .notif-empty {
      text-align: center; padding: 4rem 2rem;
      background: rgba(255,255,255,0.15); backdrop-filter: blur(20px);
      border-radius: 16px; border: 1px solid rgba(255,255,255,0.2);
      color: white;
    }
    .notif-empty .empty-icon { font-size: 3.5rem; margin-bottom: 1rem; }
    .notif-empty p { font-size: 1rem; opacity: 0.85; }
    .notif-loading {
      text-align: center; padding: 3rem;
      background: rgba(255,255,255,0.15); backdrop-filter: blur(20px);
      border-radius: 16px; color: white; font-size: 1rem;
    }
  `;
  document.head.appendChild(style);

  // Replace page structure
  var container = document.querySelector('.container') || document.querySelector('.notif-wrap');
  if (!container) {
    container = document.createElement('div');
    document.body.appendChild(container);
  }
  container.className = 'notif-wrap';
  container.innerHTML = `
    <div class="notif-page-header">
      <div class="notif-page-title">
        🔔 Notifications
        <span id="unread-pill" class="unread-pill" style="display:none"></span>
      </div>
      <button id="mark-read-btn" class="mark-read-btn" style="display:none">✓ Mark all read</button>
    </div>
    <div id="notif-content">
      <div class="notif-loading">⏳ Loading notifications…</div>
    </div>
  `;

  var TYPE_CONFIG = {
    turn_approaching: { icon: '🏥', iconClass: 'icon-turn', badgeClass: 'badge-turn', label: 'Your Turn' },
    queue_delay:      { icon: '⏱️', iconClass: 'icon-delay', badgeClass: 'badge-delay', label: 'Delay' },
    counter_changed:  { icon: '🔄', iconClass: 'icon-changed', badgeClass: 'badge-changed', label: 'Counter' },
    general:          { icon: '📢', iconClass: 'icon-general', badgeClass: 'badge-general', label: 'Info' }
  };

  function timeAgo(iso) {
    if (!iso) return '';
    var diff = Math.floor((Date.now() - new Date(iso)) / 1000);
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff/60) + ' min ago';
    if (diff < 86400) return Math.floor(diff/3600) + ' hr ago';
    return new Date(iso).toLocaleDateString();
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function renderCard(n, idx) {
    var cfg = TYPE_CONFIG[n.type] || TYPE_CONFIG.general;
    var unread = n.is_read === 0;
    var typeClass = n.type === 'turn_approaching' ? 'type-turn' : n.type === 'queue_delay' ? 'type-delay' : 'type-general';
    return `
      <div class="notif-card ${unread ? 'unread' : ''} ${typeClass}" style="animation-delay:${idx * 0.06}s">
        <div class="notif-icon-wrap ${cfg.iconClass}">${cfg.icon}</div>
        <div class="notif-body">
          <div class="notif-msg">${escHtml(n.message)}</div>
          <div class="notif-footer">
            ${unread ? '<span class="unread-dot"></span>' : ''}
            <span class="notif-time">${timeAgo(n.created_at)}</span>
            <span class="notif-badge ${cfg.badgeClass}">${cfg.label}</span>
          </div>
        </div>
      </div>
    `;
  }

  try {
    var res = await fetch('/api/notifications');
    var data = await res.json();
    var notifications = data.notifications || [];
    var content = document.getElementById('notif-content');
    var unreadCount = notifications.filter(function(n){ return n.is_read === 0; }).length;

    if (notifications.length === 0) {
      content.innerHTML = `
        <div class="notif-empty">
          <div class="empty-icon">🔕</div>
          <p>No notifications yet.</p>
          <p style="font-size:.85rem;margin-top:.5rem;opacity:.7">You'll be notified when your turn is approaching.</p>
        </div>
      `;
    } else {
      content.innerHTML = '<div class="notif-list">' +
        notifications.map(function(n, i){ return renderCard(n, i); }).join('') +
        '</div>';
    }

    if (unreadCount > 0) {
      var pill = document.getElementById('unread-pill');
      pill.textContent = unreadCount;
      pill.style.display = 'inline';
      var btn = document.getElementById('mark-read-btn');
      btn.style.display = 'inline-block';
      btn.addEventListener('click', async function() {
        await fetch('/api/notifications/mark-read', { method: 'POST' });
        document.querySelectorAll('.notif-card.unread').forEach(function(c){
          c.classList.remove('unread');
          var dot = c.querySelector('.unread-dot');
          if (dot) dot.remove();
        });
        pill.style.display = 'none';
        btn.style.display = 'none';
      });
      await fetch('/api/notifications/mark-read', { method: 'POST' });
    }

  } catch(e) {
    document.getElementById('notif-content').innerHTML =
      '<div class="notif-loading" style="color:#fca5a5">Failed to load notifications.</div>';
  }
});
