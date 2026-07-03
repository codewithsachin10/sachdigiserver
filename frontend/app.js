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

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

function setupEventListeners() {
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const u = document.getElementById('username').value;
        const p = document.getElementById('password').value;
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });
            if (res.ok) {
                loginError.classList.add('hidden');
                checkAuth();
            } else {
                loginError.textContent = 'Invalid credentials';
                loginError.classList.remove('hidden');
            }
        } catch (err) {
            loginError.textContent = 'Connection failed';
            loginError.classList.remove('hidden');
        }
    });

    document.getElementById('logout-btn').addEventListener('click', async () => {
        await fetch('/api/logout', { method: 'POST' });
        if (ws) ws.close();
        location.reload();
    });

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const tab = item.getAttribute('data-tab');
            switchTab(tab);
        });
    });
}

async function checkAuth() {
    try {
        const res = await fetch('/api/me');
        if (res.ok) {
            currentUser = await res.json();
            userDisplay.textContent = currentUser.username;
            authScreen.classList.add('hidden');
            appScreen.classList.remove('hidden');
            initWebSocket();
            switchTab('projects');
        } else {
            authScreen.classList.remove('hidden');
            appScreen.classList.add('hidden');
        }
    } catch (e) {
        authScreen.classList.remove('hidden');
        appScreen.classList.add('hidden');
    }
}

// --- WebSocket Management ---
function initWebSocket() {
    if (ws) {
        try { ws.close(); } catch(e){}
    }
    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${proto}//${location.host}/ws/events`);

    ws.onopen = () => {
        console.log('[SachDeploy] WebSocket connected');
        document.getElementById('ws-status-dot').classList.remove('bg-red-500');
        document.getElementById('ws-status-dot').classList.add('bg-green-500');
        if (reconnectTimer) clearInterval(reconnectTimer);
    };

    ws.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            handleWsMessage(msg);
        } catch (e) { console.error('WS parse error:', e); }
    };

    ws.onclose = () => {
        document.getElementById('ws-status-dot').classList.remove('bg-green-500');
        document.getElementById('ws-status-dot').classList.add('bg-red-500');
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
    document.getElementById('top-cpu').textContent = `${data.cpu_percent}%`;
    document.getElementById('top-ram').textContent = `${data.ram_percent}%`;
    document.getElementById('top-disk').textContent = `${data.disk_percent}%`;
    document.getElementById('top-temp').textContent = `${data.temperature}°C`;
    document.getElementById('top-tailscale').textContent = data.tailscale_ip;
}

// --- Tab Navigation ---
function switchTab(tabName) {
    activeTab = tabName;
    navItems.forEach(item => {
        if (item.getAttribute('data-tab') === tabName) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    tabViews.forEach(view => {
        if (view.id === `view-${tabName}`) {
            view.classList.remove('hidden');
        } else {
            view.classList.add('hidden');
        }
    });

    refreshCurrentTab();
}

function refreshCurrentTab() {
    if (activeTab === 'projects') loadProjects();
    else if (activeTab === 'containers') loadContainers();
    else if (activeTab === 'files') loadFiles('');
    else if (activeTab === 'backups') loadBackups();
    else if (activeTab === 'server') fetchTelemetryNow();
    else if (activeTab === 'settings') loadSettings();
}

// --- Projects & Deployments ---
async function loadProjects() {
    try {
        const res = await fetch('/api/projects');
        const projects = await res.json();
        const grid = document.getElementById('projects-grid');
        
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
                        <div>Type: <span class="text-gray-200">${p.type.toUpperCase()}</span></div>
                        <div>Source: <span class="text-gray-200 truncate inline-block max-w-[180px] align-bottom">${p.source}</span></div>
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
    await fetch(`/api/projects/${id}/${act}`, { method: 'POST' });
    loadProjects();
}

async function deleteProject(id, name) {
    if (!confirm(`Delete project '${name}' and all its container resources?`)) return;
    await fetch(`/api/projects/${id}`, { method: 'DELETE' });
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
    const name = document.getElementById('zip-name').value;
    const file = document.getElementById('zip-file').files[0];
    if (!file) return alert('Select a ZIP file');

    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);

    closeDeployModal();
    openProgressModal(name);

    try {
        const res = await fetch('/api/deploy/zip', { method: 'POST', body: formData });
        if (!res.ok) {
            const err = await res.json();
            showToast(`Deploy Error: ${err.detail}`, 'error');
            closeProgressModal();
        }
    } catch (err) {
        showToast('Deploy request failed', 'error');
        closeProgressModal();
    }
}

async function submitGitDeploy(e) {
    e.preventDefault();
    const name = document.getElementById('git-name').value;
    const url = document.getElementById('git-url').value;
    const branch = document.getElementById('git-branch').value || 'main';

    closeDeployModal();
    openProgressModal(name);

    try {
        const res = await fetch('/api/deploy/git', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, git_url: url, branch: branch })
        });
        if (!res.ok) {
            const err = await res.json();
            showToast(`Deploy Error: ${err.detail}`, 'error');
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
        const res = await fetch('/api/docker/containers');
        const containers = await res.json();
        const tbody = document.getElementById('containers-tbody');
        
        tbody.innerHTML = containers.map(c => {
            const statusClass = c.status === 'running' ? 'text-green-400' : 'text-gray-400';
            const portsStr = c.ports && c.ports.length ? c.ports.join(', ') : 'None';
            return `
            <tr class="border-b border-gray-800 hover:bg-gray-800/40 font-mono text-xs">
                <td class="py-3 px-4 font-semibold text-white">${c.name}</td>
                <td class="py-3 px-4 text-gray-300 truncate max-w-[180px]">${c.image}</td>
                <td class="py-3 px-4 <span class="${statusClass} font-bold">${c.status.toUpperCase()}</span></td>
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
    await fetch(`/api/docker/containers/${id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: act })
    });
    loadContainers();
}

