// model_popup.js - Modular Model Selection Logic
import { App } from './state.js';

export let pendingSelectedModelId = null;

// The global model list is populated from settings_hub.js -> loadModels() -> App.modelsCache
// We assume systemProviders are available globally via settings_hub if needed, 
// but since systemProviders is inside settings_hub.js, we will just pass it or extract it.
// To keep it simple, we'll read App.modelsCache.

function normalizeProviderName(pName) {
    let lower = (pName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    if (lower.includes('nvidia')) return 'nvidia';
    if (lower.includes('google')) return 'google';
    return lower;
}

function stripMarkdown(text) {
    if (!text) return '';
    return text.replace(/(\*\*|__)(.*?)\1/g, '$2')
               .replace(/(\*|_)(.*?)\1/g, '$2')
               .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
               .replace(/`([^`]+)`/g, '$1')
               .replace(/#+\s+(.*)/g, '$1')
               .replace(/>\s+(.*)/g, '$1')
               .replace(/\n/g, ' ')
               .trim();
}

export function selectModelRow(rowEl, modelId) {
    // Clear previous selection visually
    document.querySelectorAll('.model-popup-row').forEach(row => {
        row.classList.remove('selected');
        row.style.background = 'transparent';
    });
    
    // Set new selection
    rowEl.classList.add('selected');
    rowEl.style.background = 'rgba(37, 99, 235, 0.2)';
    pendingSelectedModelId = modelId;
    
    // Enable OK button
    const okBtn = document.getElementById('btn-apply-model-selection');
    if (okBtn) {
        okBtn.disabled = false;
    }
}

export function renderModelPopupTabs(filterEcosystem, systemProviders = []) {
    const tabsHeader = document.getElementById('model-dev-tabs-header');
    const tabsContent = document.getElementById('model-dev-tabs-content');
    if (!tabsHeader || !tabsContent) return;
    
    tabsHeader.innerHTML = '';
    tabsContent.innerHTML = '';
    
    if (!App.modelsCache || App.modelsCache.length === 0) {
        tabsContent.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-dim);">No models fetched.</div>`;
        return;
    }
    
    let filterId = null;
    if (filterEcosystem !== "All" && systemProviders.length > 0) {
        const prov = systemProviders.find(p => p.ecosystem === filterEcosystem);
        if (prov) filterId = normalizeProviderName(prov.ecosystem);
    }
    
    const modelsByDev = {};
    App.modelsCache.forEach(m => {
        const provNormalized = normalizeProviderName(m.provider || 'nvidia');
        if (filterId && provNormalized !== filterId) return;
        
        let dev = m.developer || 'Other';
        if (typeof dev === 'string' && dev.length > 0) {
            dev = dev.charAt(0).toUpperCase() + dev.slice(1).toLowerCase();
        }
        if (!modelsByDev[dev]) modelsByDev[dev] = [];
        modelsByDev[dev].push(m);
    });
    
    const sortedDevs = Object.keys(modelsByDev).sort();
    
    if (sortedDevs.length === 0) {
        tabsContent.innerHTML = `<div style="text-align: center; padding: 2rem; color: var(--text-dim);">No models available.</div>`;
        return;
    }
    
    let first = true;
    sortedDevs.forEach(dev => {
        const safeDevId = dev.replace(/[^a-zA-Z0-9]/g, '-');
        
        const btn = document.createElement('button');
        btn.textContent = dev;
        btn.className = 'settings-tab' + (first ? ' active' : '');
        
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
            const statusStyle = isFree ? 'color: #28a745; border: 1px solid #28a745;' : 'color: #dc3545; border: 1px solid #dc3545;';
            const badge = `<span style="padding: 2px 6px; border-radius: 2px; font-size: 0.8rem; font-weight: bold; display: inline-block; ${statusStyle}">${statusText}</span>`;
            const modelIdSafe = (m.id || m.name || '').replace(/'/g, "\\'");
            
            tableHtml += `
                <tr class="model-popup-row" onclick="window.selectModelRow(this, '${modelIdSafe}')">
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
            Array.from(tabsHeader.children).forEach(c => c.classList.remove('active'));
            Array.from(tabsContent.children).forEach(c => c.style.display = 'none');
            btn.classList.add('active');
            contentDiv.style.display = 'block';
        };
        
        tabsHeader.appendChild(btn);
        tabsContent.appendChild(contentDiv);
        first = false;
    });
}

// Function called when "OK / Apply" is clicked in the modal
export function applyModelSelection() {
    if (!pendingSelectedModelId) return;
    
    // Update global state
    App.activeModelId = pendingSelectedModelId;
    
    // Update the visual label on the workspace
    const label = document.getElementById('active-model-label');
    if (label) {
        label.textContent = pendingSelectedModelId;
        label.style.color = 'var(--text-bright)';
    }
    
    // Close the modal
    document.getElementById('model-manager-modal').style.display = 'none';
}
