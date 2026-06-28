// Theme toggle
function initTheme() {
  const isDark = localStorage.getItem('bridge-theme') === 'dark' ||
    (!localStorage.getItem('bridge-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
  
  if (isDark) {
    document.documentElement.classList.add('dark');
  }
}

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('bridge-theme', isDark ? 'dark' : 'light');
  updateAllData();
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
    
    polls.forEach(poll => {
      const card = createPollCard(poll);
      container.appendChild(card);
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
        <span>${((option.votes / totalVotes) * 100).toFixed(1)}%</span>
      </div>
      <div class="poll-bar">
        <div class="poll-bar-fill" style="width: ${(option.votes / maxVotes) * 100}%;">
          ${option.votes > 0 ? option.votes : ''}
        </div>
      </div>
    </div>
  `).join('');
  
  card.innerHTML = `
    <h3 class="card-title">${poll.question}</h3>
    ${optionsHTML}
    <div class="poll-stats">
      <span><strong>${totalVotes}</strong> total votes</span>
      <span>Leading: <strong>${leadingOption.name}</strong></span>
    </div>
    <div class="card-meta">Last updated: ${new Date(poll.timestamp).toLocaleString()}</div>
  `;
  
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
  } catch (error) {
    console.error('Error loading vote log:', error);
  }
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
  tbody.innerHTML = pageVotes.map(vote => `
    <tr>
      <td>${new Date(vote.timestamp).toLocaleString()}</td>
      <td>${vote.username}</td>
      <td>${vote.question}</td>
      <td><strong>${vote.choice}</strong></td>
    </tr>
  `).join('');
}

function renderPagination(totalItems) {
  const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
  const paginationContainer = document.getElementById('pagination');
  
  let html = `<button onclick="renderVoteLogPage(1)" ${currentPage === 1 ? 'disabled' : ''}>First</button>
             <button onclick="renderVoteLogPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>Prev</button>`;
  
  for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
    html += `<button onclick="renderVoteLogPage(${i})" class="${i === currentPage ? 'active' : ''}">${i}</button>`;
  }
  
  html += `<button onclick="renderVoteLogPage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>Next</button>
          <button onclick="renderVoteLogPage(${totalPages})" ${currentPage === totalPages ? 'disabled' : ''}>Last</button>`;
  
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
    container.innerHTML = `
      <div class="card">
        <h3 class="card-title">Bot Status</h3>
        <div class="status-indicator">
          <div class="status-dot ${status.online ? 'online' : 'offline'}"></div>
          <span>${status.online ? 'Online' : 'Offline'}</span>
        </div>
        <div class="status-info">
          <div class="status-row">
            <span class="status-label">Uptime:</span>
            <span class="status-value">${status.uptime}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Last Command:</span>
            <span class="status-value">${status.last_command || 'N/A'}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Today's Votes:</span>
            <span class="status-value">${status.votes_today}</span>
          </div>
          <div class="status-row">
            <span class="status-label">Total Votes:</span>
            <span class="status-value">${status.votes_total}</span>
          </div>
        </div>
      </div>
    `;
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
    
    schedule.forEach(session => {
      const card = createSessionCard(session);
      container.appendChild(card);
    });
  } catch (error) {
    console.error('Error loading schedule:', error);
  }
}

function createSessionCard(session) {
  const card = document.createElement('div');
  card.className = `session-card ${session.pillar === 'Holistic STEMinist' ? 'holistic' : 'prodev'}`;
  
  card.innerHTML = `
    <div class="session-name">${session.name}</div>
    <div class="session-meta">${session.pillar}</div>
    <div class="session-time">${session.time}</div>
    <div class="session-detail" id="detail-${session.id}">
      <strong>Speaker:</strong> ${session.speaker}<br>
      <strong>Location:</strong> ${session.location}<br>
      <strong>Description:</strong> ${session.description || 'No description available'}
    </div>
  `;
  
  card.addEventListener('click', function() {
    const detail = document.getElementById(`detail-${session.id}`);
    detail.classList.toggle('show');
  });
  
  return card;
}

// Auto-refresh bot status
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
