import os
import re

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STITCH_DIR = os.path.join(ROOT_DIR, "stitch_sachdeploy_premium_ui_platform")
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")

# Ensure frontend directory exists
os.makedirs(FRONTEND_DIR, exist_ok=True)

# Common modals to append to the end of body
MODALS_HTML = """
    <!-- TOAST CONTAINER -->
    <div id="toast-container" class="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none"></div>

    <!-- MODAL 1: DEPLOY WIZARD -->
    <div id="deploy-modal" class="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 opacity-0 pointer-events-none transition-opacity duration-200">
        <div class="bg-[#18181b] border border-white/10 rounded-2xl p-6 max-w-lg w-full m-4 space-y-6 shadow-2xl relative">
            <div class="flex items-center justify-between border-b border-white/10 pb-4">
                <div class="flex items-center gap-2">
                    <span class="material-symbols-outlined text-primary">rocket_launch</span>
                    <h3 class="text-lg font-bold text-white font-headline-lg">Deploy Application</h3>
                </div>
                <button onclick="closeDeployModal()" class="text-gray-400 hover:text-white text-lg font-mono">✕</button>
            </div>
            
            <div class="space-y-6">
                <!-- ZIP Upload Form -->
                <form onsubmit="submitZipDeploy(event)" class="space-y-4 bg-[#10131a] p-4 rounded-xl border border-white/5">
                    <div class="text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1.5">
                        <span class="material-symbols-outlined text-sm">folder_zip</span> Option A: ZIP Archive Upload
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Project Name</label>
                        <input type="text" id="zip-name" placeholder="my-app" required
                            class="w-full bg-[#0b0e15] border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:border-primary outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Select ZIP File (.zip)</label>
                        <input type="file" id="zip-file" accept=".zip" required
                            class="w-full bg-[#0b0e15] border border-white/10 rounded-lg px-3 py-1.5 text-gray-300 text-xs">
                    </div>
                    <button type="submit" class="w-full bg-primary hover:bg-primary-container text-on-primary py-2.5 rounded-lg text-xs font-bold transition-all shadow-lg shadow-primary/20 flex items-center justify-center gap-2">
                        <span class="material-symbols-outlined text-sm">cloud_upload</span> Deploy from ZIP
                    </button>
                </form>

                <!-- Git Repo Form -->
                <form onsubmit="submitGitDeploy(event)" class="space-y-4 bg-[#10131a] p-4 rounded-xl border border-white/5">
                    <div class="text-xs font-bold text-[#c0c6db] uppercase tracking-wider flex items-center gap-1.5">
                        <span class="material-symbols-outlined text-sm">code</span> Option B: Git Repository Clone
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Project Name</label>
                        <input type="text" id="git-name" placeholder="repo-app" required
                            class="w-full bg-[#0b0e15] border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:border-primary outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Git Clone URL</label>
                        <input type="url" id="git-url" placeholder="https://github.com/username/repo.git" required
                            class="w-full bg-[#0b0e15] border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:border-primary outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-medium text-gray-300 mb-1">Branch</label>
                        <input type="text" id="git-branch" placeholder="main" value="main"
                            class="w-full bg-[#0b0e15] border border-white/10 rounded-lg px-3 py-2 text-white text-sm font-mono focus:border-primary outline-none">
                    </div>
                    <button type="submit" class="w-full bg-[#404758] hover:bg-[#4d8eff] text-white py-2.5 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2">
                        <span class="material-symbols-outlined text-sm">fork_right</span> Deploy from Git
                    </button>
                </form>
            </div>
        </div>
    </div>

    <!-- MODAL 2: DEPLOY PROGRESS STUDIO -->
    <div id="progress-modal" class="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 opacity-0 pointer-events-none transition-opacity duration-200">
        <div class="bg-[#18181b] border border-primary/40 rounded-2xl p-6 max-w-xl w-full m-4 space-y-4 shadow-2xl">
            <div class="flex items-center justify-between border-b border-white/10 pb-3">
                <div class="flex items-center gap-2">
                    <span class="w-3 h-3 rounded-full bg-primary animate-ping"></span>
                    <h3 id="progress-project-name" class="text-base font-bold text-white font-mono">Deploying Application...</h3>
                </div>
                <button onclick="closeProgressModal()" class="text-xs text-gray-400 hover:text-white px-3 py-1.5 bg-white/5 rounded-lg">Minimize</button>
            </div>
            <div id="progress-steps-list" class="space-y-1.5 max-h-[380px] overflow-y-auto pr-2 font-mono text-xs"></div>
        </div>
    </div>

    <!-- MODAL 3: LOGS TERMINAL -->
    <div id="logs-modal" class="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 opacity-0 pointer-events-none transition-opacity duration-200">
        <div class="bg-[#18181b] border border-white/10 rounded-2xl p-6 max-w-4xl w-full m-4 space-y-4 shadow-2xl">
            <div class="flex items-center justify-between border-b border-white/10 pb-3">
                <h3 id="logs-modal-title" class="text-base font-bold text-white font-mono">Container Logs</h3>
                <button onclick="closeLogsModal()" class="text-gray-400 hover:text-white text-lg font-mono">✕</button>
            </div>
            <pre id="logs-terminal" class="bg-[#0b0e15] border border-white/5 rounded-xl p-4 font-mono text-xs text-gray-200 overflow-y-auto max-h-[450px] leading-relaxed"></pre>
        </div>
    </div>

    <!-- MODAL 4: ENV VARIABLES -->
    <div id="env-modal" class="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 opacity-0 pointer-events-none transition-opacity duration-200">
        <div class="bg-[#18181b] border border-white/10 rounded-2xl p-6 max-w-lg w-full m-4 space-y-4 shadow-2xl">
            <div class="flex items-center justify-between border-b border-white/10 pb-3">
                <h3 id="env-modal-title" class="text-base font-bold text-white font-mono">Environment Variables</h3>
                <button onclick="closeEnvModal()" class="text-gray-400 hover:text-white text-lg font-mono">✕</button>
            </div>
            <p class="text-xs text-gray-400">Enter environment variables (one per line in KEY=VALUE format):</p>
            <textarea id="env-textarea" rows="10" placeholder="PORT=8000&#10;DATABASE_URL=sqlite:///db.sqlite"
                class="w-full bg-[#0b0e15] border border-white/10 rounded-xl p-3 font-mono text-xs text-green-400 focus:outline-none focus:border-primary"></textarea>
            <div class="flex justify-end gap-3 pt-2">
                <button onclick="closeEnvModal()" class="px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg text-xs font-medium">Cancel</button>
                <button onclick="saveProjectEnvVariables()" class="px-5 py-2 bg-primary text-on-primary rounded-lg text-xs font-bold">Save Variables</button>
            </div>
        </div>
    </div>

    <!-- MODAL 5: FILE EDITOR -->
    <div id="file-editor-modal" class="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 opacity-0 pointer-events-none transition-opacity duration-200">
        <div class="bg-[#18181b] border border-white/10 rounded-2xl p-6 max-w-4xl w-full m-4 space-y-4 shadow-2xl">
            <div class="flex items-center justify-between border-b border-white/10 pb-3">
                <div class="flex items-center gap-2">
                    <span class="text-primary font-mono text-sm">editing:</span>
                    <h3 id="editor-filename" class="text-base font-bold text-white font-mono">file.txt</h3>
                </div>
                <button onclick="closeFileEditor()" class="text-gray-400 hover:text-white text-lg font-mono">✕</button>
            </div>
            <input type="hidden" id="editor-filepath">
            <textarea id="editor-textarea" rows="18"
                class="w-full bg-[#0b0e15] border border-white/10 rounded-xl p-4 font-mono text-xs text-gray-200 focus:outline-none focus:border-primary leading-relaxed"></textarea>
            <div class="flex justify-end gap-3 pt-2">
                <button onclick="closeFileEditor()" class="px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg text-xs font-medium">Discard</button>
                <button onclick="saveFileContent()" class="px-5 py-2 bg-primary text-on-primary rounded-lg text-xs font-bold">Save Changes</button>
            </div>
        </div>
    </div>

    <!-- MODAL 6: MARKETPLACE DEPLOY -->
    <div id="marketplace-modal" class="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-50 opacity-0 pointer-events-none transition-opacity duration-200">
        <div class="bg-[#18181b] border border-white/10 rounded-2xl p-6 max-w-lg w-full m-4 space-y-4 shadow-2xl">
            <div class="flex items-center justify-between border-b border-white/10 pb-3">
                <h3 class="text-lg font-bold text-white flex items-center gap-2" id="market-modal-title">🚀 Launch Template</h3>
                <button onclick="closeMarketplaceModal()" class="text-gray-400 hover:text-white text-lg font-mono">✕</button>
            </div>
            <form id="marketplace-form" class="space-y-4" onsubmit="submitMarketplaceDeploy(event)">
                <input type="hidden" id="market-template-id" />
                <div>
                    <label class="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1">Container Name</label>
                    <input type="text" id="market-app-name" required class="w-full bg-[#0b0e15] border border-white/10 rounded-lg px-3 py-2 text-white font-mono text-sm focus:border-primary outline-none" />
                </div>
                <div>
                    <label class="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1">Host Port Binding</label>
                    <input type="number" id="market-app-port" required class="w-full bg-[#0b0e15] border border-white/10 rounded-lg px-3 py-2 text-white font-mono text-sm focus:border-primary outline-none" />
                </div>
                <div id="market-env-container" class="space-y-3 pt-2 border-t border-white/10">
                    <label class="block text-xs font-semibold text-primary uppercase tracking-wider">Configuration & Passwords</label>
                    <div id="market-env-inputs" class="space-y-3"></div>
                </div>
                <div class="pt-4 flex justify-end gap-3">
                    <button type="button" onclick="closeMarketplaceModal()" class="px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-300 rounded-lg text-xs font-semibold">Cancel</button>
                    <button type="submit" class="px-5 py-2 bg-primary hover:bg-primary-container text-on-primary rounded-lg text-xs font-bold flex items-center gap-2 shadow-lg shadow-primary/20">⚡ Deploy Now</button>
                </div>
            </form>
        </div>
    </div>

    <!-- CUSTOM TOAST CSS & JS UTILS -->
    <style>
        #deploy-modal.open, #progress-modal.open, #logs-modal.open, #env-modal.open, #file-editor-modal.open, #marketplace-modal.open, #marketplace-modal.active {
            opacity: 1 !important;
            pointer-events: auto !important;
        }
        .toast {
            background: rgba(24, 24, 27, 0.95);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 4px solid #adc6ff;
            padding: 0.75rem 1rem;
            border-radius: 0.75rem;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-width: 280px;
            color: #e1e2ec;
            font-size: 0.875rem;
            pointer-events: auto;
            animation: toast-in 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes toast-in {
            from { transform: translateY(100%); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    </style>
    <script src="/app.js"></script>
"""

