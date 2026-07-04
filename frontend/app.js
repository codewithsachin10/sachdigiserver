// SachDeploy v2.0 Enterprise Application Logic
let currentUser = null;
let activeTab = 'projects';
let ws = null;
let reconnectTimer = null;
let activeDeployProjectId = null;

// DOM Elements
const authScreen = document.getElementById('auth-screen');
const appScreen = document.getElementById('app-screen');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');
const userDisplay = document.getElementById('user-display');
const tabViews = document.querySelectorAll('.tab-view');
const navItems = document.querySelectorAll('.nav-item');

// --- Helper: Robust API Fetch with Authorization Bearer Token & Error Handling ---
async function apiFetch(url, options = {}) {
    const token = localStorage.getItem('sach_token');
    const headers = options.headers || {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    options.headers = headers;
    options.credentials = 'include'; // Send cookies as fallback

    try {
        const res = await fetch(url, options);
        if (res.status === 401 && !url.includes('/api/login')) {
            // Session expired or unauthorized
            console.warn('[SachDeploy] Unauthorized (401). Redirecting to login.');
            localStorage.removeItem('sach_token');
            if (ws) { try { ws.close(); } catch(e){} }
            authScreen.classList.remove('hidden');
            appScreen.classList.add('hidden');
        }
        return res;
    } catch (err) {
        console.error(`[SachDeploy] Network error calling ${url}:`, err);
        throw err;
    }
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

function setupEventListeners() {
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const u = document.getElementById('username').value.trim();
            const p = document.getElementById('password').value;
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            const origBtnText = submitBtn.textContent;

            if (loginError) loginError.classList.add('hidden');
            submitBtn.disabled = true;
            submitBtn.textContent = 'Signing in... ⏳';

            try {
                const res = await apiFetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: u, password: p })
                });

                if (res.ok) {
                    const data = await res.json();
                    if (data.token) {
                        localStorage.setItem('sach_token', data.token);
                    }
                    if (loginError) loginError.classList.add('hidden');
                    showToast('✅ Welcome to SachDeploy Enterprise!', 'info');
                    window.location.href = '/';
                } else if (res.status === 401 || res.status === 403) {
                    if (loginError) {
                        loginError.innerHTML = '❌ Invalid credentials. Default is <code class="text-white">admin</code> / <code class="text-white">sachdeploy</code>';
                        loginError.classList.remove('hidden');
                    }
                } else {
                    const errData = await res.json().catch(() => ({}));
                    if (loginError) {
                        loginError.textContent = errData.detail || `Server Error (${res.status})`;
                        loginError.classList.remove('hidden');
                    }
                }
            } catch (err) {
                if (loginError) {
                    loginError.textContent = '❌ Cannot connect to backend server. Is Docker container running?';
                    loginError.classList.remove('hidden');
                }
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = origBtnText;
            }
        });
    }

    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logoutUser);
    }
}

async function logoutUser() {
    try { await apiFetch('/api/logout', { method: 'POST' }); } catch(e) {}
    localStorage.removeItem('sach_token');
    if (ws) { try { ws.close(); } catch(e){} }
    window.location.href = '/login.html';
}

async function checkAuth() {
    const isLoginPage = window.location.pathname.endsWith('/login.html') || window.location.pathname.endsWith('/login');
    try {
        const res = await apiFetch('/api/me');
        if (res && res.ok) {
            currentUser = await res.json();
            const userEl = document.getElementById('user-display');
            if (userEl) userEl.textContent = currentUser.username || 'admin';
            
            if (isLoginPage) {
                window.location.href = '/';
                return;
            }
            if (authScreen) authScreen.classList.add('hidden');
            if (appScreen) appScreen.classList.remove('hidden');
            
            initWebSocket();
            initCurrentPage();
        } else {
            if (!isLoginPage) {
                window.location.href = '/login.html';
            }
        }
    } catch (e) {
        if (!isLoginPage) {
            window.location.href = '/login.html';
        }
    }
}

function initCurrentPage() {
    const path = window.location.pathname;
    if (path === '/' || path === '/index.html' || path === '/dashboard.html' || path === '/dashboard') {
        initDashboardPage();
    } else if (path.includes('projects')) {
        loadProjects();
    } else if (path.includes('deployments')) {
        loadDeployments();
    } else if (path.includes('marketplace')) {
        loadMarketplace();
    } else if (path.includes('containers')) {
        loadContainers();
    } else if (path.includes('volumes')) {
        loadVolumes();
    } else if (path.includes('networks')) {
        loadNetworks();
    } else if (path.includes('monitoring')) {
        initMonitoringPage();
    } else if (path.includes('terminal')) {
        if (typeof initTerminalView === 'function') initTerminalView();
    } else if (path.includes('settings')) {
        loadSettings();
    } else if (path.includes('support')) {
        loadBackups();
    }
}

// --- WebSocket Management ---
function initWebSocket() {
    if (ws) {
        try { ws.close(); } catch(e){}
    }
    const token = localStorage.getItem('sach_token') || '';
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${proto}//${location.host}/ws/events?token=${encodeURIComponent(token)}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('[SachDeploy] WebSocket connected');
        const dot = document.getElementById('ws-status-dot');
        if (dot) {
            dot.classList.remove('bg-red-500');
            dot.classList.add('bg-green-500');
        }
        if (reconnectTimer) clearInterval(reconnectTimer);
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWsMessage(msg);
        } catch (e) { console.error('WS parse error:', e); }
    };

    ws.onclose = () => {
        const dot = document.getElementById('ws-status-dot');
        if (dot) {
            dot.classList.remove('bg-green-500');
            dot.classList.add('bg-red-500');
        }
        reconnectTimer = setTimeout(initWebSocket, 4000);
    };
}

