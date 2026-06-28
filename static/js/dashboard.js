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

function filterVotes() {
  const searchTerm = document.getElementById('search-input').value.toLowerCase();
  const filtered = allVotes.filter(vote =>
    vote.username.toLowerCase().includes(searchTerm) ||
    vote.question.toLowerCase().includes(searchTerm)
  );
  
  currentPage = 1;
  renderVoteTable(filtered);
  renderPagination(filtered.length);
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
  tbody.innerHTML = pageVotes.map((vote, index) => `
    <tr style="animation-delay: ${index * 50}ms;">
      <td>⏰ ${new Date(vote.timestamp).toLocaleString()}</td>
      <td>👤 ${vote.username}</td>
      <td>❓ ${vote.question}</td>
      <td><strong>✓ ${vote.choice}</strong></td>
    </tr>
  `).join('');
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

// Schedule
async function loadScheduleData() {
  try {
    const response = await fetch('/api/schedule');
    const schedule = await response.json();
    
    const container = document.getElementById('schedule-container');
    container.innerHTML = '';
    
    schedule.forEach((session, index) => {
      setTimeout(() => {
        const card = createSessionCard(session);
        container.appendChild(card);
      }, index * 100);
    });
  } catch (error) {
    console.error('Error loading schedule:', error);
  }
}

function createSessionCard(session) {
  const card = document.createElement('div');
  card.className = `session-card ${session.pillar === 'Holistic STEMinist' ? 'holistic' : 'prodev'}`;
  
  const emoji = session.pillar === 'Holistic STEMinist' ? '✨' : '💼';
  
  card.innerHTML = `
    <div class="session-name">${emoji} ${session.name}</div>
    <div class="session-meta">${session.pillar}</div>
    <div class="session-time">🕐 ${session.time}</div>
    <div class="session-detail" id="detail-${session.id}">
      <strong>🎤 Speaker:</strong> ${session.speaker}<br>
      <strong>📍 Location:</strong> ${session.location}<br>
      <strong>📝 Description:</strong> ${session.description || 'No description available'}
    </div>
  `;
  
  card.addEventListener('click', function() {
    const detail = document.getElementById(`detail-${session.id}`);
    detail.classList.toggle('show');
  });
  
  return card;
}

// Auto-refresh bot status every 30 seconds
setInterval(loadBotStatus, 30000);

// Update all data
function updateAllData() {
  if (document.getElementById('polls').classList.contains('active')) loadPollData();
  if (document.getElementById('vote-log').classList.contains('active')) loadVoteLogData();
  if (document.getElementById('schedule').classList.contains('active')) loadScheduleData();
  loadBotStatus();
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
  initTheme();
  loadBotStatus();
  showSection('polls');
});

