const REFRESH_INTERVAL = 5000;
let refreshIntervalId = null;

const apiCache = new Map();
const CACHE_DURATION = 30000;
async function cachedFetch(url) {
  const now = Date.now();
  const cached = apiCache.get(url);
  if (cached && now - cached.timestamp < CACHE_DURATION) return cached.data;
  const resp = await fetch(url);
  const data = await resp.json();
  apiCache.set(url, { data, timestamp: now });
  return data;
}

function initTheme() {
  const isDark = localStorage.getItem("bridge-theme") === "dark" ||
    (!localStorage.getItem("bridge-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
  updateThemeIcon();
}

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute("data-theme") === "dark";
  html.setAttribute("data-theme", isDark ? "light" : "dark");
  localStorage.setItem("bridge-theme", isDark ? "light" : "dark");
  updateThemeIcon();
  updateAllData();
}

function updateThemeIcon() {
  const icon = document.getElementById("theme-icon");
  if (!icon) return;
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  icon.textContent = isDark ? "\u2600" : "\uD83C\uDF19";
}

function showHub() {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  const hub = document.getElementById("hub");
  if (hub) hub.classList.add("active");
  loadGitHubProfile();
}

function showSection(sectionId) {
  document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
  const page = document.getElementById(sectionId);
  if (page) page.classList.add("active");
  if (sectionId === "polls") loadPollData();
  if (sectionId === "interactive") { loadPollData(); loadChannels(); loadRoles(); }
  if (sectionId === "vote-log") loadVoteLogData();
  if (sectionId === "bot-status") loadBotStatusSection();
  loadHealthData();
}

async function loadGitHubProfile() {
  const section = document.getElementById("profile-section");
  if (!section) return;
  try {
    if (githubProfileData) {
      renderGitHubProfile(githubProfileData);
      return;
    }
    const resp = await fetch("/api/github/profile");
    if (!resp.ok) {
      section.innerHTML = '<div class="profile-loading">Could not load profile</div>';
      return;
    }
    const data = await resp.json();
    if (data.error) {
      section.innerHTML = '<div class="profile-loading">Could not load profile</div>';
      return;
    }
    githubProfileData = data;
    const repoCards = (data.repos || []).map(r => {
      const desc = r.description || "";
      const lang = r.language ? '<span class="repo-lang"><span class="lang-dot"></span>' + escapeHtml(r.language) + "</span>" : "";
      return '<a href="' + escapeHtml(r.url) + '" target="_blank" class="repo-card">' +
        '<div class="repo-name">' + escapeHtml(r.name) + "</div>" +
        (desc ? '<div class="repo-desc">' + escapeHtml(desc) + "</div>" : "") +
        '<div class="repo-meta">' + lang +
        '<span>\u2B50 ' + r.stars + "</span>" +
        "</div></a>";
    }).join("");

    renderGitHubProfile(data);
  } catch (e) {
    section.innerHTML = '<div class="profile-loading">Could not load profile</div>';
  }
}

function renderGitHubProfile(data) {
  const section = document.getElementById("profile-section");
  if (!section) return;
  const repoCards = (data.repos || []).map(r => {
    const desc = r.description || "";
    const lang = r.language ? '<span class="repo-lang"><span class="lang-dot"></span>' + escapeHtml(r.language) + "</span>" : "";
    return '<a href="' + escapeHtml(r.url) + '" target="_blank" class="repo-card">' +
      '<div class="repo-name">' + escapeHtml(r.name) + "</div>" +
      (desc ? '<div class="repo-desc">' + escapeHtml(desc) + "</div>" : "") +
      '<div class="repo-meta">' + lang +
      '<span>\u2B50 ' + r.stars + "</span>" +
      "</div></a>";
  }).join("");
  section.innerHTML =
    '<div class="profile-row">' +
    '<img class="profile-avatar" src="' + escapeHtml(data.avatar_url) + '" alt="avatar" />' +
    '<div class="profile-info">' +
    '<div class="profile-name">' + escapeHtml(data.name || data.login) + "</div>" +
    (data.bio ? '<div class="profile-bio">' + escapeHtml(data.bio) + "</div>" : "") +
    (data.location ? '<div class="profile-location">\uD83D\uDCCD ' + escapeHtml(data.location) + "</div>" : "") +
    "</div>" +
    "</div>" +
    '<div class="stats-row">' +
    '<div class="stats-item"><span class="stats-num">' + data.public_repos + '</span><span class="stats-label">Repos</span></div>' +
    '<div class="stats-item"><span class="stats-num">' + data.followers + '</span><span class="stats-label">Followers</span></div>' +
    '<div class="stats-item"><span class="stats-num">' + data.following + '</span><span class="stats-label">Following</span></div>' +
    "</div>" +
    '<div class="repo-grid">' + repoCards + "</div>";
}

async function loadHealthData() {
  try {
    const data = await cachedFetch("/api/data/status");
    const recordsEl = document.getElementById("health-records");
    const lastEl = document.getElementById("health-last");
    const sizeEl = document.getElementById("health-size");
    const cacheEl = document.getElementById("health-cache");
    if (recordsEl) recordsEl.textContent = data.total_records + " records";
    if (lastEl) lastEl.textContent = data.last_timestamp !== "N/A" ? new Date(data.last_timestamp).toLocaleString() : "N/A";
    if (sizeEl) sizeEl.textContent = data.file_size;
    if (cacheEl) cacheEl.textContent = data.cache_dirty ? "\uD83D\uDD35 Syncing..." : "\uD83D\uDFE2 Synced";
  } catch (e) {
    console.error("Error loading health data:", e);
  }
}

function animateCounter(element, target, duration) {
  if (!element) return;
  if (duration === undefined) duration = 800;
  const start = 0;
  const startTime = performance.now();
  function easeOutQuad(t) { return t * (2 - t); }
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const current = Math.floor(start + (target - start) * easeOutQuad(progress));
    element.textContent = current;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}



async function loadPollData() {
  try {
    const response = await fetch("/api/polls");
    const polls = await response.json();
    if (!Array.isArray(polls)) return;
    const container = document.getElementById("polls-container");
    if (!container) return;
    let totalVotes = 0;
    polls.forEach(poll => {
      (poll.options || []).forEach(opt => { totalVotes += opt.votes || 0; });
    });
    const activePollsEl = document.getElementById("active-polls-count");
    const totalVotesEl = document.getElementById("total-votes-count");
    const engagementEl = document.getElementById("engagement-rate");
    if (activePollsEl) animateCounter(activePollsEl, polls.length);
    if (totalVotesEl) animateCounter(totalVotesEl, totalVotes);
    if (engagementEl) {
      const rate = polls.length > 0 ? Math.min(Math.round((totalVotes / (polls.length * 100)) * 100), 100) : 0;
      engagementEl.textContent = rate + "%";
    }
    const fragment = document.createDocumentFragment();
    polls.forEach((poll, index) => {
      const card = createPollCard(poll);
      card.style.animationDelay = index * 50 + "ms";
      fragment.appendChild(card);
    });
    container.innerHTML = "";
    container.appendChild(fragment);
  } catch (error) {
    console.error("Error loading polls:", error);
  }
}

function createPollCard(poll) {
  const card = document.createElement("div");
  card.className = "card";
  card.setAttribute("data-poll-id", poll.poll_id || "");
  const options = poll.options || [];
  const totalVotes = options.reduce((sum, o) => sum + (o.votes || 0), 0);
  const maxVotes = Math.max(...options.map(o => o.votes || 0), 1);
  const leadingOption = options.reduce((max, o) => (o.votes || 0) > (max.votes || 0) ? o : max, options[0] || {});
  const optionsHTML = options.map(option => {
    const pct = totalVotes > 0 ? ((option.votes / totalVotes) * 100).toFixed(1) : 0;
    const barWidth = maxVotes > 0 ? (option.votes / maxVotes) * 100 : 0;
    return '<div class="poll-option">' +
      '<div class="poll-option-label">' +
      '<span>' + escapeHtml(option.name || "") + "</span>" +
      '<span><span class="vote-percentage">' + pct + "</span>%</span>" +
      "</div>" +
      '<div class="poll-bar">' +
      '<div class="poll-bar-fill" style="width:0%;" data-width="' + barWidth + '">' +
      '<span class="vote-count">' + (option.votes || 0) + "</span>" +
      "</div></div></div>";
  }).join("");
  const ts = poll.timestamp ? new Date(poll.timestamp).toLocaleString() : "N/A";
  const activeBadge = poll.active !== false ? '<span class="poll-badge poll-badge-active">Live</span>' : '<span class="poll-badge poll-badge-ended">Ended</span>';
  card.innerHTML = '<h3 class="card-title" style="display:flex;align-items:center;gap:8px;">' + activeBadge + escapeHtml(poll.question) + "</h3>" +
    optionsHTML +
    '<div class="poll-stats">' +
    '<span><strong class="total-votes">0</strong> total votes</span>' +
    '<span>Leading: <strong>' + escapeHtml(leadingOption.name || "") + "</strong></span>" +
    "</div>" +
    '<div class="card-meta">\uD83D\uDCC5 Last updated: ' + ts + "</div>";
  card.style.cursor = "pointer";
  card.addEventListener("click", () => openPollModal(poll.poll_id));
  requestAnimationFrame(() => {
    card.querySelectorAll(".poll-bar-fill").forEach(bar => {
      bar.style.width = bar.getAttribute("data-width") + "%";
    });
    const totalSpan = card.querySelector(".total-votes");
    animateCounter(totalSpan, totalVotes);
  });
  return card;
}

let currentPage = 1;
const ITEMS_PER_PAGE = 25;
let allVotes = [];

async function loadVoteLogData() {
  try {
    const response = await fetch("/api/votes?page=" + currentPage + "&limit=" + ITEMS_PER_PAGE);
    const data = await response.json();
    if (!data || !data.votes) return;
    allVotes = data.votes || [];
    renderVoteTable(allVotes);
    renderPagination(data.total || 0);
    updateSyncTime();
  } catch (error) {
    console.error("Error loading vote log:", error);
  }
}

function updateSyncTime() {
  const el = document.getElementById("sync-time");
  if (el) el.textContent = "\uD83D\uDD04 Last synced: " + new Date().toLocaleTimeString();
}

let searchTimeout;
function filterVotesOptimized() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    const term = (document.getElementById("search-input")?.value || "").toLowerCase();
    if (!term) { loadVoteLogData(); return; }
    const filtered = allVotes.filter(v =>
      (v.username || "").toLowerCase().includes(term) ||
      (v.question || "").toLowerCase().includes(term)
    );
    renderVoteTable(filtered);
    renderPagination(filtered.length);
  }, 300);
}