function handleWsMessage(msg) {
    if (msg.type === 'telemetry') {
        updateTopbarTelemetry(msg.data);
        if (activeTab === 'server') renderServerStats(msg.data);
    } else if (msg.type === 'status_update') {
        refreshCurrentTab();
    } else if (msg.type === 'deploy_step') {
        updateDeployProgressModal(msg);
    } else if (msg.type === 'notification') {
        showToast(msg.message, 'info');
    }
}

function updateTopbarTelemetry(data) {
    if (!data) return;
    const cpuEl = document.getElementById('top-cpu');
    if (cpuEl) cpuEl.textContent = `${data.cpu_percent}%`;
    const ramEl = document.getElementById('top-ram');
    if (ramEl) ramEl.textContent = `${data.ram_percent}%`;
    const diskEl = document.getElementById('top-disk');
    if (diskEl) diskEl.textContent = `${data.disk_percent}%`;
    const tempEl = document.getElementById('top-temp');
    if (tempEl) tempEl.textContent = `${data.temperature}°C`;
    const tsEl = document.getElementById('top-tailscale');
    if (tsEl) tsEl.textContent = data.tailscale_ip || 'N/A';

    // Update Monitoring Page metrics if present
    const monCpu = document.getElementById('mon-cpu-val');
    if (monCpu) monCpu.textContent = `${data.cpu_percent}%`;
    const monRam = document.getElementById('mon-ram-val');
    if (monRam) monRam.textContent = `${data.ram_percent}%`;
    const monDisk = document.getElementById('mon-disk-val');
    if (monDisk) monDisk.textContent = `${data.disk_percent}%`;

    // Update Server stats if elements present
    renderServerStats(data);
}

// --- Navigation & Page Loaders ---
function switchTab(tabName) {
    if (tabName === 'projects') window.location.href = '/projects.html';
    else if (tabName === 'containers') window.location.href = '/containers.html';
    else if (tabName === 'marketplace') window.location.href = '/marketplace.html';
    else if (tabName === 'terminal') window.location.href = '/terminal.html';
    else if (tabName === 'files') window.location.href = '/settings.html';
    else if (tabName === 'backups') window.location.href = '/support.html';
    else if (tabName === 'server') window.location.href = '/monitoring.html';
    else if (tabName === 'settings') window.location.href = '/settings.html';
    else window.location.href = '/';
}

function refreshCurrentTab() {
    initCurrentPage();
}

function initDashboardPage() {
    fetchTelemetryNow();
    setInterval(fetchTelemetryNow, 3000);
    loadProjects();
}

function initMonitoringPage() {
    fetchTelemetryNow();
    setInterval(fetchTelemetryNow, 2000);
}

async function loadDeployments() {
    try {
        const res = await apiFetch('/api/projects');
        if (!res || !res.ok) return;
        const projects = await res.json();
    } catch(e) {}
}

async function loadVolumes() {
    try {
        const res = await apiFetch('/api/docker/volumes');
        if (!res || !res.ok) return;
        const volumes = await res.json();
        const tbody = document.getElementById('volumes-tbody');
        if (!tbody) return;
        tbody.innerHTML = (volumes || []).map(v => `
            <tr class="border-b border-white/5 hover:bg-white/[0.02] font-mono text-xs">
                <td class="py-3 px-6 text-white font-bold">${v.name}</td>
                <td class="py-3 px-6 text-gray-300">${v.driver || 'local'}</td>
                <td class="py-3 px-6 text-gray-400">${v.scope || 'local'}</td>
                <td class="py-3 px-6 text-gray-400">${v.created || 'N/A'}</td>
                <td class="py-3 px-6 text-right">
                    <button onclick="removeVolume('${v.name}')" class="px-2.5 py-1 bg-red-500/20 text-red-400 rounded border border-red-500/30 hover:bg-red-500/30">Remove</button>
                </td>
            </tr>
        `).join('') || '<tr><td colspan="5" class="py-6 text-center text-gray-500">No volumes found</td></tr>';
    } catch(e) {}
}

async function removeVolume(name) {
    if (!confirm(`Remove Docker volume '${name}'?`)) return;
    await apiFetch(`/api/docker/volumes/${encodeURIComponent(name)}`, { method: 'DELETE' });
    loadVolumes();
}

async function loadNetworks() {
    try {
        const res = await apiFetch('/api/docker/networks');
        if (!res || !res.ok) return;
        const networks = await res.json();
        const tbody = document.getElementById('networks-tbody');
        if (!tbody) return;
        tbody.innerHTML = (networks || []).map(n => `
            <tr class="border-b border-white/5 hover:bg-white/[0.02] font-mono text-xs">
                <td class="py-3 px-6 text-white font-bold">${n.name}</td>
                <td class="py-3 px-6 text-gray-400">${(n.id || '').substring(0, 12)}</td>
                <td class="py-3 px-6 text-gray-300">${n.driver || 'bridge'}</td>
                <td class="py-3 px-6 text-gray-400">${n.scope || 'local'}</td>
                <td class="py-3 px-6 text-gray-400">${n.subnet || 'N/A'}</td>
                <td class="py-3 px-6 text-right">
                    ${['bridge', 'host', 'none'].includes(n.name) ? '<span class="text-gray-600 text-[10px]">System</span>' : `<button onclick="removeNetwork('${n.id}')" class="px-2.5 py-1 bg-red-500/20 text-red-400 rounded border border-red-500/30 hover:bg-red-500/30">Remove</button>`}
                </td>
            </tr>
        `).join('') || '<tr><td colspan="6" class="py-6 text-center text-gray-500">No networks found</td></tr>';
    } catch(e) {}
}

