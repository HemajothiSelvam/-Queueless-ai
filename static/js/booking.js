/* booking.js — replaces old form with location-based hospital card picker */

document.addEventListener('DOMContentLoaded', function() {

  // Replace the old form with new card-based UI
  var card = document.getElementById('booking-card');
  if (!card) return;

  card.innerHTML = `
    <h1 style="font-size:1.5rem;font-weight:800;margin-bottom:1rem">🏥 Book Appointment</h1>
    <div id="loc-bar" style="padding:.6rem 1rem;border-radius:8px;font-size:.85rem;font-weight:600;margin-bottom:1.25rem;background:#dbeafe;color:#1e40af;border:1px solid #93c5fd">
      📍 <span id="loc-text">Detecting your location…</span>
    </div>
    <div id="alert-msg" style="display:none;background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;padding:.75rem 1rem;border-radius:8px;margin-bottom:1rem;font-size:.9rem"></div>

    <div style="margin-bottom:1rem">
      <div style="font-size:.75rem;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:#6366f1;margin-bottom:.75rem">Step 1 — Select Hospital (nearest first)</div>
      <div id="hosp-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem">
        <div style="color:#94a3b8;grid-column:1/-1">Loading hospitals…</div>
      </div>
    </div>

    <div id="step2" style="display:none;margin-bottom:1rem">
      <div style="font-size:.75rem;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:#6366f1;margin-bottom:.75rem">Step 2 — Department</div>
      <select id="new-service" style="width:100%;padding:.6rem .75rem;border:1px solid #e2e8f0;border-radius:8px;font-size:.9rem"></select>
    </div>

    <div id="step3" style="display:none;margin-bottom:1rem">
      <div style="font-size:.75rem;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:#6366f1;margin-bottom:.75rem">Step 3 — Date</div>
      <input type="date" id="new-date" style="width:100%;padding:.6rem .75rem;border:1px solid #e2e8f0;border-radius:8px;font-size:.9rem">
    </div>

    <div id="step4" style="display:none;margin-bottom:1rem">
      <div style="font-size:.75rem;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:#6366f1;margin-bottom:.75rem">Step 4 — Time Slot</div>
      <div id="ai-info" style="display:none;background:#d1fae5;color:#065f46;padding:.5rem .75rem;border-radius:8px;font-size:.8rem;margin-bottom:.6rem"></div>
      <div id="slot-btns" style="display:grid;grid-template-columns:repeat(6,1fr);gap:.3rem"></div>
      <div id="wait-est" style="display:none;background:#dbeafe;color:#1e40af;padding:.5rem .75rem;border-radius:8px;font-size:.82rem;margin-top:.6rem">
        ⏱️ Est. wait: <strong id="wait-val">—</strong> min
      </div>
    </div>

    <button id="new-book-btn" style="display:none;width:100%;padding:.9rem;background:#6366f1;color:white;border:none;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer">
      🎫 Confirm Appointment
    </button>
  `;

  var uLat = null, uLng = null, selBr = null, selSl = null;

  var SLOTS = [];
  for (var h = 9; h < 17; h++)
    for (var m = 0; m < 60; m += 10)
      SLOTS.push(String(h).padStart(2,'0') + ':' + String(m).padStart(2,'0'));

  function kd(a,b,c,d) {
    var R=6371, r=Math.PI/180, dL=(c-a)*r, dG=(d-b)*r;
    var x=Math.sin(dL/2)**2+Math.cos(a*r)*Math.cos(c*r)*Math.sin(dG/2)**2;
    return (R*2*Math.atan2(Math.sqrt(x),Math.sqrt(1-x))).toFixed(1);
  }

  function setLoc(msg, ok) {
    var el = document.getElementById('loc-bar');
    var txt = document.getElementById('loc-text');
    if (ok === true) { el.style.background='#d1fae5'; el.style.color='#065f46'; el.style.borderColor='#6ee7b7'; }
    else if (ok === false) { el.style.background='#fef3c7'; el.style.color='#92400e'; el.style.borderColor='#fcd34d'; }
    txt.textContent = msg;
  }

  function showAlert(msg) {
    var el = document.getElementById('alert-msg');
    el.textContent = msg; el.style.display = 'block';
    setTimeout(function(){ el.style.display='none'; }, 5000);
  }

  // Get location then load hospitals
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(
      function(pos) {
        uLat = pos.coords.latitude; uLng = pos.coords.longitude;
        setLoc('✅ ' + uLat.toFixed(4) + ', ' + uLng.toFixed(4), true);
        loadHospitals();
      },
      function() {
        setLoc('⚠️ Location denied — showing all hospitals', false);
        loadHospitals();
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  } else {
    setLoc('⚠️ Geolocation not supported', false);
    loadHospitals();
  }

  function loadHospitals() {
    fetch('/api/branches').then(function(r){ return r.json(); }).then(function(hs) {
      if (uLat !== null) {
        hs = hs.map(function(h) {
          return Object.assign({}, h, { km: h.latitude ? parseFloat(kd(uLat,uLng,h.latitude,h.longitude)) : 9999 });
        }).sort(function(a,b){ return a.km - b.km; });
      } else {
        hs = hs.map(function(h){ return Object.assign({}, h, { km: null }); });
      }
      renderHospitals(hs);
    }).catch(function(){ showAlert('Failed to load hospitals'); });
  }

  function renderHospitals(hs) {
    var g = document.getElementById('hosp-grid');
    g.innerHTML = '';
    var mn = uLat ? Math.min.apply(null, hs.filter(function(h){ return h.km; }).map(function(h){ return h.km; })) : null;

    hs.forEach(function(h) {
      var c = document.createElement('div');
      c.style.cssText = 'border:2px solid #e2e8f0;border-radius:12px;padding:1rem;cursor:pointer;background:white;transition:all .18s;position:relative';
      c.innerHTML =
        '<div style="font-weight:800;font-size:.9rem;color:#1e293b;margin-bottom:.2rem">🏥 ' + h.name + '</div>' +
        '<div style="font-size:.75rem;color:#64748b;margin-bottom:.35rem;line-height:1.4">' + h.location + '</div>' +
        (h.km ? '<span style="background:#ede9fe;color:#6366f1;font-size:.7rem;font-weight:700;padding:.1rem .45rem;border-radius:999px">📍 ' + h.km + ' km</span>' : '') +
        (h.km && h.km === mn ? '<div style="font-size:.7rem;color:#059669;font-weight:700;margin-top:.2rem">⚡ Nearest</div>' : '');

      c.addEventListener('mouseover', function(){ c.style.borderColor='#6366f1'; c.style.transform='translateY(-2px)'; });
      c.addEventListener('mouseout', function(){ if (!c.classList.contains('sel')){ c.style.borderColor='#e2e8f0'; c.style.transform=''; } });
      c.addEventListener('click', function(){ selectHospital(h.id, c); });
      g.appendChild(c);
    });
  }

  function selectHospital(bid, el) {
    document.querySelectorAll('#hosp-grid > div').forEach(function(c){
      c.style.borderColor='#e2e8f0'; c.style.background='white'; c.style.transform='';
    });
    el.style.borderColor='#6366f1'; el.style.background='#eef2ff';
    selBr = bid;

    fetch('/api/branches/' + bid + '/services').then(function(r){ return r.json(); }).then(function(svs) {
      var s = document.getElementById('new-service');
      s.innerHTML = '<option value="">— Choose department —</option>';
      svs.forEach(function(sv){
        var o = document.createElement('option'); o.value = sv.id; o.textContent = sv.name; s.appendChild(o);
      });
      document.getElementById('step2').style.display = 'block';
      var today = new Date().toISOString().split('T')[0];
      document.getElementById('new-date').setAttribute('min', today);
      document.getElementById('new-date').value = today;
      document.getElementById('step3').style.display = 'block';
      document.getElementById('step4').style.display = 'block';
      document.getElementById('new-book-btn').style.display = 'block';
      renderSlots();
    });
  }

  function renderSlots() {
    var g = document.getElementById('slot-btns');
    g.innerHTML = ''; selSl = null;
    document.getElementById('wait-est').style.display = 'none';
    var sid = document.getElementById('new-service').value;
    var aiSlots = [];

    function doRender(ai) {
      SLOTS.forEach(function(sl) {
        var b = document.createElement('button');
        b.type = 'button';
        b.style.cssText = 'padding:.35rem .1rem;border:1.5px solid ' + (ai.includes(sl) ? '#10b981' : '#e2e8f0') + ';border-radius:7px;background:white;font-size:.7rem;cursor:pointer;text-align:center;color:#334155';
        b.innerHTML = sl + (ai.includes(sl) ? '<br><span style="font-size:.55rem;background:#d1fae5;color:#065f46;border-radius:3px;padding:0 2px">AI</span>' : '');
        b.addEventListener('click', function(){
          document.querySelectorAll('#slot-btns button').forEach(function(x){ x.style.background='white'; x.style.color='#334155'; x.style.fontWeight=''; });
          b.style.background='#6366f1'; b.style.color='white'; b.style.fontWeight='700';
          selSl = sl; updateWait();
        });
        g.appendChild(b);
      });
    }

    if (selBr && sid) {
      fetch('/api/predict/best-slots?branch_id=' + selBr + '&service_type_id=' + sid)
        .then(function(r){ return r.json(); })
        .then(function(d){
          aiSlots = (d.slots || []).map(function(s){ return s.slot; });
          if (aiSlots.length) {
            document.getElementById('ai-info').textContent = '🤖 AI recommends: ' + aiSlots.join(', ');
            document.getElementById('ai-info').style.display = 'block';
          }
          doRender(aiSlots);
        }).catch(function(){ doRender([]); });
    } else { doRender([]); }
  }

  function updateWait() {
    var sid = document.getElementById('new-service').value;
    if (!selBr || !sid || !selSl) return;
    fetch('/api/predict/wait-time?branch_id=' + selBr + '&service_type_id=' + sid + '&slot=' + selSl)
      .then(function(r){ return r.json(); })
      .then(function(d){
        document.getElementById('wait-val').textContent = d.estimated_wait_minutes || '—';
        document.getElementById('wait-est').style.display = 'block';
      }).catch(function(){});
  }

  document.getElementById('new-service').addEventListener('change', renderSlots);

  document.getElementById('new-book-btn').addEventListener('click', function() {
    var sid = document.getElementById('new-service').value;
    var date = document.getElementById('new-date').value;
    if (!selBr) { showAlert('Please select a hospital'); return; }
    if (!sid) { showAlert('Please select a department'); return; }
    if (!date) { showAlert('Please select a date'); return; }
    if (!selSl) { showAlert('Please select a time slot'); return; }

    var btn = document.getElementById('new-book-btn');
    btn.disabled = true; btn.textContent = 'Booking…';

    fetch('/api/tokens/book', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ branch_id: parseInt(selBr), service_type_id: parseInt(sid), preferred_slot: selSl, date: date })
    }).then(function(r){
      if (r.status === 401) { window.location.href = '/login'; return null; }
      return r.json().then(function(d){ return { ok: r.ok, data: d }; });
    }).then(function(res){
      if (!res) return;
      if (!res.ok) { showAlert(res.data.error || 'Booking failed'); return; }
      // Show success
      var sc = document.getElementById('success-card');
      document.getElementById('booking-card').style.display = 'none';
      document.getElementById('result-token-number').textContent = res.data.token_number;
      document.getElementById('result-wait-time').textContent = res.data.estimated_wait_minutes || '—';
      sc.style.display = 'block';
    }).catch(function(){ showAlert('Network error'); })
    .finally(function(){ btn.disabled = false; btn.textContent = '🎫 Confirm Appointment'; });
  });

});