def update_nav_links(html):
    # Map link texts to target URLs
    mapping = {
        r"Dashboard": "/",
        r"Projects": "/projects.html",
        r"Deployments": "/deployments.html",
        r"Containers": "/containers.html",
        r"Volumes": "/volumes.html",
        r"Networks": "/networks.html",
        r"Monitoring": "/monitoring.html",
        r"Terminal": "/terminal.html",
        r"Support": "/support.html",
        r"Settings": "/settings.html",
    }
    
    for text, url in mapping.items():
        # Regex to match <a> tags containing the specific text and href="#"
        pattern = re.compile(rf'(<a\s+[^>]*?href=)["\']#["\']([^>]*?>\s*(?:<[^>]+>\s*)*?{text}\s*<)', re.IGNORECASE)
        html = pattern.sub(r'\1"' + url + r'"\2', html)
    
    # Also add Marketplace item if not present after Deployments
    if '/marketplace.html' not in html and '/deployments.html' in html:
        mkt_item = '''
<a class="flex items-center gap-3 px-4 py-3 text-on-surface-variant hover:text-on-surface hover:bg-white/5 transition-all duration-200" href="/marketplace.html">
<span class="material-symbols-outlined">storefront</span>
<span class="font-label-sm">Marketplace</span>
</a>'''
        # Try inserting after deployments tab
        html = re.sub(r'(href=["\']/deployments\.html["\'][^>]*?>.*?</a>)', r'\1' + mkt_item, html, flags=re.DOTALL)
        
    return html

