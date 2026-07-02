/**
 * Bridge 2026 Dashboard - Main JavaScript
 * Handles data loading, polling, and UI updates
 */

const REFRESH_INTERVAL = 5000; // Refresh data every 5 seconds
let refreshIntervalId = null;
let currentPollData = {};

/**
 * Initialize dashboard on page load
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Dashboard initialized');
    loadDashboardData();
    startAutoRefresh();
    setupEventListeners();
});

/**
 * Setup event listeners for navigation and controls
 */
function setupEventListeners() {
    // Navigation links
    document.querySelectorAll('[data-section]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.dataset.section;
            showSection(section);
        });
    });
    
    // Refresh button
    const refreshBtn = document.getElementById('refresh-polls');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', loadDashboardData);
    }
    
    // Export button
    const exportBtn = document.querySelector('[onclick="exportCSV()"]');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportCSV);
    }
    
    // Create poll form
    const pollForm = document.getElementById('create-poll-form');
    if (pollForm) {
        pollForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await createPollFromForm();
        });
    }
    
    // Search/filter
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', filterVotes);
    }
    
    // Theme toggle
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
}

/**
 * Show specific dashboard section
 */
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Deactivate all nav links
    document.querySelectorAll('[data-section]').forEach(link => {
        link.classList.remove('active');
    });
    
    // Show selected section
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
        const link = document.querySelector(`[data-section="${sectionId}"]`);
        if (link) link.classList.add('active');
    }
}

/**
 * Load all dashboard data from API
 */
async function loadDashboardData() {
    try {
        // Load overview stats
        const overview = await fetch('/api/dashboard/overview').then(r => r.json());
        updateOverviewStats(overview);
        
        // Load poll data
        const summary = await fetch('/api/summary').then(r => r.json());
        updatePollsSection(summary);
        
        // Load vote log
        const votes = await fetch('/api/votes/all?limit=100').then(r => r.json());
        updateVoteLog(votes.votes);
        
        console.log('Dashboard data loaded');
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError('Failed to load dashboard data');
    }
}

/**
 * Update overview statistics
 */
function updateOverviewStats(data) {
    const elements = {
        'active-polls-count': data.active_polls || 0,
        'total-votes-count': data.total_votes || 0,
        'engagement-rate': data.engagement_rate || '0%'
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }
}

/**
 * Update polls section with current poll data
 */
function updatePollsSection(data) {
    const container = document.getElementById('polls-container');
    if (!container) return;
    
    if (!data.summary || Object.keys(data.summary).length === 0) {
        container.innerHTML = '<div class="card"><p style="color: var(--color-text-muted); text-align: center;">No active polls</p></div>';
        return;
    }
    
    const pollsHtml = Object.entries(data.summary).map(([question, stats]) => {
        const choices = stats.Choice || {};
        const totalVotes = stats.Total_Votes || 0;
        
        const choicesHtml = Object.entries(choices).map(([choice, count]) => {
            const percentage = totalVotes > 0 ? ((count / totalVotes) * 100).toFixed(1) : 0;
            return `
                <div style="margin: 12px 0;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span>${escapeHtml(choice)}</span>
                        <span style="font-weight: 600;">${count} (${percentage}%)</span>
                    </div>
                    <div style="background: #e0e0e0; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #667eea, #764ba2); height: 100%; width: ${percentage}%;"></div>
                    </div>
                </div>
            `;
        }).join('');
        
        return `
            <div class="card">
                <h3 class="card-title">${escapeHtml(question)}</h3>
                <p style="color: var(--color-text-muted); font-size: 0.875rem; margin-bottom: 16px;">
                    Total Votes: ${totalVotes}
                </p>
                ${choicesHtml}
            </div>
        `;
    }).join('');
    
    container.innerHTML = pollsHtml;
}

/**
 * Update vote log table
 */
