// ChaosMonkey Dashboard JavaScript
// Updated: 2025-10-10 03:49 - Restored Dora VM table with power actions

// Global state
let currentTab = 'dashboard';
let chaosTypes = [];
let nodes = [];
let reports = [];
let pendingChaosTypeSelection = null;
// currentNodeSource reflects the currently selected datasource in the UI.
// Keep this as a plain variable in production; debugging instrumentation
// was removed to avoid noisy console output.
let currentNodeSource = 'nomad'; // default
let doraEnvironments = [];
let currentDoraEnvironment = 'Dev'; // Default to Dev environment
// Dora status updater
let doraStatusInterval = null;
let doraStatusIntervalMs = 15000; // 15s

// Small helper to escape values when rendered into HTML attributes
function escapeHtml(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// Normalize a single Dora VM record so the UI can consistently render Dora rows.
function normalizeDoraClient(vm) {
    const normalized = Object.assign({}, vm);
    normalized.source = 'dora';
    try {
        if (normalized.probe_source && String(normalized.probe_source).toLowerCase() === 'olvm' && normalized.probe_status) {
            normalized.status = normalized.probe_status;
        } else {
            normalized.status = normalized.status || normalized.power_state || normalized.state || normalized.powerState || 'unknown';
        }
    } catch (e) {
        normalized.status = normalized.status || normalized.power_state || normalized.state || normalized.powerState || 'unknown';
    }
    normalized.guestOS = normalized.guestOS || normalized.guest_os || normalized.guest || '-';
    return normalized;
}

// Background refresh state
let autoRefreshInterval = null;
let isRefreshing = false;
let autoRefreshEnabled = true;
const AUTO_REFRESH_INTERVAL = 30000; // 30 seconds

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    loadChaosTypes();
    loadDoraEnvironments(); // Load Dora environments on startup
    setupEventListeners();
    
    // Load auto-refresh state from localStorage
    const savedState = localStorage.getItem('autoRefreshEnabled');
    if (savedState !== null) {
        autoRefreshEnabled = savedState === 'true';
    }
    
    // Set toggle state
    const toggle = document.getElementById('auto-refresh-toggle');
    if (toggle) {
        toggle.checked = autoRefreshEnabled;
    }
    
    if (autoRefreshEnabled) {
        startAutoRefresh();
    }
});

// Ensure UI select matches internal state when page loads
document.addEventListener('DOMContentLoaded', function() {
    const src = document.getElementById('source-select');
    if (src) {
        try { src.value = currentNodeSource; } catch (e) {}
    }
});

// Tab switching
function showTab(tabName, evt = null) {
    if (evt) {
        evt.preventDefault();
    }

    // Hide all tabs then reveal chosen view
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = tab.id === `${tabName}-tab` ? 'block' : 'none';
    });

    // Update nav state based on data attribute
    document.querySelectorAll('.nav-link[data-tab]').forEach(link => {
        link.classList.toggle('active', link.dataset.tab === tabName);
    });

    currentTab = tabName;

    // Load tab data on demand
    switch (tabName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'nodes':
            loadNodes();
            // Ensure Dora updater is started when switching to nodes tab
            try { startDoraStatusUpdater(); } catch (e) { console.debug('startDoraStatusUpdater call in showTab failed', e); }
            break;
        case 'execute':
            loadChaosTypes();
            break;
        case 'reports':
            loadReports();
            break;
        default:
            break;
    }

    // Stop or start Dora updater depending on whether we're on the nodes tab
    if (currentTab !== 'nodes') {
        stopDoraStatusUpdater();
    } else {
        // When switching to nodes tab, let loadNodes decide whether to start the updater
    }
}

