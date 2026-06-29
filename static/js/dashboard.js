// Animate counter values
function animateCounter(element, target) {
  const start = 0;
  const duration = 800;
  const startTime = Date.now();
  
  function update() {
    const elapsed = Date.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const current = Math.floor(start + (target - start) * easeOutQuad(progress));
    element.textContent = current;
    
    if (progress < 1) requestAnimationFrame(update);
  }
  
  function easeOutQuad(t) {
    return t * (2 - t);
  }
  
  update();
}

// Theme toggle
function initTheme() {
  const isDark = localStorage.getItem('bridge-theme') === 'dark' ||
    (!localStorage.getItem('bridge-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
  
  if (isDark) {
    document.documentElement.classList.add('dark');
    updateThemeIcon();
  }
}

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('bridge-theme', isDark ? 'dark' : 'light');
  updateThemeIcon();
  updateAllData();
}

function updateThemeIcon() {
  const icon = document.getElementById('theme-icon');
  if (document.documentElement.classList.contains('dark')) {
    icon.textContent = '☀️';
  } else {
    icon.textContent = '🌙';
  }
}

// Section navigation
function showSection(sectionId) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  
  const section = document.getElementById(sectionId);
  const link = document.querySelector(`[data-section="${sectionId}"]`);
  
  if (section) section.classList.add('active');
  if (link) link.classList.add('active');
  
  // Load data when section becomes active
  if (sectionId === 'polls') loadPollData();
  if (sectionId === 'vote-log') loadVoteLogData();
  if (sectionId === 'schedule') loadScheduleData();
}

// Poll Results
let pollChart = null;

async function loadPollData() {
  try {
    const response = await fetch('/api/polls');
    const polls = await response.json();
    
    const container = document.getElementById('polls-container');
    container.innerHTML = '';
    
    polls.forEach((poll, index) => {
      setTimeout(() => {
        const card = createPollCard(poll);
        container.appendChild(card);
      }, index * 100);
    });
  } catch (error) {
    console.error('Error loading polls:', error);
  }
}

function createPollCard(poll) {
  const card = document.createElement('div');
  card.className = 'card';
  
  const options = poll.options || [];
  const maxVotes = Math.max(...options.map(o => o.votes), 1);
  const totalVotes = options.reduce((sum, o) => sum + o.votes, 0);
  const leadingOption = options.reduce((max, o) => o.votes > max.votes ? o : max, options[0]);
  
  const optionsHTML = options.map(option => `
    <div class="poll-option">
      <div class="poll-option-label">
        <span>${option.name}</span>
        <span><span class="vote-percentage">${((option.votes / totalVotes) * 100).toFixed(1)}</span>%</span>
      </div>
      <div class="poll-bar">
        <div class="poll-bar-fill" style="width: 0%;" data-width="${(option.votes / maxVotes) * 100}">
          <span class="vote-count">${option.votes}</span>
        </div>
      </div>
    </div>
  `).join('');
  
  card.innerHTML = `
    <h3 class="card-title">${poll.question}</h3>
    ${optionsHTML}
    <div class="poll-stats">
      <span><strong><span class="total-votes">0</span></strong> total votes</span>
      <span>Leading: <strong>${leadingOption.name}</strong></span>
    </div>
    <div class="card-meta">📅 Last updated: ${new Date(poll.timestamp).toLocaleString()}</div>
  `;
  
  // Animate bars and counters
  setTimeout(() => {
    card.querySelectorAll('.poll-bar-fill').forEach(bar => {
      const width = bar.getAttribute('data-width');
      bar.style.width = width + '%';
    });
    
    const totalVotesSpan = card.querySelector('.total-votes');
    animateCounter(totalVotesSpan, totalVotes);
  }, 10);
  
  return card;
}

// Vote Log
let currentPage = 1;
const ITEMS_PER_PAGE = 25;
let allVotes = [];

async function loadVoteLogData() {
  try {
    const response = await fetch('/api/votes');
    allVotes = await response.json();
    renderVoteLogPage(1);
    updateSyncTime();
  } catch (error) {
    console.error('Error loading vote log:', error);
  }
}

