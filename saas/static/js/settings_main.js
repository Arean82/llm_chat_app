// settings_main.js - Unified Node Config Controller
import { App } from './state.js';
import { fetchAdminUsers } from './api.js';

let systemInstructions = [];
let sysEditorMode = 'add'; // 'add' or 'edit'

async function loadUserInstructions() {
    if (!App.user) return;
    
    if (App.user.key_type === 'admin_funded') {
        try {
            const res = await fetch('/api/admin/system_prompts', {
                headers: { 'Authorization': `Bearer ${App.token}` }
            });
            const data = await res.json();
            if (data.success && data.data && Array.isArray(data.data) && data.data.length > 0) {
                systemInstructions = data.data;
                return;
            }
        } catch (e) {
            console.error("Admin prompt sync failed:", e);
        }
    }
    if (App.user.key_type !== 'admin_funded') {
        try {
            const res = await fetch('/api/user/settings', {
                headers: { 'Authorization': `Bearer ${App.token}` }
            });
            const data = await res.json();
            if (data.success && data.data && data.data.systemInstructions && data.data.systemInstructions.length > 0) {
                systemInstructions = data.data.systemInstructions;
                return;
            }
        } catch(e) {
            console.error("User settings load failed:", e);
        }
    } else {
        // For admin, fallback to localStorage if they want to load gen params locally (for now sys instr is handled above)
        // Actually for admin, if fetch fails, we fall back to localStorage as before.
        const stored = localStorage.getItem(`sys_instr_${App.user.username}`);
        if (stored) {
            try {
                systemInstructions = JSON.parse(stored);
                if (!Array.isArray(systemInstructions)) throw new Error("Not an array");
                return;
            } catch (e) {
                console.warn("Resetting corrupt system instructions:", e);
            }
        }
    }
    
    // Default fallback
    systemInstructions = [
        { id: 1, name: "General Assistant", text: "You are a helpful, intelligent AI assistant.", checked: true }
    ];
    saveUserInstructions();
}

