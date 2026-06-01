// settings_hub.js - Strict 1:1 Mirror logic for AI Settings Hub
import { App } from './state.js';
import { fetchTenantCredentials, saveTenantCredentials } from './api.js';
import { loadModels } from './workspace.js';

function isValidKey(key) {
  // Allow only alphanumeric, hyphen, underscore keys and block prototype properties
  return typeof key === "string" && /^[a-zA-Z0-9_-]+$/.test(key) && !["__proto__", "prototype", "constructor"].includes(key);
}

function safeGet(obj, key) {
  return isValidKey(key) && Object.prototype.hasOwnProperty.call(obj, key) ? Reflect.get(obj, key) : undefined;
}

function safeSet(obj, key, value) {
  if (isValidKey(key)) {
    Reflect.set(obj, key, value);
  }
}

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
        
        // Initialize Failover Sequence
        if (window.renderFailoverUI) {
            await window.renderFailoverUI();
        }
        
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
        
        const hasKey = !!safeGet(tenantCredentialsCache, p.id);
        const isActive = (currentActiveProvider === p.id);
        
        let statusHtml = '';
        if (isActive) {
            statusHtml = '<span style="color: var(--accent-cyan); font-weight: bold;"><i class="fa-solid fa-circle-check"></i> ACTIVE</span>';
        } else if (hasKey) {
            statusHtml = '<span style="color: var(--accent-green);"><i class="fa-solid fa-check"></i> AVAILABLE</span>';
        } else {
            statusHtml = '<span style="color: var(--text-dim);"><i class="fa-solid fa-xmark"></i> UNAVAILABLE</span>';
        }
        
        const currentUrl = safeGet(tenantCredentialsCache, `${p.id}_base_url`) || p.default_url;
        let keyDisplay = hasKey ? '********' : 'Missing';
        let keyStyle = hasKey ? '' : 'color: var(--accent-red);';
        
        // Safe DOM Construction to prevent XSS
        const tdStatus = document.createElement('td');
        tdStatus.style.cssText = "text-align: center; font-size: 0.75rem;";
        tdStatus.innerHTML = statusHtml; // Safe, built strictly from internal logic

        const tdSdk = document.createElement('td');
        tdSdk.style.cssText = "font-family: monospace; color: var(--text-dim);";
        tdSdk.textContent = p.sdk; // Unescaped user data: Use textContent

        const tdEco = document.createElement('td');
        tdEco.style.cssText = "font-weight: 500;";
        tdEco.textContent = p.ecosystem; // Unescaped user data: Use textContent

        const tdUrl = document.createElement('td');
        tdUrl.style.cssText = "font-size: 0.8rem; color: var(--text-muted);";
        tdUrl.textContent = currentUrl; // Unescaped user data: Use textContent

        const tdKey = document.createElement('td');
        tdKey.style.cssText = `font-family: monospace; ${keyStyle}`;
        tdKey.textContent = keyDisplay; // Unescaped user data: Use textContent

        const tdActions = document.createElement('td');
        tdActions.style.textAlign = "right";
        
        // Use textContent for p.id just in case, though it is usually safe. 
        // We will build the buttons cleanly.
        const btnEdit = document.createElement('button');
        btnEdit.className = "btn-new";
        btnEdit.style.cssText = "padding: 4px 10px; font-size: 0.75rem; width: auto; margin: 0 4px 0 0;";
        btnEdit.textContent = "Edit";
        btnEdit.onclick = () => window.editCredential(p.id);

        const btnActive = document.createElement('button');
        btnActive.className = "btn-new";
        btnActive.style.cssText = `padding: 4px 10px; font-size: 0.75rem; width: auto; margin: 0; background: ${isActive ? 'var(--accent-cyan)' : ''}; color: ${isActive ? '#000' : ''};`;
        btnActive.textContent = "Set Active";
        btnActive.disabled = isActive;
        btnActive.onclick = () => window.setActiveProvider(p.id);

        tdActions.appendChild(btnEdit);
        tdActions.appendChild(btnActive);

        tr.appendChild(tdStatus);
        tr.appendChild(tdSdk);
        tr.appendChild(tdEco);
        tr.appendChild(tdUrl);
        tr.appendChild(tdKey);
        tr.appendChild(tdActions);
        
        tbody.appendChild(tr);
    });
}

