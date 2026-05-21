// settings_hub.js - Strict 1:1 Mirror logic for AI Settings Hub
import { App } from './state.js';
import { fetchTenantCredentials, saveTenantCredentials } from './api.js';
import { loadModels } from './workspace.js';

let tenantCredentialsCache = {};
let systemProviders = [];
let currentActiveProvider = localStorage.getItem('active_provider') || 'nvidia';

export function switchSettingsTab(tabId) {
    document.querySelectorAll('.settings-tab').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.settings-content').forEach(el => el.classList.remove('active'));
    
    document.getElementById(`tab-btn-${tabId}`).classList.add('active');
    document.getElementById(`tab-content-${tabId}`).classList.add('active');
}

export async function loadSettingsHub() {
    try {
        // Fetch dynamic provider list from backend
        const resp = await fetch('/v1/system/providers', { headers: { 'Authorization': `Bearer ${App.token}` } });
        const providerData = await resp.json();
        systemProviders = [...providerData.base, ...providerData.custom];
        
        tenantCredentialsCache = await fetchTenantCredentials(App.token);
        
        populateCredentialTable();
        
        // Initialize Model Ecosystem Filter
        populateEcosystemFilter();
        filterModels();
        
    } catch (e) {
        console.error("Failed to load settings hub credentials", e);
    }
}

