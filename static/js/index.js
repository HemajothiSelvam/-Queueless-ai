/* QueueLess AI — index.js: counter animation + testimonials slider */

// ── Animated counters ──────────────────────────────────────────────────────
function animateCounter(el, target, duration) {
  const start = performance.now();
  const from = 0;
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // ease-out cubic
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(from + (target - from) * eased);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

async function loadStats() {
  const visitorsEl  = document.getElementById('stat-visitors');
  const waitEl      = document.getElementById('stat-wait');
  const countersEl  = document.getElementById('stat-counters');

  if (!visitorsEl || !waitEl || !countersEl) return;

  try {
    const res  = await fetch('/api/admin/dashboard');
    if (!res.ok) throw new Error('non-ok');
    const data = await res.json();

    animateCounter(visitorsEl,  data.total_visitors  ?? data.total_tokens ?? 0, 1500);
    animateCounter(waitEl,      data.avg_wait_time   ?? 0,                       1500);
    animateCounter(countersEl,  data.active_counters ?? 0,                       1500);
  } catch {
    // Fallback demo values when API is unavailable
    animateCounter(visitorsEl,  1240, 1500);
    animateCounter(waitEl,      8,    1500);
    animateCounter(countersEl,  12,   1500);
  }
}

// ── Testimonials slider ────────────────────────────────────────────────────
const testimonials = [
  {
    text:   '"QueueLess AI saved me hours of waiting. I just booked my slot and showed up right on time!"',
    author: '— Priya S., Regular User'
  },
  {
    text:   '"The AI slot recommendations are spot-on. I always get the shortest wait time now."',
    author: '— Rahul M., Daily Commuter'
  },
  {
    text:   '"As a branch manager, the admin dashboard gives me everything I need to keep queues moving."',
    author: '— Anita K., Branch Manager'
  }
];

let currentIndex = 0;

function showTestimonial(index) {
  const textEl   = document.getElementById('testimonial-text');
  const authorEl = document.getElementById('testimonial-author');
  if (!textEl || !authorEl) return;

  const t = testimonials[index];
  textEl.textContent   = t.text;
  authorEl.textContent = t.author;
}

function initTestimonials() {
  const prevBtn = document.getElementById('btn-prev');
  const nextBtn = document.getElementById('btn-next');
  if (!prevBtn || !nextBtn) return;

  showTestimonial(currentIndex);

  prevBtn.addEventListener('click', () => {
    currentIndex = (currentIndex - 1 + testimonials.length) % testimonials.length;
    showTestimonial(currentIndex);
  });

  nextBtn.addEventListener('click', () => {
    currentIndex = (currentIndex + 1) % testimonials.length;
    showTestimonial(currentIndex);
  });

  // Auto-advance every 6 seconds
  setInterval(() => {
    currentIndex = (currentIndex + 1) % testimonials.length;
    showTestimonial(currentIndex);
  }, 6000);
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  initTestimonials();
});
