"""
ui/static/js/dashboard.js - Dashboard JavaScript functionality
Handles real-time updates and user interactions
"""
"""

// Configuration
const CONFIG = {
    API_BASE: '/api',
    REFRESH_INTERVAL: 10000, // 10 seconds
    ALERTS_LIMIT: 5,
};

// Application state
let appState = {
    isRunning: true,
    refreshTimer: null,
};

// ========================================================================
// INITIALIZATION
// ========================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initializing...');
    
    // Setup event listeners
    setupEventListeners();
    
    // Initial data load
    refreshDashboard();
    
    // Setup auto-refresh
    appState.refreshTimer = setInterval(refreshDashboard, CONFIG.REFRESH_INTERVAL);
    
    console.log('Dashboard ready');
});

function setupEventListeners() {
    // Pause/Resume button
    const btnPause = document.getElementById('btn-pause');
    if (btnPause) {
        btnPause.addEventListener('click', toggleBotStatus);
    }
    
    // Modal close buttons
    document.querySelectorAll('.close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').style.display = 'none';
        });
    });
    
    // Exit position form
    const formExit = document.getElementById('form-exit');
    if (formExit) {
        formExit.addEventListener('submit', submitExitOrder);
    }
}

// ========================================================================
// DATA REFRESH
// ========================================================================

async function refreshDashboard() {
    try {
        // Parallel requests
        const [status, account, positions, trades, performance] = await Promise.all([
            fetchAPI('/status'),
            fetchAPI('/account'),
            fetchAPI('/positions'),
            fetchAPI('/trades?limit=50'),
            fetchAPI('/performance'),
        ]);
        
        // Update UI
        updateStatus(status);
        updateAccount(account);
        updatePositions(positions);
        updateTrades(trades);
        updatePerformance(performance);
        updateLastRefresh();
        
    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showAlert('Error refreshing data', 'danger');
    }
}

async function fetchAPI(endpoint) {
    const response = await fetch(CONFIG.API_BASE + endpoint);
    if (!response.ok) {
        throw new Error(`API error: \${response.status}`);
    }
    return await response.json();
}

// ========================================================================
// UI UPDATES
// ========================================================================

function updateStatus(status) {
    const indicator = document.getElementById('status-indicator');
    const btnPause = document.getElementById('btn-pause');
    
    if (status.trading_active) {
        indicator.textContent = 'TRADING ACTIVE';
        indicator.classList.remove('paused', 'error');
        indicator.classList.add('active');
        
        if (btnPause) {
            btnPause.textContent = '⏸ Pause';
            btnPause.classList.remove('active');
        }
    } else {
        indicator.textContent = 'PAUSED';
        indicator.classList.add('paused');
        indicator.classList.remove('error');
        
        if (btnPause) {
            btnPause.textContent = '▶ Resume';
            btnPause.classList.add('active');
        }
    }
}

function updateAccount(account) {
    if (!account || Object.keys(account).length === 0) return;
    
    document.getElementById('portfolio-value').textContent = 
        formatCurrency(account.portfolio_value);
    document.getElementById('available-cash').textContent = 
        formatCurrency(account.cash);
    document.getElementById('buying-power').textContent = 
        formatCurrency(account.buying_power);
}

function updatePositions(data) {
    if (!data || !data.open_positions) return;
    
    const positions = data.open_positions;
    const tbody = document.getElementById('positions-tbody');
    const count = document.getElementById('position-count');
    
    count.textContent = positions.length;
    
    if (positions.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="9">No open positions</td></tr>';
        return;
    }
    
    tbody.innerHTML = positions.map(pos => `
        <tr>
            <td><strong>${pos.ticker}</strong></td>
            <td><span class="badge badge-${pos.option_type.toLowerCase()}">\${pos.option_type}</span></td>
            <td>$${formatPrice(pos.strike)}</td>
            <td>$${formatPrice(pos.entry_price)}</td>
            <td>$${formatPrice(pos.current_price)}</td>
            <td>${pos.dte}</td>
            <td class="pnl-${pos.unrealized_pl >= 0 ? 'positive' : 'negative'}">
                $${formatPrice(pos.unrealized_pl)}
            </td>
            <td class="pnl-${pos.unrealized_pl_pct >= 0 ? 'positive' : 'negative'}">
                ${formatPercent(pos.unrealized_pl_pct)}
            </td>
            <td>
                <button class="btn-exit" onclick="openExitModal('${pos.symbol}')">Exit</button>
            </td>
        </tr>
    `).join('');
}
function updateTrades(data) {
    if (!data || !data.recent_trades) return;
    
    const trades = data.recent_trades;
    const tbody = document.getElementById('trades-tbody');
    
    if (trades.length === 0) {
        tbody.innerHTML = '<tr class="empty-row"><td colspan="9">No closed trades</td></tr>';
        return;
    }
    
    tbody.innerHTML = trades.map(trade => {
        const date = new Date(trade.entry_time).toLocaleDateString();
        const pnlClass = trade.pnl_dollars >= 0 ? 'pnl-positive' : 'pnl-negative';
        
        return `
            <tr>
                <td>${date}</td>
                <td><strong>${trade.ticker}</strong></td>
                <td><span class="badge badge-${trade.option_type.toLowerCase()}">${trade.option_type}</span></td>
                <td>$${formatPrice(trade.entry_price)}</td>
                <td>$${formatPrice(trade.exit_price)}</td>
                <td class="${pnlClass}">$${formatPrice(trade.pnl_dollars)}</td>
                <td class="${pnlClass}">${formatPercent(trade.pnl_pct)}</td>
                <td>${trade.hold_days}d</td>
                <td>${trade.exit_reason}</td>
            </tr>
        `;
    }).join('');
}
function updatePerformance(performance) {
    if (!performance || Object.keys(performance).length === 0) return;
    
    document.getElementById('total-trades').textContent = 
        performance.total_trades || 0;
    document.getElementById('win-rate').textContent = 
        formatPercent(performance.win_rate_pct) || '0%';
    document.getElementById('avg-win').textContent = 
        formatPercent(performance.avg_win_pct) || '+0.00%';
    document.getElementById('avg-loss').textContent = 
        formatPercent(performance.avg_loss_pct) || '-0.00%';
    document.getElementById('profit-factor').textContent = 
        (performance.profit_factor || 0).toFixed(2);
    document.getElementById('total-pnl').textContent = 
        formatCurrency(performance.total_pnl_dollars);
}
function updateLastRefresh() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    document.getElementById('last-updated').textContent = timeStr;
}
// ========================================================================
// USER ACTIONS
// ========================================================================
async function toggleBotStatus() {
    try {
        const endpoint = appState.isRunning ? '/bot/pause' : '/bot/resume';
        const response = await fetch(CONFIG.API_BASE + endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        
        const result = await response.json();
        appState.isRunning = result.status === 'RUNNING';
        refreshDashboard();
        
    } catch (error) {
        console.error('Error toggling bot status:', error);
        showAlert('Error toggling bot status', 'danger');
    }
}
function openExitModal(symbol) {
    document.getElementById('exit-symbol').textContent = symbol;
    document.getElementById('modal-exit').style.display = 'block';
}
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}
async function submitExitOrder(event) {
    event.preventDefault();
    
    try {
        const symbol = document.getElementById('exit-symbol').textContent;
        const portion = document.getElementById('exit-portion').value;
        
        const response = await fetch(CONFIG.API_BASE + '/trade/exit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, portion }),
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showAlert(`Exit order submitted for ${symbol}`, 'success');
            closeModal('modal-exit');
            refreshDashboard();
        } else {
            showAlert(result.error || 'Error submitting exit order', 'danger');
        }
        
    } catch (error) {
        console.error('Error submitting exit order:', error);
        showAlert('Error submitting exit order', 'danger');
    }
}
// ========================================================================
// UTILITIES
// ========================================================================
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
    }).format(value || 0);
}
function formatPrice(value) {
    return (value || 0).toFixed(2);
}
function formatPercent(value) {
    const num = parseFloat(value) || 0;
    const sign = num >= 0 ? '+' : '';
    return `${sign}${num.toFixed(2)}%`;
}
function showAlert(message, type = 'info') {
    const container = document.getElementById('alerts-container');
    
    // Remove "no alerts" message
    const noAlerts = container.querySelector('.no-alerts');
    if (noAlerts) noAlerts.remove();
    
    // Create alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.textContent = `${type.toUpperCase()}: ${message}`;
    
    container.insertBefore(alert, container.firstChild);
    
    // Limit alerts display
    const alerts = container.querySelectorAll('.alert');
    if (alerts.length > CONFIG.ALERTS_LIMIT) {
        alerts[alerts.length - 1].remove();
    }
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
        
        // Show "no alerts" if empty
        if (container.children.length === 0) {
            const noAlerts = document.createElement('p');
            noAlerts.className = 'no-alerts';
            noAlerts.textContent = 'No active alerts';
            container.appendChild(noAlerts);
        }
    }, 5000);
}
// ========================================================================
// CLEANUP
// ========================================================================
window.addEventListener('beforeunload', function() {
    if (appState.refreshTimer) {
        clearInterval(appState.refreshTimer);
    }
});
// Close modals on outside click
window.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
});