async function saveUserInstructions() {
    if (!App.user) return;
    if (App.user.key_type === 'admin_funded') {
        try {
            await fetch('/api/admin/system_prompts', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${App.token}`
                },
                body: JSON.stringify(systemInstructions)
            });
        } catch(e) {
            console.error("Admin prompt push failed:", e);
        }
        localStorage.setItem(`sys_instr_${App.user.username}`, JSON.stringify(systemInstructions));
    } else {
        try {
            const res = await fetch('/api/user/settings', { headers: { 'Authorization': `Bearer ${App.token}` } });
            const data = await res.json();
            const current = data.data || {};
            current.systemInstructions = systemInstructions;
            await fetch('/api/user/settings', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${App.token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(current)
            });
        } catch(e) {
            console.error("Failed to save user instructions to db:", e);
        }
    }
}

export async function getActiveSystemPrompt() {
    if (systemInstructions.length === 0) await loadUserInstructions();
    const active = systemInstructions.find(i => i.checked);
    return active ? active.text : "";
}

// ==========================================
// SYSTEM INSTRUCTION MANAGER
// ==========================================
function renderSystemInstructions() {
    const tbody = document.getElementById('nc-sys-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    const searchTerm = (document.getElementById('sys-search-input')?.value || "").toLowerCase();
    
    systemInstructions.forEach(instr => {
        if (searchTerm && !instr.name.toLowerCase().includes(searchTerm)) return;
        
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        
        tr.innerHTML = `
            <td style="padding: 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <input type="checkbox" class="sys-instr-check" data-id="${instr.id}" ${instr.checked ? 'checked' : ''}>
            </td>
            <td style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);">${instr.name}</td>
        `;
        
        tr.addEventListener('click', (e) => {
            if (e.target.classList.contains('sys-instr-check')) return;
            document.querySelectorAll('#nc-sys-tbody tr').forEach(row => row.style.background = 'transparent');
            tr.style.background = 'rgba(255,255,255,0.1)';
            document.getElementById('nc-sys-preview').value = instr.text;
            window._activeInstrId = instr.id;
        });
        
        const check = tr.querySelector('.sys-instr-check');
        check.addEventListener('change', (e) => {
            systemInstructions.forEach(i => i.checked = false);
            instr.checked = e.target.checked;
            saveUserInstructions();
            renderSystemInstructions();
        });
        
        tbody.appendChild(tr);
    });
}

function openSysEditor(mode) {
    sysEditorMode = mode;
    document.getElementById('sys-editor-title').textContent = mode === 'add' ? "Add Instruction" : "Edit Instruction";
    document.getElementById('sys-editor-name').value = "";
    document.getElementById('sys-editor-text').value = "";
    
    if (mode === 'edit') {
        if (!window._activeInstrId) {
            alert("Please select an instruction to edit.");
            return;
        }
        const instr = systemInstructions.find(i => i.id === window._activeInstrId);
        if (instr) {
            document.getElementById('sys-editor-name').value = instr.name;
            document.getElementById('sys-editor-text').value = instr.text;
        }
    }
    document.getElementById('sys-editor-modal').style.display = 'flex';
}

function closeSysEditor() {
    document.getElementById('sys-editor-modal').style.display = 'none';
}

function saveSysEditor() {
    const name = document.getElementById('sys-editor-name').value.trim();
    const text = document.getElementById('sys-editor-text').value.trim();
    if (!name || !text) {
        alert("Name and Text cannot be empty.");
        return;
    }
    
    if (sysEditorMode === 'add') {
        const newId = Math.max(...systemInstructions.map(i => i.id), 0) + 1;
        systemInstructions.push({ id: newId, name, text, checked: false });
    } else {
        const instr = systemInstructions.find(i => i.id === window._activeInstrId);
        if (instr) {
            instr.name = name;
            instr.text = text;
        }
    }
    
    saveUserInstructions();
    renderSystemInstructions();
    closeSysEditor();
}

function handleDeleteInstruction() {
    if (!window._activeInstrId) {
        alert("Please select an instruction to delete.");
        return;
    }
    const instr = systemInstructions.find(i => i.id === window._activeInstrId);
    if (!instr) return;
    
    if (confirm(`Are you sure you want to delete "${instr.name}"?`)) {
        systemInstructions = systemInstructions.filter(i => i.id !== instr.id);
        saveUserInstructions();
        window._activeInstrId = null;
        document.getElementById('nc-sys-preview').value = '';
        renderSystemInstructions();
    }
}

async function loadUserGenParams() {
    if (!App.user) return;
    
    let p = null;
    if (App.user.key_type === 'admin_funded') {
        try {
            const res = await fetch('/api/admin/gen_params', { headers: { 'Authorization': `Bearer ${App.token}` } });
            const data = await res.json();
            if (data.success && data.data) {
                p = data.data;
            }
        } catch(e) {
            console.error("Admin gen_params load failed:", e);
        }
    } else {
        try {
            const res = await fetch('/api/user/settings', { headers: { 'Authorization': `Bearer ${App.token}` } });
            const data = await res.json();
            if (data.success && data.data && data.data.genParams) {
                p = data.data.genParams;
            }
        } catch(e) {}
    }
    
    if (p) {
        if (document.getElementById('nc-preset')) document.getElementById('nc-preset').value = p.preset || "0";
        if (document.getElementById('nc-temp')) {
            document.getElementById('nc-temp').value = p.temp || 0.7;
            document.getElementById('nc-temp-val').textContent = p.temp || 0.7;
            updateTempExplanation(parseFloat(p.temp || 0.7));
        }
        if (document.getElementById('nc-max-tokens')) document.getElementById('nc-max-tokens').value = p.max_tokens || 4096;
        if (document.getElementById('nc-rerank-enable')) document.getElementById('nc-rerank-enable').checked = p.rerank_enable || false;
        if (document.getElementById('nc-rerank-engine')) document.getElementById('nc-rerank-engine').value = p.rerank_engine || "local";
        if (document.getElementById('nc-rag-k')) document.getElementById('nc-rag-k').value = p.rag_k || 5;
        if (document.getElementById('nc-rerank-endpoint')) document.getElementById('nc-rerank-endpoint').value = p.rerank_endpoint || "";
        if (document.getElementById('nc-rerank-key')) document.getElementById('nc-rerank-key').value = p.rerank_key || "";
        if (document.getElementById('nc-logging-opt')) document.getElementById('nc-logging-opt').checked = p.logging || false;
    }
}

export async function saveUserGenParams() {
    if (!App.user) return;
    const p = {
        preset: document.getElementById('nc-preset')?.value || "0",
        temp: document.getElementById('nc-temp')?.value || 0.7,
        max_tokens: document.getElementById('nc-max-tokens')?.value || 4096,
        rerank_enable: document.getElementById('nc-rerank-enable')?.checked || false,
        rerank_engine: document.getElementById('nc-rerank-engine')?.value || "local",
        rag_k: document.getElementById('nc-rag-k')?.value || 5,
        rerank_endpoint: document.getElementById('nc-rerank-endpoint')?.value || "",
        rerank_key: document.getElementById('nc-rerank-key')?.value || "",
        logging: document.getElementById('nc-logging-opt')?.checked || false
    };
    
    if (App.user.key_type === 'admin_funded') {
        try {
            await fetch('/api/admin/gen_params', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${App.token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(p)
            });
        } catch(e) {
            console.error("Admin gen_params save failed:", e);
        }
    } else {
        try {
            const res = await fetch('/api/user/settings', { headers: { 'Authorization': `Bearer ${App.token}` } });
            const data = await res.json();
            const current = data.data || {};
            current.genParams = p;
            await fetch('/api/user/settings', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${App.token}`, 'Content-Type': 'application/json' },
                body: JSON.stringify(current)
            });
        } catch(e) {
            console.error("Failed to save gen params to db:", e);
        }
    }
}


