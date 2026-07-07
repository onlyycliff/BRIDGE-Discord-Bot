function showToast(message, type, duration) {
  type = type || 'info';
  duration = duration || 3500;
  var container = document.getElementById('toast-container');
  if (!container) return;
  var icons = { success: '\u2705', error: '\u274C', info: '\u2139\uFE0F' };
  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.innerHTML = '<span class="toast-icon">' + (icons[type] || icons.info) + '</span><span class="toast-message">' + escapeHtml(message) + '</span><button class="toast-close" onclick="var t=this.parentElement;t.classList.add(\'removing\');setTimeout(function(){if(t.parentElement)t.remove()},250)">&times;</button>';
  container.appendChild(toast);
  setTimeout(function () {
    if (toast.parentElement) {
      toast.classList.add('removing');
      setTimeout(function () { if (toast.parentElement) toast.remove(); }, 250);
    }
  }, duration);
}

var REFRESH_INTERVAL = 5000;
var refreshIntervalId = null;
var githubProfileData = null;
var pollChartInstance = null;
var currentPage = 1;
var ITEMS_PER_PAGE = 25;
var allVotes = [];
var currentAbortController = null;

var apiCache = new Map();
var CACHE_DURATION = 30000;

async function cachedFetch(url, signal) {
  var now = Date.now();
  var cached = apiCache.get(url);
  if (cached && now - cached.timestamp < CACHE_DURATION) return cached.data;
  try {
    var resp = await fetch(url, { signal: signal || null });
    var data = await resp.json();
    apiCache.set(url, { data: data, timestamp: now });
    return data;
  } catch (e) {
    if (e.name === 'AbortError') return;
    throw e;
  }
}

