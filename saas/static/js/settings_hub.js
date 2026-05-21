// settings_hub.js - Modular logic for AI Settings Hub (Credentials & Models)
import { App } from './state.js';
import { fetchTenantCredentials, saveTenantCredentials } from './api.js';
import { loadModels } from './workspace.js';

let tenantCredentialsCache = {};
let currentActiveProvider = localStorage.getItem('active_provider') || 'nvidia';

const baseProviders = [
    { id: 'nvidia', sdk: 'openai', ecosystem: 'NVIDIA NIM', default_url: 'https://integrate.api.nvidia.com/v1' },
    { id: 'google', sdk: 'google-genai', ecosystem: 'Google Gemini', default_url: 'https://generativelanguage.googleapis.com/v1beta' },
    { id: 'anthropic', sdk: 'anthropic', ecosystem: 'Anthropic', default_url: 'https://api.anthropic.com/v1' },
    { id: 'openai', sdk: 'openai', ecosystem: 'OpenAI / Compatible', default_url: 'https://api.openai.com/v1' }
];

export function switchSettingsTab(tabId) {
    document.querySelectorAll('.settings-tab').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.settings-content').forEach(el => el.classList.remove('active'));
    
    document.getElementById(`tab-btn-${tabId}`).classList.add('active');
    document.getElementById(`tab-content-${tabId}`).classList.add('active');
}

export async function loadSettingsHub() {
    try {
        tenantCredentialsCache = await fetchTenantCredentials(App.token);
        populateCredentialTable();
        renderModelManagerTable();
    } catch (e) {
        console.error("Failed to load settings hub credentials", e);
    }
}

function populateCredentialTable() {
    const tbody = document.getElementById('cred-manager-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    baseProviders.forEach(p => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--border-glow)';
        
        const hasKey = !!tenantCredentialsCache[p.id];
        const isActive = (currentActiveProvider === p.id);
        
        let statusHtml = '';
        if (isActive) {
            statusHtml = '<span style="color: var(--accent-cyan); font-weight: bold;"><i class="fa-solid fa-circle-check"></i> ACTIVE</span>';
        } else if (hasKey) {
            statusHtml = '<span style="color: var(--accent-green);"><i class="fa-solid fa-check"></i> AVAILABLE</span>';
        } else {
            statusHtml = '<span style="color: var(--text-dim);"><i class="fa-solid fa-xmark"></i> UNAVAILABLE</span>';
        }
        
        const currentUrl = tenantCredentialsCache[`${p.id}_base_url`] || p.default_url;
        let keyDisplay = hasKey ? '********' : 'Missing';
        let keyStyle = hasKey ? '' : 'color: var(--accent-red);';
        
        tr.innerHTML = `
            <td style="padding: 12px; text-align: center; font-size: 0.8rem;">${statusHtml}</td>
            <td style="padding: 12px; font-family: monospace; color: var(--text-dim);">${p.sdk}</td>
            <td style="padding: 12px; font-weight: 500;">${p.ecosystem}</td>
            <td style="padding: 12px; font-size: 0.85rem; color: var(--text-muted);">${currentUrl}</td>
            <td style="padding: 12px; font-family: monospace; ${keyStyle}">${keyDisplay}</td>
            <td style="padding: 12px; text-align: right;">
                <button onclick="window.editCredential('${p.id}')" class="btn-new" style="padding: 4px 10px; font-size: 0.75rem; width: auto; margin: 0 4px 0 0;">Edit</button>
                <button onclick="window.setActiveProvider('${p.id}')" class="btn-new" style="padding: 4px 10px; font-size: 0.75rem; width: auto; margin: 0; background: ${isActive ? 'var(--accent-cyan)' : ''}; color: ${isActive ? '#000' : ''};" ${isActive ? 'disabled' : ''}>Set Active</button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

window.editCredential = async function(providerId) {
    const p = baseProviders.find(x => x.id === providerId);
    if (!p) return;
    
    // Prompt for new key
    const currentKey = tenantCredentialsCache[providerId] || '';
    const newKey = prompt(`Enter new API Key for ${p.ecosystem}:`, currentKey);
    
    if (newKey === null) return; // User cancelled
    
    // Prompt for new Base URL
    const currentUrl = tenantCredentialsCache[`${providerId}_base_url`] || p.default_url;
    const newUrl = prompt(`Enter custom Base URL for ${p.ecosystem} (Leave as default if unsure):`, currentUrl);
    
    if (newUrl === null) return; // User cancelled
    
    try {
        const payload = {};
        
        if (newKey.trim() !== '' && !newKey.includes('***')) {
            payload[providerId] = newKey.trim();
        } else if (newKey.trim() === '') {
            payload[providerId] = '';
        }
        
        if (newUrl.trim() !== '') {
            payload[`${providerId}_base_url`] = newUrl.trim();
        }
        
        await saveTenantCredentials(App.token, payload);
        
        // Update local cache
        tenantCredentialsCache[providerId] = payload[providerId] !== undefined ? payload[providerId] : currentKey;
        tenantCredentialsCache[`${providerId}_base_url`] = newUrl.trim();
        
        populateCredentialTable();
        await loadModels();
        renderModelManagerTable();
        
        alert(`Successfully updated credentials for ${p.ecosystem}!`);
    } catch (e) {
        console.error("Failed to update credentials", e);
        alert("Failed to save credentials. Check console for details.");
    }
};

window.setActiveProvider = function(providerId) {
    const newProvider = baseProviders.find(x => x.id === providerId);
    const oldProvider = baseProviders.find(x => x.id === currentActiveProvider) || baseProviders[0];
    
    if (!newProvider) return;
    
    const confirmChange = confirm(`You are changing the active provider from ${oldProvider.ecosystem} to ${newProvider.ecosystem}. Accept?`);
    if (confirmChange) {
        currentActiveProvider = providerId;
        localStorage.setItem('active_provider', providerId);
        populateCredentialTable();
        alert('Saved! Active provider changed.');
    }
};

function renderModelManagerTable() {
    const tbody = document.getElementById('model-manager-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!App.availableModels || App.availableModels.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" style="text-align: center; padding: 1rem; color: var(--text-dim);">No unlocked models. Provide an API key to sync ecosystem nodes.</td></tr>`;
        return;
    }
    
    App.availableModels.forEach(m => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--border-glow)';
        
        const caps = m.capabilities || {};
        let capsHtml = '';
        if (caps.chat) capsHtml += '<i class="fa-solid fa-message" title="Chat" style="color: var(--accent-blue); margin: 0 4px;"></i>';
        if (caps.vision) capsHtml += '<i class="fa-solid fa-eye" title="Vision/Multimodal" style="color: var(--accent-cyan); margin: 0 4px;"></i>';
        if (caps.tools) capsHtml += '<i class="fa-solid fa-wrench" title="Tool Support" style="color: var(--accent-violet); margin: 0 4px;"></i>';
        
        tr.innerHTML = `
            <td style="padding: 12px; text-transform: uppercase; font-size: 0.8rem; color: var(--accent-cyan);">${m.owned_by}</td>
            <td style="padding: 12px; font-weight: 500;">${m.name || m.id} <br><span style="font-size: 0.75rem; color: var(--text-dim); font-weight: normal;">${m.id}</span></td>
            <td style="padding: 12px; text-align: center; font-size: 1.1rem;">${capsHtml}</td>
        `;
        tbody.appendChild(tr);
    });
}