function renderVoteTable(votes) {
  const tbody = document.querySelector("#vote-log-table tbody");
  if (!tbody) return;
  if (!votes || votes.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px;color:var(--color-text-muted)">No votes yet</td></tr>';
    return;
  }
  const fragment = document.createDocumentFragment();
  votes.forEach((vote, index) => {
    const tr = document.createElement("tr");
    tr.style.animationDelay = index * 30 + "ms";
    const ts = vote.timestamp ? new Date(vote.timestamp).toLocaleString() : "-";
    tr.innerHTML = "<td>\u23F0 " + ts + "</td>" +
      "<td>\uD83D\uDC64 " + escapeHtml(vote.username || "") + "</td>" +
      "<td>\u2753 " + escapeHtml(vote.question || "") + "</td>" +
      "<td><strong>\u2713 " + escapeHtml(vote.choice || "") + "</strong></td>";
    fragment.appendChild(tr);
  });
  tbody.innerHTML = "";
  tbody.appendChild(fragment);
}

function renderPagination(total) {
  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);
  const container = document.getElementById("pagination");
  if (!container) return;
  if (totalPages <= 1) {
    container.innerHTML = '<span id="page-info">Page 1 of 1</span>';
    return;
  }
  let html = '<button onclick="goToPage(1)" ' + (currentPage === 1 ? "disabled" : "") + ">\u00AB First</button>";
  html += '<button onclick="goToPage(' + (currentPage - 1) + ')" ' + (currentPage === 1 ? "disabled" : "") + ">\u2039 Prev</button>";
  for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
    html += '<button onclick="goToPage(' + i + ')" class="' + (i === currentPage ? "active" : "") + '">' + i + "</button>";
  }
  html += '<button onclick="goToPage(' + (currentPage + 1) + ')" ' + (currentPage === totalPages ? "disabled" : "") + ">Next \u203A</button>";
  html += '<button onclick="goToPage(' + totalPages + ')" ' + (currentPage === totalPages ? "disabled" : "") + ">Last \u00BB</button>";
  container.innerHTML = html;
  const pageInfo = document.getElementById("page-info");
  if (pageInfo) pageInfo.textContent = "Page " + currentPage + " of " + totalPages;
}

