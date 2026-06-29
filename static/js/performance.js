/* Performance-optimized JavaScript utilities */

// Memoization cache for expensive operations
const memoCache = new Map();

function memoize(fn, key) {
  if (memoCache.has(key)) return memoCache.get(key);
  const result = fn();
  memoCache.set(key, result);
  return result;
}

// Debounce function for resize events (time complexity: O(1))
function debounce(fn, delay) {
  let timeoutId;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

// Throttle function for scroll events (time complexity: O(1))
function throttle(fn, delay) {
  let lastCall = 0;
  return function(...args) {
    const now = Date.now();
    if (now - lastCall >= delay) {
      lastCall = now;
      fn(...args);
    }
  };
}

// Intersection Observer for lazy loading (time complexity: O(n))
const observerOptions = {
  threshold: 0.1,
  rootMargin: '50px'
};

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('loaded');
      observer.unobserve(entry.target);
    }
  });
}, observerOptions);

// Cache API responses (time complexity: O(1) for lookup, O(n) for first fetch)
const apiCache = new Map();
const CACHE_DURATION = 30000; // 30 seconds

async function cachedFetch(url) {
  const now = Date.now();
  const cached = apiCache.get(url);
  
  if (cached && now - cached.timestamp < CACHE_DURATION) {
    return cached.data;
  }
  
  const response = await fetch(url);
  const data = await response.json();
  apiCache.set(url, { data, timestamp: now });
  return data;
}

// Batch DOM updates to prevent layout thrashing (time complexity: O(n))
class BatchDOMUpdater {
  constructor() {
    this.updates = [];
    this.scheduled = false;
  }
  
  add(fn) {
    this.updates.push(fn);
    this.scheduleFlush();
  }
  
  scheduleFlush() {
    if (!this.scheduled) {
      this.scheduled = true;
      requestAnimationFrame(() => this.flush());
    }
  }
  
  flush() {
    this.updates.forEach(fn => fn());
    this.updates = [];
    this.scheduled = false;
  }
}

const domUpdater = new BatchDOMUpdater();

// Optimize polls rendering (time complexity: O(n) where n = number of polls)
async function loadPollDataOptimized() {
  try {
    const polls = await cachedFetch('/api/polls');
    const container = document.getElementById('polls-container');
    
    if (!container) return;
    
    // Use DocumentFragment to batch inserts
    const fragment = document.createDocumentFragment();
    
    polls.forEach((poll, index) => {
      const card = createPollCard(poll);
      card.style.animationDelay = `${index * 50}ms`;
      fragment.appendChild(card);
    });
    
    domUpdater.add(() => {
      container.innerHTML = '';
      container.appendChild(fragment);
    });
  } catch (error) {
    console.error('Error loading polls:', error);
  }
}

// Optimize vote table rendering (time complexity: O(n) where n = items per page)
function renderVoteTableOptimized(votes) {
  const start = (currentPage - 1) * ITEMS_PER_PAGE;
  const end = start + ITEMS_PER_PAGE;
  const pageVotes = votes.slice(start, end);
  
  const tbody = document.querySelector('#vote-log-table tbody');
  const fragment = document.createDocumentFragment();
  
  pageVotes.forEach((vote, index) => {
    const tr = document.createElement('tr');
    tr.style.animationDelay = `${index * 30}ms`;
    tr.innerHTML = `
      <td>⏰ ${new Date(vote.timestamp).toLocaleString()}</td>
      <td>👤 ${vote.username}</td>
      <td>❓ ${vote.question}</td>
      <td><strong>✓ ${vote.choice}</strong></td>
    `;
    fragment.appendChild(tr);
  });
  
  domUpdater.add(() => {
    tbody.innerHTML = '';
    tbody.appendChild(fragment);
  });
}

// Optimize counter animation with RequestAnimationFrame (time complexity: O(1) per frame)
function animateCounterOptimized(element, target, duration = 800) {
  const start = 0;
  const startTime = performance.now();
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const current = Math.floor(start + (target - start) * easeOutQuad(progress));
    
    element.textContent = current;
    
    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }
  
  function easeOutQuad(t) {
    return t * (2 - t);
  }
  
  requestAnimationFrame(update);
}

// Export optimized functions
export { memoize, debounce, throttle, cachedFetch, domUpdater, loadPollDataOptimized, renderVoteTableOptimized, animateCounterOptimized };