// ==========================================
// ADMIN SAAS CONFIG (SMTP ALERTS)
// ==========================================
async function loadAdminSaaSConfig() {
    if (!App.user || App.user.key_type !== 'admin_funded') return;
    
    try {
        const res = await fetch('/api/admin/saas_config', { headers: { 'Authorization': `Bearer ${App.token}` } });
        const data = await res.json();
        if (data.success && data.data) {
            const p = data.data;
            const elEnable = document.getElementById('nc-smtp-enable');
            const elHost = document.getElementById('nc-smtp-host');
            const elPort = document.getElementById('nc-smtp-port');
            const elUser = document.getElementById('nc-smtp-user');
            const elPass = document.getElementById('nc-smtp-pass');
            
            if (elEnable) elEnable.checked = p.smtp_enabled || false;
            if (elHost) elHost.value = p.smtp_host || "";
            if (elPort) elPort.value = p.smtp_port || 587;
            if (elUser) elUser.value = p.smtp_user || "";
            if (elPass) elPass.value = p.smtp_password || "";
        }
    } catch(e) {
        console.error("Admin SaaS config load failed:", e);
    }
}

export async function saveAdminSaaSConfig() {
    if (!App.user || App.user.key_type !== 'admin_funded') return;
    
    const p = {
        smtp_enabled: document.getElementById('nc-smtp-enable')?.checked || false,
        smtp_host: document.getElementById('nc-smtp-host')?.value || "",
        smtp_port: document.getElementById('nc-smtp-port')?.value || 587,
        smtp_user: document.getElementById('nc-smtp-user')?.value || "",
        smtp_password: document.getElementById('nc-smtp-pass')?.value || ""
    };
    
    try {
        await fetch('/api/admin/saas_config', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${App.token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(p)
        });
    } catch(e) {
        console.error("Admin SaaS config save failed:", e);
    }
}

export function switchNodeConfigTab(tabId) {
    document.querySelectorAll('#node-config-modal .settings-tab').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('#node-config-modal .settings-content').forEach(el => el.classList.remove('active'));
    
    document.getElementById(`tab-btn-nc-${tabId}`).classList.add('active');
    document.getElementById(`tab-content-nc-${tabId}`).classList.add('active');

    if (tabId === 'extensions' && window.loadExtensionsHub) {
        window.loadExtensionsHub();
    }
}

export async function openNodeConfigModal() {
    if (!App.user) return;
    
    // Ensure user instructions are loaded before opening
    await loadUserInstructions();
    
    const isAdmin = App.user.key_type === 'admin_funded';
    document.querySelectorAll('.admin-only-tab').forEach(el => {
        if (isAdmin) el.classList.remove('hidden');
        else el.classList.add('hidden');
    });
    
    switchNodeConfigTab('sys-instruct');
    
    // Init Generation Params
    await loadUserGenParams();
    
    if (isAdmin) {
        await loadAdminSaaSConfig();
        await loadAdminData();
    }
    
    renderSystemInstructions();
    
    document.getElementById('node-config-modal').style.display = 'flex';
}

export function closeNodeConfigModal() {
    document.getElementById('node-config-modal').style.display = 'none';
}

// ==========================================
// GENERATION PARAMS LOGIC
// ==========================================
function updateTempExplanation(val) {
    const descEl = document.getElementById('nc-temp-desc');
    if (!descEl) return;
    if (val <= 0.2) descEl.innerHTML = "💡 **Precise**: Strictly factual. Best for pure computer code.";
    else if (val <= 0.5) descEl.innerHTML = "⚖️ **Coherent**: Mostly factual. Good for formal business summaries.";
    else if (val <= 0.8) descEl.innerHTML = "🤝 **Balanced**: Standard defaults. Best all-rounder.";
    else if (val <= 1.2) descEl.innerHTML = "🎨 **Creative**: High variance. Best for fiction and brainstorming.";
    else descEl.innerHTML = "🔥 **Experimental**: Total chaos. Highly random and unpredictable.";
}