async function removeNetwork(id) {
    if (!confirm('Remove this Docker network?')) return;
    await apiFetch(`/api/docker/networks/${encodeURIComponent(id)}`, { method: 'DELETE' });
    loadNetworks();
}


// --- Projects & Deployments ---
async function loadProjects() {
    try {
        const res = await apiFetch('/api/projects');
        if (!res || !res.ok) return;
        const projects = await res.json();
        const grid = document.getElementById('projects-grid');
        if (!grid) return;
        
        if (projects.length === 0) {
            grid.innerHTML = `
                <div class="col-span-full py-16 text-center text-gray-500 border border-dashed border-gray-800 rounded-xl">
                    <p class="text-lg font-medium mb-2">No Applications Deployed</p>
                    <p class="text-sm">Upload a ZIP file or connect a Git repository to get started.</p>
                </div>`;
            return;
        }

        grid.innerHTML = projects.map(p => {
            const badgeClass = p.status === 'running' ? 'badge-running' : (p.status === 'building' ? 'badge-building' : 'badge-stopped');
            const portLink = p.port ? `<a href="http://${location.hostname}:${p.port}" target="_blank" class="text-indigo-400 hover:underline flex items-center gap-1">:${p.port} ↗</a>` : 'N/A';
            
            return `
            <div class="glass-card p-5 flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between mb-3">
                        <span class="font-bold text-lg text-white">${p.name}</span>
                        <span class="badge ${badgeClass}">${p.status}</span>
                    </div>
                    <div class="text-xs text-gray-400 space-y-1 mb-4 font-mono">
                        <div>Type: <span class="text-gray-200">${(p.type || 'unknown').toUpperCase()}</span></div>
                        <div>Source: <span class="text-gray-200 truncate inline-block max-w-[180px] align-bottom">${p.source || 'N/A'}</span></div>
                        <div class="flex items-center gap-2">Port: ${portLink}</div>
                    </div>
                </div>
                <div class="pt-3 border-t border-gray-800 flex flex-wrap gap-2">
                    ${p.status === 'running' ? 
                        `<button onclick="projectAction('${p.id}', 'stop')" class="px-2.5 py-1 text-xs bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded border border-red-500/30 font-medium">Stop</button>` :
                        `<button onclick="projectAction('${p.id}', 'start')" class="px-2.5 py-1 text-xs bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded border border-green-500/30 font-medium">Start</button>`
                    }
                    <button onclick="projectAction('${p.id}', 'restart')" class="px-2.5 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded text-gray-300 font-medium">Restart</button>
                    <button onclick="openLogsModal('${p.id}', '${p.name}')" class="px-2.5 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded text-gray-300 font-medium">Logs</button>
                    <button onclick="openEnvModal('${p.id}', '${p.name}')" class="px-2.5 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded text-gray-300 font-medium">Env</button>
                    <button onclick="deleteProject('${p.id}', '${p.name}')" class="px-2.5 py-1 text-xs bg-red-900/30 hover:bg-red-900/50 text-red-400 rounded ml-auto font-medium">Delete</button>
                </div>
            </div>`;
        }).join('');
    } catch (e) { console.error('Error loading projects:', e); }
}

async function projectAction(id, act) {
    showToast(`Initiating ${act}...`, 'info');
    await apiFetch(`/api/projects/${id}/${act}`, { method: 'POST' });
    loadProjects();
}

async function deleteProject(id, name) {
    if (!confirm(`Delete project '${name}' and all its container resources?`)) return;
    await apiFetch(`/api/projects/${id}`, { method: 'DELETE' });
    showToast(`Project '${name}' deleted`, 'info');
    loadProjects();
}

// --- Deployment Wizards & Studio ---
function openDeployModal() {
    document.getElementById('deploy-modal').classList.add('open');
}
function closeDeployModal() {
    document.getElementById('deploy-modal').classList.remove('open');
}

async function submitZipDeploy(e) {
    e.preventDefault();
    const name = document.getElementById('zip-name').value.trim();
    const file = document.getElementById('zip-file').files[0];
    if (!file) return alert('Select a ZIP file');

    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);

    closeDeployModal();
    openProgressModal(name);

    try {
        const res = await apiFetch('/api/deploy/zip', { method: 'POST', body: formData });
        if (!res || !res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(`Deploy Error: ${err.detail || 'Upload failed'}`, 'error');
            closeProgressModal();
        }
    } catch (err) {
        showToast('Deploy request failed', 'error');
        closeProgressModal();
    }
}

async function submitGitDeploy(e) {
    e.preventDefault();
    const name = document.getElementById('git-name').value.trim();
    const url = document.getElementById('git-url').value.trim();
    const branch = document.getElementById('git-branch').value.trim() || 'main';

    closeDeployModal();
    openProgressModal(name);

    try {
        const res = await apiFetch('/api/deploy/git', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, git_url: url, branch: branch })
        });
        if (!res || !res.ok) {
            const err = await res.json().catch(() => ({}));
            showToast(`Deploy Error: ${err.detail || 'Git clone failed'}`, 'error');
            closeProgressModal();
        }
    } catch (err) {
        showToast('Deploy request failed', 'error');
        closeProgressModal();
    }
}