def inject_modals_and_scripts(html):
    if "</body>" in html:
        return html.replace("</body>", MODALS_HTML + "\n</body>")
    return html + MODALS_HTML

def process_file(src_path, dest_filename, page_type=None):
    if not os.path.exists(src_path):
        print(f"Warning: {src_path} not found")
        return
        
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # 1. Update navigation links
    content = update_nav_links(content)
    
    # 2. Inject modals and script
    content = inject_modals_and_scripts(content)
    
    # 3. Specific page ID injections for dynamic data binding
    if page_type == "dashboard":
        # Add quick action button IDs
        content = re.sub(r'(<button[^>]*?>\s*<div[^>]*?>\s*<span[^>]*?>rocket_launch</span>\s*<span[^>]*?>Deploy Project</span>)', r'<button onclick="openDeployModal()" \1', content)
        content = re.sub(r'(<button[^>]*?>\s*<div[^>]*?>\s*<span[^>]*?>restart_alt</span>\s*<span[^>]*?>Restart Docker</span>)', r'<button onclick="quickRestartDocker()" \1', content)
        content = re.sub(r'(<button[^>]*?>\s*<div[^>]*?>\s*<span[^>]*?>settings_backup_restore</span>\s*<span[^>]*?>Create Backup</span>)', r'<button onclick="quickCreateBackup()" \1', content)
        content = re.sub(r'(<button[^>]*?>\s*<div[^>]*?>\s*<span[^>]*?>terminal</span>\s*<span[^>]*?>Open Terminal</span>)', r'<button onclick="window.location.href=\'/terminal.html\'" \1', content)
        # Top Deploy button
        content = re.sub(r'(<button[^>]*?>\s*Deploy\s*</button>)', r'<button onclick="openDeployModal()" class="bg-primary text-on-primary px-6 py-2 rounded-lg font-label-sm hover:shadow-[0_0_20px_rgba(59,132,246,0.4)] hover:scale-105 transition-all duration-200">Deploy</button>', content)
        # Recent activity container
        content = re.sub(r'(<h3 class="font-title-md text-on-surface mb-8">Recent Activity</h3>\s*<div class="space-y-6">)', r'\1\n<div id="dashboard-activity-list" class="space-y-6">', content)

    elif page_type == "projects":
        # Add id to projects grid
        content = re.sub(r'(<div class="grid grid-cols-1 lg:grid-cols-2 gap-gutter">)', r'<div id="projects-grid" class="grid grid-cols-1 lg:grid-cols-2 gap-gutter">', content)
        # Connect New Project button
        content = re.sub(r'(<button[^>]*?>\s*<span[^>]*?>add</span>\s*New Project\s*</button>)', r'<button onclick="openDeployModal()" class="bg-primary text-on-primary px-6 py-2 rounded-lg font-bold text-sm hover:shadow-[0_0_20px_rgba(59,132,246,0.4)] transition-all flex items-center gap-2"><span class="material-symbols-outlined text-sm">add</span> New Project</button>', content)

    elif page_type == "containers":
        content = re.sub(r'(<tbody class="divide-y divide-white/5">)', r'<tbody id="containers-tbody" class="divide-y divide-white/5">', content)

    elif page_type == "deployments":
        content = re.sub(r'(<tbody class="divide-y divide-white/5">)', r'<tbody id="deployments-tbody" class="divide-y divide-white/5">', content)

    elif page_type == "monitoring":
        content = re.sub(r'(<h4 class="text-on-surface text-title-md font-bold" id="node-1-load">)', r'<h4 class="text-on-surface text-title-md font-bold" id="mon-cpu-val">', content)
        content = re.sub(r'(<h4 class="text-on-surface text-title-md font-bold" id="node-2-load">)', r'<h4 class="text-on-surface text-title-md font-bold" id="mon-ram-val">', content)
        content = re.sub(r'(<h4 class="text-on-surface text-title-md font-bold" id="node-3-load">)', r'<h4 class="text-on-surface text-title-md font-bold" id="mon-disk-val">', content)

    elif page_type == "terminal":
        # Inject xterm container inside terminal main area if not already present
        if 'id="xterm-container"' not in content:
            content = re.sub(r'(<!-- Main Content Area -->\s*<main[^>]*?>)', r'\1\n<div id="xterm-container" class="flex-1 w-full p-4 bg-[#060911]"></div>', content)

    dest_path = os.path.join(FRONTEND_DIR, dest_filename)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Generated: {dest_filename}")