function goToPage(page) {
  currentPage = page;
  loadVoteLogData();
}

async function loadBotStatus() {
  try {
    const status = await cachedFetch("/api/bot-status");
    const indicator = document.getElementById("bot-status-indicator");
    if (indicator) {
      const dot = indicator.querySelector(".status-dot");
      if (dot) {
        dot.classList.remove("online", "offline");
        dot.classList.add(status.online ? "online" : "offline");
      }
      const label = indicator.querySelector(".status-text");
      if (label) label.textContent = status.online ? "Online" : "Offline";
    }
  } catch (error) {
    console.error("Error loading bot status:", error);
  }
}

async function loadBotStatusSection() {
  try {
    const status = await cachedFetch("/api/bot-status");
    const container = document.getElementById("bot-status-container");
    if (!container) return;
    container.innerHTML = '<div class="card" style="max-width:600px;">' +
      '<h3 class="card-title">\uD83E\uDD16 Discord Bot</h3>' +
      '<div class="status-indicator">' +
      '<div class="status-dot ' + (status.online ? "online" : "offline") + '"></div>' +
      '<span style="font-weight:600;">' + (status.online ? "\uD83D\uDFE2 Online" : "\uD83D\uDD34 Offline") + "</span>" +
      "</div>" +
      '<div class="status-info">' +
      '<div class="status-row"><span class="status-label">\u23F1\uFE0F Uptime:</span><span class="status-value">' + (status.uptime || "N/A") + "</span></div>" +
      '<div class="status-row"><span class="status-label">\uD83C\uDFAF Total Votes:</span><span class="status-value"><span class="votes-total">0</span></span></div>' +
      '<div class="status-row"><span class="status-label">\uD83D\uDCCA Today\'s Votes:</span><span class="status-value"><span class="votes-today">0</span></span></div>' +
      '<div class="status-row"><span class="status-label">\uD83D\uDDA5\uFE0F Latency:</span><span class="status-value">' + (status.latency_ms || 0) + "ms</span></div>" +
      "</div></div>";
    requestAnimationFrame(() => {
      const todaySpan = container.querySelector(".votes-today");
      const totalSpan = container.querySelector(".votes-total");
      animateCounter(todaySpan, status.votes_today || 0);
      animateCounter(totalSpan, status.votes_total || 0);
    });
  } catch (error) {
    console.error("Error loading bot status section:", error);
  }
}