function openProgressModal(name) {
    document.getElementById('progress-project-name').textContent = `Deploying: ${name}`;
    document.getElementById('progress-steps-list').innerHTML = `
        <div class="flex items-center gap-3 py-2 text-gray-400 font-mono text-sm">
            <span class="animate-spin text-indigo-400">⚡</span> Initializing deployment studio pipeline...
        </div>`;
    document.getElementById('progress-modal').classList.add('open');
}

function closeProgressModal() {
    document.getElementById('progress-modal').classList.remove('open');
    loadProjects();
}

function updateDeployProgressModal(msg) {
    const list = document.getElementById('progress-steps-list');
    if (!list) return;
    const stepId = `step-${msg.step_num}`;
    let el = document.getElementById(stepId);
    
    const icon = msg.status === 'done' ? '✅' : (msg.status === 'error' ? '❌' : '⚡');
    const color = msg.status === 'done' ? 'text-green-400' : (msg.status === 'error' ? 'text-red-400' : 'text-indigo-400 font-semibold animate-pulse');

    const html = `
        <div class="flex items-start gap-3 py-2.5 border-b border-gray-800 font-mono text-sm">
            <span class="text-base">${icon}</span>
            <div>
                <div class="${color}">Step ${msg.step_num}: ${msg.step_name}</div>
                <div class="text-xs text-gray-400 mt-0.5">${msg.log}</div>
            </div>
        </div>`;

    if (el) {
        el.innerHTML = html;
    } else {
        const div = document.createElement('div');
        div.id = stepId;
        div.innerHTML = html;
        list.appendChild(div);
    }
}

// --- Portainer Replacement (Containers, Images, Volumes) ---
async function loadContainers() {
    try {
        const res = await apiFetch('/api/docker/containers');
        if (!res || !res.ok) return;
        const containers = await res.json();
        const tbody = document.getElementById('containers-tbody');
        if (!tbody) return;
        
        tbody.innerHTML = containers.map(c => {
            const statusClass = c.status === 'running' ? 'text-green-400' : 'text-gray-400';
            const portsStr = c.ports && c.ports.length ? c.ports.join(', ') : 'None';
            return `
            <tr class="border-b border-gray-800 hover:bg-gray-800/40 font-mono text-xs">
                <td class="py-3 px-4 font-semibold text-white">${c.name}</td>
                <td class="py-3 px-4 text-gray-300 truncate max-w-[180px]">${c.image}</td>
                <td class="py-3 px-4 <span class="${statusClass} font-bold">${(c.status || '').toUpperCase()}</span></td>
                <td class="py-3 px-4 text-gray-400">${portsStr}</td>
                <td class="py-3 px-4 text-gray-400">${c.created}</td>
                <td class="py-3 px-4 text-right space-x-1">
                    ${c.status === 'running' ? 
                        `<button onclick="dockerContainerAct('${c.id}', 'stop')" class="px-2 py-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30">Stop</button>` :
                        `<button onclick="dockerContainerAct('${c.id}', 'start')" class="px-2 py-1 bg-green-500/20 text-green-400 rounded hover:bg-green-500/30">Start</button>`
                    }
                    <button onclick="dockerContainerAct('${c.id}', 'restart')" class="px-2 py-1 bg-gray-800 text-gray-300 rounded hover:bg-gray-700">Restart</button>
                    <button onclick="duplicateContainerPrompt('${c.id}', '${c.name}')" class="px-2 py-1 bg-indigo-500/20 text-indigo-400 rounded hover:bg-indigo-500/30">Duplicate</button>
                    <button onclick="dockerContainerAct('${c.id}', 'delete')" class="px-2 py-1 bg-red-900/40 text-red-400 rounded hover:bg-red-900/60">Delete</button>
                </td>
            </tr>`;
        }).join('');
    } catch(e) { console.error('Containers load err:', e); }
}

async function dockerContainerAct(id, act) {
    if (act === 'delete' && !confirm('Force delete this container?')) return;
    showToast(`Executing container ${act}...`, 'info');
    await apiFetch(`/api/docker/containers/${id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: act })
    });
    loadContainers();
}

async function duplicateContainerPrompt(id, oldName) {
    const newName = prompt('Enter name for duplicate container:', `${oldName}-copy`);
    if (!newName) return;
    await apiFetch(`/api/docker/containers/${id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'duplicate', new_name: newName })
    });
    showToast('Container duplicate launched', 'info');
    loadContainers();
}

async function loadImages() {
    try {
        const res = await apiFetch('/api/docker/images');
        if (!res || !res.ok) return;
        const images = await res.json();
        const tbody = document.getElementById('images-tbody');
        if (!tbody) return;
        tbody.innerHTML = images.map(img => `
            <tr class="border-b border-gray-800 font-mono text-xs">
                <td class="py-2.5 px-4 text-gray-200">${(img.tags || []).join(', ')}</td>
                <td class="py-2.5 px-4 text-gray-400">${(img.id || '').substring(0, 12)}</td>
                <td class="py-2.5 px-4 text-gray-400">${img.size_mb} MB</td>
                <td class="py-2.5 px-4 text-gray-400">${img.created}</td>
                <td class="py-2.5 px-4 text-right">
                    <button onclick="deleteDockerImage('${img.id}')" class="px-2 py-1 bg-red-500/20 text-red-400 rounded">Remove</button>
                </td>
            </tr>
        `).join('');
    } catch(e) { console.error('Images load err:', e); }
}

async function pullDockerImagePrompt() {
    const name = prompt('Enter Docker image name to pull (e.g. redis:alpine, nginx:latest):');
    if (!name) return;
    showToast(`Pulling ${name}... Please wait.`, 'info');
    await apiFetch('/api/docker/images/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_name: name })
    });
    showToast(`Pulled ${name}`, 'info');
    loadImages();
}