// Dashboard functions
async function loadDashboard() {
    try {
        // Load statistics
        await Promise.all([
            loadNodeStats(),
            loadRecentExperiments(),
            loadChaosTypesSummary()
        ]);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadNodeStats() {
    try {
        const response = await fetch('/api/discover/clients');
        const data = await response.json();
        
        if (data.success && data.output && data.output.clients) {
            const clients = data.output.clients;
            const totalNodes = clients.length;
            const readyNodes = clients.filter(n => n.status.includes('ready')).length;
            // Count nodes that are draining or drained (Yes or Draining...)
            const drainedNodes = clients.filter(n => 
                n.drain && (n.drain.includes('Yes') || n.drain.includes('Draining'))
            ).length;
            // Count recovered nodes (eligible, no drain, and ready status)
            const recoveredNodes = clients.filter(n => 
                n.drain === 'No' && n.status.includes('ready')
            ).length;
            
            document.getElementById('stat-total-nodes').textContent = totalNodes;
            document.getElementById('stat-ready-nodes').textContent = `Ready: ${readyNodes}`;
            document.getElementById('stat-drained-nodes').textContent = drainedNodes;
            document.getElementById('stat-recovered-nodes').textContent = recoveredNodes;
        }
    } catch (error) {
        console.error('Error loading node stats:', error);
    }
}

async function loadRecentExperiments() {
    try {
        const response = await fetch('/api/reports');
        const data = await response.json();
        
        if (data.reports) {
            reports = data.reports;
            const recentReports = data.reports.slice(0, 5);
            
            document.getElementById('stat-total-experiments').textContent = data.reports.length;
            
            // Calculate success rate
            const completed = data.reports.filter(r => r.status === 'completed').length;
            const successRate = data.reports.length > 0 
                ? Math.round((completed / data.reports.length) * 100) 
                : 0;
            // Defensive: update success-rate only if element exists in the DOM
            const successEl = document.getElementById('stat-success-rate');
            if (successEl) {
                successEl.textContent = successRate + '%';
            }
            
            // Display recent experiments
            const container = document.getElementById('recent-experiments');
            if (recentReports.length === 0) {
                container.innerHTML = '<div class="text-muted text-center">No experiments yet</div>';
                return;
            }
            
            container.innerHTML = recentReports.map(report => `
                <a href="#" class="list-group-item list-group-item-action experiment-item experiment-status-${report.status}" 
                   onclick="showReport('${report.run_id}'); return false;">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <strong>${getChaosIcon(report.chaos_type)} ${report.chaos_type}</strong>
                            <br>
                            <small class="text-muted">${formatDate(report.started_at)}</small>
                        </div>
                        <span class="badge status-badge status-${report.status}">${report.status}</span>
                    </div>
                </a>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading recent experiments:', error);
    }
}

async function loadChaosTypesSummary() {
    const container = document.getElementById('chaos-types-list');
    if (!container) {
        return;
    }

    container.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i></div>';

    try {
        const response = await fetch('/api/chaos-types');
        const data = await response.json();
        
        if (Array.isArray(data.chaos_types) && data.chaos_types.length > 0) {
            chaosTypes = data.chaos_types;
            container.innerHTML = data.chaos_types.map(type => `
                <div class="col-md-4 mb-3">
                    <div class="chaos-type-card" onclick="selectChaosType('${type.name}')">
                        <div class="chaos-type-icon">${type.icon}</div>
                        <h6>${type.display_name}</h6>
                    </div>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="text-center text-muted">No chaos types available.</div>';
        }
    } catch (error) {
        console.error('Error loading chaos types:', error);
        container.innerHTML = '<div class="alert alert-danger">Failed to load chaos types.</div>';
    }
}

// Nodes functions
async function loadNodes(silent = false) {
    const container = document.getElementById('nodes-table');
    
    if (!silent) {
        container.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i></div>';
    }
    
    try {
    // Get source (nomad or dora)
    const sourceSelect = document.getElementById('source-select');
    // If the user changed the select control, honor it. Otherwise fall back to
    // the internal state so programmatic refreshes can preserve the last
    // chosen source.
    const source = sourceSelect ? sourceSelect.value : (currentNodeSource || 'nomad');
    // Keep DOM in sync (ensure select shows current source)
    if (sourceSelect && sourceSelect.value !== source) sourceSelect.value = source;
    currentNodeSource = source;
        
        // Get environment if Dora
        let url = '/api/discover/clients';
        if (source === 'dora') {
            const envSelect = document.getElementById('dora-environment-select');
            const environment = envSelect ? envSelect.value : 'Dev';
            // Add timestamp to force fresh data (no browser or server cache)
            const timestamp = new Date().getTime();
            url = `/api/discover/clients?source=dora&environment=${environment}&_t=${timestamp}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success && data.output && data.output.clients) {
            // If caller requested Dora VMs, mark each record so renderNodesTable
            // can pick the Dora rendering path. Also normalize common status
            // fields so the Dora table can determine running/stopped state.
            if (source === 'dora') {
                nodes = data.output.clients.map(vm => {
                    const normalized = Object.assign({}, vm);
                    normalized.source = 'dora';
                    // Prefer OLVM probe_status when available (shows live state).
                    // Fall back to any existing status fields if probe info is absent.
                    try {
                        if (normalized.probe_source && String(normalized.probe_source).toLowerCase() === 'olvm' && normalized.probe_status) {
                            normalized.status = normalized.probe_status;
                        } else {
                            // Normalize status: various backends may use different keys
                            normalized.status = normalized.status || normalized.power_state || normalized.state || normalized.powerState || 'unknown';
                        }
                    } catch (e) {
                        // Defensive: ensure a status exists even if unexpected shapes appear
                        normalized.status = normalized.status || normalized.power_state || normalized.state || normalized.powerState || 'unknown';
                    }
                    // Normalize guest OS naming
                    normalized.guestOS = normalized.guestOS || normalized.guest_os || normalized.guest || '-';
                    return normalized;
                });
            } else {
                nodes = data.output.clients;
            }
                renderNodesTable(data.output);
        } else {
            if (!silent) {
                // If we already have a table rendered, keep it and show a small alert instead
                if (nodes && nodes.length > 0) {
                    const alertHtml = `<div class="alert alert-warning">Failed to load ${source === 'dora' ? 'VMs' : 'nodes'}: ${data.error || 'Unknown error'}</div>`;
                    container.insertAdjacentHTML('afterbegin', alertHtml);
                } else {
                    container.innerHTML = `<div class="alert alert-warning">Failed to load ${source === 'dora' ? 'VMs' : 'nodes'}: ${data.error || 'Unknown error'}</div>`;
                }
            }
        }
    } catch (error) {
        console.error('Error loading nodes:', error);
        if (!silent) {
            // Preserve existing table if possible and show a non-blocking alert
            if (nodes && nodes.length > 0) {
                const alertHtml = `<div class="alert alert-danger">Error loading nodes: ${error.message || error}</div>`;
                container.insertAdjacentHTML('afterbegin', alertHtml);
            } else {
                container.innerHTML = `<div class="alert alert-danger">Error loading nodes: ${error.message || error}</div>`;
            }
        }
    }
}

function renderNodesTable(data) {
    const container = document.getElementById('nodes-table');
    // Normalize incoming data: some callers pass the full response {cached, output: {...}}
    // while others pass the output object directly. Create a payload with a consistent shape.
    const payload = (data && Object.prototype.hasOwnProperty.call(data, 'output'))
        ? data
        : { cached: false, output: data || { clients: [], stats: null } };
    
    // Check if this is Dora data (VMs) and render appropriate table
    if (nodes.length > 0 && nodes[0].source === 'dora') {
        renderDoraTable(payload.output);
        return;
    }
    
    // Show cache indicator
    const cacheIndicator = payload.cached ? 
        '<span class="badge bg-info">📦 Cached</span>' : 
        '<span class="badge bg-success">🔄 Live</span>';
    
    // Show refresh indicator
    const refreshIndicator = isRefreshing ? 
        '<span class="badge bg-warning"><i class="fas fa-sync-alt fa-spin"></i> Refreshing...</span>' : '';
    
    // Show stats if available
    let statsHtml = '';
    if (payload.output && payload.output.stats) {
        const stats = payload.output.stats;
        if (stats.new > 0 || stats.updated > 0) {
            statsHtml = `<div class="alert alert-info alert-sm mt-2">
                <small>Updated: ${stats.new} new, ${stats.updated} changed, ${stats.cached} cached</small>
            </div>`;
        }
    }
    
    const table = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <div>
                ${cacheIndicator}
                ${refreshIndicator}
            </div>
            <small class="text-muted">Last updated: ${new Date().toLocaleTimeString()}</small>
        </div>
        ${statsHtml}
        
        <!-- Bulk Actions Toolbar -->
        <div class="card mb-3" id="bulk-actions-toolbar" style="display: none;">
            <div class="card-body py-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="me-3"><strong><span id="selected-count">0</span></strong> nodes selected</span>
                        <button class="btn btn-sm btn-danger me-2" onclick="bulkDrainNodes()" id="bulk-drain-btn">
                            <i class="fas fa-power-off"></i> Drain Selected
                        </button>
                        <button class="btn btn-sm btn-success me-2" onclick="bulkRecoverNodes()" id="bulk-recover-btn">
                            <i class="fas fa-check-circle"></i> Recover Selected
                        </button>
                        <button class="btn btn-sm btn-warning" onclick="showPercentageDrainModal()">
                            <i class="fas fa-percent"></i> Drain by Percentage
                        </button>
                    </div>
                    <button class="btn btn-sm btn-outline-secondary" onclick="clearNodeSelection()">
                        <i class="fas fa-times"></i> Clear Selection
                    </button>
                </div>
            </div>
        </div>
        
        <table class="table table-striped table-hover">
            <thead class="table-dark">
                <tr>
                    <th style="width: 40px;">
                        <input type="checkbox" id="select-all-nodes" onchange="toggleSelectAllNodes()" title="Select All">
                    </th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Datacenter</th>
                    <th>CPU</th>
                    <th>Memory</th>
                    <th>Drain Status</th>
                    <th>Allocations</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${nodes.map(node => {
                    // Check if node is drained or draining (with safe property access)
                    const drainStatus = node.drain || 'N/A';
                    const isDrainedOrDraining = drainStatus && typeof drainStatus === 'string' && (
                        drainStatus.toLowerCase().includes('yes') || 
                        drainStatus.toLowerCase().includes('draining')
                    );
                    
                    // Safe access to properties
                    const status = node.status || 'unknown';
                    const statusClass = typeof status === 'string' ? status.toLowerCase().replace(/[^a-z]/g, '') : 'unknown';
                    const drainClass = typeof drainStatus === 'string' ? drainStatus.toLowerCase().replace(/[^a-z]/g, '') : 'na';
                    
                    return `
                    <tr>
                        <td>
                            <input type="checkbox" class="node-checkbox" value="${node.id || ''}" data-name="${node.name || 'unknown'}" onchange="updateBulkActionButtons()">
                        </td>
                        <td><strong>${node.name || 'Unknown'}</strong><br><small class="text-muted" title="${node.id || ''}">${(node.id || '').substring(0, 12)}...</small></td>
                        <td><span class="node-status-${statusClass}">${status}</span></td>
                        <td>${node.datacenter || 'unknown'}</td>
                        <td>${node.cpu || '-'}</td>
                        <td>${node.memory || '-'}</td>
                        <td><span class="node-drain-${drainClass}">${drainStatus}</span></td>
                        <td>${node.allocations || '-'}</td>
                        <td class="node-actions">
                            ${node.source === 'dora' 
                                ? `<span class="text-muted"><i class="fas fa-info-circle"></i> Dora VM</span>`
                                : (isDrainedOrDraining
                                    ? `<button class="btn btn-sm btn-success" onclick="enableNode('${node.id}', '${node.name}')">
                                        <i class="fas fa-check-circle"></i> Recover
                                       </button>`
                                    : `<button class="btn btn-sm btn-danger" onclick="drainNode('${node.id}', '${node.name}')">
                                        <i class="fas fa-power-off"></i> Drain
                                       </button>`)
                            }
                        </td>
                    </tr>
                `}).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = table;
    updateBulkActionButtons();
}

// Render Dora VMs table (different structure from Nomad nodes)
function renderDoraTable(data) {
    const container = document.getElementById('nodes-table');
    
    // Show cache indicator
    const cacheIndicator = data.cached ? 
        '<span class="badge bg-info">📦 Cached</span>' : 
        '<span class="badge bg-success">🔄 Live</span>';
    
    const table = `
        <div class="d-flex justify-content-between align-items-center mb-2">
            <div>
                ${cacheIndicator}
            </div>
            <small class="text-muted">Last updated: ${new Date().toLocaleTimeString()}</small>
        </div>
        
        <table class="table table-striped table-hover">
            <thead class="table-dark">
                <tr>
                    <th>Name</th>
                    <th>Power State</th>
                    <th>Hypervisor</th>
                    <th>CPU</th>
                    <th>Memory</th>
                    <th>Guest OS</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${nodes.map(vm => {
                    const powerState = vm.status || 'unknown';
                    // Show a visible indicator when the UI is displaying a live OLVM probe
                    const displayState = (vm.probe_source && String(vm.probe_source).toLowerCase() === 'olvm' && vm.probe_status)
                        ? `${powerState} (live)`
                        : powerState;
                    const isRunning = powerState.toLowerCase().includes('running') || powerState.toLowerCase().includes('on');
                    const isStopped = powerState.toLowerCase().includes('off') || powerState.toLowerCase().includes('stopped');
                    
                    // Use escaped attributes to avoid breaking the generated HTML when VM names
                    // contain quotes or other special characters. Action buttons are rendered
                    // with data attributes and wired after insertion.
                    const safeName = escapeHtml(vm.name || '');
                    const safeId = escapeHtml(vm.id || '');
                    return `
                    <tr data-vm-name="${safeName}">
                        <td><strong>${escapeHtml(vm.name) || 'Unknown'}</strong><br><small class="text-muted">${safeId}</small></td>
                        <td><span class="badge ${isRunning ? 'bg-success' : 'bg-secondary'}" title="Source: ${escapeHtml(vm.probe_source || 'dora')}">${escapeHtml(displayState)}</span></td>
                        <td>${escapeHtml(vm.datacenter || '-')}</td>
                        <td>${escapeHtml(vm.cpu || '-')}</td>
                        <td>${escapeHtml(vm.memory || '-')}</td>
                        <td>${escapeHtml(vm.guestOS || '-')}</td>
                        <td class="vm-actions">
                            <button class="btn btn-sm btn-success me-1 vm-action-start" data-vm="${safeName}" ${isRunning ? 'disabled' : ''}>
                                <i class="fas fa-play"></i> Start
                            </button>
                            <button class="btn btn-sm btn-warning me-1 vm-action-reboot" data-vm="${safeName}" ${isStopped ? 'disabled' : ''}>
                                <i class="fas fa-redo"></i> Reboot
                            </button>
                            <button class="btn btn-sm btn-danger vm-action-stop" data-vm="${safeName}" ${isStopped ? 'disabled' : ''}>
                                <i class="fas fa-stop"></i> Stop
                            </button>
                        </td>
                    </tr>
                `}).join('')}
            </tbody>
        </table>
    `;
    
    container.innerHTML = table;
    updateBulkActionButtons();
    // Start background updater for Dora table when rendered
    startDoraStatusUpdater();

    // Wire up action button event handlers now that DOM elements exist
    try {
        container.querySelectorAll('.vm-action-start').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const vmName = btn.getAttribute('data-vm');
                vmPowerAction(vmName, 'start');
            });
        });
        container.querySelectorAll('.vm-action-reboot').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const vmName = btn.getAttribute('data-vm');
                vmPowerAction(vmName, 'reboot');
            });
        });
        container.querySelectorAll('.vm-action-stop').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const vmName = btn.getAttribute('data-vm');
                vmPowerAction(vmName, 'stop');
            });
        });
    } catch (e) {
        console.error('Error wiring VM action buttons:', e);
    }
}

// Background updater: fetches latest OLVM probe statuses for current environment
async function fetchDoraStatuses(environment) {
    console.debug('fetchDoraStatuses: fetching statuses for env=', environment);
    try {
        const response = await fetch('/api/dora/vms-status?environment=' + encodeURIComponent(environment));
        const data = await response.json();
        if (!data.success) return;

        // data.vms is an array of {vm_name, probe_status, probe_source}
        data.vms.forEach(vm => {
            try {
                // Iterate rows and match by attribute equality to handle special characters
                const rows = document.querySelectorAll('#nodes-table table tbody tr');
                let row = null;
                rows.forEach(r => {
                    if (r.getAttribute('data-vm-name') === vm.vm_name) row = r;
                });
                if (!row) return;
                const badge = row.querySelector('td:nth-child(2) .badge');
                if (!badge) return;
                const statusText = vm.probe_source && String(vm.probe_source).toLowerCase() === 'olvm' && vm.probe_status
                    ? `${vm.probe_status} (live)`
                    : (vm.dora_status || 'unknown');
                const isRunning = String((vm.probe_status || vm.dora_status || '')).toLowerCase().includes('on') || String((vm.probe_status || vm.dora_status || '')).toLowerCase().includes('running');
                badge.textContent = statusText;
                badge.title = `Source: ${vm.probe_source || 'dora'}`;
                badge.classList.toggle('bg-success', isRunning);
                badge.classList.toggle('bg-secondary', !isRunning);
            } catch (e) {
                console.error('Error updating row for', vm.vm_name, e);
            }
        });
    } catch (e) {
        console.error('Error fetching Dora statuses:', e);
    }
}

function startDoraStatusUpdater() {
    // Only start when on nodes tab and source is dora
    if (doraStatusInterval) return; // already running
    if (currentTab !== 'nodes') return;
    if (currentNodeSource !== 'dora') return;

    const envSelect = document.getElementById('dora-environment-select');
    const env = envSelect ? envSelect.value : currentDoraEnvironment;

    console.debug('startDoraStatusUpdater: starting updater for env=', env, ' intervalMs=', doraStatusIntervalMs);
    // Immediately run once
    fetchDoraStatuses(env);

    doraStatusInterval = setInterval(() => fetchDoraStatuses(env), doraStatusIntervalMs);
}

function stopDoraStatusUpdater() {
    if (!doraStatusInterval) return;
    console.debug('stopDoraStatusUpdater: stopping updater');
    clearInterval(doraStatusInterval);
    doraStatusInterval = null;
}

// Handle VM power actions (Start, Reboot, Stop)
async function vmPowerAction(vmName, action) {
    if (!confirm(`Are you sure you want to ${action} VM "${vmName}"?`)) {
        return;
    }
    
    // Show loading state
    const button = event.target.closest('button');
    const originalHTML = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + action.charAt(0).toUpperCase() + action.slice(1) + 'ing...';
    
    try {
        const environment = document.getElementById('dora-environment-select')?.value || 'Dev1';
        const response = await fetch('/api/dora/vm-power', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                vm_name: vmName, 
                action: action,
                environment: environment
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            const note = data.note ? `\n\n${data.note}` : '';
            alert(`✅ VM ${action} successful!\n\nVM: ${vmName}\nAction: ${action}${note}`);
            
            // Poll for status update directly from vSphere (faster than waiting for Dora)
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Verifying status...';
            let attempts = 0;
            const maxAttempts = 10; // Try for ~30 seconds (10 * 3s)
            
            const pollStatus = async () => {
                attempts++;
                try {
                    // Check real-time status directly from vSphere
                    const statusResponse = await fetch('/api/dora/vm-status', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            vm_name: vmName,
                            environment: environment
                        })
                    });
                    const statusData = await statusResponse.json();
                    
                    // Expected status after action
                    const expectedStatus = {
                        'start': 'poweredOn',
                        'stop': 'poweredOff',
                        'reboot': 'poweredOn'
                    }[action];
                    
                    // Prefer probe_status when available (live OLVM probe), otherwise fall back to status
                    if (statusData.success) {
                        const actual = statusData.probe_status || statusData.status || statusData.dora_status;
                        if (actual === expectedStatus) {
                            // Status confirmed! Ensure the UI remains on the Dora datasource
                            try {
                                currentNodeSource = 'dora';
                                const sourceSelect = document.getElementById('source-select');
                                if (sourceSelect) sourceSelect.value = 'dora';
                            } catch (e) { /* defensive */ }
                            // Reload the table (will use Dora source)
                            await loadNodes();
                            return;
                        }
                    }
                } catch (error) {
                    console.error('Error checking VM status:', error);
                }
                
                if (attempts < maxAttempts) {
                    // Continue polling every 3 seconds
                    setTimeout(pollStatus, 3000);
                } else {
                    // Final reload after max attempts - ensure Dora remains selected
                    try {
                        currentNodeSource = 'dora';
                        const sourceSelect = document.getElementById('source-select');
                        if (sourceSelect) sourceSelect.value = 'dora';
                    } catch (e) { /* defensive */ }
                    await loadNodes();
                }
            };
            
            // Start polling after initial delay
            setTimeout(pollStatus, 3000);
        } else {
            alert(`❌ Failed to ${action} VM:\n${data.error || 'Unknown error'}`);
            button.disabled = false;
            button.innerHTML = originalHTML;
        }
    } catch (error) {
        alert(`❌ Error ${action}ing VM:\n${error.message}`);
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}

async function refreshNodes() {
    // Force refresh from Nomad API (bypass cache) in background
    if (isRefreshing) {
        console.log('Refresh already in progress, skipping...');
        return;
    }
    
    isRefreshing = true;
    updateRefreshIndicator();
    
    try {
        // If current source is Dora, ask Dora discover to refresh and include environment
        let url = '/api/discover/clients?refresh=true';
        if (currentNodeSource === 'dora') {
            const env = document.getElementById('dora-environment-select')?.value || currentDoraEnvironment;
            url = `/api/discover/clients?source=dora&environment=${encodeURIComponent(env)}&refresh=true&_t=${Date.now()}`;
        }
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            // Update nodes array
            // Normalize Dora clients so renderNodesTable picks the Dora rendering path
            if (currentNodeSource === 'dora' && data.output && data.output.clients) {
                nodes = data.output.clients.map(normalizeDoraClient);
                // Re-render with a payload matching renderNodesTable expectation
                renderNodesTable({ cached: false, output: { clients: nodes, stats: data.output.stats || null } });
            } else {
                nodes = data.output.clients;
                renderNodesTable(data);
            }
        } else {
            console.error('Failed to refresh nodes:', data.error);
        }
    } catch (error) {
        console.error('Error refreshing nodes:', error);
    } finally {
        isRefreshing = false;
        updateRefreshIndicator();
    }
}

function updateRefreshIndicator() {
    // Update the refresh indicator if we're on the nodes tab
    if (currentTab === 'nodes' && document.getElementById('nodes-table')) {
        const currentData = {
            cached: false,
            output: {
                clients: nodes,
                stats: null
            }
        };
        renderNodesTable(currentData);
    }
}

async function drainNode(nodeId, nodeName) {
    if (!confirm(`Are you sure you want to drain node "${nodeName}"?\n\nAll allocations will be migrated to other nodes.`)) {
        return;
    }
    
    // Show loading state
    const button = event.target.closest('button');
    const originalHTML = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Draining...';
    
    try {
        const response = await fetch('/api/node/drain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: nodeId, node_name: nodeName })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`✅ Node drain initiated successfully!\n\nNode: ${nodeName}\nID: ${nodeId}\n\nAllocations will be migrated to other nodes.`);
            // Wait a bit for Nomad to update the node status before refreshing
            await new Promise(resolve => setTimeout(resolve, 2000));
            // Force refresh to get real-time data
            await refreshNodes();
        } else {
            alert(`❌ Failed to drain node:\n${data.error || 'Unknown error'}`);
            button.disabled = false;
            button.innerHTML = originalHTML;
        }
    } catch (error) {
        alert(`❌ Error draining node:\n${error.message}`);
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}

async function enableNode(nodeId, nodeName) {
    if (!confirm(`Are you sure you want to recover node "${nodeName}"?\n\nThe node will become eligible for allocations again.`)) {
        return;
    }
    
    // Show loading state
    const button = event.target.closest('button');
    const originalHTML = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Recovering...';
    
    try {
        const response = await fetch('/api/node/eligibility', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: nodeId, node_name: nodeName, enable: true })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`✅ Node recovered successfully!\n\nNode: ${nodeName}\nID: ${nodeId}\n\nThe node is now eligible for allocations.`);
            // Wait a bit for Nomad to update the node status before refreshing
            await new Promise(resolve => setTimeout(resolve, 2000));
            // Force refresh to get real-time data
            await refreshNodes();
        } else {
            alert(`❌ Failed to recover node:\n${data.error || 'Unknown error'}`);
            button.disabled = false;
            button.innerHTML = originalHTML;
        }
    } catch (error) {
        alert(`❌ Error recovering node:\n${error.message}`);
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}

// Dora environment management
async function loadDoraEnvironments() {
    try {
        const response = await fetch('/api/dora/environments');
        const data = await response.json();
        
        if (data.success && data.environments) {
            doraEnvironments = data.environments;
            const select = document.getElementById('dora-environment-select');
            
            if (select) {
                select.innerHTML = data.environments.map(env => 
                    `<option value="${env}" ${env === currentDoraEnvironment ? 'selected' : ''}>${env}</option>`
                ).join('');
            }
        }
    } catch (error) {
        console.error('Error loading Dora environments:', error);
    }
}

// ...existing changeNodeSource handler consolidated later in file...

// Bulk node operations
function toggleSelectAllNodes() {
    const selectAll = document.getElementById('select-all-nodes');
    if (!selectAll) return; // no select-all present (e.g. Dora table)
    const checkboxes = document.querySelectorAll('.node-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
    updateBulkActionButtons();
}

function updateBulkActionButtons() {
    const checkboxes = document.querySelectorAll('.node-checkbox:checked');
    const toolbar = document.getElementById('bulk-actions-toolbar');
    const selectedCount = document.getElementById('selected-count');

    // If toolbar isn't present (for example when rendering Dora VMs), do nothing.
    if (!toolbar || !selectedCount) return;

    if (checkboxes.length > 0) {
        toolbar.style.display = 'block';
        selectedCount.textContent = checkboxes.length;
    } else {
        toolbar.style.display = 'none';
        selectedCount.textContent = '0';
    }
}

function clearNodeSelection() {
    document.querySelectorAll('.node-checkbox').forEach(cb => cb.checked = false);
    const selectAll = document.getElementById('select-all-nodes');
    if (selectAll) selectAll.checked = false;
    updateBulkActionButtons();
}

function getSelectedNodes() {
    const selected = [];
    document.querySelectorAll('.node-checkbox:checked').forEach(cb => {
        selected.push({
            id: cb.value,
            name: cb.dataset.name
        });
    });
    return selected;
}

async function bulkDrainNodes() {
    const selectedNodes = getSelectedNodes();
    
    if (selectedNodes.length === 0) {
        alert('Please select nodes to drain');
        return;
    }
    
    if (!confirm(`Are you sure you want to drain ${selectedNodes.length} node(s)?\n\nThis will migrate all allocations from these nodes.`)) {
        return;
    }
    
    const toolbar = document.getElementById('bulk-actions-toolbar');
    if (toolbar) {
        toolbar.innerHTML = '<div class="card-body py-2"><i class="fas fa-spinner fa-spin"></i> Draining nodes...</div>';
    }
    
    try {
        // Use batch drain endpoint
        const response = await fetch('/api/node/batch-drain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                node_ids: selectedNodes.map(n => ({ id: n.id, name: n.name })),
                deadline: 3600
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Bulk drain completed!\n\n✅ Success: ${data.success_count}/${data.total_count}`);
        } else {
            alert(`Bulk drain completed with errors!\n\n✅ Success: ${data.success_count}/${data.total_count}\n\n${data.message}`);
        }
    } catch (error) {
        console.error('Error in bulk drain:', error);
        alert('Error performing bulk drain operation');
    }
    
    clearNodeSelection();
    await new Promise(resolve => setTimeout(resolve, 2000));
    await refreshNodes();
}

async function bulkRecoverNodes() {
    const selectedNodes = getSelectedNodes();
    
    if (selectedNodes.length === 0) {
        alert('Please select nodes to recover');
        return;
    }
    
    if (!confirm(`Are you sure you want to recover ${selectedNodes.length} node(s)?\n\nThis will make them eligible for allocations again.`)) {
        return;
    }
    
    const toolbar = document.getElementById('bulk-actions-toolbar');
    if (toolbar) {
        toolbar.innerHTML = '<div class="card-body py-2"><i class="fas fa-spinner fa-spin"></i> Recovering nodes...</div>';
    }
    
    try {
        // Use batch recover endpoint
        const response = await fetch('/api/node/batch-recover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                node_ids: selectedNodes.map(n => ({ id: n.id, name: n.name }))
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Bulk recover completed!\n\n✅ Success: ${data.success_count}/${data.total_count}`);
        } else {
            alert(`Bulk recover completed with errors!\n\n✅ Success: ${data.success_count}/${data.total_count}\n\n${data.message}`);
        }
    } catch (error) {
        console.error('Error in bulk recover:', error);
        alert('Error performing bulk recover operation');
    }
    
    clearNodeSelection();
    await new Promise(resolve => setTimeout(resolve, 2000));
    await refreshNodes();
}

function showPercentageDrainModal() {
    // Calculate available healthy nodes (not drained)
    const healthyNodes = nodes.filter(n => n.drain === 'No');
    const totalCount = healthyNodes.length;
    
    document.getElementById('total-nodes-preview').textContent = totalCount;
    
    // Update preview when percentage changes
    const percentageInput = document.getElementById('drain-percentage');
    const updatePreview = () => {
        const percentage = parseInt(percentageInput.value);
        const count = Math.ceil((percentage / 100) * totalCount);
        document.getElementById('drain-count-preview').textContent = count;
    };
    
    percentageInput.addEventListener('input', updatePreview);
    updatePreview();
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('percentageDrainModal'));
    modal.show();
}

async function executePercentageDrain() {
    const percentage = parseInt(document.getElementById('drain-percentage').value);
    const healthyNodes = nodes.filter(n => n.drain === 'No');
    const count = Math.ceil((percentage / 100) * healthyNodes.length);
    
    // Randomly select nodes
    const shuffled = [...healthyNodes].sort(() => 0.5 - Math.random());
    const selectedNodes = shuffled.slice(0, count);
    
    if (selectedNodes.length === 0) {
        alert('No healthy nodes available to drain');
        return;
    }
    
    // Close modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('percentageDrainModal'));
    modal.hide();
    
    if (!confirm(`Drain ${selectedNodes.length} randomly selected nodes (${percentage}% of ${healthyNodes.length} healthy nodes)?`)) {
        return;
    }
    
    try {
        // Use batch drain endpoint
        const response = await fetch('/api/node/batch-drain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                node_ids: selectedNodes.map(n => ({ id: n.id, name: n.name })),
                deadline: 3600
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Percentage drain completed!\n\nDrained ${percentage}% of nodes\n✅ Success: ${data.success_count}/${data.total_count}`);
        } else {
            alert(`Percentage drain completed with errors!\n\n✅ Success: ${data.success_count}/${data.total_count}\n\n${data.message}`);
        }
    } catch (error) {
        console.error('Error in percentage drain:', error);
        alert('Error performing percentage drain operation');
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
    await refreshNodes();
}

// Execute chaos functions
async function loadChaosTypes() {
    try {
        const response = await fetch('/api/chaos-types');
        const data = await response.json();
        
        const select = document.getElementById('chaos-type-select');
        if (!select) {
            return;
        }

        if (Array.isArray(data.chaos_types) && data.chaos_types.length > 0) {
            chaosTypes = data.chaos_types;
            select.innerHTML = '<option value="">Select a chaos type...</option>' +
                data.chaos_types.map(type => `
                    <option value="${type.name}" data-description="${type.description || ''}">
                        ${type.icon} ${type.display_name}
                    </option>
                `).join('');

            if (pendingChaosTypeSelection) {
                select.value = pendingChaosTypeSelection;
                pendingChaosTypeSelection = null;
                updateChaosDescription();
            }
        } else {
            select.innerHTML = '<option value="">No chaos types available</option>';
        }
    } catch (error) {
        console.error('Error loading chaos types:', error);
        const select = document.getElementById('chaos-type-select');
        if (select) {
            select.innerHTML = '<option value="">Failed to load chaos types</option>';
        }
    }
}

function selectChaosType(chaosType) {
    pendingChaosTypeSelection = chaosType;
    showTab('execute');
}

function updateChaosDescription() {
    const select = document.getElementById('chaos-type-select');
    const selectedOption = select.options[select.selectedIndex];
    const description = selectedOption ? selectedOption.getAttribute('data-description') : '';
    document.getElementById('chaos-type-description').textContent = description || '';
    
    // Show/hide k6 options based on selected chaos type
    const chaosType = select.value;
    const k6Options = document.getElementById('k6-options');
    if (k6Options) {
        if (chaosType && chaosType.includes('k6')) {
            k6Options.style.display = 'block';
        } else {
            k6Options.style.display = 'none';
        }
    }
}

function setupEventListeners() {
    // Chaos form submission
    const form = document.getElementById('chaos-form');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const chaosType = document.getElementById('chaos-type-select').value;
            const dryRun = document.getElementById('dry-run-check').checked;
            
            if (!chaosType) {
                alert('Please select a chaos type');
                return;
            }
            
            // Get target based on selected target type (from main branch)
            let targetId = null;
            const targetType = document.querySelector('input[name="target-type"]:checked')?.value || 'manual';
            
            if (targetType === 'manual') {
                targetId = document.getElementById('target-id-input')?.value;
            } else if (targetType === 'service') {
                const serviceSelect = document.getElementById('service-select');
                if (serviceSelect) {
                    const selectedServices = Array.from(serviceSelect.selectedOptions).map(opt => opt.value).filter(v => v !== '');
                    
                    if (selectedServices.length === 0) {
                        alert('Please select at least one service');
                        return;
                    }
                    
                    // If multiple services selected, join them or use the first one
                    targetId = selectedServices.length === 1 ? selectedServices[0] : selectedServices.join(',');
                }
            } else if (targetType === 'node') {
                const nodeSelect = document.getElementById('node-select');
                if (nodeSelect) {
                    const selectedNodes = Array.from(nodeSelect.selectedOptions).map(opt => opt.value).filter(v => v !== '');
                    
                    if (selectedNodes.length === 0) {
                        alert('Please select at least one node');
                        return;
                    }
                    
                    // If multiple nodes selected, join them or use the first one
                    targetId = selectedNodes.length === 1 ? selectedNodes[0] : selectedNodes.join(',');
                }
            }
            // If 'auto', targetId remains null (automatic target selection)
            
            // Collect k6-specific parameters if k6 chaos type is selected (from chaosk6 branch)
            const requestBody = {
                chaos_type: chaosType,
                target_id: targetId || null,
                dry_run: dryRun
            };
            
            if (chaosType && chaosType.includes('k6')) {
                const virtualUsers = document.getElementById('virtual-users')?.value;
                const targetUrl = document.getElementById('target-url')?.value;
                const responseThreshold = document.getElementById('response-threshold')?.value;
                
                if (virtualUsers) requestBody.virtual_users = parseInt(virtualUsers);
                if (targetUrl) requestBody.target_url = targetUrl;
                if (responseThreshold) requestBody.response_threshold = parseInt(responseThreshold);
            }
            
            const resultDiv = document.getElementById('execution-result');
            const outputPre = document.getElementById('execution-output');
            
            resultDiv.style.display = 'block';
            outputPre.textContent = 'Executing experiment...\n';
            
            try {
                const response = await fetch('/api/execute', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    outputPre.textContent = JSON.stringify(data.output, null, 2);
                } else {
                    outputPre.textContent = `Error:\n${data.stderr || data.error}`;
                }
            } catch (error) {
                outputPre.textContent = `Error: ${error.message}`;
            }
        });
    }
    
    // Chaos type selection
    const chaosSelect = document.getElementById('chaos-type-select');
    if (chaosSelect) {
        chaosSelect.addEventListener('change', updateChaosDescription);
    }
    
    // Target type radio button handlers
    const targetTypeRadios = document.querySelectorAll('input[name="target-type"]');
    targetTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const manualContainer = document.getElementById('manual-target-container');
            const serviceContainer = document.getElementById('service-target-container');
            const nodeContainer = document.getElementById('node-target-container');
            
            // Hide all containers
            manualContainer.style.display = 'none';
            serviceContainer.style.display = 'none';
            nodeContainer.style.display = 'none';
            
            // Show selected container and load data if needed
            if (this.value === 'manual') {
                manualContainer.style.display = 'block';
            } else if (this.value === 'service') {
                serviceContainer.style.display = 'block';
                loadServicesDropdown();
            } else if (this.value === 'node') {
                nodeContainer.style.display = 'block';
                loadNodesDropdown();
            }
            // 'auto' shows nothing (automatic target selection)
        });
    });
}