async function loadChannels() {
  const select = document.getElementById("poll-channel");
  if (!select) return;
  try {
    const channels = await cachedFetch("/api/discord/channels");
    if (!Array.isArray(channels)) return;
    const currentValue = select.value;
    select.innerHTML = '<option value="">Default Channel</option>';
    channels.forEach(ch => {
      const opt = document.createElement("option");
      opt.value = ch.id;
      opt.textContent = "#" + ch.name;
      select.appendChild(opt);
    });
    if (currentValue) select.value = currentValue;
  } catch (e) {
    console.error("Error loading channels:", e);
  }
}

async function loadRoles() {
  const container = document.getElementById("role-picker");
  if (!container) return;
  try {
    const roles = await cachedFetch("/api/discord/roles");
    if (!Array.isArray(roles)) return;
    container.innerHTML = "";
    roles.forEach(r => {
      const label = document.createElement("label");
      label.style.cssText = "display:inline-flex;align-items:center;gap:4px;font-size:0.75rem;cursor:pointer;padding:4px 8px;border-radius:6px;border:1px solid var(--color-border);background:var(--color-surface);";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "role-checkbox";
      cb.value = r.id;
      label.appendChild(cb);
      label.appendChild(document.createTextNode("@" + r.name));
      container.appendChild(label);
    });
  } catch (e) {
    console.error("Error loading roles:", e);
  }
}

let githubProfileData = null;
let pollChartInstance = null;

