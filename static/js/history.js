/* history.js — User queue history page */

let currentPage = 1;
let totalPages = 1;

function loadHistory(page) {
  currentPage = page;

  // Show loading, hide everything else
  document.getElementById('loading-state').style.display = 'block';
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('history-table-wrap').style.display = 'none';
  document.getElementById('pagination').style.display = 'none';

  fetch('/api/tokens/history?page=' + page)
    .then(function (res) {
      if (!res.ok) throw new Error('Failed to load history');
      return res.json();
    })
    .then(function (data) {
      document.getElementById('loading-state').style.display = 'none';

      if (data.tokens.length === 0 && page === 1) {
        document.getElementById('empty-state').style.display = 'block';
        return;
      }

      totalPages = data.pages;

      // Render rows
      var tbody = document.getElementById('history-body');
      tbody.innerHTML = '';
      data.tokens.forEach(function (token) {
        tbody.insertAdjacentHTML('beforeend', renderRow(token));
      });

      // Show table
      document.getElementById('history-table-wrap').style.display = 'block';

      // Update and show pagination only when there are multiple pages
      if (data.pages > 1) {
        updatePagination(data.page, data.pages);
        document.getElementById('pagination').style.display = 'flex';
      }
    })
    .catch(function (err) {
      document.getElementById('loading-state').innerHTML =
        '⚠️ Failed to load history. Please try refreshing the page.';
    });
}

function renderRow(token) {
  var date = token.booked_at
    ? new Date(token.booked_at).toLocaleDateString()
    : '—';

  var waitTime = token.estimated_wait_minutes != null
    ? token.estimated_wait_minutes + ' min'
    : '—';

  var statusClass = {
    'Waiting': 'badge-waiting',
    'Now Serving': 'badge-serving',
    'Served': 'badge-served',
    'Cancelled': 'badge-cancelled',
    'Skipped': 'badge-skipped'
  }[token.status] || 'badge-waiting';

  return '<tr>' +
    '<td>' + date + '</td>' +
    '<td><strong>' + (token.token_number || '—') + '</strong></td>' +
    '<td>' + (token.branch_name || '—') + '</td>' +
    '<td>' + (token.service_type_name || '—') + '</td>' +
    '<td>' + waitTime + '</td>' +
    '<td><span class="badge ' + statusClass + '">' + (token.status || '—') + '</span></td>' +
    '</tr>';
}

function updatePagination(page, pages) {
  document.getElementById('page-info').textContent = 'Page ' + page + ' of ' + pages;
  document.getElementById('btn-prev').disabled = page <= 1;
  document.getElementById('btn-next').disabled = page >= pages;
}

document.addEventListener('DOMContentLoaded', function () {
  document.getElementById('btn-prev').addEventListener('click', function () {
    if (currentPage > 1) {
      loadHistory(currentPage - 1);
    }
  });

  document.getElementById('btn-next').addEventListener('click', function () {
    if (currentPage < totalPages) {
      loadHistory(currentPage + 1);
    }
  });

  loadHistory(1);
});