# Generate core screens
process_file(os.path.join(STITCH_DIR, "sachdeploy_dashboard", "code.html"), "index.html", "dashboard")
process_file(os.path.join(STITCH_DIR, "sachdeploy_dashboard", "code.html"), "dashboard.html", "dashboard")
process_file(os.path.join(STITCH_DIR, "sachdeploy_projects", "code.html"), "projects.html", "projects")
process_file(os.path.join(STITCH_DIR, "sachdeploy_deployments", "code.html"), "deployments.html", "deployments")
process_file(os.path.join(STITCH_DIR, "sachdeploy_containers", "code.html"), "containers.html", "containers")
process_file(os.path.join(STITCH_DIR, "sachdeploy_monitoring", "code.html"), "monitoring.html", "monitoring")
process_file(os.path.join(STITCH_DIR, "sachdeploy_terminal", "code.html"), "terminal.html", "terminal")
process_file(os.path.join(STITCH_DIR, "sachdeploy_settings", "code.html"), "settings.html", "settings")
process_file(os.path.join(STITCH_DIR, "sachdeploy_support", "code.html"), "support.html", "support")

# Derive Marketplace from Projects
proj_path = os.path.join(STITCH_DIR, "sachdeploy_projects", "code.html")
if os.path.exists(proj_path):
    with open(proj_path, "r", encoding="utf-8") as f:
        mkt_content = f.read()
    mkt_content = update_nav_links(mkt_content)
    mkt_content = mkt_content.replace(">Projects</h1>", ">One-Click Marketplace</h1>")
    mkt_content = mkt_content.replace("Manage and monitor your deployed services.", "Deploy pre-configured enterprise databases, AI models, and tools with one click.")
    mkt_content = re.sub(r'(<div class="grid grid-cols-1 lg:grid-cols-2 gap-gutter">)', r'<div id="marketplace-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">', mkt_content)
    mkt_content = inject_modals_and_scripts(mkt_content)
    with open(os.path.join(FRONTEND_DIR, "marketplace.html"), "w", encoding="utf-8") as f:
        f.write(mkt_content)
    print("Generated: marketplace.html")