function updateVoteLog(votes) {
    const tbody = document.querySelector('#vote-log-table tbody');
    if (!tbody) return;
    
    if (!votes || votes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 24px; color: var(--color-text-muted);">No votes yet</td></tr>';
        return;
    }
    
    const voteRows = votes.map(vote => `
        <tr>
            <td>${formatTimestamp(vote.Timestamp)}</td>
            <td>${escapeHtml(vote.Username)}</td>
            <td>${escapeHtml(vote.Question)}</td>
            <td><strong>${escapeHtml(vote.Choice)}</strong></td>
        </tr>
    `).join('');
    
    tbody.innerHTML = voteRows;
    
    // Update sync time
    const syncEl = document.getElementById('sync-time');
    if (syncEl) {
        syncEl.textContent = `Last synced: ${new Date().toLocaleTimeString()}`;
    }
}

/**
 * Filter votes based on search input
 */
function filterVotes() {
    const searchTerm = document.getElementById('search-input')?.value.toLowerCase() || '';
    const rows = document.querySelectorAll('#vote-log-table tbody tr');
    
    rows.forEach(row => {
        if (searchTerm === '') {
            row.style.display = '';
        } else {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(searchTerm) ? '' : 'none';
        }
    });
}

/**
 * Create poll from form
 */
async function createPollFromForm() {
    const questionEl = document.getElementById('poll-question');
    const option1El = document.getElementById('poll-option1');
    const option2El = document.getElementById('poll-option2');
    const responseEl = document.getElementById('create-response');
    
    if (!questionEl || !option1El || !option2El) return;
    
    const question = questionEl.value.trim();
    const options = [option1El.value.trim(), option2El.value.trim()].filter(Boolean);
    
    if (!question) {
        showResponseMessage(responseEl, 'Please enter a question', true);
        return;
    }
    
    if (options.length < 2) {
        showResponseMessage(responseEl, 'Please enter at least 2 options', true);
        return;
    }
    
    try {
        const response = await fetch('/api/polls/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, options })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showResponseMessage(responseEl, '✅ Poll created successfully!', false);
            questionEl.value = '';
            option1El.value = '';
            option2El.value = '';
            loadDashboardData();
        } else {
            showResponseMessage(responseEl, `❌ Error: ${data.error || 'Unknown error'}`, true);
        }
    } catch (error) {
        showResponseMessage(responseEl, `❌ Network error: ${error.message}`, true);
        console.error('Error:', error);
    }
}

/**
 * Export data to CSV
 */
async function exportCSV() {
    try {
        const response = await fetch('/api/export/csv');
        const data = await response.json();
        
        if (response.ok) {
            alert(`✅ Data exported to: ${data.file}`);
        } else {
            alert(`❌ Export failed: ${data.error}`);
        }
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    }
}

/**
 * Start automatic refresh interval
 */
function startAutoRefresh() {
    if (refreshIntervalId) clearInterval(refreshIntervalId);
    refreshIntervalId = setInterval(loadDashboardData, REFRESH_INTERVAL);
}

/**
 * Stop automatic refresh
 */
function stopAutoRefresh() {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
    }
}

/**
 * Toggle dark/light theme
 */
function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.getAttribute('data-theme') === 'dark';
    html.setAttribute('data-theme', isDark ? 'light' : 'dark');
    localStorage.setItem('theme', isDark ? 'light' : 'dark');
    
    const icon = document.getElementById('theme-icon');
    if (icon) icon.textContent = isDark ? '🌙' : '☀️';
}

/**
 * Utility: Show response message
 */
function showResponseMessage(element, message, isError) {
    if (element) {
        element.textContent = message;
        element.style.color = isError ? '#ff6b6b' : '#51cf66';
    }
}

/**
 * Utility: Show error notification
 */
function showError(message) {
    console.error(message);
    // Could add toast notification here
}

/**
 * Utility: Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Utility: Format timestamp
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

/**
 * Pause refresh when tab loses focus
 */
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        loadDashboardData();
        startAutoRefresh();
    }
});