async function deleteDockerImage(id) {
    if (!confirm('Remove this Docker image?')) return;
    await apiFetch(`/api/docker/images/${id}`, { method: 'DELETE' });
    loadImages();
}

async function pruneDockerImages() {
    if (!confirm('Prune all dangling Docker images?')) return;
    const res = await apiFetch('/api/docker/images/prune', { method: 'POST' });
    if (!res || !res.ok) return;
    const data = await res.json();
    showToast(`Pruned! Reclaimed ${Math.round((data.reclaimed_bytes || 0) / 1024 / 1024)} MB`, 'info');
    loadImages();
}

// --- File Manager ---
let currentDirPath = '';
async function loadFiles(path = '') {
    currentDirPath = path;
    try {
        const res = await apiFetch(`/api/files/list?path=${encodeURIComponent(path)}`);
        if (!res || !res.ok) return;
        const data = await res.json();
        const pathEl = document.getElementById('file-current-path');
        if (pathEl) pathEl.textContent = `/storage/${data.current_path || ''}`;
        
        const list = document.getElementById('file-entries-list');
        if (!list) return;
        let html = '';
        if (path !== '') {
            const parent = path.split('/').slice(0, -1).join('/');
            html += `<div onclick="loadFiles('${parent}')" class="flex items-center gap-3 p-2.5 hover:bg-gray-800/50 rounded cursor-pointer text-indigo-400 font-mono text-sm">📁 .. (Up one directory)</div>`;
        }

        (data.entries || []).forEach(e => {
            const icon = e.is_dir ? '📁' : '📄';
            const action = e.is_dir ? `loadFiles('${e.path}')` : `openFileEditor('${e.path}', '${e.name}')`;
            html += `
                <div class="flex items-center justify-between p-2.5 hover:bg-gray-800/50 rounded cursor-pointer border-b border-gray-800/40 text-sm font-mono">
                    <div onclick="${action}" class="flex items-center gap-3 flex-1 text-gray-200">
                        <span>${icon}</span>
                        <span class="${e.is_dir ? 'font-bold text-indigo-300' : ''}">${e.name}</span>
                    </div>
                    <div class="flex items-center gap-4 text-xs text-gray-500">
                        <span>${e.is_dir ? '-' : formatBytes(e.size_bytes)}</span>
                        <span>${e.mod_time}</span>
                        <button onclick="deleteFileItem('${e.path}')" class="text-red-400 hover:text-red-300 ml-2">🗑️</button>
                    </div>
                </div>`;
        });
        list.innerHTML = html || '<div class="p-4 text-center text-gray-500">Directory is empty</div>';
    } catch(e) { console.error('Files load err:', e); }
}

async function openFileEditor(path, name) {
    const res = await apiFetch(`/api/files/read?path=${encodeURIComponent(path)}`);
    if (!res || !res.ok) return alert('File too large or cannot be read.');
    const data = await res.json();
    
    document.getElementById('editor-filepath').value = path;
    document.getElementById('editor-filename').textContent = name;
    document.getElementById('editor-textarea').value = data.content || '';
    document.getElementById('file-editor-modal').classList.add('open');
}

function closeFileEditor() {
    document.getElementById('file-editor-modal').classList.remove('open');
}

async function saveFileContent() {
    const path = document.getElementById('editor-filepath').value;
    const content = document.getElementById('editor-textarea').value;
    await apiFetch('/api/files/write', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: path, content: content })
    });
    showToast('File saved successfully', 'info');
    closeFileEditor();
}

async function createNewFolderPrompt() {
    const name = prompt('New folder name:');
    if (!name) return;
    const full = currentDirPath ? `${currentDirPath}/${name}` : name;
    await apiFetch('/api/files/folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: full })
    });
    loadFiles(currentDirPath);
}