function initTheme() {
  var isDark = localStorage.getItem('bridge-theme') === 'dark' ||
    (!localStorage.getItem('bridge-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  updateThemeIcon();
}

function toggleTheme() {
  var html = document.documentElement;
  var isDark = html.getAttribute('data-theme') === 'dark';
  html.setAttribute('data-theme', isDark ? 'light' : 'dark');
  localStorage.setItem('bridge-theme', isDark ? 'light' : 'dark');
  updateThemeIcon();
  var toggle = document.querySelector('.theme-toggle-corner');
  if (toggle) { toggle.style.transform = 'scale(0.95)'; setTimeout(function () { toggle.style.transform = ''; }, 150); }
  updateAllData();
}

function updateThemeIcon() {
  var icon = document.getElementById('theme-icon');
  if (!icon) return;
  var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  icon.textContent = isDark ? '\u2600\uFE0F' : '\uD83C\uDF19';
}

function showHub() {
  abortCurrentRequests();
  document.querySelectorAll('.page').forEach(function (p) { p.classList.remove('active'); });
  var hub = document.getElementById('hub');
  if (hub) hub.classList.add('active');
  loadGitHubProfile();
}

function showSection(sectionId) {
  abortCurrentRequests();
  document.querySelectorAll('.page').forEach(function (p) { p.classList.remove('active'); });
  var page = document.getElementById(sectionId);
  if (page) {
    page.classList.add('active');
    page.scrollTop = 0;
  }
  if (sectionId === 'polls') loadPollData();
  if (sectionId === 'interactive') { loadPollData(); loadActivePolls(); loadChannels(); loadRoles(); }
  if (sectionId === 'vote-log') loadVoteLogData();
  if (sectionId === 'bot-status') loadBotStatusSection();
  loadHealthData();
}

function abortCurrentRequests() {
  if (currentAbortController) currentAbortController.abort();
  currentAbortController = new AbortController();
}

async function loadGitHubProfile() {
  var section = document.getElementById('profile-section');
  if (!section) return;
  try {
    if (githubProfileData) { renderGitHubProfile(githubProfileData); return; }
    var resp = await fetch('/api/github/profile', { signal: currentAbortController ? currentAbortController.signal : null });
    if (!resp.ok) { section.innerHTML = '<div class="profile-loading">Could not load profile</div>'; return; }
    var data = await resp.json();
    if (data.error) { section.innerHTML = '<div class="profile-loading">Could not load profile</div>'; return; }
    githubProfileData = data;
    renderGitHubProfile(data);
  } catch (e) {
    if (e.name === 'AbortError') return;
    section.innerHTML = '<div class="profile-loading">Could not load profile</div>';
  }
}

function renderGitHubProfile(data) {
  var section = document.getElementById('profile-section');
  if (!section) return;
  var repoCards = (data.repos || []).map(function (r) {
    var desc = r.description || '';
    var lang = r.language ? '<span class="repo-lang"><span class="lang-dot"></span>' + escapeHtml(r.language) + '</span>' : '';
    return '<a href="' + escapeHtml(r.url) + '" target="_blank" class="repo-card">' +
      '<div class="repo-name">' + escapeHtml(r.name) + '</div>' +
      (desc ? '<div class="repo-desc">' + escapeHtml(desc) + '</div>' : '') +
      '<div class="repo-meta">' + lang + '<span>\u2B50 ' + r.stars + '</span></div></a>';
  }).join('');
  section.innerHTML =
    '<div class="profile-row">' +
    '<img class="profile-avatar" src="' + escapeHtml(data.avatar_url) + '" alt="avatar" />' +
    '<div class="profile-info">' +
    '<div class="profile-name">' + escapeHtml(data.name || data.login) + '</div>' +
    (data.bio ? '<div class="profile-bio">' + escapeHtml(data.bio) + '</div>' : '') +
    (data.location ? '<div class="profile-location">\uD83D\uDCCD ' + escapeHtml(data.location) + '</div>' : '') +
    '</div></div>' +
    '<div class="stats-row">' +
    '<div class="stats-item"><span class="stats-num">' + data.public_repos + '</span><span class="stats-label">Repos</span></div>' +
    '<div class="stats-item"><span class="stats-num">' + data.followers + '</span><span class="stats-label">Followers</span></div>' +
    '<div class="stats-item"><span class="stats-num">' + data.following + '</span><span class="stats-label">Following</span></div>' +
    '</div>' +
    '<div class="repo-grid">' + repoCards + '</div>';
}

async function loadHealthData() {
  try {
    var data = await cachedFetch('/api/data/status', currentAbortController ? currentAbortController.signal : null);
    if (!data) return;
    var recordsEl = document.getElementById('health-records');
    var lastEl = document.getElementById('health-last');
    var sizeEl = document.getElementById('health-size');
    var cacheEl = document.getElementById('health-cache');
    if (recordsEl) recordsEl.textContent = data.total_records + ' records';
    if (lastEl) lastEl.textContent = data.last_timestamp !== 'N/A' ? new Date(data.last_timestamp).toLocaleString() : 'N/A';
    if (sizeEl) sizeEl.textContent = data.file_size;
    if (cacheEl) cacheEl.textContent = data.cache_dirty ? '\uD83D\uDD35 Syncing...' : '\uD83D\uDFE2 Synced';
  } catch (e) { if (e.name === 'AbortError') return; }
}

function animateCounter(element, target, duration) {
  if (!element || target === undefined || target === null) return;
  if (duration === undefined) duration = 800;
  var start = 0;
  var startTime = performance.now();
  function easeOutExpo(t) { return t === 1 ? 1 : 1 - Math.pow(2, -10 * t); }
  function update(currentTime) {
    var elapsed = currentTime - startTime;
    var progress = Math.min(elapsed / duration, 1);
    var current = Math.floor(start + (target - start) * easeOutExpo(progress));
    element.textContent = current;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

async function loadPollData() {
  try {
    var response = await fetch('/api/polls', { signal: currentAbortController ? currentAbortController.signal : null });
    var polls = await response.json();
    if (!Array.isArray(polls)) return;
    var container = document.getElementById('polls-container');
    if (!container) return;
    var totalVotes = 0;
    polls.forEach(function (poll) { (poll.options || []).forEach(function (opt) { totalVotes += opt.votes || 0; }); });
    var activePollsEl = document.getElementById('active-polls-count');
    var totalVotesEl = document.getElementById('total-votes-count');
    var engagementEl = document.getElementById('engagement-rate');
    if (activePollsEl) animateCounter(activePollsEl, polls.length);
    if (totalVotesEl) animateCounter(totalVotesEl, totalVotes);
    if (engagementEl) {
      var rate = polls.length > 0 ? Math.min(Math.round((totalVotes / (polls.length * 100)) * 100), 100) : 0;
      engagementEl.textContent = rate + '%';
    }
    var fragment = document.createDocumentFragment();
    polls.forEach(function (poll, index) {
      var card = createPollCard(poll);
      card.style.animation = 'slideUp 0.4s ease forwards';
      card.style.opacity = '0';
      card.style.animationDelay = index * 60 + 'ms';
      fragment.appendChild(card);
    });
    container.innerHTML = '';
    container.appendChild(fragment);
  } catch (error) { if (error.name === 'AbortError') return; }
}

function createPollCard(poll) {
  var card = document.createElement('div');
  card.className = 'card';
  card.setAttribute('data-poll-id', poll.poll_id || '');
  var options = poll.options || [];
  var totalVotes = options.reduce(function (sum, o) { return sum + (o.votes || 0); }, 0);
  var maxVotes = Math.max.apply(null, options.map(function (o) { return o.votes || 0; }), 1);
  var leadingOption = options.reduce(function (max, o) { return (o.votes || 0) > (max.votes || 0) ? o : max; }, options[0] || {});
  var optionsHTML = options.map(function (option) {
    var pct = totalVotes > 0 ? ((option.votes / totalVotes) * 100).toFixed(1) : 0;
    var barWidth = maxVotes > 0 ? (option.votes / maxVotes) * 100 : 0;
    return '<div class="poll-option">' +
      '<div class="poll-option-label">' +
      '<span>' + escapeHtml(option.name || '') + '</span>' +
      '<span><span class="vote-percentage">' + pct + '</span>%</span></div>' +
      '<div class="poll-bar">' +
      '<div class="poll-bar-fill" style="width:0%;" data-width="' + barWidth + '">' +
      '<span class="vote-count">' + (option.votes || 0) + '</span>' +
      '</div></div></div>';
  }).join('');
  var ts = poll.timestamp ? new Date(poll.timestamp).toLocaleString() : 'N/A';
  var activeBadge = poll.active !== false ? '<span class="poll-badge poll-badge-active">Live</span>' : '<span class="poll-badge poll-badge-ended">Ended</span>';
  card.innerHTML = '<h3 class="card-title" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">' + activeBadge + escapeHtml(poll.question) + '</h3>' +
    optionsHTML +
    '<div class="poll-stats">' +
    '<span><strong class="total-votes">0</strong> total votes</span>' +
    '<span>Leading: <strong>' + escapeHtml(leadingOption.name || '') + '</strong></span></div>' +
    '<div class="card-meta">\uD83D\uDCC5 Last updated: ' + ts + '</div>';
  card.style.cursor = 'pointer';
  card.addEventListener('click', function () { openPollModal(poll.poll_id); });
  requestAnimationFrame(function () {
    card.querySelectorAll('.poll-bar-fill').forEach(function (bar) { bar.style.width = bar.getAttribute('data-width') + '%'; });
    var totalSpan = card.querySelector('.total-votes');
    animateCounter(totalSpan, totalVotes, 800);
  });
  return card;
}

async function loadVoteLogData() {
  try {
    var response = await fetch('/api/votes?page=' + currentPage + '&limit=' + ITEMS_PER_PAGE, { signal: currentAbortController ? currentAbortController.signal : null });
    var data = await response.json();
    if (!data || !data.votes) return;
    allVotes = data.votes || [];
    renderVoteTable(allVotes);
    renderPagination(data.total || 0);
    updateSyncTime();
  } catch (error) { if (error.name === 'AbortError') return; }
}

function updateSyncTime() {
  var el = document.getElementById('sync-time');
  if (el) el.textContent = '\uD83D\uDD04 Last synced: ' + new Date().toLocaleTimeString();
}

var searchTimeout;
function filterVotesOptimized() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(function () {
    var term = (document.getElementById('search-input') ? document.getElementById('search-input').value : '').toLowerCase();
    if (!term) { loadVoteLogData(); return; }
    var filtered = allVotes.filter(function (v) { return (v.username || '').toLowerCase().includes(term) || (v.question || '').toLowerCase().includes(term); });
    renderVoteTable(filtered);
    renderPagination(filtered.length);
  }, 300);
}

function renderVoteTable(votes) {
  var tbody = document.querySelector('#vote-log-table tbody');
  if (!tbody) return;
  if (!votes || votes.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--color-text-muted)">No votes yet</td></tr>';
    return;
  }
  var fragment = document.createDocumentFragment();
  votes.forEach(function (vote, index) {
    var tr = document.createElement('tr');
    tr.style.animation = 'slideUp 0.3s ease forwards';
    tr.style.opacity = '0';
    tr.style.animationDelay = index * 25 + 'ms';
    var ts = vote.timestamp ? new Date(vote.timestamp).toLocaleString() : '-';
    tr.innerHTML = '<td>\u23F0 ' + ts + '</td><td>\uD83D\uDC64 ' + escapeHtml(vote.username || '') + '</td><td>\u2753 ' + escapeHtml(vote.question || '') + '</td><td><strong>\u2713 ' + escapeHtml(vote.choice || '') + '</strong></td>';
    fragment.appendChild(tr);
  });
  tbody.innerHTML = '';
  tbody.appendChild(fragment);
}

function renderPagination(total) {
  var totalPages = Math.ceil(total / ITEMS_PER_PAGE);
  var container = document.getElementById('pagination');
  if (!container) return;
  if (totalPages <= 1) { container.innerHTML = '<span id="page-info">Page 1 of 1</span>'; return; }
  var html = '<button onclick="goToPage(1)" ' + (currentPage === 1 ? 'disabled' : '') + '>\u00AB First</button>';
  html += '<button onclick="goToPage(' + (currentPage - 1) + ')" ' + (currentPage === 1 ? 'disabled' : '') + '>\u2039 Prev</button>';
  for (var i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
    html += '<button onclick="goToPage(' + i + ')" class="' + (i === currentPage ? 'active' : '') + '">' + i + '</button>';
  }
  html += '<button onclick="goToPage(' + (currentPage + 1) + ')" ' + (currentPage === totalPages ? 'disabled' : '') + '>Next \u203A</button>';
  html += '<button onclick="goToPage(' + totalPages + ')" ' + (currentPage === totalPages ? 'disabled' : '') + '>Last \u00BB</button>';
  container.innerHTML = html;
  var pageInfo = document.getElementById('page-info');
  if (pageInfo) pageInfo.textContent = 'Page ' + currentPage + ' of ' + totalPages;
}

function goToPage(page) { currentPage = page; loadVoteLogData(); }

async function loadBotStatus() {
  try {
    var status = await cachedFetch('/api/bot-status', currentAbortController ? currentAbortController.signal : null);
    if (!status) return;
    var indicator = document.getElementById('bot-status-indicator');
    if (indicator) {
      var dot = indicator.querySelector('.status-dot');
      if (dot) { dot.classList.remove('online', 'offline'); dot.classList.add(status.online ? 'online' : 'offline'); }
      var label = indicator.querySelector('.status-text');
      if (label) label.textContent = status.online ? 'Online' : 'Offline';
    }
  } catch (e) { if (e.name === 'AbortError') return; }
}

async function loadBotStatusSection() {
  try {
    var status = await cachedFetch('/api/bot-status', currentAbortController ? currentAbortController.signal : null);
    if (!status) return;
    var container = document.getElementById('bot-status-container');
    if (!container) return;
    container.innerHTML = '<div class="card">' +
      '<h3 class="card-title">\uD83E\uDD16 Discord Bot</h3>' +
      '<div class="status-indicator"><div class="status-dot ' + (status.online ? 'online' : 'offline') + '"></div><span style="font-weight:600;">' + (status.online ? '\uD83D\uDFE2 Online' : '\uD83D\uDD34 Offline') + '</span></div>' +
      '<div class="status-info">' +
      '<div class="status-row"><span class="status-label">\u23F1\uFE0F Uptime:</span><span class="status-value">' + (status.uptime || 'N/A') + '</span></div>' +
      '<div class="status-row"><span class="status-label">\uD83C\uDFAF Total Votes:</span><span class="status-value"><span class="votes-total">0</span></span></div>' +
      '<div class="status-row"><span class="status-label">\uD83D\uDCCA Today\'s Votes:</span><span class="status-value"><span class="votes-today">0</span></span></div>' +
      '<div class="status-row"><span class="status-label">\uD83D\uDDA5\uFE0F Latency:</span><span class="status-value">' + (status.latency_ms || 0) + 'ms</span></div></div></div>';
    requestAnimationFrame(function () {
      animateCounter(container.querySelector('.votes-today'), status.votes_today || 0);
      animateCounter(container.querySelector('.votes-total'), status.votes_total || 0);
    });
  } catch (error) { if (error.name === 'AbortError') return; }
}

async function loadChannels() {
  var select = document.getElementById('poll-channel');
  if (!select) return;
  try {
    var channels = await cachedFetch('/api/discord/channels', currentAbortController ? currentAbortController.signal : null);
    if (!Array.isArray(channels)) return;
    var currentValue = select.value;
    select.innerHTML = '<option value="">Default Channel</option>';
    channels.forEach(function (ch) { var opt = document.createElement('option'); opt.value = ch.id; opt.textContent = '#' + ch.name; select.appendChild(opt); });
    if (currentValue) select.value = currentValue;
  } catch (e) { if (e.name === 'AbortError') return; }
}

async function loadRoles() {
  var container = document.getElementById('role-picker');
  if (!container) return;
  try {
    var roles = await cachedFetch('/api/discord/roles', currentAbortController ? currentAbortController.signal : null);
    if (!Array.isArray(roles)) return;
    container.innerHTML = '';
    roles.forEach(function (r) {
      var label = document.createElement('label');
      label.className = 'role-checkbox-label';
      var cb = document.createElement('input');
      cb.type = 'checkbox'; cb.className = 'role-checkbox'; cb.value = r.id;
      label.appendChild(cb);
      label.appendChild(document.createTextNode('@' + r.name));
      container.appendChild(label);
    });
  } catch (e) { if (e.name === 'AbortError') return; }
}

async function loadActivePolls() {
  var container = document.getElementById('active-polls-list');
  if (!container) return;
  try {
    var response = await fetch('/api/polls', { signal: currentAbortController ? currentAbortController.signal : null });
    var polls = await response.json();
    if (!Array.isArray(polls)) return;
    var active = polls.filter(function (p) { return p.active !== false; });
    if (active.length === 0) { container.innerHTML = '<p style="color:var(--color-text-muted);">No active polls.</p>'; return; }
    var fragment = document.createDocumentFragment();
    active.forEach(function (poll) {
      var row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid var(--color-border);border-radius:8px;margin-bottom:8px;background:var(--color-surface);';
      var totalVotes = (poll.options || []).reduce(function (s, o) { return s + (o.votes || 0); }, 0);
      var leading = (poll.options || []).reduce(function (best, o) { return (o.votes || 0) > (best.votes || 0) ? o : best; }, (poll.options || [])[0] || {});
      row.innerHTML = '<div style="flex:1;min-width:0;"><div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(poll.question) + '</div><div style="font-size:0.75rem;color:var(--color-text-muted);margin-top:2px;">' + totalVotes + ' vote' + (totalVotes !== 1 ? 's' : '') + ' &middot; Leading: ' + escapeHtml(leading.name || 'N/A') + '</div></div>' +
        '<label style="display:flex;align-items:center;gap:4px;font-size:0.75rem;white-space:nowrap;cursor:pointer;color:var(--color-text-muted);"><input type="checkbox" class="active-poll-send-results" checked /> Breakdown</label>' +
        '<button class="btn btn-danger active-poll-end-btn" style="padding:6px 14px;font-size:0.75rem;white-space:nowrap;" data-poll-id="' + poll.poll_id + '">End</button>';
      fragment.appendChild(row);
    });
    container.innerHTML = '';
    container.appendChild(fragment);
    container.querySelectorAll('.active-poll-end-btn').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        var pollId = btn.getAttribute('data-poll-id');
        var sendResults = btn.parentElement.querySelector('.active-poll-send-results') ? btn.parentElement.querySelector('.active-poll-send-results').checked : false;
        if (!confirm('End poll #' + pollId + '? Votes will be frozen.')) return;
        try {
          var r = await fetch('/api/polls/' + pollId + '/end', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ send_results: sendResults }) });
          var j = await r.json();
          if (r.ok) { showToast('Poll ended successfully', 'success'); loadActivePolls(); loadPollData(); }
          else { showToast('Error: ' + (j.error || 'Unknown'), 'error'); }
        } catch (e) { showToast('Network error ending poll', 'error'); }
      });
    });
  } catch (e) {
    if (e.name === 'AbortError') return;
    container.innerHTML = '<p style="color:var(--color-text-muted);">Error loading polls.</p>';
  }
}

