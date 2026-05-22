import { App } from './state.js';

export function openModelPopup() {
    document.getElementById('model-popup-modal').classList.remove('hidden');
    renderModelPopup();
}

export function renderModelPopup() {
    const tbody = document.getElementById('model-popup-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    if (!App.modelsCache) return;
    
    const showAll = document.getElementById('mp-show-all').checked;
    const filterIdx = document.getElementById('mp-capability-filter').value;
    
    const activeProvider = localStorage.getItem('active_provider') || 'nvidia';
    
    let filtered = App.modelsCache.filter(m => {
        if (m.type !== 'chat') return false;
        
        const prov = (m.provider || 'nvidia').toLowerCase();
        if (!showAll && prov !== activeProvider.toLowerCase()) return false;
        
        const mId = (m.id || '').toLowerCase();
        const mDesc = (m.description || '').toLowerCase();
        const isVision = mId.includes('vision') || mId.includes('-vl') || mDesc.includes('vision') || mDesc.includes('multimodal');
        const hasTools = (m.capabilities && m.capabilities.tools) || false;
        
        if (filterIdx === '1' && isVision) return false;
        if (filterIdx === '2' && !hasTools) return false;
        if (filterIdx === '3' && !isVision) return false;
        
        return true;
    });
    
    filtered.forEach((m) => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        tr.style.cursor = 'pointer';
        
        const isSelected = (m.id === App.activeModelId);
        if (isSelected) {
            tr.style.background = '#E3F2FD';
            tr.style.color = '#0D47A1';
        }
        
        tr.onclick = function() {
            const rad = tr.querySelector('input[type="radio"]');
            if (rad) rad.checked = true;
            Array.from(tbody.children).forEach(r => {
                r.style.background = 'transparent';
                r.style.color = 'inherit';
            });
            tr.style.background = '#E3F2FD';
            tr.style.color = '#0D47A1';
        };
        
        const tdRadio = document.createElement('td');
        tdRadio.style.textAlign = 'center';
        tdRadio.style.padding = '10px';
        const rad = document.createElement('input');
        rad.type = 'radio';
        rad.name = 'mp-model-select';
        rad.value = m.id;
        rad.style.pointerEvents = 'none';
        if (isSelected) rad.checked = true;
        tdRadio.appendChild(rad);
        tr.appendChild(tdRadio);
        
        const tdEco = document.createElement('td');
        tdEco.style.padding = '10px';
        tdEco.textContent = (m.provider || 'nvidia').toUpperCase();
        tr.appendChild(tdEco);
        
        const tdDev = document.createElement('td');
        tdDev.style.padding = '10px';
        tdDev.textContent = m.developer || 'Unknown';
        tr.appendChild(tdDev);
        
        const tdName = document.createElement('td');
        tdName.style.padding = '10px';
        const hasTools = (m.capabilities && m.capabilities.tools) || false;
        tdName.textContent = (m.name || m.id) + (hasTools ? ' 🛠️' : '');
        tr.appendChild(tdName);
        
        const tdDesc = document.createElement('td');
        tdDesc.style.padding = '10px';
        tdDesc.textContent = m.description || '';
        tr.appendChild(tdDesc);
        
        tbody.appendChild(tr);
    });
}

export function applyModelSelection() {
    const selectedRad = document.querySelector('input[name="mp-model-select"]:checked');
    if (!selectedRad) {
        alert("Please select a model.");
        return;
    }
    App.activeModelId = selectedRad.value;
    
    const m = App.modelsCache.find(x => x.id === App.activeModelId);
    if (m) {
        const btnText = document.getElementById('active-model-name');
        if (btnText) btnText.textContent = m.name || m.id;
    }
    
    document.getElementById('model-popup-modal').classList.add('hidden');
}