function updateSyncTime() {
  const now = new Date();
  document.getElementById('sync-time').textContent = `🔄 Last synced: ${now.toLocaleTimeString()}`;
}

// Debounce for search input (time complexity: O(n) filtering, O(1) debounce)
let searchTimeout;
function filterVotesOptimized() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    if (!searchTerm) {
      currentPage = 1;
      renderVoteTableOptimized(allVotes);
      renderPagination(allVotes.length);
      return;
    }
    
    // Time complexity: O(n) single pass filter
    const filtered = allVotes.filter(vote =>
      vote.username.toLowerCase().includes(searchTerm) ||
      vote.question.toLowerCase().includes(searchTerm)
    );
    
    currentPage = 1;
    renderVoteTableOptimized(filtered);
    renderPagination(filtered.length);
  }, 300);
}

function renderVoteLogPage(page) {
  currentPage = page;
  renderVoteTable(allVotes);
  renderPagination(allVotes.length);
}

function renderVoteTable(votes) {
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
  
  tbody.innerHTML = '';
  tbody.appendChild(fragment);
}

function renderPagination(totalItems) {
  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
  const paginationContainer = document.getElementById('pagination');
  
  let html = `<button onclick="renderVoteLogPage(1)" ${currentPage === 1 ? 'disabled' : ''}>« First</button>
             <button onclick="renderVoteLogPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>‹ Prev</button>`;
  
  for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
    html += `<button onclick="renderVoteLogPage(${i})" class="${i === currentPage ? 'active' : ''}">${i}</button>`;
  }
  
  html += `<button onclick="renderVoteLogPage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>Next ›</button>
          <button onclick="renderVoteLogPage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>Last »</button>`;
  
  paginationContainer.innerHTML = html;
  document.getElementById('page-info').textContent = `Page ${currentPage} of ${totalPages}`;
}

async function exportCSV() {
  try {
    const response = await fetch('/api/votes/export');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'vote-log.csv';
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Error exporting CSV:', error);
  }
}

// Bot Status
async function loadBotStatus() {
  try {
    const response = await fetch('/api/bot-status');
    const status = await response.json();
    
    const container = document.getElementById('bot-status-container');
    
    // Update sidebar indicator
    const indicator = document.getElementById('bot-status-indicator');
    if (indicator) {
      const dot = indicator.querySelector('.status-dot');
      dot.classList.remove('online', 'offline');
      dot.classList.add(status.online ? 'online' : 'offline');
    }
    
    container.innerHTML = `
      <div class="card">
        <h3 class="card-title">🤖 Bot Status</h3>
        <div class="status-indicator">
          <div class="status-dot ${status.online ? 'online' : 'offline'}"></div>
          <span>${status.online ? '🟢 Online' : '🔴 Offline'}</span>
        </div>
        <div class="status-info">
          <div class="status-row">
            <span class="status-label">⏱️ Uptime:</span>
            <span class="status-value">${status.uptime}</span>
          </div>
          <div class="status-row">
            <span class="status-label">💬 Last Command:</span>
            <span class="status-value">${status.last_command || 'N/A'}</span>
          </div>
          <div class="status-row">
            <span class="status-label">📊 Today's Votes:</span>
            <span class="status-value"><span class="votes-today">0</span></span>
          </div>
          <div class="status-row">
            <span class="status-label">🎯 Total Votes:</span>
            <span class="status-value"><span class="votes-total">0</span></span>
          </div>
        </div>
      </div>
    `;
    
    // Animate counters
    setTimeout(() => {
      const todaySpan = container.querySelector('.votes-today');
      const totalSpan = container.querySelector('.votes-total');
      animateCounter(todaySpan, status.votes_today);
      animateCounter(totalSpan, status.votes_total);
    }, 100);
  } catch (error) {
    console.error('Error loading bot status:', error);
  }
}

// Modal handling and interactive features
let pollChartInstance = null;