async function openPollModal(pollId) {
  var modal = document.getElementById('poll-modal');
  var title = document.getElementById('modal-title');
  if (!modal || !title) return;
  try {
    var resp = await fetch('/api/polls/' + pollId, { signal: currentAbortController ? currentAbortController.signal : null });
    var data = await resp.json();
    if (!data || data.error) { title.textContent = 'Error loading poll'; return; }
    title.textContent = data.question || 'Poll';
    modal.setAttribute('aria-hidden', 'false');
    modal.classList.add('open');
    var endBtn = document.getElementById('end-poll-btn');
    var sendResultsLabel = document.getElementById('send-results-label');
    var sendResultsCheckbox = document.getElementById('send-results-checkbox');
    if (endBtn) {
      var isActive = data.active !== false;
      endBtn.style.display = isActive ? 'block' : 'none';
      if (sendResultsLabel) sendResultsLabel.style.display = isActive ? 'flex' : 'none';
      endBtn.onclick = async function () {
        if (!confirm('End this poll? Votes will be frozen and buttons disabled on Discord.')) return;
        var sendResults = sendResultsCheckbox ? sendResultsCheckbox.checked : false;
        try {
          var r = await fetch('/api/polls/' + pollId + '/end', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ send_results: sendResults }) });
          var j = await r.json();
          if (r.ok) { showToast('Poll ended successfully', 'success'); endBtn.style.display = 'none'; if (sendResultsLabel) sendResultsLabel.style.display = 'none'; closePollModal(); loadPollData(); }
          else { showToast('Error: ' + (j.error || 'Unknown'), 'error'); }
        } catch (e) { showToast('Network error ending poll', 'error'); }
      };
    }
    var ctx = document.getElementById('poll-chart-canvas');
    if (!ctx) return;
    var canvas = ctx.getContext('2d');
    if (typeof Chart === 'undefined') return;
    var labels = (data.options || []).map(function (o) { return o.name || ''; });
    var chartData = (data.options || []).map(function (o) { return o.votes || 0; });
    var colors = ['#6366F1', '#8B5CF6', '#EC4899', '#F59E0B', '#22C55E'];
    if (pollChartInstance) pollChartInstance.destroy();
    pollChartInstance = new Chart(canvas, {
      type: 'bar',
      data: { labels: labels, datasets: [{ label: 'Votes', data: chartData, backgroundColor: labels.map(function (_, i) { return colors[i % colors.length]; }), borderRadius: 6, borderSkipped: false }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: true, animation: { duration: 500, easing: 'easeOutQuart' }, scales: { x: { beginAtZero: true, ticks: { stepSize: 1, color: '#94A3B8' }, grid: { color: 'rgba(148,163,184,0.15)' } }, y: { ticks: { color: '#94A3B8' }, grid: { display: false } } }, plugins: { legend: { display: false } } }
    });
    renderVoterMatrix(data.voters_by_choice || {});
    var refreshBtn = document.getElementById('refresh-poll-data');
    if (refreshBtn) refreshBtn.onclick = function () { openPollModal(pollId); };
  } catch (error) { if (error.name === 'AbortError') return; }
}