# Derive Volumes and Networks from Containers
cont_path = os.path.join(STITCH_DIR, "sachdeploy_containers", "code.html")
if os.path.exists(cont_path):
    with open(cont_path, "r", encoding="utf-8") as f:
        vol_content = f.read()
    vol_content = update_nav_links(vol_content)
    vol_content = vol_content.replace("Container Overview", "Docker Volumes")
    vol_content = re.sub(r'<thead>.*?</thead>', r'<thead><tr class="border-b border-white/5 bg-white/2"><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">Volume Name</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">Driver</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">Scope</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">Created</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs text-right">Actions</th></tr></thead>', vol_content, flags=re.DOTALL)
    vol_content = re.sub(r'(<tbody class="divide-y divide-white/5">)', r'<tbody id="volumes-tbody" class="divide-y divide-white/5">', vol_content)
    vol_content = inject_modals_and_scripts(vol_content)
    with open(os.path.join(FRONTEND_DIR, "volumes.html"), "w", encoding="utf-8") as f:
        f.write(vol_content)
    print("Generated: volumes.html")

    with open(cont_path, "r", encoding="utf-8") as f:
        net_content = f.read()
    net_content = update_nav_links(net_content)
    net_content = net_content.replace("Container Overview", "Docker Networks")
    net_content = re.sub(r'<thead>.*?</thead>', r'<thead><tr class="border-b border-white/5 bg-white/2"><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">Network Name</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">ID</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">Driver</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">Scope</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs">Subnet</th><th class="px-6 py-4 font-bold text-on-surface-variant uppercase text-xs text-right">Actions</th></tr></thead>', net_content, flags=re.DOTALL)
    net_content = re.sub(r'(<tbody class="divide-y divide-white/5">)', r'<tbody id="networks-tbody" class="divide-y divide-white/5">', net_content)
    net_content = inject_modals_and_scripts(net_content)
    with open(os.path.join(FRONTEND_DIR, "networks.html"), "w", encoding="utf-8") as f:
        f.write(net_content)
    print("Generated: networks.html")