function updateTokensExplanation(val) {
    const descEl = document.getElementById('nc-token-desc');
    if (descEl) {
        descEl.innerHTML = `📏 Ceiling for response length. ~${Math.floor(val * 0.75)} English words max.`;
    }
}

function onPresetChanged(e) {
    const preset = e.target.value;
    const tempIn = document.getElementById('nc-temp');
    const tokensIn = document.getElementById('nc-max-tokens');
    const tempDesc = document.getElementById('nc-temp-desc');
    const tokenDesc = document.getElementById('nc-token-desc');
    
    if (preset === "1") { // Precise
        tempIn.disabled = tokensIn.disabled = false;
        tempIn.value = 0.1; tokensIn.value = 4096;
    } else if (preset === "2") { // Balanced
        tempIn.disabled = tokensIn.disabled = false;
        tempIn.value = 0.7; tokensIn.value = 4096;
    } else if (preset === "3") { // Creative
        tempIn.disabled = tokensIn.disabled = false;
        tempIn.value = 1.0; tokensIn.value = 8192;
    } else if (preset === "4") { // Model Default
        tempIn.disabled = tokensIn.disabled = true;
        tempDesc.innerHTML = "☁️ Using remote cloud baseline. No overrides active.";
        tokenDesc.innerHTML = "☁️ Using remote cloud baseline. No overrides active.";
        document.getElementById('nc-temp-val').textContent = "-";
        return;
    } else { // Custom
        tempIn.disabled = tokensIn.disabled = false;
    }
    
    document.getElementById('nc-temp-val').textContent = tempIn.value;
    updateTempExplanation(parseFloat(tempIn.value));
    updateTokensExplanation(parseInt(tokensIn.value));
}

function onRerankEnabledToggled(e) {
    const engineCombo = document.getElementById('nc-rerank-engine');
    engineCombo.disabled = !e.target.checked;
    if (e.target.checked) {
        onRerankEngineChanged({ target: engineCombo });
    } else {
        document.getElementById('nc-rerank-custom-fields').style.display = 'none';
    }
}

function onRerankEngineChanged(e) {
    if (!document.getElementById('nc-rerank-enable').checked) return;
    const fields = document.getElementById('nc-rerank-custom-fields');
    const ep = document.getElementById('nc-rerank-endpoint');
    const key = document.getElementById('nc-rerank-key');
    
    if (e.target.value === "local") {
        fields.style.display = 'none';
    } else if (e.target.value === "cloud_cohere") {
        fields.style.display = 'grid';
        ep.parentElement.style.display = 'none'; // hide endpoint
        key.parentElement.style.display = 'block';
    } else if (e.target.value === "cloud_custom") {
        fields.style.display = 'grid';
        ep.parentElement.style.display = 'block';
        key.parentElement.style.display = 'block';
    }
}

// ==========================================
// ADMIN LOADERS
// ==========================================
async function loadAdminData() {
    try {
        const res = await fetchAdminUsers(App.token);
        const users = res?.data || [];
        const tbody = document.getElementById('nc-tenants-tbody');
        if(!tbody) return;
        tbody.innerHTML = '';
        
        if (users && users.length > 0) {
            users.forEach(u => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);">${u.username}</td>
                    <td style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);">${u.role || 'Standard'}</td>
                    <td style="padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05);">${u.usage?.prompt_tokens || 0} tokens</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; padding: 15px; color: var(--text-dim);">No tenants found.</td></tr>';
        }
        
        const alertsContainer = document.getElementById('nc-auth-alerts-container');
        if(alertsContainer) {
            alertsContainer.innerHTML = `
                <div>[WARN] Failed login attempt from IP 192.168.1.55</div>
                <div>[INFO] Passport validated for user: system_admin</div>
                <div>[INFO] New tenant registration: guest_pilot_88</div>
                <div style="color: var(--text-dim); margin-top: 10px;">-- End of log --</div>
            `;
        }
    } catch (err) {
        console.error("Failed to load admin data for Node Config:", err);
    }
}