function renderVoterMatrix(votersByChoice) {
  var container = document.getElementById('voter-matrix-table');
  if (!container) return;
  var entries = Object.keys(votersByChoice);
  if (entries.length === 0) { container.innerHTML = '<p style="color:var(--color-text-muted);font-size:0.8125rem;">No voter data available.</p>'; return; }
  var rows = '<table class="matrix-table"><thead><tr><th>Option</th><th>Voters</th></tr></thead><tbody>';
  entries.forEach(function (choice) {
    var voters = votersByChoice[choice] || [];
    var voterList = voters.length > 0 ? voters.map(function (v) { return '<span class="matrix-voter">' + escapeHtml(v) + '</span>'; }).join(' ') : '<span style="color:var(--color-text-muted)">No voters yet</span>';
    rows += '<tr><td><strong>' + escapeHtml(choice) + '</strong></td><td>' + voterList + '</td></tr>';
  });
  rows += '</tbody></table>';
  container.innerHTML = rows;
}

function closePollModal() {
  var modal = document.getElementById('poll-modal');
  if (!modal) return;
  modal.setAttribute('aria-hidden', 'true');
  modal.classList.remove('open');
}

async function submitPollForm(e) {
  e.preventDefault();
  var q = document.getElementById('poll-question');
  var descEl = document.getElementById('poll-description');
  var resp = document.getElementById('create-response');
  if (!q || !resp) return;
  var question = q.value.trim();
  var description = descEl ? descEl.value.trim() : '';
  var optionInputs = document.querySelectorAll('.poll-option-input');
  var options = Array.from(optionInputs).map(function (i) { return i.value.trim(); }).filter(Boolean);
  if (!question) { resp.textContent = 'Please enter a question.'; return; }
  if (options.length < 2) { resp.textContent = 'Please provide at least 2 options.'; return; }
  var channelSelect = document.getElementById('poll-channel');
  var channelId = channelSelect ? channelSelect.value || null : null;
  var roleCheckboxes = document.querySelectorAll('.role-checkbox:checked');
  var roleIds = roleCheckboxes.length > 0 ? Array.from(roleCheckboxes).map(function (cb) { return cb.value; }) : null;
  var maxVotesInput = document.getElementById('poll-max-votes');
  var maxVotes = maxVotesInput ? parseInt(maxVotesInput.value) || null : null;
  try {
    var r = await fetch('/api/polls/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: question, description: description, options: options, channel_id: channelId, role_ids: roleIds, max_votes_per_option: maxVotes }) });
    var json = await r.json();
    if (r.ok) {
      showToast('Poll created successfully!', 'success');
      q.value = '';
      if (descEl) descEl.value = '';
      document.getElementById('poll-options-list').innerHTML = '';
      addPollOption(''); addPollOption('');
      document.querySelectorAll('.role-checkbox:checked').forEach(function (cb) { cb.checked = false; });
      if (maxVotesInput) maxVotesInput.value = '';
      loadPollData();
      resp.textContent = '';
    } else { showToast('Error: ' + (json.error || 'Unknown error'), 'error'); }
  } catch (err) { showToast('Network error creating poll', 'error'); }
}

function addPollOption(value) {
  if (value === undefined) value = '';
  var MAX = 5;
  var container = document.getElementById('poll-options-list');
  if (!container) return;
  var idx = container.children.length;
  if (idx >= MAX) return;
  var div = document.createElement('div');
  div.style.cssText = 'display:flex;gap:8px;align-items:center;';
  div.innerHTML = '<input type="text" class="poll-option-input search-input" placeholder="Option ' + (idx + 1) + '" value="' + value + '" required style="flex:1;">' +
    '<button type="button" class="btn btn-secondary" style="padding:6px 10px;font-size:0.8rem;" onclick="this.parentElement.remove();updatePollOptionCount()">\u2715</button>';
  container.appendChild(div);
  updatePollOptionCount();
}

function updatePollOptionCount() {
  var count = document.querySelectorAll('.poll-option-input').length;
  var el = document.getElementById('poll-option-count');
  if (el) el.textContent = count;
  var btn = document.getElementById('add-poll-option-btn');
  if (btn) btn.disabled = count >= 5;
}

async function exportCSV() {
  try {
    var resp = await fetch('/api/export/csv', { signal: currentAbortController ? currentAbortController.signal : null });
    if (!resp.ok) {
      var err = await resp.json().catch(function () { return {}; });
      showToast('Export failed: ' + (err.error || 'Unknown error'), 'error');
      return;
    }
    var blob = await resp.blob();
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'poll_feedback.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
    showToast('CSV exported successfully', 'success');
  } catch (err) {
    if (err.name === 'AbortError') return;
    showToast('Export failed: Network error', 'error');
  }
}

function startAutoRefresh() {
  if (refreshIntervalId) clearInterval(refreshIntervalId);
  refreshIntervalId = setInterval(function () {
    var active = document.querySelector('.page.active');
    if (!active) return;
    var id = active.id;
    if (id === 'polls' || id === 'interactive') { loadPollData(); loadActivePolls(); }
    if (id === 'vote-log') loadVoteLogData();
    if (id === 'bot-status') loadBotStatusSection();
    loadHealthData();
    loadBotStatus();
  }, REFRESH_INTERVAL);
}

function stopAutoRefresh() {
  if (refreshIntervalId) { clearInterval(refreshIntervalId); refreshIntervalId = null; }
}

function updateAllData() {
  loadBotStatus();
  loadHealthData();
  var active = document.querySelector('.page.active');
  if (!active) return;
  if (active.id === 'polls' || active.id === 'interactive') { loadPollData(); loadActivePolls(); }
  if (active.id === 'vote-log') loadVoteLogData();
  if (active.id === 'bot-status') loadBotStatusSection();
}

function escapeHtml(text) {
  if (!text) return '';
  var d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

var BOT_AVATAR_FALLBACK = 'https://cdn.discordapp.com/avatars/1514286119892684881/2725db1fcb71ea2eeb98854b06fca50c.png?size=512';

function setAvatarUrl(url) {
  var src = url || BOT_AVATAR_FALLBACK;
  var introImg = document.getElementById('intro-avatar');
  var loaderImg = document.getElementById('loader-avatar');
  if (introImg) introImg.src = src;
  if (loaderImg) loaderImg.src = src;
}

function dismissIntro() {
  var overlay = document.getElementById('intro-overlay');
  if (!overlay) return;
  overlay.classList.add('hidden');
  var loader = document.getElementById('loading-screen');
  if (loader) loader.classList.add('active');
  Promise.all([
    fetch('/api/bot-status').then(function (r) { return r.json(); }).then(function (s) { if (s.avatar_url) setAvatarUrl(s.avatar_url); }).catch(function () {}),
    loadBotStatus().catch(function () {}),
    loadHealthData().catch(function () {}),
    loadGitHubProfile().catch(function () {})
  ]).then(function () {
    if (loader) loader.classList.remove('active');
    var app = document.querySelector('.app');
    if (app) app.classList.add('visible');
    startAutoRefresh();
  });
}

function handleKeydown(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
  var key = e.key.toLowerCase();
  if (key === 'escape') closePollModal();
  if (key === 'h' && !e.ctrlKey && !e.metaKey) showHub();
}

document.addEventListener('DOMContentLoaded', function () {
  initTheme();
  var form = document.getElementById('create-poll-form');
  if (form) form.addEventListener('submit', submitPollForm);
  var addBtn = document.getElementById('add-poll-option-btn');
  if (addBtn) addBtn.addEventListener('click', function (e) { e.preventDefault(); addPollOption(); });
  var refreshBtn = document.getElementById('refresh-polls');
  if (refreshBtn) refreshBtn.addEventListener('click', function () { loadPollData(); });
  if (!document.querySelector('.poll-option-input')) { addPollOption(''); addPollOption(''); }
  document.addEventListener('click', function (e) { if (e.target && (e.target.id === 'modal-backdrop' || e.target.id === 'modal-close')) closePollModal(); });
  document.addEventListener('visibilitychange', function () { if (document.hidden) stopAutoRefresh(); else { updateAllData(); startAutoRefresh(); } });
  document.addEventListener('keydown', handleKeydown);
});