async function openPollModal(pollId) {
  const modal = document.getElementById("poll-modal");
  const title = document.getElementById("modal-title");
  if (!modal || !title) return;
  try {
    const resp = await fetch("/api/polls/" + pollId);
    const data = await resp.json();
    if (!data || data.error) {
      title.textContent = "Error loading poll";
      return;
    }
    title.textContent = data.question || "Poll";
    modal.setAttribute("aria-hidden", "false");
    modal.classList.add("open");
    const endBtn = document.getElementById("end-poll-btn");
    if (endBtn) {
      endBtn.style.display = data.active !== false ? "block" : "none";
      endBtn.onclick = async function() {
        if (!confirm('End this poll? Votes will be frozen and buttons disabled on Discord.')) return;
        try {
          const r = await fetch("/api/polls/" + pollId + "/end", { method: "POST" });
          const j = await r.json();
          if (r.ok) {
            alert("Poll ended successfully.");
            endBtn.style.display = "none";
            closePollModal();
            loadPollData();
          } else {
            alert("Error: " + (j.error || "Unknown"));
          }
        } catch (e) {
          alert("Network error ending poll.");
        }
      };
    }
    const ctx = document.getElementById("poll-chart-canvas");
    if (!ctx) return;
    const canvas = ctx.getContext("2d");
    if (typeof Chart === "undefined") {
      console.warn("Chart.js not loaded");
      return;
    }
    const labels = (data.options || []).map(o => o.name || "");
    const chartData = (data.options || []).map(o => o.votes || 0);
    const colors = ["#6366F1", "#8B5CF6", "#EC4899", "#F59E0B", "#22C55E"];
    if (pollChartInstance) pollChartInstance.destroy();
    pollChartInstance = new Chart(canvas, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Votes",
          data: chartData,
          backgroundColor: labels.map(function(_, i) { return colors[i % colors.length]; }),
          borderRadius: 6,
          borderSkipped: false
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: true,
        animation: { duration: 500, easing: "easeOutQuart" },
        scales: {
          x: { beginAtZero: true, ticks: { stepSize: 1, color: "#94A3B8" }, grid: { color: "rgba(148,163,184,0.15)" } },
          y: { ticks: { color: "#94A3B8" }, grid: { display: false } }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
    renderVoterMatrix(data.voters_by_choice || {});
    const refreshBtn = document.getElementById("refresh-poll-data");
    if (refreshBtn) {
      refreshBtn.onclick = function() { openPollModal(pollId); };
    }
  } catch (error) {
    console.error("Error opening poll modal:", error);
    title.textContent = "Error loading poll";
  }
}

function renderVoterMatrix(votersByChoice) {
  const container = document.getElementById("voter-matrix-table");
  if (!container) return;
  const entries = Object.keys(votersByChoice);
  if (entries.length === 0) {
    container.innerHTML = '<p style="color:var(--color-text-muted);font-size:0.8125rem;">No voter data available.</p>';
    return;
  }
  let rows = '<table class="matrix-table"><thead><tr><th>Option</th><th>Voters</th></tr></thead><tbody>';
  entries.forEach(choice => {
    const voters = votersByChoice[choice] || [];
    const voterList = voters.length > 0 ? voters.map(v => '<span class="matrix-voter">' + escapeHtml(v) + "</span>").join(" ") : '<span style="color:var(--color-text-muted)">No voters yet</span>';
    rows += "<tr><td><strong>" + escapeHtml(choice) + "</strong></td><td>" + voterList + "</td></tr>";
  });
  rows += "</tbody></table>";
  container.innerHTML = rows;
}



function closePollModal() {
  const modal = document.getElementById("poll-modal");
  if (!modal) return;
  modal.setAttribute("aria-hidden", "true");
  modal.classList.remove("open");
}

async function submitPollForm(e) {
  e.preventDefault();
  const q = document.getElementById("poll-question");
  const resp = document.getElementById("create-response");
  if (!q || !resp) return;
  const question = q.value.trim();
  const optionInputs = document.querySelectorAll(".poll-option-input");
  const options = Array.from(optionInputs).map(function(i) { return i.value.trim(); }).filter(Boolean);
  if (!question) { resp.textContent = "Please enter a question."; return; }
  if (options.length < 2) { resp.textContent = "Please provide at least 2 options."; return; }

  const channelSelect = document.getElementById("poll-channel");
  const channelId = channelSelect ? channelSelect.value || null : null;

  const roleCheckboxes = document.querySelectorAll(".role-checkbox:checked");
  const roleIds = roleCheckboxes.length > 0 ? Array.from(roleCheckboxes).map(function(cb) { return cb.value; }) : null;

  const maxVotesInput = document.getElementById("poll-max-votes");
  const maxVotes = maxVotesInput ? parseInt(maxVotesInput.value) || null : null;

  try {
    const r = await fetch("/api/polls/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question,
        options: options,
        channel_id: channelId,
        role_ids: roleIds,
        max_votes_per_option: maxVotes
      })
    });
    const json = await r.json();
    if (r.ok) {
      resp.textContent = "\u2705 Poll created successfully!";
      q.value = "";
      document.getElementById("poll-options-list").innerHTML = "";
      addPollOption(); addPollOption();
      document.querySelectorAll(".role-checkbox:checked").forEach(function(cb) { cb.checked = false; });
      if (maxVotesInput) maxVotesInput.value = "";
      loadPollData();
      setTimeout(function() { resp.textContent = ""; }, 3000);
    } else {
      resp.textContent = "\u274C Error: " + (json.error || "Unknown error");
    }
  } catch (err) {
    console.error(err);
    resp.textContent = "\u274C Network error creating poll";
  }
}

