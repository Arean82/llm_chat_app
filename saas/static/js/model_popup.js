// model_popup.js - Pure standalone model selection modal (1:1 Desktop Clone)
import { App } from './state.js';

let pendingModelId = null;

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

function normalizeProviderName(pName) {
    let lower = (pName || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    if (lower.includes('nvidia')) return 'nvidia';
    if (lower.includes('google')) return 'google';
    if (lower.includes('openai')) return 'openai';
    return lower;
}

export function renderDesktopCloneTable() {
    const tbody = document.getElementById('pure-model-table-body');
    if (!tbody) return;
    
    // Desktop logic: Show all vs active provider
    const showAll = document.getElementById('pure-model-show-all').checked;
    const capabilityFilter = parseInt(document.getElementById('pure-model-capability-filter').value, 10) || 0;
    
    const activeProvider = App.activeProviderId || 'nvidia';
    
    let filtered = (App.modelsCache || []).filter(m => {
        const prov = normalizeProviderName(m.owned_by || 'nvidia');
        
        // Strictly show chat models only
        if (m.capabilities && m.capabilities.chat === false) return false;
        if (!m.capabilities && m.type && m.type !== 'chat') return false; // Fallback
        
        if (!showAll && prov !== activeProvider) return false;
        
        // Capability filter based on the backend's provided capabilities object
        const isVision = m.capabilities ? m.capabilities.vision : (m.id || '').toLowerCase().includes('vision');
        const supportsTools = m.capabilities ? m.capabilities.tools : false;
        
        if (capabilityFilter === 1) { // General Chat (no vision)
            if (isVision) return false;
        } else if (capabilityFilter === 2) { // Supports Tools
            if (!supportsTools) return false;
        } else if (capabilityFilter === 3) { // Multimodal / Vision
            if (!isVision) return false;
        }
        
        return true;
    });
    
    tbody.innerHTML = '';
    
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 2rem; color: var(--text-dim);">No models match the filter.</td></tr>`;
        return;
    }
    
    filtered.forEach((m, idx) => {
        const tr = document.createElement('tr');
        tr.className = 'pure-model-row';
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        tr.style.cursor = 'pointer';
        
        const isSelected = pendingModelId === m.id;
        if (isSelected) {
            tr.style.background = 'rgba(37, 99, 235, 0.2)';
        }
        
        tr.innerHTML = `
            <td style="text-align: center; padding: 10px;">
                <input type="radio" name="pure_model_radio" value="${m.id}" ${isSelected ? 'checked' : ''} style="cursor: pointer;">
            </td>
            <td style="padding: 10px; color: var(--accent-cyan); font-weight: 500;">${(m.owned_by || 'nvidia').toUpperCase()}</td>
            <td style="padding: 10px;">${m.developer || 'Other'}</td>
            <td style="padding: 10px; font-weight: 600;">${m.name || m.id}</td>
            <td style="padding: 10px; color: var(--text-dim); font-size: 0.85rem;">${stripMarkdown(m.description || '')}</td>
        `;
        
        tr.onclick = () => {
            pendingModelId = m.id;
            renderDesktopCloneTable(); // Re-render to update highlights and radios
            
            // Enable apply button
            const applyBtn = document.getElementById('pure-model-apply-btn');
            if (applyBtn) {
                applyBtn.disabled = false;
            }
        };
        
        tbody.appendChild(tr);
    });
}

export function applyModelSelection() {
    if (!pendingModelId) return;
    
    // Update global state
    App.activeModelId = pendingModelId;
    
    // Update the visual label on the workspace
    const label = document.getElementById('active-model-label');
    if (label) {
        label.textContent = pendingModelId;
        label.style.color = 'var(--text-bright)';
    }
    
    // Close the modal
    document.getElementById('pure-model-selection-modal').style.display = 'none';
}

// Expose strictly to window so inline onclicks can reach them
window.renderDesktopCloneTable = renderDesktopCloneTable;
window.applyModelSelection = applyModelSelection;