function openPollModal(poll) {
const modal = document.getElementById('poll-modal');
const title = document.getElementById('modal-title');
title.textContent = poll.question;
modal.setAttribute('aria-hidden', 'false');
modal.classList.add('open');

// Render Chart.js horizontal bar chart
const ctx = document.getElementById('poll-chart-canvas').getContext('2d');
const labels = poll.options.map(o => o.name);
const data = poll.options.map(o => o.votes);

if (pollChartInstance) {
  pollChartInstance.destroy();
  }

pollChartInstance = new Chart(ctx, {
  type: 'bar',
  data: {
    labels: labels,
    datasets: [{
      label: 'Votes',
      data: data,
      backgroundColor: labels.map(() => getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() || '#FFD700'),
      borderRadius: 8
    }]
  },
  options: {
    indexAxis: 'y',
    responsive: true,
    scales: {
      x: { beginAtZero: true }
    },
    plugins: { legend: { display: false } }
  }
});

// Also show a small preview in the Live Poll Preview card
const preview = document.getElementById('live-poll-preview');
preview.innerHTML = `<strong>${poll.question}</strong><div style="margin-top:8px;color:var(--color-text-muted)">Click the chart to open full view</div>`;
}

function closePollModal() {
const modal = document.getElementById('poll-modal');
modal.setAttribute('aria-hidden', 'true');
modal.classList.remove('open');
}

// Poll creation
async function submitPollForm(e) {
e.preventDefault();
const q = document.getElementById('poll-question').value.trim();
const o1 = document.getElementById('poll-option1').value.trim();
const o2 = document.getElementById('poll-option2').value.trim();
const resp = document.getElementById('create-response');

if (!q || !o1 || !o2) {
  resp.textContent = 'Please provide a question and two options.';
  return;
}

try {
  const r = await fetch('/submit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question: q, option1: o1, option2: o2 })
  });

  const json = await r.json();
  if (r.ok) {
    resp.textContent = 'Poll created — refreshing list...';
    document.getElementById('create-poll-form').reset();
    loadPollData();
    setTimeout(() => resp.textContent = '', 3000);
  } else {
    resp.textContent = json.error || 'Error creating poll';
  }
} catch (err) {
  console.error(err);
  resp.textContent = 'Network error creating poll';
}
}

// Refresh polls button
document.addEventListener('click', function(e) {
if (e.target && e.target.id === 'refresh-polls') {
  loadPollData();
}
});

// Wire modal close
document.addEventListener('click', function(e) {
if (e.target && (e.target.id === 'modal-backdrop' || e.target.id === 'modal-close')) {
  closePollModal();
}
});

// Make poll cards clickable: modify createPollCard to attach click handler (done below when creating cards)

// Auto-refresh bot status every 30 seconds
setInterval(loadBotStatus, 30000);

// Update all data
function updateAllData() {
if (document.getElementById('polls').classList.contains('active')) loadPollData();
if (document.getElementById('vote-log').classList.contains('active')) loadVoteLogData();
if (document.getElementById('interactive').classList.contains('active')) {
  // nothing heavy here; polls are refreshed on demand
}
loadBotStatus();
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
initTheme();
loadBotStatus();
showSection('polls');

// Setup form listener (live control)
const form = document.getElementById('create-poll-form');
if (form) form.addEventListener('submit', submitPollForm);

// Delegate clicks on poll cards to open modal
const pollsStreamObserver = new MutationObserver(() => {
  document.querySelectorAll('#polls-container .card, #polls-stream .card').forEach(card => {
    if (!card.dataset.clickBound) {
      card.dataset.clickBound = '1';
      card.style.cursor = 'pointer';
      card.addEventListener('click', () => {
        const idx = Array.from(card.parentElement.children).indexOf(card);
        // attempt to read poll data embedded on card
        const q = card.querySelector('.card-title')?.textContent || 'Poll';
        const optionEls = card.querySelectorAll('.poll-option');
        const options = Array.from(optionEls).map(el => ({
          name: el.querySelector('.poll-option-label span')?.textContent || 'Option',
          votes: parseInt(el.querySelector('.vote-count')?.textContent || '0', 10)
        }));
        openPollModal({ question: q, options });
      });
    }
  });
});
pollsStreamObserver.observe(document.getElementById('polls-container'), { childList: true, subtree: true });
pollsStreamObserver.observe(document.getElementById('polls-stream'), { childList: true, subtree: true });

});