function addPollOption(value) {
  if (value === undefined) value = "";
  var MAX = 5;
  var container = document.getElementById("poll-options-list");
  if (!container) return;
  var idx = container.children.length;
  if (idx >= MAX) return;
  var div = document.createElement("div");
  div.style.cssText = "display:flex;gap:8px;align-items:center;";
  div.innerHTML = '<input type="text" class="poll-option-input search-input" placeholder="Option ' + (idx + 1) + '" value="' + value + '" required style="flex:1;">' +
    '<button type="button" class="btn btn-secondary" style="padding:6px 10px;font-size:0.8rem;" onclick="this.parentElement.remove();updatePollOptionCount()">\u2715</button>';
  container.appendChild(div);
  updatePollOptionCount();
}

function updatePollOptionCount() {
  var count = document.querySelectorAll(".poll-option-input").length;
  var el = document.getElementById("poll-option-count");
  if (el) el.textContent = count;
  var btn = document.getElementById("add-poll-option-btn");
  if (btn) btn.disabled = count >= 5;
}

async function exportCSV() {
  try {
    const resp = await fetch("/api/export/csv");
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      alert("\u274C Export failed: " + (err.error || "Unknown error"));
      return;
    }
    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "poll_feedback.csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  } catch (err) {
    console.error(err);
    alert("\u274C Export failed: Network error");
  }
}

function startAutoRefresh() {
  if (refreshIntervalId) clearInterval(refreshIntervalId);
  refreshIntervalId = setInterval(function() {
    var active = document.querySelector(".page.active");
    if (!active) return;
    var id = active.id;
    if (id === "polls" || id === "interactive") loadPollData();
    if (id === "vote-log") loadVoteLogData();
    if (id === "bot-status") loadBotStatusSection();
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
  var active = document.querySelector(".page.active");
  if (!active) return;
  if (active.id === "polls" || active.id === "interactive") loadPollData();
  if (active.id === "vote-log") loadVoteLogData();
  if (active.id === "bot-status") loadBotStatusSection();
}

function escapeHtml(text) {
  if (!text) return "";
  var d = document.createElement("div");
  d.textContent = text;
  return d.innerHTML;
}

var BOT_AVATAR_FALLBACK = "https://cdn.discordapp.com/avatars/1514286119892684881/2725db1fcb71ea2eeb98854b06fca50c.png?size=512";

function setAvatarUrl(url) {
  var src = url || BOT_AVATAR_FALLBACK;
  var introImg = document.getElementById("intro-avatar");
  var loaderImg = document.getElementById("loader-avatar");
  if (introImg) introImg.src = src;
  if (loaderImg) loaderImg.src = src;
}

function dismissIntro() {
  var overlay = document.getElementById("intro-overlay");
  if (!overlay) return;
  overlay.classList.add("hidden");
  var loader = document.getElementById("loading-screen");
  if (loader) loader.classList.add("active");

  Promise.all([
    fetch("/api/bot-status").then(function(r) { return r.json(); }).then(function(s) {
      if (s.avatar_url) setAvatarUrl(s.avatar_url);
    }).catch(function(){}),
    loadBotStatus().catch(function(){}),
    loadHealthData().catch(function(){}),
    loadGitHubProfile().catch(function(){})
  ]).then(function () {
    if (loader) loader.classList.remove("active");
    var app = document.querySelector(".app");
    if (app) app.classList.add("visible");
    startAutoRefresh();
  });
}

document.addEventListener("DOMContentLoaded", function () {
  initTheme();

  // Bind form handlers (data loads after intro dismissal)
  const form = document.getElementById("create-poll-form");
  if (form) form.addEventListener("submit", submitPollForm);

  const addBtn = document.getElementById("add-poll-option-btn");
  if (addBtn) addBtn.addEventListener("click", function (e) { e.preventDefault(); addPollOption(); });

  const refreshBtn = document.getElementById("refresh-polls");
  if (refreshBtn) refreshBtn.addEventListener("click", function () { loadPollData(); });

  if (!document.querySelector(".poll-option-input")) {
    addPollOption(""); addPollOption("");
  }

  document.addEventListener("click", function (e) {
    if (e.target && (e.target.id === "modal-backdrop" || e.target.id === "modal-close")) closePollModal();
  });

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stopAutoRefresh(); else { updateAllData(); startAutoRefresh(); }
  });
});