export function setupNodeConfigListeners() {
    const closeBtn = document.getElementById('btn-close-node-config');
    if (closeBtn) closeBtn.addEventListener('click', closeNodeConfigModal);
    
    const applyBtn = document.getElementById('btn-nc-apply');
    if (applyBtn) {
        applyBtn.addEventListener('click', () => {
            console.log("Configuration Applied");
            closeNodeConfigModal();
        });
    }
    
    // Tabs
    ['sys-instruct', 'gen-params', 'rerank', 'telemetry', 'auth-alerts', 'tenants', 'local-api', 'extensions'].forEach(tabId => {
        const tabBtn = document.getElementById(`tab-btn-nc-${tabId}`);
        if (tabBtn) tabBtn.addEventListener('click', () => switchNodeConfigTab(tabId));
    });
    
    // Sliders & Presets
    const tempSlider = document.getElementById('nc-temp');
    if (tempSlider) {
        tempSlider.addEventListener('input', (e) => {
            document.getElementById('nc-temp-val').textContent = e.target.value;
            updateTempExplanation(parseFloat(e.target.value));
            document.getElementById('nc-preset').value = "0"; // Set to Custom
            saveUserGenParams();
        });
    }
    
    const tokenIn = document.getElementById('nc-max-tokens');
    if (tokenIn) {
        tokenIn.addEventListener('input', (e) => {
            updateTokensExplanation(parseInt(e.target.value));
            document.getElementById('nc-preset').value = "0"; // Set to Custom
            saveUserGenParams();
        });
    }
    
    const presetCombo = document.getElementById('nc-preset');
    if (presetCombo) presetCombo.addEventListener('change', (e) => {
        onPresetChanged(e);
        saveUserGenParams();
    });
    
    const rerankEnable = document.getElementById('nc-rerank-enable');
    if (rerankEnable) rerankEnable.addEventListener('change', (e) => {
        onRerankEnabledToggled(e);
        saveUserGenParams();
    });
    
    const rerankEngine = document.getElementById('nc-rerank-engine');
    if (rerankEngine) rerankEngine.addEventListener('change', (e) => {
        onRerankEngineChanged(e);
        saveUserGenParams();
    });
    
    const ragK = document.getElementById('nc-rag-k');
    if (ragK) ragK.addEventListener('input', saveUserGenParams);
    
    const rerankEndpoint = document.getElementById('nc-rerank-endpoint');
    if (rerankEndpoint) rerankEndpoint.addEventListener('input', saveUserGenParams);
    
    const rerankKey = document.getElementById('nc-rerank-key');
    if (rerankKey) rerankKey.addEventListener('input', saveUserGenParams);
    
    const logOpt = document.getElementById('nc-logging-opt');
    if (logOpt) logOpt.addEventListener('change', saveUserGenParams);
    
    // Bind SMTP Configuration inputs
    const smtpEnable = document.getElementById('nc-smtp-enable');
    const smtpHost = document.getElementById('nc-smtp-host');
    const smtpPort = document.getElementById('nc-smtp-port');
    const smtpUser = document.getElementById('nc-smtp-user');
    const smtpPass = document.getElementById('nc-smtp-pass');
    
    if (smtpEnable) smtpEnable.addEventListener('change', saveAdminSaaSConfig);
    if (smtpHost) smtpHost.addEventListener('input', saveAdminSaaSConfig);
    if (smtpPort) smtpPort.addEventListener('input', saveAdminSaaSConfig);
    if (smtpUser) smtpUser.addEventListener('input', saveAdminSaaSConfig);
    if (smtpPass) smtpPass.addEventListener('input', saveAdminSaaSConfig);
    
    // System Instruction Manager Bindings
    const btnAdd = document.getElementById('btn-sys-add');
    if (btnAdd) btnAdd.addEventListener('click', () => openSysEditor('add'));
    
    const btnEdit = document.getElementById('btn-sys-edit');
    if (btnEdit) btnEdit.addEventListener('click', () => openSysEditor('edit'));
    
    const btnDelete = document.getElementById('btn-sys-delete');
    if (btnDelete) btnDelete.addEventListener('click', handleDeleteInstruction);
    
    const btnSaveEditor = document.getElementById('btn-sys-editor-save');
    if (btnSaveEditor) btnSaveEditor.addEventListener('click', saveSysEditor);
    
    const btnCancelEditor = document.getElementById('btn-sys-editor-cancel');
    if (btnCancelEditor) btnCancelEditor.addEventListener('click', closeSysEditor);
    
    const searchInput = document.getElementById('sys-search-input');
    if (searchInput) searchInput.addEventListener('input', renderSystemInstructions);
}

window.switchNodeConfigTab = switchNodeConfigTab;
window.openNodeConfigModal = openNodeConfigModal;
window.closeNodeConfigModal = closeNodeConfigModal;

document.addEventListener('DOMContentLoaded', () => {
    setupNodeConfigListeners();
});