// Reports functions
async function loadReports() {
    const container = document.getElementById('reports-list');
    container.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i></div>';
    
    try {
        const response = await fetch('/api/reports');
        const data = await response.json();
        
        if (data.reports) {
            reports = data.reports;
            renderReportsList(data.reports);
        }
    } catch (error) {
        console.error('Error loading reports:', error);
        container.innerHTML = '<div class="alert alert-danger">Error loading reports</div>';
    }
}

function renderReportsList(reportsList) {
    const container = document.getElementById('reports-list');
    
    if (!container) return;
    
    if (reportsList.length === 0) {
        container.innerHTML = '<div class="text-center text-muted">No reports available</div>';
        return;
    }
    
    container.innerHTML = reportsList.map(report => `
        <div class="card report-card">
            <div class="report-header">
                <div>
                    <h5>${getChaosIcon(report.chaos_type)} ${report.chaos_type}</h5>
                    <small class="text-muted">Run ID: ${report.run_id}</small>
                </div>
                <span class="badge status-badge status-${report.status}">${report.status}</span>
            </div>
            <div class="report-body">
                <div class="row">
                    <div class="col-md-6">
                        <strong>Target:</strong> ${report.target_id || 'N/A'}<br>
                        <strong>Started:</strong> ${formatDate(report.started_at)}<br>
                        <strong>Completed:</strong> ${formatDate(report.completed_at)}
                    </div>
                    <div class="col-md-6 text-end">
                        <button class="btn btn-sm btn-primary" onclick="showReport('${report.run_id}')">
                            <i class="fas fa-eye"></i> View Details
                        </button>
                        ${report.has_html ? `
                            <a href="/reports/${report.run_id}.html" target="_blank" class="btn btn-sm btn-info">
                                <i class="fas fa-external-link-alt"></i> HTML
                            </a>
                        ` : ''}
                        ${report.k6_dashboard ? `
                            <a href="/reports/${report.k6_dashboard}" target="_blank" class="btn btn-sm btn-success">
                                <i class="fas fa-chart-line"></i> View K6 Dashboard
                            </a>
                        ` : ''}
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function refreshReports() {
    loadReports();
    loadNodeOperations();
}

async function loadNodeOperations() {
    try {
        const response = await fetch('/api/node-operations');
        const data = await response.json();
        
        if (!data.success || data.operations.length === 0) {
            document.getElementById('node-operations-list').innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i> No node operations recorded yet
                </div>
            `;
            return;
        }
        
        const operations = data.operations;
        let html = `
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Operation</th>
                            <th>Node</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        operations.forEach(op => {
            const timestamp = new Date(op.timestamp).toLocaleString();
            const typeIcon = op.type === 'drain' ? '⚠️' : '✅';
            const typeBadge = op.type === 'drain' 
                ? '<span class="badge bg-warning">Drain</span>'
                : '<span class="badge bg-success">Recover</span>';
            
            // Handle batch operations
            let statusBadge = '';
            let nodeName = '';
            
            if (op.is_batch) {
                // Batch operation
                const batchIcon = '<i class="fas fa-layer-group"></i>';
                statusBadge = `<span class="badge bg-info">${batchIcon} Batch (${op.node_count} nodes)</span> `;
                if (op.success_count && op.failed_count !== undefined) {
                    statusBadge += `<span class="badge bg-success">${op.success_count} OK</span> `;
                    if (op.failed_count > 0) {
                        statusBadge += `<span class="badge bg-danger">${op.failed_count} Failed</span>`;
                    }
                }
                nodeName = `<span class="text-muted">${op.node_count} nodes</span>`;
            } else {
                // Single node operation
                statusBadge = op.success 
                    ? '<span class="badge bg-success">Success</span>'
                    : '<span class="badge bg-danger">Failed</span>';
                nodeName = `<code>${op.node_name}</code>`;
            }
            
            html += `
                <tr>
                    <td>${timestamp}</td>
                    <td>${typeIcon} ${typeBadge}</td>
                    <td>${nodeName}</td>
                    <td>${statusBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewNodeOperationDetails('${op.operation_id}')">
                            <i class="fas fa-eye"></i> View
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        document.getElementById('node-operations-list').innerHTML = html;
    } catch (error) {
        console.error('Error loading node operations:', error);
        document.getElementById('node-operations-list').innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i> Error loading node operations
            </div>
        `;
    }
}

async function viewNodeOperationDetails(operationId) {
    try {
        // Fetch the operation details
        const response = await fetch('/api/node-operations');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error('Failed to fetch operations');
        }
        
        // Find the specific operation
        const operation = data.operations.find(op => op.operation_id === operationId);
        
        if (!operation) {
            throw new Error('Operation not found');
        }
        
        // Format the details
        const timestamp = new Date(operation.timestamp).toLocaleString();
        const typeIcon = operation.type === 'drain' ? '⚠️' : '✅';
        const typeBadge = operation.type === 'drain' 
            ? '<span class="badge bg-warning">Drain</span>'
            : '<span class="badge bg-success">Recover</span>';
        
        let detailsHTML = `
            <div class="card">
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <h6 class="text-muted">Operation ID</h6>
                            <code>${operation.operation_id}</code>
                        </div>
                        <div class="col-md-6">
                            <h6 class="text-muted">Timestamp</h6>
                            <p>${timestamp}</p>
                        </div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <h6 class="text-muted">Operation Type</h6>
                            <p>${typeIcon} ${typeBadge}</p>
                        </div>
                        <div class="col-md-6">
                            <h6 class="text-muted">Status</h6>
        `;
        
        // Handle batch operations
        if (operation.is_batch) {
            const batchIcon = '<i class="fas fa-layer-group"></i>';
            detailsHTML += `
                            <p>
                                <span class="badge bg-info">${batchIcon} Batch Operation</span>
                                <span class="badge bg-success">${operation.success_count} Success</span>
                                <span class="badge bg-danger">${operation.failed_count} Failed</span>
                            </p>
                        </div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-12">
                            <h6 class="text-muted">Nodes (${operation.node_count} total)</h6>
                            <div class="table-responsive">
                                <table class="table table-sm">
                                    <thead>
                                        <tr>
                                            <th>Node Name</th>
                                            <th>Node ID</th>
                                            <th>Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
            `;
            
            operation.nodes.forEach(node => {
                const nodeStatusBadge = node.success 
                    ? '<span class="badge bg-success">Success</span>'
                    : '<span class="badge bg-danger">Failed</span>';
                detailsHTML += `
                                        <tr>
                                            <td><code>${node.name}</code></td>
                                            <td><code class="small">${node.id}</code></td>
                                            <td>${nodeStatusBadge}</td>
                                        </tr>
                `;
            });
            
            detailsHTML += `
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
            `;
        } else {
            // Single node operation
            const statusBadge = operation.success 
                ? '<span class="badge bg-success">Success</span>'
                : '<span class="badge bg-danger">Failed</span>';
            detailsHTML += `
                            <p>${statusBadge}</p>
                        </div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <h6 class="text-muted">Node Name</h6>
                            <code>${operation.node_name}</code>
                        </div>
                        <div class="col-md-6">
                            <h6 class="text-muted">Node ID</h6>
                            <code class="small">${operation.node_id}</code>
                        </div>
                    </div>
            `;
        }
        
        // Add additional details if available
        if (operation.details && Object.keys(operation.details).length > 0) {
            detailsHTML += `
                    <div class="row mb-3">
                        <div class="col-12">
                            <h6 class="text-muted">Additional Details</h6>
                            <pre class="bg-light p-3 rounded"><code>${JSON.stringify(operation.details, null, 2)}</code></pre>
                        </div>
                    </div>
            `;
        }
        
        detailsHTML += `
                </div>
            </div>
        `;
        
        // Update modal content and show it
        document.getElementById('nodeOperationDetails').innerHTML = detailsHTML;
        const modal = new bootstrap.Modal(document.getElementById('nodeOperationModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error loading operation details:', error);
        alert('Error loading operation details: ' + error.message);
    }
}

async function showReport(runId) {
    console.log('Loading report:', runId);
    
    // Get the modal element
    const modalElement = document.getElementById('reportModal');
    if (!modalElement) {
        console.error('Report modal element not found');
        return;
    }
    
    // Set title
    const titleElement = document.getElementById('reportModalTitle');
    if (titleElement) {
        titleElement.textContent = `Report: ${runId}`;
    }
    
    // Get content elements
    const jsonContent = document.getElementById('report-json-content');
    const markdownContent = document.getElementById('report-markdown-content');
    const htmlContent = document.getElementById('report-html-content');
    
    console.log('Content elements found:', {
        json: !!jsonContent,
        markdown: !!markdownContent,
        html: !!htmlContent
    });
    
    // Set loading state with visible content
    if (jsonContent) {
        jsonContent.textContent = 'Loading JSON data...';
    }
    if (markdownContent) {
        markdownContent.textContent = 'Loading Markdown content...';
    }
    if (htmlContent) {
        htmlContent.innerHTML = `
            <div class="text-center p-5">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-3">Loading HTML report...</p>
            </div>
        `;
    }
    
    // Store current run ID for download/view functions
    window.currentReportRunId = runId;
    
    // Ensure JSON tab is active
    const jsonTab = document.getElementById('json-tab');
    const jsonPane = document.getElementById('json-content');
    if (jsonTab && jsonPane) {
        // Remove active from all tabs
        document.querySelectorAll('#reportTabs .nav-link').forEach(tab => {
            tab.classList.remove('active');
            tab.setAttribute('aria-selected', 'false');
        });
        document.querySelectorAll('#reportTabContent .tab-pane').forEach(pane => {
            pane.classList.remove('show', 'active');
        });
        
        // Activate JSON tab
        jsonTab.classList.add('active');
        jsonTab.setAttribute('aria-selected', 'true');
        jsonPane.classList.add('show', 'active');
        
        console.log('JSON tab activated');
    }
    
    // Show modal with loading state
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal.show();
    
    console.log('Modal shown, starting data fetch...');
    
    // Load JSON
    try {
        console.log('Fetching JSON...');
        const jsonResponse = await fetch(`/api/reports/${runId}?format=json`);
        if (!jsonResponse.ok) {
            throw new Error(`HTTP ${jsonResponse.status}: ${jsonResponse.statusText}`);
        }
        const jsonData = await jsonResponse.json();
        console.log('JSON loaded successfully');
        if (jsonContent) {
            jsonContent.textContent = JSON.stringify(jsonData, null, 2);
        }
    } catch (error) {
        console.error('Error loading JSON report:', error);
        if (jsonContent) {
            jsonContent.textContent = `Error loading JSON report: ${error.message}`;
        }
    }
    
    // Load Markdown
    try {
        console.log('Fetching Markdown...');
        const mdResponse = await fetch(`/api/reports/${runId}?format=markdown`);
        if (!mdResponse.ok) {
            throw new Error(`HTTP ${mdResponse.status}: ${mdResponse.statusText}`);
        }
        const mdData = await mdResponse.json();
        console.log('Markdown loaded successfully');
        if (markdownContent) {
            markdownContent.textContent = mdData.content || 'Not available';
        }
    } catch (error) {
        console.error('Error loading Markdown report:', error);
        if (markdownContent) {
            markdownContent.textContent = `Error loading Markdown: ${error.message}`;
        }
    }
    
    // Load HTML
    try {
        console.log('Fetching HTML...');
        const htmlResponse = await fetch(`/api/reports/${runId}?format=html`);
        if (!htmlResponse.ok) {
            throw new Error(`HTTP ${htmlResponse.status}: ${htmlResponse.statusText}`);
        }
        const htmlData = await htmlResponse.json();
        console.log('HTML loaded successfully');
        if (htmlContent) {
            htmlContent.innerHTML = htmlData.content || '<p class="text-muted">Not available</p>';
        }
    } catch (error) {
        console.error('Error loading HTML report:', error);
        if (htmlContent) {
            htmlContent.innerHTML = `<div class="alert alert-danger">Error loading HTML: ${error.message}</div>`;
        }
    }
    
    console.log('All content loaded');
}

// Report download and view functions
function downloadReport(format) {
    const runId = window.currentReportRunId;
    if (!runId) {
        alert('No report selected');
        return;
    }
    
    // Create a temporary link and trigger download
    const downloadUrl = `/api/reports/${runId}/download?format=${format}`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `chaos-report-${runId}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Show notification
    showNotification(`Downloading ${format.toUpperCase()} report...`, 'info');
}

function viewFullHTMLReport() {
    const runId = window.currentReportRunId;
    if (!runId) {
        alert('No report selected');
        return;
    }
    
    // Open full HTML report in new tab
    const reportUrl = `/api/reports/${runId}/html`;
    window.open(reportUrl, '_blank');
}

// Utility functions
function getChaosIcon(chaosType) {
    const icons = {
        'cpu_hog': '🔥',
        'memory_hog': '💾',
        'network_latency': '🐌',
        'packet_loss': '📦',
        'host_down': '💀',
        'disk_io': '💿'
    };
    return icons[chaosType] || '⚡';
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Auto-refresh functionality
function startAutoRefresh() {
    console.log('🔄 Starting auto-refresh (every 30 seconds)');
    
    // Clear any existing interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
    
    // Set up new interval
    autoRefreshInterval = setInterval(() => {
        if (!isRefreshing) {
            backgroundRefresh();
        }
    }, AUTO_REFRESH_INTERVAL);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('⏸️  Auto-refresh stopped');
    }
}

async function backgroundRefresh() {
    console.log('🔄 Background refresh triggered');
    
    // Refresh data based on current tab
    switch (currentTab) {
        case 'dashboard':
            await backgroundRefreshDashboard();
            break;
        case 'nodes':
            await refreshNodes();
            break;
        case 'reports':
            await backgroundRefreshReports();
            break;
        default:
            break;
    }
}

async function backgroundRefreshDashboard() {
    try {
        // Silently update statistics without showing loading indicators
        await Promise.all([
            loadNodeStats(),
            loadRecentExperiments(),
            loadChaosTypesSummary()
        ]);
        console.log('✅ Dashboard refreshed in background');
    } catch (error) {
        console.error('Background refresh error:', error);
    }
}

async function backgroundRefreshReports() {
    try {
        const response = await fetch('/api/reports');
        const data = await response.json();
        
        if (data.reports) {
            reports = data.reports;
            // Only update if we're still on reports tab
            if (currentTab === 'reports') {
                const container = document.getElementById('reports-list');
                if (container) {
                    renderReportsList(data.reports);
                }
            }
            console.log('✅ Reports refreshed in background');
        }
    } catch (error) {
        console.error('Background reports refresh error:', error);
    }
}

// Toggle auto-refresh (for user control)
function toggleAutoRefresh() {
    const toggle = document.getElementById('auto-refresh-toggle');
    
    if (!toggle) return;
    
    autoRefreshEnabled = toggle.checked;
    localStorage.setItem('autoRefreshEnabled', autoRefreshEnabled);
    
    if (autoRefreshEnabled) {
        startAutoRefresh();
        console.log('Auto-refresh enabled');
    } else {
        stopAutoRefresh();
        console.log('Auto-refresh disabled');
    }
}

// Manual refresh button handler
async function manualRefresh(event) {
    // Make event optional (top-nav calls may not pass event)
    const button = (event && event.target) ? event.target.closest('button') : document.querySelector('button[onclick*="manualRefresh"]');
    const icon = button ? button.querySelector('i') : null;

    // Capture UI state to preserve across refresh
    const nodesSearchInput = document.getElementById('nodes-search-input');
    const searchTerm = nodesSearchInput ? nodesSearchInput.value : '';
    const checkedCheckboxes = Array.from(document.querySelectorAll('.node-checkbox:checked'));
    const checkedIds = checkedCheckboxes.map(cb => cb.value);
    const checkedNames = checkedCheckboxes.map(cb => (cb.dataset && cb.dataset.name) ? cb.dataset.name : cb.getAttribute('data-name'));
    const nodesTableElement = document.getElementById('nodes-table');
    const scrollTop = nodesTableElement ? nodesTableElement.scrollTop : 0;

    // Add spinning animation if we have a button/icon
    if (icon) icon.classList.add('fa-spin');
    if (button) button.disabled = true;

    try {
        // Refresh all data based on current tab
        const activeTab = document.querySelector('.nav-link.active')?.dataset.tab || 'dashboard';

        switch(activeTab) {
            case 'dashboard':
            case 'nodes':
                // If nodes tab and Dora source, pause the background updater while we refresh
                if (currentNodeSource === 'dora') stopDoraStatusUpdater();
                await refreshNodes();
                if (currentNodeSource === 'dora') startDoraStatusUpdater();
                break;
            case 'execute':
                await loadChaosTypes();
                break;
            case 'reports':
                await refreshReports();
                break;
        }

        // Restore preserved UI state
        // Restore checked checkboxes: try by ID first, then fallback to matching by node name
        if ((checkedIds && checkedIds.length > 0) || (checkedNames && checkedNames.length > 0)) {
            console.log('manualRefresh: restoring selections', { checkedIds, checkedNames });
            // First, try to restore by ID
            checkedIds.forEach(id => {
                const cb = document.querySelector(`.node-checkbox[value="${id}"]`);
                console.log('manualRefresh: try restore by id', id, !!cb);
                if (cb) {
                    cb.checked = true;
                    try { cb.setAttribute('checked', 'checked'); } catch (e) {}
                    try { cb.dispatchEvent(new Event('change')); } catch (e) {}
                    console.log('manualRefresh: restored by id', id);
                }
            });

            // Then attempt to restore by node name for any selections that couldn't be restored by ID
            checkedNames.forEach(name => {
                let cbByName = document.querySelector(`.node-checkbox[data-name="${name}"]`);
                console.log('manualRefresh: try restore by name', name, !!cbByName);
                if (cbByName) {
                    cbByName.checked = true;
                    try { cbByName.setAttribute('checked', 'checked'); } catch (e) {}
                    try { cbByName.dispatchEvent(new Event('change')); } catch (e) {}
                    console.log('manualRefresh: restored by name', name);
                    return;
                }

                // Fallback: try finding a row where a cell contains the node name text
                const rows = document.querySelectorAll('#nodes-table tr');
                rows.forEach(r => {
                    if (r.textContent && r.textContent.includes(name)) {
                        const cb = r.querySelector('.node-checkbox');
                        console.log('manualRefresh: fallback matched row for', name, !!cb);
                        if (cb) {
                            cb.checked = true;
                            try { cb.setAttribute('checked', 'checked'); } catch (e) {}
                            try { cb.dispatchEvent(new Event('change')); } catch (e) {}
                            console.log('manualRefresh: restored by fallback name', name);
                        }
                    }
                });
            });

            // Ensure toolbar reflects restored selection
            updateBulkActionButtons();
        }

        // Restore search value and reapply filter
        if (nodesSearchInput) {
            nodesSearchInput.value = searchTerm;
            if (searchTerm) filterNodesTable();
        }

        // Restore scroll position
        const newNodesTable = document.getElementById('nodes-table');
        if (newNodesTable) {
            try { newNodesTable.scrollTop = scrollTop; } catch (e) { /* ignore */ }
        }

        // Show success feedback
        const originalText = button ? button.innerHTML : null;
        if (button) button.innerHTML = '<i class="fas fa-check"></i> Refreshed!';
        setTimeout(() => {
            if (button && originalText !== null) button.innerHTML = originalText;
            if (button) button.disabled = false;
            if (icon) icon.classList.remove('fa-spin');
        }, 1500);

    } catch (error) {
        console.error('Manual refresh error:', error);
        icon.classList.remove('fa-spin');
        button.disabled = false;
        alert('Error refreshing data');
    }
}

async function recoverAllDrainedNodes() {
    // Get all drained nodes
    const drainedNodes = nodes.filter(n => n.drain === 'Yes' || n.drain === 'Draining...');
    
    if (drainedNodes.length === 0) {
        alert('No drained nodes found');
        return;
    }
    
    if (!confirm(`Recover ${drainedNodes.length} drained node(s)?\n\nThis will enable scheduling and remove drain status from all drained nodes.`)) {
        return;
    }
    
    try {
        // Use batch recover endpoint
        const response = await fetch('/api/node/batch-recover', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                node_ids: drainedNodes.map(n => ({ id: n.id, name: n.name }))
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Bulk recovery completed!\n\n✅ Success: ${data.success_count}/${data.total_count}`);
        } else {
            alert(`Bulk recovery completed with errors!\n\n✅ Success: ${data.success_count}/${data.total_count}\n\n${data.message}`);
        }
    } catch (error) {
        console.error('Error in bulk recovery:', error);
        alert('Error performing bulk recovery operation');
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
    await refreshNodes();
}

// Filter nodes table by search input
function filterNodesTable() {
    const searchInput = document.getElementById('nodes-search-input');
    const searchTerm = searchInput.value.toLowerCase();
    const table = document.querySelector('#nodes-table table tbody');
    
    if (!table) return;
    
    const rows = table.querySelectorAll('tr');
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}

// Filter chaos options (types and targets)
function filterChaosOptions() {
    const searchInput = document.getElementById('chaos-search-input');
    const searchTerm = searchInput.value.toLowerCase();
    
    // Filter chaos type select options
    const chaosTypeSelect = document.getElementById('chaos-type-select');
    if (chaosTypeSelect) {
        Array.from(chaosTypeSelect.options).forEach(option => {
            if (option.value === '') return; // Skip placeholder
            const text = option.textContent.toLowerCase();
            option.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    }
    
    // Filter service select options
    const serviceSelect = document.getElementById('service-select');
    if (serviceSelect) {
        const parent = serviceSelect.parentElement && serviceSelect.parentElement.parentElement;
        if (parent && parent.style && parent.style.display !== 'none') {
            Array.from(serviceSelect.options).forEach(option => {
                if (option.value === '') return; // Skip placeholder
                const text = option.textContent.toLowerCase();
                option.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        }
    }
    
    // Filter node select options
    const nodeSelect = document.getElementById('node-select');
    if (nodeSelect) {
        const parent = nodeSelect.parentElement && nodeSelect.parentElement.parentElement;
        if (parent && parent.style && parent.style.display !== 'none') {
            Array.from(nodeSelect.options).forEach(option => {
                if (option.value === '') return; // Skip placeholder
                const text = option.textContent.toLowerCase();
                option.style.display = text.includes(searchTerm) ? '' : 'none';
            });
        }
    }
}

// Load services into dropdown
async function loadServicesDropdown() {
    const serviceSelect = document.getElementById('service-select');
    serviceSelect.innerHTML = '<option value="">Loading services...</option>';
    
    try {
        const response = await fetch('/api/discover/services');
        const data = await response.json();
        
        console.log('Services API response:', data);
        
        // Check multiple response formats for compatibility
        let services = [];
        
        if (data.success && data.output && data.output.targets) {
            services = data.output.targets;
        } else if (data.output && Array.isArray(data.output.services)) {
            services = data.output.services;
        } else if (Array.isArray(data.services)) {
            services = data.services;
        }
        
        if (services.length > 0) {
            serviceSelect.innerHTML = '';
            services.forEach(service => {
                const option = document.createElement('option');
                option.value = service.id || service.ID || service.name || service.Name;
                option.textContent = `${service.name || service.Name}${(service.type || service.Type) ? ' (' + (service.type || service.Type) + ')' : ''}`;
                serviceSelect.appendChild(option);
            });
            console.log(`✅ Loaded ${services.length} services`);
        } else {
            console.warn('No services found in response:', data);
            serviceSelect.innerHTML = '<option value="">No services found</option>';
        }
    } catch (error) {
        console.error('Error loading services:', error);
        serviceSelect.innerHTML = '<option value="">Error loading services</option>';
    }
}

// Load nodes into dropdown for target selection

async function executeRandomChaosOnNode() {
    if (!confirm('Execute random chaos on a random node?\n\nThis will select a random chaos type and random node target!')) {
        return;
    }
    
    try {
        // Load nodes
        const nodesResponse = await fetch('/api/discover/clients');
        const nodesData = await nodesResponse.json();
        
        if (!nodesData.success || !nodesData.output || !nodesData.output.clients || nodesData.output.clients.length === 0) {
            alert('No nodes available for random chaos');
            return;
        }
        
        const clients = nodesData.output.clients;
        // Pick random node
        const randomNode = clients[Math.floor(Math.random() * clients.length)];
        
        // Pick random chaos type
        if (chaosTypes.length === 0) {
            await loadChaosTypes();
        }
        const randomChaosType = chaosTypes[Math.floor(Math.random() * chaosTypes.length)];
        
        // Show what will be executed
        const dryRun = document.getElementById('dry-run-check').checked;
        alert(`🎲 Random Selection:\n\nChaos: ${randomChaosType.name}\nTarget: ${randomNode.name}\nMode: ${dryRun ? 'DRY RUN' : 'LIVE'}`);
        
        // Execute
        await executeChaos(randomChaosType.name, randomNode.id, dryRun);
        
    } catch (error) {
        console.error('Error executing random chaos on node:', error);
        alert('Error executing random chaos on node');
    }
}

async function executeRandomChaosAnywhere() {
    if (!confirm('🔥 COMPLETE RANDOM CHAOS! 🔥\n\nThis will randomly select:\n- A chaos type\n- Either a service OR node target\n- Completely at random!\n\nAre you sure?')) {
        return;
    }
    
    // Randomly choose service or node
    const targetType = Math.random() < 0.5 ? 'service' : 'node';
    
    if (targetType === 'service') {
        await executeRandomChaosOnService();
    } else {
        await executeRandomChaosOnNode();
    }
}

// Helper function to execute chaos with given parameters
async function executeChaos(chaosType, targetId, dryRun) {
    const formData = {
        chaos_type: chaosType,
        target_id: targetId,
        dry_run: dryRun,
        // Enable metrics collection by default for Web UI executions
        collect_metrics: true,
        metrics_duration: 60,  // 60 seconds
        metrics_interval: 5    // 5 second intervals
    };
    
    try {
        const response = await fetch('/api/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        // Show formatted result
        displayExecutionResult(data, chaosType, targetId, dryRun);
        
    } catch (error) {
        console.error('Error executing chaos:', error);
        alert('Error executing chaos experiment');
    }
}

// Format and display execution results
function displayExecutionResult(data, chaosType, targetId, dryRun) {
    const resultDiv = document.getElementById('execution-result');
    const outputPre = document.getElementById('execution-output');
    
    let formattedOutput = '';
    
    if (data.success) {
        formattedOutput = `
╔══════════════════════════════════════════════════════════════════════════════╗
║                      ✅ CHAOS EXPERIMENT SUCCESSFUL                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 EXPERIMENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Chaos Type:     ${chaosType}
  • Target:         ${targetId || 'Auto-selected'}
  • Mode:           ${dryRun ? '🔍 DRY RUN (Simulated)' : '🔥 LIVE EXECUTION'}
  • Status:         SUCCESS
  • Timestamp:      ${new Date().toLocaleString()}

📊 EXECUTION OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
${JSON.stringify(data.output, null, 2)}

💾 REPORT STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Detailed report has been generated
  ✓ Check the Reports tab for full analysis
  ✓ All critical information has been logged
`;
        
        outputPre.textContent = formattedOutput;
        resultDiv.style.display = 'block';
        
        // Show success notification
        showNotification('success', '✅ Chaos experiment executed successfully!', 
                        'Check the Reports tab for detailed analysis');
        
    } else {
        formattedOutput = `
╔══════════════════════════════════════════════════════════════════════════════╗
║                      ❌ CHAOS EXPERIMENT FAILED                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 EXPERIMENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Chaos Type:     ${chaosType}
  • Target:         ${targetId || 'Auto-selected'}
  • Mode:           ${dryRun ? '🔍 DRY RUN (Simulated)' : '🔥 LIVE EXECUTION'}
  • Status:         FAILED
  • Timestamp:      ${new Date().toLocaleString()}

❌ ERROR DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
${data.stderr || data.error || data.message || 'Unknown error'}

📝 RAW OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
${JSON.stringify(data, null, 2)}
`;
        
        outputPre.textContent = formattedOutput;
        resultDiv.style.display = 'block';
        
        // Show error notification
        showNotification('error', '❌ Chaos experiment failed', 
                        data.stderr || data.error || data.message || 'Unknown error');
    }
}

// Show notification (can be expanded to use toast notifications)
function showNotification(type, title, message) {
    const alertType = type === 'success' ? 'success' : 'danger';
    alert(`${title}\n\n${message}`);
}

// Toggle select all services
function toggleSelectAllServices() {
    const checkbox = document.getElementById('select-all-services');
    const select = document.getElementById('service-select');
    
    if (checkbox.checked) {
        // Select all options
        Array.from(select.options).forEach(option => {
            if (option.value !== '') {
                option.selected = true;
            }
        });
    } else {
        // Deselect all
        Array.from(select.options).forEach(option => {
            option.selected = false;
        });
    }
}

// Toggle select all options in the node-target <select> (used on Execute tab)
function toggleSelectAllNodeOptions() {
    const checkbox = document.getElementById('select-all-node-targets');
    const select = document.getElementById('node-select');
    if (!checkbox || !select) return;
    
    if (checkbox.checked) {
        // Select all options
        Array.from(select.options).forEach(option => {
            if (option.value !== '') {
                option.selected = true;
            }
        });
    } else {
        // Deselect all
        Array.from(select.options).forEach(option => {
            option.selected = false;
        });
    }
}

// Handle node source changes (Nomad vs Dora)
function changeNodeSource() {
    const sourceSelect = document.getElementById('source-select');
    const recoverAllBtn = document.getElementById('recover-all-btn');
    const doraEnvContainer = document.getElementById('dora-environment-container');
    
    if (!sourceSelect) return;
    // When the user interacts with the selector, prefer the DOM value. Only
    // fall back to internal state if the select is not present.
    const source = sourceSelect ? sourceSelect.value : (currentNodeSource || 'nomad');
    currentNodeSource = source;
    if (sourceSelect.value !== source) sourceSelect.value = source;
    
    // Show/hide recover all button based on source
    if (recoverAllBtn) {
        if (source === 'nomad') {
            recoverAllBtn.style.display = 'inline-block';
        } else {
            recoverAllBtn.style.display = 'none';
        }
    }
    
    // Show/hide Dora environment selector and manage updater
    if (doraEnvContainer) {
        if (source === 'dora') {
            doraEnvContainer.style.display = 'block';
            // Ensure environment list is loaded when switching to Dora
            loadDoraEnvironments();
            // Start the Dora background updater
            startDoraStatusUpdater();
        } else {
            doraEnvContainer.style.display = 'none';
            // Stop the Dora background updater
            stopDoraStatusUpdater();
        }
    }
    
    // Reload nodes with new source (will use currentNodeSource)
    loadNodes();
}

// Load Dora environments into dropdown
async function loadDoraEnvironments() {
    const envSelect = document.getElementById('dora-environment-select');
    if (!envSelect) return;
    
    // Check if already loaded
    if (envSelect.options.length > 1) return;
    
    try {
        const response = await fetch('/api/dora/environments');
        const data = await response.json();
        
        if (data.success && data.environments && data.environments.length > 0) {
            envSelect.innerHTML = '';
            data.environments.forEach(env => {
                const option = document.createElement('option');
                option.value = env;
                option.textContent = env;
                envSelect.appendChild(option);
            });
            console.log(`✅ Loaded ${data.environments.length} Dora environments`);
        } else {
            envSelect.innerHTML = '<option value="">No environments found</option>';
        }
    } catch (error) {
        console.error('Error loading Dora environments:', error);
        envSelect.innerHTML = '<option value="">Error loading environments</option>';
    }
}
// Version check: Fri 10 Oct 2025 04:13:37 PM IST
console.log('TEST: JavaScript updated at Fri 10 Oct 2025 04:16:56 PM IST');

// Load nodes into dropdown for target selection - combining Nomad nodes and DORA VMs
async function loadNodesDropdown() {
    const nodeSelect = document.getElementById('node-select');
    nodeSelect.innerHTML = '<option value="">Loading nodes...</option>';
    
    try {
        // Load Nomad nodes
        const nomadResponse = await fetch('/api/discover/clients');
        const nomadData = await nomadResponse.json();
        
        // Load DORA VMs (using default Dev1 environment)
        const environment = document.getElementById('dora-environment-select')?.value || 'Dev1';
        const doraResponse = await fetch(`/api/discover/clients?source=dora&environment=${environment}`);
        const doraData = await doraResponse.json();
        
        nodeSelect.innerHTML = '<option value="">Select a node...</option>';
        
        // Add Nomad nodes with Nomad icon
        if (nomadData.success && nomadData.output && nomadData.output.clients) {
            const nomadClients = nomadData.output.clients;
            nomadClients.forEach(node => {
                const option = document.createElement('option');
                option.value = node.name;  // Use hostname
                option.textContent = `⬢ ${node.name} (${node.status})`;
                option.setAttribute('data-type', 'nomad');
                nodeSelect.appendChild(option);
            });
        }
        
        // Add DORA VMs with VM icon
        if (doraData.success && doraData.output && doraData.output.clients) {
            const doraVMs = doraData.output.clients;
            doraVMs.forEach(vm => {
                const option = document.createElement('option');
                option.value = vm.name;  // Use VM hostname
                option.textContent = `💻 ${vm.name} (${vm.status || 'VM'})`;
                option.setAttribute('data-type', 'dora');
                nodeSelect.appendChild(option);
            });
        }
        
        console.log('[Combined Nodes] Combined Nomad nodes and DORA VMs in dropdown');
    } catch (error) {
        console.error('Error loading combined nodes:', error);
        nodeSelect.innerHTML = '<option value="">Error loading nodes</option>';
    }
}