async function deleteFileItem(path) {
    if (!confirm(`Delete ${path}?`)) return;
    await apiFetch(`/api/files/delete?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
    loadFiles(currentDirPath);
}

// --- Backups Service ---
async function loadBackups() {
    try {
        const res = await apiFetch('/api/backups');
        if (!res || !res.ok) return;
        const backups = await res.json();
        const list = document.getElementById('backups-list');
        if (!list) return;
        if (backups.length === 0) {
            list.innerHTML = '<div class="p-6 text-center text-gray-500">No system backups generated yet.</div>';
            return;
        }
        list.innerHTML = backups.map(b => `
            <div class="glass-card p-4 flex items-center justify-between font-mono text-sm">
                <div>
                    <div class="font-bold text-white">${b.filename}</div>
                    <div class="text-xs text-gray-400">Created: ${b.created_at} | Size: ${b.size_mb} MB</div>
                </div>
                <div class="space-x-2">
                    <button onclick="restoreBackupConfirm('${b.filename}')" class="px-3 py-1.5 bg-indigo-500/20 text-indigo-300 rounded border border-indigo-500/30 hover:bg-indigo-500/30 text-xs">Restore</button>
                    <button onclick="deleteBackupFile('${b.filename}')" class="px-3 py-1.5 bg-red-500/20 text-red-400 rounded border border-red-500/30 hover:bg-red-500/30 text-xs">Delete</button>
                </div>
            </div>
        `).join('');
    } catch(e) { console.error('Backups load err:', e); }
}

async function createNewBackup() {
    showToast('Creating full system ZIP backup...', 'info');
    const res = await apiFetch('/api/backups/create', { method: 'POST' });
    if (res && res.ok) {
        showToast('System backup generated!', 'info');
        loadBackups();
    } else {
        showToast('Backup creation failed', 'error');
    }
}

async function restoreBackupConfirm(filename) {
    if (!confirm(`RESTORE SYSTEM from '${filename}'? This will overwrite existing SQLite DB and project configs!`)) return;
    showToast('Restoring system state...', 'info');
    await apiFetch('/api/backups/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: filename })
    });
    showToast('Restored successfully! Reconnecting...', 'info');
    setTimeout(() => location.reload(), 2000);
}

async function deleteBackupFile(filename) {
    if (!confirm(`Delete backup '${filename}'?`)) return;
    await apiFetch(`/api/backups/${encodeURIComponent(filename)}`, { method: 'DELETE' });
    loadBackups();
}

// --- Server Control & Telemetry ---
async function fetchTelemetryNow() {
    try {
        const res = await apiFetch('/api/telemetry');
        if (!res || !res.ok) return;
        const data = await res.json();
        updateTopbarTelemetry(data);
        renderServerStats(data);
    } catch(e) {}
}

function renderServerStats(data) {
    if (!data) return;
    const osEl = document.getElementById('srv-os');
    if (osEl) osEl.textContent = data.os;
    const kernEl = document.getElementById('srv-kernel');
    if (kernEl) kernEl.textContent = data.kernel;
    const upEl = document.getElementById('srv-uptime');
    if (upEl) upEl.textContent = `${Math.floor(data.uptime_seconds / 3600)}h ${Math.floor((data.uptime_seconds % 3600) / 60)}m`;
    const docEl = document.getElementById('srv-docker');
    if (docEl) docEl.textContent = `${data.docker_version} (${data.docker_status})`;
    
    const ramBar = document.getElementById('srv-ram-bar');
    if (ramBar) ramBar.style.width = `${data.ram_percent}%`;
    const ramTxt = document.getElementById('srv-ram-txt');
    if (ramTxt) ramTxt.textContent = `${data.ram_used_mb} MB / ${data.ram_total_mb} MB (${data.ram_percent}%)`;
    
    const diskBar = document.getElementById('srv-disk-bar');
    if (diskBar) diskBar.style.width = `${data.disk_percent}%`;
    const diskTxt = document.getElementById('srv-disk-txt');
    if (diskTxt) diskTxt.textContent = `${data.disk_used_gb} GB / ${data.disk_total_gb} GB (${data.disk_percent}%)`;
}

async function triggerServerAction(act) {
    if (act === 'reboot' && !confirm('REBOOT host Ubuntu server?')) return;
    if (act === 'shutdown' && !confirm('SHUTDOWN host Ubuntu server?')) return;
    if (act === 'restart_service' && !confirm('Restart SachDeploy background engine?')) return;

    showToast(`Sending command: ${act}...`, 'info');
    const res = await apiFetch('/api/server/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: act })
    });
    if (!res || !res.ok) return;
    const data = await res.json();
    showToast(data.message || 'Command executed', 'info');
}

// --- Logs Modal ---
async function openLogsModal(id, name) {
    document.getElementById('logs-modal-title').textContent = `Logs: ${name}`;
    document.getElementById('logs-terminal').textContent = 'Loading logs...';
    document.getElementById('logs-modal').classList.add('open');
    try {
        const res = await apiFetch(`/api/projects/${id}/logs`);
        if (!res || !res.ok) throw new Error();
        const data = await res.json();
        document.getElementById('logs-terminal').textContent = data.logs || 'No logs output generated yet.';
    } catch(e) {
        document.getElementById('logs-terminal').textContent = 'Error fetching logs.';
    }
}
function closeLogsModal() {
    document.getElementById('logs-modal').classList.remove('open');
}

// --- Env Modal ---
async function openEnvModal(id, name) {
    activeDeployProjectId = id;
    document.getElementById('env-modal-title').textContent = `Environment Variables: ${name}`;
    document.getElementById('env-textarea').value = 'Loading...';
    document.getElementById('env-modal').classList.add('open');
    try {
        const res = await apiFetch(`/api/projects/${id}/env`);
        if (!res || !res.ok) throw new Error();
        const envObj = await res.json();
        const lines = Object.entries(envObj).map(([k, v]) => `${k}=${v}`).join('\n');
        document.getElementById('env-textarea').value = lines;
    } catch(e) {
        document.getElementById('env-textarea').value = '';
    }
}
function closeEnvModal() {
    document.getElementById('env-modal').classList.remove('open');
}
async function saveProjectEnvVariables() {
    const text = document.getElementById('env-textarea').value;
    const envObj = {};
    text.split('\n').forEach(line => {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
            const idx = trimmed.indexOf('=');
            envObj[trimmed.substring(0, idx).trim()] = trimmed.substring(idx + 1).trim();
        }
    });
    await apiFetch(`/api/projects/${activeDeployProjectId}/env`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ env: envObj })
    });
    showToast('Environment variables saved. Restart project to apply!', 'info');
    closeEnvModal();
}

// --- Settings ---
async function loadSettings() {
    try {
        const res = await apiFetch('/api/settings');
        if (!res || !res.ok) return;
        const data = await res.json();
        const ramEl = document.getElementById('set-ram-limit');
        if (ramEl) ramEl.value = data.max_ram_mb || '512';
        const appEl = document.getElementById('set-max-apps');
        if (appEl) appEl.value = data.max_active_apps || '3';
    } catch(e) {}
}
async function saveSettingsForm(e) {
    e.preventDefault();
    await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'max_ram_mb', value: document.getElementById('set-ram-limit').value })
    });
    await apiFetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'max_active_apps', value: document.getElementById('set-max-apps').value })
    });
    showToast('System settings saved', 'info');
}

// --- Helpers ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const div = document.createElement('div');
    div.className = 'toast';
    div.innerHTML = `<span class="text-sm text-gray-200">${message}</span>`;
    container.appendChild(div);
    setTimeout(() => { div.style.opacity = '0'; setTimeout(() => div.remove(), 300); }, 4000);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// --- One-Click App Marketplace ---
let marketplaceCatalog = [];
let activeMarketCategory = 'All';

async function loadMarketplace() {
    const grid = document.getElementById('marketplace-grid');
    grid.innerHTML = '<div class="text-gray-500 text-sm col-span-full">Loading catalog...</div>';
    try {
        const res = await apiFetch('/api/marketplace/catalog');
        marketplaceCatalog = res;
        renderMarketplace();
    } catch (err) {
        grid.innerHTML = `<div class="text-red-400 text-sm col-span-full">Failed to load marketplace: ${err.message}</div>`;
    }
}

function filterMarketplace(category) {
    activeMarketCategory = category;
    document.querySelectorAll('.market-pill').forEach(btn => {
        if (btn.innerText.trim() === category || (category === 'Databases & Storage' && btn.innerText.includes('Databases')) || (category === 'Local AI & LLMs' && btn.innerText.includes('Local AI')) || (category === 'Automation & Workflows' && btn.innerText.includes('Automation')) || (category === 'Observability & Monitoring' && btn.innerText.includes('Monitoring')) || (category === 'DevOps & Management' && btn.innerText.includes('DevOps'))) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    renderMarketplace();
}

function renderMarketplace() {
    const grid = document.getElementById('marketplace-grid');
    grid.innerHTML = '';
    const filtered = activeMarketCategory === 'All' 
        ? marketplaceCatalog 
        : marketplaceCatalog.filter(t => t.category === activeMarketCategory);
        
    if (filtered.length === 0) {
        grid.innerHTML = '<div class="text-gray-500 text-sm col-span-full">No apps found in this category.</div>';
        return;
    }
    
    filtered.forEach(tmpl => {
        const card = document.createElement('div');
        card.className = 'glass-card p-5 rounded-2xl border border-gray-800 hover:border-indigo-500/50 transition-all flex flex-col justify-between space-y-4 shadow-lg';
        
        const ramBadgeColor = tmpl.ram_tier.includes('Low') ? 'text-green-400 bg-green-950/40 border-green-800/50' : (tmpl.ram_tier.includes('Medium') ? 'text-yellow-400 bg-yellow-950/40 border-yellow-800/50' : 'text-red-400 bg-red-950/40 border-red-800/50');
        
        card.innerHTML = `
            <div class="space-y-3">
                <div class="flex items-start justify-between gap-3">
                    <div class="flex items-center gap-3">
                        <span class="text-3xl p-2 bg-gray-900/80 rounded-xl border border-gray-800 inline-block">${tmpl.icon}</span>
                        <div>
                            <h3 class="text-base font-bold text-white leading-tight">${tmpl.name}</h3>
                            <span class="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider">${tmpl.category}</span>
                        </div>
                    </div>
                    <span class="text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${ramBadgeColor}">${tmpl.ram_tier}</span>
                </div>
                <p class="text-xs text-gray-400 leading-relaxed">${tmpl.description}</p>
            </div>
            <div class="pt-3 border-t border-gray-800/80 flex items-center justify-between">
                <span class="text-xs font-mono text-gray-500">Port: <strong class="text-gray-300">${tmpl.default_port}</strong></span>
                <button onclick="openMarketplaceModal('${tmpl.id}')" class="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold shadow-lg shadow-indigo-600/20 flex items-center gap-1 transition-all">⚡ Deploy</button>
            </div>
        `;
        grid.appendChild(card);
    });
}

function openMarketplaceModal(templateId) {
    const tmpl = marketplaceCatalog.find(t => t.id === templateId);
    if (!tmpl) return;
    
    document.getElementById('market-template-id').value = tmpl.id;
    document.getElementById('market-modal-title').innerHTML = `${tmpl.icon} Launch ${tmpl.name}`;
    document.getElementById('market-app-name').value = tmpl.name.toLowerCase().replace(/\\s+/g, '-');
    document.getElementById('market-app-port').value = tmpl.default_port;
    
    const envContainer = document.getElementById('market-env-inputs');
    envContainer.innerHTML = '';
    
    const envKeys = Object.keys(tmpl.env || {});
    if (envKeys.length === 0) {
        envContainer.innerHTML = '<div class="text-xs text-gray-500 italic">No environment configuration required.</div>';
    } else {
        envKeys.forEach(key => {
            const val = tmpl.env[key];
            const div = document.createElement('div');
            div.className = 'space-y-1';
            div.innerHTML = `
                <label class="block text-[11px] font-mono font-semibold text-gray-300">${key}</label>
                <input type="text" data-env-key="${key}" value="${val}" required class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-1.5 text-white font-mono text-xs focus:border-indigo-500 outline-none" />
            `;
            envContainer.appendChild(div);
        });
    }
    
    document.getElementById('marketplace-modal').classList.add('active');
}

function closeMarketplaceModal() {
    document.getElementById('marketplace-modal').classList.remove('active');
}

async function submitMarketplaceDeploy(e) {
    e.preventDefault();
    const template_id = document.getElementById('market-template-id').value;
    const name = document.getElementById('market-app-name').value.trim();
    const port = parseInt(document.getElementById('market-app-port').value, 10);
    
    const env = {};
    document.querySelectorAll('#market-env-inputs input[data-env-key]').forEach(input => {
        env[input.getAttribute('data-env-key')] = input.value;
    });
    
    closeMarketplaceModal();
    showToast(`⚡ Deploying ${name}... Check live notifications!`, 'info');
    switchTab('projects');
    
    try {
        await apiFetch('/api/marketplace/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ template_id, name, port, env })
        });
        showToast(`🎉 ${name} deployed successfully!`, 'success');
        loadProjects();
    } catch (err) {
        showToast(`❌ Marketplace deploy failed: ${err.message}`, 'error');
    }
}

// --- Integrated Zero-SSH Terminal ---
let xtermInstance = null;
let fitAddon = null;
let termWs = null;
let activeTerminalSessionId = null;

async function initTerminalView() {
    try {
        const sessions = await apiFetch('/api/terminal/sessions');
        if (!sessions || sessions.length === 0) {
            await createNewTerminalTab('Host Terminal', '/app');
        } else {
            renderTerminalTabs(sessions);
            if (!activeTerminalSessionId || !sessions.find(s => s.id === activeTerminalSessionId)) {
                switchTerminalTab(sessions[0].id);
            } else {
                switchTerminalTab(activeTerminalSessionId);
            }
        }
    } catch (err) {
        showToast(`Terminal error: ${err.message}`, 'error');
    }
}

function renderTerminalTabs(sessions) {
    const bar = document.getElementById('terminal-tabs-bar');
    bar.innerHTML = '';
    sessions.forEach(sess => {
        const btn = document.createElement('button');
        btn.className = `term-tab ${sess.id === activeTerminalSessionId ? 'active' : ''}`;
        btn.innerHTML = `<span>🐚</span> <span>${sess.name}</span>`;
        btn.onclick = () => switchTerminalTab(sess.id);
        bar.appendChild(btn);
    });
}

function switchTerminalTab(sessionId) {
    activeTerminalSessionId = sessionId;
    document.querySelectorAll('.term-tab').forEach((btn) => {
        btn.classList.remove('active');
    });
    apiFetch('/api/terminal/sessions').then(renderTerminalTabs).catch(()=>{});
    connectTerminalWs(sessionId);
}

async function createNewTerminalTab(name="Host Terminal", cwd="/app") {
    try {
        const sess = await apiFetch('/api/terminal/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, cwd })
        });
        activeTerminalSessionId = sess.id;
        initTerminalView();
    } catch (err) {
        showToast(`Failed to create terminal tab: ${err.message}`, 'error');
    }
}

async function killCurrentTerminalTab() {
    if (!activeTerminalSessionId) return;
    try {
        await apiFetch(`/api/terminal/sessions/${activeTerminalSessionId}`, { method: 'DELETE' });
        if (termWs) termWs.close();
        activeTerminalSessionId = null;
        initTerminalView();
    } catch (err) {
        showToast(`Failed to kill tab: ${err.message}`, 'error');
    }
}

function connectTerminalWs(sessionId) {
    if (termWs) {
        try { termWs.close(); } catch(e){}
    }
    
    if (!xtermInstance) {
        const container = document.getElementById('xterm-container');
        container.innerHTML = '';
        xtermInstance = new Terminal({
            cursorBlink: true,
            theme: {
                background: '#0d1117',
                foreground: '#f0f6fc',
                cursor: '#58a6ff',
                selectionBackground: 'rgba(56, 139, 253, 0.4)',
                black: '#0d1117',
                red: '#ff7b72',
                green: '#3fb950',
                yellow: '#d29922',
                blue: '#58a6ff',
                magenta: '#bc8cff',
                cyan: '#39c5cf',
                white: '#b1bac4'
            },
            fontFamily: '"JetBrains Mono", monospace',
            fontSize: 13,
            rows: 28
        });
        fitAddon = new FitAddon.FitAddon();
        xtermInstance.loadAddon(fitAddon);
        xtermInstance.open(container);
        setTimeout(() => fitAddon.fit(), 100);
        
        window.addEventListener('resize', () => {
            if (fitAddon && activeTab === 'terminal') {
                fitAddon.fit();
                if (termWs && termWs.readyState === WebSocket.OPEN) {
                    termWs.send(JSON.stringify({ type: 'resize', cols: xtermInstance.cols, rows: xtermInstance.rows }));
                }
            }
        });
    } else {
        xtermInstance.reset();
    }
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    termWs = new WebSocket(`${protocol}//${window.location.host}/ws/terminal?session_id=${sessionId}`);
    
    termWs.onopen = () => {
        xtermInstance.onData(data => {
            if (termWs.readyState === WebSocket.OPEN) {
                termWs.send(data);
            }
        });
        if (fitAddon) {
            setTimeout(() => {
                fitAddon.fit();
                termWs.send(JSON.stringify({ type: 'resize', cols: xtermInstance.cols, rows: xtermInstance.rows }));
            }, 150);
        }
    };
    
    termWs.onmessage = (event) => {
        xtermInstance.write(event.data);
    };
    
    termWs.onerror = () => {
        xtermInstance.write('\r\n\x1b[31m[WebSocket Connection Error]\x1b[0m\r\n');
    };
}

function sendTerminalCommand(cmd) {
    if (termWs && termWs.readyState === WebSocket.OPEN) {
        termWs.send(cmd + "\r");
        if (xtermInstance) xtermInstance.focus();
    } else {
        showToast('Terminal not connected', 'error');
    }
}