window.editCredential = async function(providerId) {
    const p = systemProviders.find(x => x.id === providerId);
    if (!p) return;
    
    const currentKey = safeGet(tenantCredentialsCache, providerId) || '';
    const newKey = prompt(`Enter new API Key for ${p.ecosystem}:`, currentKey);
    
    if (newKey === null) return;
    
    const currentUrl = safeGet(tenantCredentialsCache, `${providerId}_base_url`) || p.default_url;
    const newUrl = prompt(`Enter custom Base URL for ${p.ecosystem} (Leave as default if unsure):`, currentUrl);
    
    if (newUrl === null) return;
    
    try {
        const payload = {};
        
        if (newKey.trim() !== '' && !newKey.includes('***')) {
            Reflect.set(payload, providerId, newKey.trim());
        } else if (newKey.trim() === '') {
            Reflect.set(payload, providerId, '');
        }
        
        if (newUrl.trim() !== '') {
            Reflect.set(payload, `${providerId}_base_url`, newUrl.trim());
        }
        
        await saveTenantCredentials(App.token, payload);
        
        safeSet(tenantCredentialsCache, providerId, Reflect.get(payload, providerId) !== undefined ? Reflect.get(payload, providerId) : currentKey);
        safeSet(tenantCredentialsCache, `${providerId}_base_url`, newUrl.trim());
        
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
        if (safeGet(tenantCredentialsCache, p.id)) {
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
        if (!Reflect.has(modelsByDev, dev)) Reflect.set(modelsByDev, dev, []);
        Reflect.get(modelsByDev, dev).push(m);
    });
    
    const sortedDevs = Object.keys(modelsByDev).sort();
    
    if (sortedDevs.length === 0) {
        // Clear previous content
        while (tabsContent.firstChild) tabsContent.removeChild(tabsContent.firstChild);
        const emptyDiv = document.createElement('div');
        emptyDiv.style.textAlign = 'center';
        emptyDiv.style.padding = '2rem';
        emptyDiv.style.color = 'var(--text-dim)';
        emptyDiv.textContent = `No models available for ${filterEcosystem}.`;
        tabsContent.appendChild(emptyDiv);
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
        
        const table = document.createElement('table');
        table.style.cssText = "width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left;";
        
        const thead = document.createElement('thead');
        thead.style.cssText = "border-bottom: 1px solid var(--border-glow); background: rgba(0,0,0,0.2);";
        const trHead = document.createElement('tr');
        
        const thName = document.createElement('th');
        thName.textContent = "Model Name";
        trHead.appendChild(thName);
        
        if (isGlobal) {
            const thEco = document.createElement('th');
            thEco.textContent = "Ecosystem";
            trHead.appendChild(thEco);
        }
        
        const thDesc = document.createElement('th');
        thDesc.textContent = "Description";
        trHead.appendChild(thDesc);
        
        const thStatus = document.createElement('th');
        thStatus.textContent = "Status";
        thStatus.style.textAlign = "center";
        trHead.appendChild(thStatus);
        
        thead.appendChild(trHead);
        table.appendChild(thead);
        
        const tbody = document.createElement('tbody');
        
        Reflect.get(modelsByDev, dev).forEach(m => {
            const isFree = m.free !== undefined ? m.free : true;
            const statusText = isFree ? 'Free' : 'Paid';
            const statusStyle = isFree ? 'color: #28a745; border: 1px solid #28a745; background: transparent;' : 'color: #dc3545; border: 1px solid #dc3545; background: transparent;';
            
            const tr = document.createElement('tr');
            tr.style.cssText = "border-bottom: 1px solid rgba(255,255,255,0.05); cursor: pointer;";
            tr.onmouseover = () => tr.style.background = 'rgba(255,255,255,0.05)';
            tr.onmouseout = () => tr.style.background = 'transparent';
            
            const tdName = document.createElement('td');
            tdName.style.fontWeight = "500";
            tdName.textContent = m.name || m.id;
            tr.appendChild(tdName);
            
            if (isGlobal) {
                const tdEco = document.createElement('td');
                tdEco.style.color = "var(--accent-cyan)";
                tdEco.textContent = (m.provider || 'nvidia').toUpperCase();
                tr.appendChild(tdEco);
            }
            
            const tdDesc = document.createElement('td');
            tdDesc.style.cssText = "color: var(--text-dim); font-size: 0.8rem;";
            tdDesc.textContent = stripMarkdown(m.description || '');
            tr.appendChild(tdDesc);
            
            const tdStatus = document.createElement('td');
            tdStatus.style.textAlign = "center";
            const badge = document.createElement('span');
            badge.style.cssText = `padding: 2px 6px; border-radius: 2px; font-size: 0.8rem; font-weight: bold; display: inline-block; ${statusStyle}`;
            badge.textContent = statusText;
            tdStatus.appendChild(badge);
            tr.appendChild(tdStatus);
            
            tbody.appendChild(tr);
        });
        
        table.appendChild(tbody);
        
        while (contentDiv.firstChild) contentDiv.removeChild(contentDiv.firstChild);
        contentDiv.appendChild(table);
        
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
    // Clear ecosystem select options safely
    while (ecoSelect.firstChild) ecoSelect.removeChild(ecoSelect.firstChild);
    
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
    const sdk = document.getElementById('add-prov-sdk').value;
    let ecosystem = document.getElementById('add-prov-eco').value;
    const url = document.getElementById('add-prov-url').value;
    const key = document.getElementById('add-prov-key').value;
    
    if (ecosystem === "Custom...") {
        ecosystem = document.getElementById('add-prov-custom-eco').value;
    }
    
    if (!ecosystem || !url) {
        alert("Ecosystem name and URL are required.");
        return;
    }
    
    try {
        const payload = { sdk, ecosystem, url };
        await fetch('/v1/system/providers', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${App.token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (key.trim() !== '') {
            const eco_key = ecosystem.toLowerCase().replace(/ /g, '_');
            const provId = `${sdk}_${eco_key}`;
            const keyPayload = {};
            keyPayload[provId] = key.trim();
            await saveTenantCredentials(App.token, keyPayload);
        }
        
        document.getElementById('add-provider-modal').style.display = 'none';
        alert(`Custom Provider ${ecosystem} saved successfully!`);
        
        // Reload credentials table
        await loadSettingsHub();
    } catch (e) {
        console.error("Failed to save custom provider", e);
        alert("Failed to save custom provider. Check console for details.");
    }
};

window.showAddModelModal = function() {
    document.getElementById('add-model-modal').style.display = 'flex';
};

window.saveAdminModel = async function() {
    if (!App.user || App.user.key_type !== 'admin_funded') {
        alert("Only the Admin can modify models globally.");
        return;
    }
    
    const id = document.getElementById('add-mod-id').value.trim();
    if (!id) {
        alert("Model ID is required.");
        return;
    }
    
    const payload = {
        id: id,
        name: document.getElementById('add-mod-name').value.trim() || id,
        provider: document.getElementById('add-mod-provider').value.trim() || "nvidia",
        developer: document.getElementById('add-mod-dev').value.trim() || "Custom",
        description: document.getElementById('add-mod-desc').value.trim(),
        context_window: parseInt(document.getElementById('add-mod-ctx').value) || 4096,
        free: document.getElementById('add-mod-free').checked
    };
    
    try {
        await fetch('/api/admin/models', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${App.token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        document.getElementById('add-model-modal').style.display = 'none';
        alert(`Model ${payload.id} saved successfully!`);
        
        // Reload Models
        if (window.fetchModelsAPI) {
            window.fetchModelsAPI();
        }
    } catch (e) {
        console.error("Failed to save model", e);
        alert("Failed to save model. Check console.");
    }
};

// --- AUTO-FAILOVER LOGIC (DRAG AND DROP) ---

window.renderFailoverUI = async function() {
    const listEl = document.getElementById('failover-sortable-list');
    if (!listEl) return;
    // Show loading placeholder safely
    while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
    const loadingLi = document.createElement('li');
    loadingLi.style.padding = '10px';
    loadingLi.style.color = '#888';
    loadingLi.textContent = 'Loading...';
    listEl.appendChild(loadingLi);

    try {
        const resp = await fetch('/api/tenant/settings', {
            headers: { 'Authorization': `Bearer ${App.token}` }
        });
        const data = await resp.json();
        const settings = data.settings || {};
        
        // Parse current sequence
        let sequence = [];
        if (settings.failover_provider_sequence) {
            sequence = settings.failover_provider_sequence.split(',').map(s => s.trim().toLowerCase()).filter(s => s);
        }
        
        // Identify all connected providers
        const connectedProviders = [];
        systemProviders.forEach(p => {
            if (safeGet(tenantCredentialsCache, p.id)) {
                connectedProviders.push(p.id.toLowerCase());
            }
        });
        
        // Also add admin's offline models to list if they are admin, but since we don't know here, we'll just show what's requested
        // Actually, let's just let them see all connected keys.
        // If they don't have keys, they shouldn't failover.
        if (connectedProviders.length === 0) {
            listEl.innerHTML = '<li style="padding:10px; color:#888;">No providers configured yet. Add API keys first.</li>';
            return;
        }

        // Build final list: Selected ones in order, then unselected ones
        const finalList = [];
        sequence.forEach(pId => {
            if (connectedProviders.includes(pId)) {
                finalList.push({ id: pId, selected: true });
            }
        });
        
        connectedProviders.forEach(pId => {
            if (!sequence.includes(pId)) {
                finalList.push({ id: pId, selected: false });
            }
        });
        
        listEl.innerHTML = '';
        finalList.forEach(item => {
            const li = document.createElement('li');
            li.style.cssText = "display:flex; align-items:center; padding:10px; margin-bottom:5px; background:rgba(255,255,255,0.05); border:1px solid var(--border-glow); border-radius:4px; cursor:grab;";
            li.draggable = true;
            li.dataset.providerId = item.id;
            
            // Build list item using DOM APIs for safety
            const dragSpan = document.createElement('span');
            dragSpan.style.marginRight = '10px';
            dragSpan.style.color = '#888';
            dragSpan.textContent = '☰';
            li.appendChild(dragSpan);

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'failover-cb';
            checkbox.value = item.id;
            if (item.selected) checkbox.checked = true;
            checkbox.style.marginRight = '15px';
            checkbox.style.cursor = 'pointer';
            checkbox.style.transform = 'scale(1.2)';
            li.appendChild(checkbox);

            const nameSpan = document.createElement('span');
            nameSpan.style.fontWeight = 'bold';
            nameSpan.style.color = 'var(--text-bright)';
            nameSpan.style.textTransform = 'capitalize';
            nameSpan.textContent = item.id;
            li.appendChild(nameSpan);
            
            // Drag logic
            li.addEventListener('dragstart', (e) => {
                li.style.opacity = '0.5';
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', item.id);
                setTimeout(() => li.classList.add('dragging'), 0);
            });
            
            li.addEventListener('dragend', () => {
                li.style.opacity = '1';
                li.classList.remove('dragging');
            });
            
            listEl.appendChild(li);
        });
        
        // Handle Drag Over
        listEl.addEventListener('dragover', (e) => {
            e.preventDefault();
            const draggingNode = listEl.querySelector('.dragging');
            if (!draggingNode) return;
            
            const siblings = [...listEl.querySelectorAll('li:not(.dragging)')];
            let nextSibling = siblings.find(sibling => {
                return e.clientY <= sibling.getBoundingClientRect().top + sibling.offsetHeight / 2;
            });
            
            listEl.insertBefore(draggingNode, nextSibling);
        });

    } catch(e) {
        console.error("Failover load error", e);
        listEl.innerHTML = '<li style="padding:10px; color:var(--accent-red);">Failed to load settings.</li>';
    }
};

window.saveFailoverSequence = async function() {
    const listEl = document.getElementById('failover-sortable-list');
    if (!listEl) return;
    
    const checkboxes = listEl.querySelectorAll('.failover-cb');
    const selected = [];
    
    checkboxes.forEach(cb => {
        if (cb.checked) {
            selected.push(cb.value);
        }
    });
    
    const sequenceStr = selected.join(',');
    
    try {
        const resp = await fetch('/api/tenant/settings', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${App.token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ failover_provider_sequence: sequenceStr })
        });
        
        if (resp.ok) {
            alert("Failover configuration saved successfully!");
        } else {
            alert("Failed to save configuration.");
        }
    } catch(e) {
        console.error("Failover save error", e);
        alert("Error saving configuration.");
    }
};