# Generate Premium Login Screen
LOGIN_HTML = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SachDeploy v2.0 Enterprise | Login</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&family=Geist:wght@600;700&display=swap" rel="stylesheet"/>
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        background: '#09090b',
                        surface: '#10131a',
                        primary: '#adc6ff',
                        'primary-container': '#4d8eff',
                    },
                    fontFamily: {
                        headline: ['Geist', 'sans-serif'],
                        body: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    }
                }
            }
        }
    </script>
    <style>
        body { background-color: #09090b; color: #e1e2ec; font-family: 'Inter', sans-serif; }
        .glass-card {
            background: rgba(24, 24, 27, 0.85);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
    <!-- Ambient glowing spheres -->
    <div class="absolute -top-40 -left-40 w-96 h-96 bg-primary/10 rounded-full blur-[120px] pointer-events-none"></div>
    <div class="absolute -bottom-40 -right-40 w-96 h-96 bg-[#ffb786]/10 rounded-full blur-[120px] pointer-events-none"></div>

    <div class="glass-card p-10 max-w-md w-full rounded-3xl relative z-10 border border-white/10 shadow-2xl space-y-8">
        <div class="text-center space-y-3">
            <div class="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto text-primary shadow-lg shadow-primary/10">
                <span class="material-symbols-outlined text-3xl">rocket_launch</span>
            </div>
            <h1 class="text-3xl font-bold font-headline tracking-tight text-white">SachDeploy</h1>
            <p class="text-sm text-gray-400">Enterprise Self-Hosted Cloud Management</p>
        </div>

        <form id="login-form" class="space-y-5" onsubmit="handleLoginSubmit(event)">
            <div class="space-y-1.5">
                <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider">Username</label>
                <div class="relative">
                    <span class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 text-lg">person</span>
                    <input type="text" id="username" required placeholder="admin"
                        class="w-full bg-[#0b0e15] border border-white/10 rounded-xl pl-11 pr-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-primary transition text-sm font-mono">
                </div>
            </div>
            <div class="space-y-1.5">
                <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider">Password</label>
                <div class="relative">
                    <span class="material-symbols-outlined absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500 text-lg">lock</span>
                    <input type="password" id="password" required placeholder="••••••••"
                        class="w-full bg-[#0b0e15] border border-white/10 rounded-xl pl-11 pr-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-primary transition text-sm font-mono">
                </div>
            </div>
            <div id="login-error" class="text-red-400 text-xs hidden bg-red-950/40 p-3 rounded-xl border border-red-500/30 text-center font-medium"></div>
            
            <button type="submit"
                class="w-full bg-primary hover:bg-primary-container text-[#002e6a] hover:text-white py-3.5 rounded-xl font-bold text-sm transition-all duration-200 shadow-lg shadow-primary/20 flex items-center justify-center gap-2 group">
                <span>Sign In to Dashboard</span>
                <span class="material-symbols-outlined text-lg group-hover:translate-x-1 transition-transform">arrow_forward</span>
            </button>
        </form>
        <div class="text-center border-t border-white/5 pt-4">
            <span class="text-[11px] text-gray-500 font-mono">v2.0.0 Stable Enterprise Edition</span>
        </div>
    </div>
    <script src="/app.js"></script>
    <script>
        async function handleLoginSubmit(e) {
            e.preventDefault();
            const u = document.getElementById('username').value;
            const p = document.getElementById('password').value;
            const err = document.getElementById('login-error');
            err.classList.add('hidden');
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: u, password: p })
                });
                const data = await res.json();
                if (res.ok && data.status === 'success') {
                    window.location.href = '/';
                } else {
                    err.textContent = data.message || 'Invalid username or password';
                    err.classList.remove('hidden');
                }
            } catch (error) {
                err.textContent = 'Connection error. Please check server status.';
                err.classList.remove('hidden');
            }
        }
    </script>
</body>
</html>
"""
with open(os.path.join(FRONTEND_DIR, "login.html"), "w", encoding="utf-8") as f:
    f.write(LOGIN_HTML)
print("Generated: login.html")