function populateCredentialTable() {
    const tbody = document.getElementById('cred-manager-tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    systemProviders.forEach(p => {
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
            <td style="text-align: center; font-size: 0.75rem;">${statusHtml}</td>
            <td style="font-family: monospace; color: var(--text-dim);">${p.sdk}</td>
            <td style="font-weight: 500;">${p.ecosystem}</td>
            <td style="font-size: 0.8rem; color: var(--text-muted);">${currentUrl}</td>
            <td style="font-family: monospace; ${keyStyle}">${keyDisplay}</td>
            <td style="text-align: right;">
                <button onclick="window.editCredential('${p.id}')" class="btn-new" style="padding: 4px 10px; font-size: 0.75rem; width: auto; margin: 0 4px 0 0;">Edit</button>
                <button onclick="window.setActiveProvider('${p.id}')" class="btn-new" style="padding: 4px 10px; font-size: 0.75rem; width: auto; margin: 0; background: ${isActive ? 'var(--accent-cyan)' : ''}; color: ${isActive ? '#000' : ''};" ${isActive ? 'disabled' : ''}>Set Active</button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

window.editCredential = async function(providerId) {
    const p = systemProviders.find(x => x.id === providerId);
    if (!p) return;
    
    const currentKey = tenantCredentialsCache[providerId] || '';
    const newKey = prompt(`Enter new API Key for ${p.ecosystem}:`, currentKey);
    
    if (newKey === null) return;
    
    const currentUrl = tenantCredentialsCache[`${providerId}_base_url`] || p.default_url;
    const newUrl = prompt(`Enter custom Base URL for ${p.ecosystem} (Leave as default if unsure):`, currentUrl);
    
    if (newUrl === null) return;
    
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
        
        tenantCredentialsCache[providerId] = payload[providerId] !== undefined ? payload[providerId] : currentKey;
        tenantCredentialsCache[`${providerId}_base_url`] = newUrl.trim();
        
        populateCredentialTable();
        populateEcosystemFilter();
        filterModels();
        await loadModels();
        
        alert(`Successfully updated credentials for ${p.ecosystem}!`);
    } catch (e) {
        console.error("Failed to update credentials", e);
        alert("Failed to save credentials. Check console for details.");
    }
};

window.setActiveProvider = function(providerId) {
    const newProvider = systemProviders.find(x => x.id === providerId);
    const oldProvider = systemProviders.find(x => x.id === currentActiveProvider) || systemProviders[0];
    
    if (!newProvider) return;
    
    const confirmChange = confirm(`You are changing the active provider from ${oldProvider ? oldProvider.ecosystem : 'None'} to ${newProvider.ecosystem}. Accept?`);
    if (confirmChange) {
        currentActiveProvider = providerId;
        localStorage.setItem('active_provider', providerId);
        populateCredentialTable();
        alert('Saved! Active provider changed.');
    }
};

// --- Model Manager UI Logic (Mirrors ui/credential_manager.py populate_model_tabs) ---

function populateEcosystemFilter() {
    const select = document.getElementById('model-ecosystem-filter');
    if (!select) return;
    
    const currentValue = select.value;
    select.innerHTML = '<option value="All">🌐 All Ecosystems</option>';
    
    // Only add ecosystems that have keys
    const connected = new Set();
    systemProviders.forEach(p => {
        if (tenantCredentialsCache[p.id]) {
            connected.add(p.ecosystem);
        }
    });
    
    Array.from(connected).sort().forEach(eco => {
        const opt = document.createElement('option');
        opt.value = eco;
        opt.textContent = eco;
        select.appendChild(opt);
    });
    
    // Restore previous if still valid
    if (Array.from(select.options).some(o => o.value === currentValue)) {
        select.value = currentValue;
    }
}

window.filterModels = function() {
    const filter = document.getElementById('model-ecosystem-filter').value;
    const headerLabel = document.getElementById('model-header-label');
    
    if (filter === "All") {
        headerLabel.textContent = "Viewing ALL Connected Models";
    } else {
        headerLabel.textContent = `Managing ${filter.toUpperCase()}`;
    }
    
    renderModelDeveloperTabs(filter);
};

window.fetchModelsAPI = function() {
    alert("Fetching models for active ecosystems...");
};

function normalizeProviderName(pName) {
    let lower = (pName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    if (lower.includes('nvidia')) return 'nvidia';
    if (lower.includes('google')) return 'google';
    return lower;
}

function stripMarkdown(text) {
    if (!text) return '';
    return text.replace(/(\*\*|__)(.*?)\1/g, '$2') // bold
               .replace(/(\*|_)(.*?)\1/g, '$2')     // italic
               .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // links
               .replace(/`([^`]+)`/g, '$1')         // code
               .replace(/#+\s+(.*)/g, '$1')         // headers
               .replace(/>\s+(.*)/g, '$1')          // blockquotes
               .replace(/\n/g, ' ')                 // newlines to space
               .trim();
}

function renderModelDeveloperTabs(filterEcosystem) {
    const tabsHeader = document.getElementById('model-dev-tabs-header');
    const tabsContent = document.getElementById('model-dev-tabs-content');
    if (!tabsHeader || !tabsContent) return;
    
    tabsHeader.innerHTML = '';
    tabsContent.innerHTML = '';
    
    if (!App.modelsCache || App.modelsCache.length === 0) {
        tabsContent.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-dim);">No models fetched.</div>`;
        return;
    }
    
    // Determine which ecosystem ID corresponds to the filter
    let filterId = null;
    if (filterEcosystem !== "All") {
        const prov = systemProviders.find(p => p.ecosystem === filterEcosystem);
        if (prov) filterId = normalizeProviderName(prov.ecosystem);
    }
    
    // Group models by developer
    const modelsByDev = {};
    App.modelsCache.forEach(m => {
        const provNormalized = normalizeProviderName(m.provider || 'nvidia');
        
        // Filter by ecosystem if required
        if (filterId && provNormalized !== filterId) {
            return;
        }
        
        let dev = m.developer || 'Other';
        if (typeof dev === 'string' && dev.length > 0) {
            dev = dev.charAt(0).toUpperCase() + dev.slice(1).toLowerCase();
        }
        if (!modelsByDev[dev]) modelsByDev[dev] = [];
        modelsByDev[dev].push(m);
    });
    
    const sortedDevs = Object.keys(modelsByDev).sort();
    
    if (sortedDevs.length === 0) {
        tabsContent.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-dim);">No models available for ${filterEcosystem}.</div>`;
        return;
    }
    
    let first = true;
    sortedDevs.forEach(dev => {
        const safeDevId = dev.replace(/[^a-zA-Z0-9]/g, '-');
        
        // Tab Header
        const btn = document.createElement('button');
        btn.textContent = dev;
        btn.className = 'settings-tab' + (first ? ' active' : '');
        
        // Tab Content
        const contentDiv = document.createElement('div');
        contentDiv.id = `tab-dev-${safeDevId}`;
        contentDiv.style.display = first ? 'block' : 'none';
        
        const isGlobal = (filterEcosystem === "All");
        
        let tableHtml = `
            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left;">
                <thead style="border-bottom: 1px solid var(--border-glow); background: rgba(0,0,0,0.2);">
                    <tr>
                        <th>Model Name</th>
                        ${isGlobal ? '<th>Ecosystem</th>' : ''}
                        <th>Description</th>
                        <th style="text-align: center;">Status</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        modelsByDev[dev].forEach(m => {
            const isFree = m.free !== undefined ? m.free : true;
            const statusText = isFree ? 'Free' : 'Paid';
            const statusStyle = isFree ? 'color: #28a745; border: 1px solid #28a745; background: transparent;' : 'color: #dc3545; border: 1px solid #dc3545; background: transparent;';
            const badge = `<span style="padding: 2px 6px; border-radius: 2px; font-size: 0.8rem; font-weight: bold; display: inline-block; ${statusStyle}">${statusText}</span>`;
            
            tableHtml += `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer;" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='transparent'">
                    <td style="font-weight: 500;">${m.name || m.id}</td>
                    ${isGlobal ? `<td style="color: var(--accent-cyan);">${(m.provider || 'nvidia').toUpperCase()}</td>` : ''}
                    <td style="color: var(--text-dim); font-size: 0.8rem;">${stripMarkdown(m.description || '')}</td>
                    <td style="text-align: center;">${badge}</td>
                </tr>
            `;
        });
        
        tableHtml += `</tbody></table>`;
        contentDiv.innerHTML = tableHtml;
        
        btn.onclick = () => {
            Array.from(tabsHeader.children).forEach(c => {
                c.classList.remove('active');
            });
            Array.from(tabsContent.children).forEach(c => c.style.display = 'none');
            
            btn.classList.add('active');
            contentDiv.style.display = 'block';
        };
        
        tabsHeader.appendChild(btn);
        tabsContent.appendChild(contentDiv);
        first = false;
    });
}

// --- ADD PROVIDER MODAL LOGIC ---

window.showAddProviderModal = function() {
    document.getElementById('add-provider-modal').style.display = 'flex';
    document.getElementById('add-prov-sdk').value = 'openai';
    window.onSdkChanged();
};

window.onSdkChanged = function() {
    const sdk = document.getElementById('add-prov-sdk').value;
    const ecoSelect = document.getElementById('add-prov-eco');
    
    const sdkMap = {
        "openai": ["NVIDIA NIM", "GroqCloud", "Official OpenAI", "OpenRouter", "DeepSeek", "Perplexity", "Fireworks AI", "Novita AI", "Ollama (Local)", "vLLM Server", "LiteLLM Proxy", "Custom..."],
        "google-genai": ["Google Gemini"],
        "anthropic": ["Anthropic"],
        "cohere": ["Cohere"],
        "mistralai": ["Mistral AI"],
        "together": ["Together AI"],
        "replicate": ["Replicate"],
        "huggingface_hub": ["Hugging Face"],
        "litellm": ["LiteLLM Proxy"]
    };
    
    const ecosystems = sdkMap[sdk] || ["Custom..."];
    ecoSelect.innerHTML = '';
    
    ecosystems.forEach(eco => {
        const opt = document.createElement('option');
        opt.value = eco;
        opt.textContent = eco;
        ecoSelect.appendChild(opt);
    });
    
    window.onEcoChanged();
};

window.onEcoChanged = function() {
    const text = document.getElementById('add-prov-eco').value;
    const customContainer = document.getElementById('add-prov-custom-container');
    const urlEdit = document.getElementById('add-prov-url');
    
    const urlMap = {
        "NVIDIA NIM": "https://integrate.api.nvidia.com/v1",
        "Google Gemini": "https://generativelanguage.googleapis.com/v1beta",
        "GroqCloud": "https://api.groq.com/openai/v1",
        "OpenRouter": "https://openrouter.ai/api/v1",
        "DeepSeek": "https://api.deepseek.com",
        "Anthropic": "https://api.anthropic.com/v1",
        "Official OpenAI": "https://api.openai.com/v1",
        "Together AI": "https://api.together.xyz/v1",
        "Ollama (Local)": "http://localhost:11434/v1",
        "vLLM Server": "http://localhost:8000/v1",
        "LiteLLM Proxy": "http://localhost:4000/v1"
    };
    
    if (text === "Custom...") {
        customContainer.style.display = 'block';
        urlEdit.readOnly = false;
        urlEdit.value = '';
        urlEdit.placeholder = "Enter custom endpoint URL...";
    } else {
        customContainer.style.display = 'none';
        urlEdit.readOnly = true;
        urlEdit.value = urlMap[text] || "";
        urlEdit.placeholder = "";
    }
};

window.saveCustomProvider = async function() {
    alert("Saving custom providers via SaaS interface is being linked. Please use the Desktop app to add custom ecosystem parameters for now. You can input API keys for existing ecosystems using the main table.");
    document.getElementById('add-provider-modal').style.display = 'none';
};