async function duplicateContainerPrompt(id, oldName) {
    const newName = prompt('Enter name for duplicate container:', `${oldName}-copy`);
    if (!newName) return;
    await fetch(`/api/docker/containers/${id}/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'duplicate', new_name: newName })
    });
    showToast('Container duplicate launched', 'info');
    loadContainers();
}

async function loadImages() {
    const res = await fetch('/api/docker/images');
    const images = await res.json();
    const tbody = document.getElementById('images-tbody');
    tbody.innerHTML = images.map(img => `
        <tr class="border-b border-gray-800 font-mono text-xs">
            <td class="py-2.5 px-4 text-gray-200">${img.tags.join(', ')}</td>
            <td class="py-2.5 px-4 text-gray-400">${img.id[:12]}</td>
            <td class="py-2.5 px-4 text-gray-400">${img.size_mb} MB</td>
            <td class="py-2.5 px-4 text-gray-400">${img.created}</td>
            <td class="py-2.5 px-4 text-right">
                <button onclick="deleteDockerImage('${img.id}')" class="px-2 py-1 bg-red-500/20 text-red-400 rounded">Remove</button>
            </td>
        </tr>
    `).join('');
}

async function pullDockerImagePrompt() {
    const name = prompt('Enter Docker image name to pull (e.g. redis:alpine, nginx:latest):');
    if (!name) return;
    showToast(`Pulling ${name}... Please wait.`, 'info');
    await fetch('/api/docker/images/pull', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_name: name })
    });
    showToast(`Pulled ${name}`, 'info');
    loadImages();
}

async function deleteDockerImage(id) {
    if (!confirm('Remove this Docker image?')) return;
    await fetch(`/api/docker/images/${id}`, { method: 'DELETE' });
    loadImages();
}

async function pruneDockerImages() {
    if (!confirm('Prune all dangling Docker images?')) return;
    const res = await fetch('/api/docker/images/prune', { method: 'POST' });
    const data = await res.json();
    showToast(`Pruned! Reclaimed ${Math.round(data.reclaimed_bytes / 1024 / 1024)} MB`, 'info');
    loadImages();
}

// --- File Manager ---
let currentDirPath = '';
async function loadFiles(path = '') {
    currentDirPath = path;
    try {
        const res = await fetch(`/api/files/list?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        document.getElementById('file-current-path').textContent = `/storage/${data.current_path || ''}`;
        
        const list = document.getElementById('file-entries-list');
        let html = '';
        if (path !== '') {
            const parent = path.split('/').slice(0, -1).join('/');
            html += `<div onclick="loadFiles('${parent}')" class="flex items-center gap-3 p-2.5 hover:bg-gray-800/50 rounded cursor-pointer text-indigo-400 font-mono text-sm">📁 .. (Up one directory)</div>`;
        }

        data.entries.forEach(e => {
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
    const res = await fetch(`/api/files/read?path=${encodeURIComponent(path)}`);
    if (!res.ok) return alert('File too large or cannot be read.');
    const data = await res.json();
    
    document.getElementById('editor-filepath').value = path;
    document.getElementById('editor-filename').textContent = name;
    document.getElementById('editor-textarea').value = data.content;
    document.getElementById('file-editor-modal').classList.add('open');
}

function closeFileEditor() {
    document.getElementById('file-editor-modal').classList.remove('open');
}

async function saveFileContent() {
    const path = document.getElementById('editor-filepath').value;
    const content = document.getElementById('editor-textarea').value;
    await fetch('/api/files/write', {
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
    await fetch('/api/files/folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: full })
    });
    loadFiles(currentDirPath);
}

async function deleteFileItem(path) {
    if (!confirm(`Delete ${path}?`)) return;
    await fetch(`/api/files/delete?path=${encodeURIComponent(path)}`, { method: 'DELETE' });
    loadFiles(currentDirPath);
}

// --- Backups Service ---
async function loadBackups() {
    const res = await fetch('/api/backups');
    const backups = await res.json();
    const list = document.getElementById('backups-list');
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
}

async function createNewBackup() {
    showToast('Creating full system ZIP backup...', 'info');
    const res = await fetch('/api/backups/create', { method: 'POST' });
    if (res.ok) {
        showToast('System backup generated!', 'info');
        loadBackups();
    } else {
        showToast('Backup creation failed', 'error');
    }
}

async function restoreBackupConfirm(filename) {
    if (!confirm(`RESTORE SYSTEM from '${filename}'? This will overwrite existing SQLite DB and project configs!`)) return;
    showToast('Restoring system state...', 'info');
    await fetch('/api/backups/restore', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: filename })
    });
    showToast('Restored successfully! Reconnecting...', 'info');
    setTimeout(() => location.reload(), 2000);
}

async function deleteBackupFile(filename) {
    if (!confirm(`Delete backup '${filename}'?`)) return;
    await fetch(`/api/backups/${encodeURIComponent(filename)}`, { method: 'DELETE' });
    loadBackups();
}

// --- Server Control & Telemetry ---
async function fetchTelemetryNow() {
    const res = await fetch('/api/telemetry');
    const data = await res.json();
    updateTopbarTelemetry(data);
    renderServerStats(data);
}

function renderServerStats(data) {
    if (!data) return;
    document.getElementById('srv-os').textContent = data.os;
    document.getElementById('srv-kernel').textContent = data.kernel;
    document.getElementById('srv-uptime').textContent = `${Math.floor(data.uptime_seconds / 3600)}h ${Math.floor((data.uptime_seconds % 3600) / 60)}m`;
    document.getElementById('srv-docker').textContent = `${data.docker_version} (${data.docker_status})`;
    
    document.getElementById('srv-ram-bar').style.width = `${data.ram_percent}%`;
    document.getElementById('srv-ram-txt').textContent = `${data.ram_used_mb} MB / ${data.ram_total_mb} MB (${data.ram_percent}%)`;
    
    document.getElementById('srv-disk-bar').style.width = `${data.disk_percent}%`;
    document.getElementById('srv-disk-txt').textContent = `${data.disk_used_gb} GB / ${data.disk_total_gb} GB (${data.disk_percent}%)`;
}

async function triggerServerAction(act) {
    if (act === 'reboot' && !confirm('REBOOT host Ubuntu server?')) return;
    if (act === 'shutdown' && !confirm('SHUTDOWN host Ubuntu server?')) return;
    if (act === 'restart_service' && !confirm('Restart SachDeploy background engine?')) return;

    showToast(`Sending command: ${act}...`, 'info');
    const res = await fetch('/api/server/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: act })
    });
    const data = await res.json();
    showToast(data.message || 'Command executed', 'info');
}

// --- Logs Modal ---
async function openLogsModal(id, name) {
    document.getElementById('logs-modal-title').textContent = `Logs: ${name}`;
    document.getElementById('logs-terminal').textContent = 'Loading logs...';
    document.getElementById('logs-modal').classList.add('open');
    try {
        const res = await fetch(`/api/projects/${id}/logs`);
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
        const res = await fetch(`/api/projects/${id}/env`);
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
    await fetch(`/api/projects/${activeDeployProjectId}/env`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ env: envObj })
    });
    showToast('Environment variables saved. Restart project to apply!', 'info');
    closeEnvModal();
}

// --- Settings ---
async function loadSettings() {
    const res = await fetch('/api/settings');
    const data = await res.json();
    document.getElementById('set-ram-limit').value = data.max_ram_mb || '512';
    document.getElementById('set-max-apps').value = data.max_active_apps || '3';
}
async function saveSettingsForm(e) {
    e.preventDefault();
    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: 'max_ram_mb', value: document.getElementById('set-ram-limit').value })
    });
    await fetch('/api/settings', {
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
