// workspace.js - Chat streaming and Arena logic
import { App } from './state.js';
import { initiateChatStream, fetchModels, fetchAdminUsers, fetchAdminStats, fetchMemoryCollections, generateShareLink } from './api.js';

export function fillPrompt(text) {
    const input = document.getElementById('main-prompt-input');
    input.value = text;
    input.dispatchEvent(new Event('input'));
    input.focus();
}

export function updateTelemetryDisplay() {
    document.getElementById('counter-prompt').textContent = App.tallyPrompt.toLocaleString();
    document.getElementById('counter-comp').textContent = App.tallyComp.toLocaleString();
}

export function appendBubble(role, text, targetContainerId = 'chat-bubble-stream') {
    const container = document.getElementById(targetContainerId);
    if (!container) return null;
    
    const div = document.createElement('div');
    div.className = `chat-bubble ${role}`;
    
    const meta = document.createElement('div');
    meta.className = 'bubble-meta';
    
    let metaText = role === 'user' ? 'Satellite Feed (User)' : 'Compute Result';
    if (targetContainerId === 'arena-bubbles-left') {
        metaText = role === 'user' ? 'User Probe' : 'Module A Core';
    } else if (targetContainerId === 'arena-bubbles-right') {
        metaText = role === 'user' ? 'User Probe' : 'Module B Core';
    }
    meta.textContent = metaText;
    
    const content = document.createElement('div');
    content.className = 'bubble-content';
    content.textContent = text;
    
    div.appendChild(meta);
    div.appendChild(content);
    container.appendChild(div);
    
    if (targetContainerId.includes('arena')) {
        const column = container.parentElement;
        column.scrollTop = column.scrollHeight;
    } else {
        const frame = document.getElementById('chat-scroll-frame');
        frame.scrollTop = frame.scrollHeight;
    }
    
    return content;
}

export function renderHistorySidebar() {
    const list = document.getElementById('history-list');
    list.innerHTML = '';
    
    const keys = Object.keys(App.conversations).reverse();
    if (keys.length === 0) {
        list.innerHTML = '<div class="empty-history" data-i18n="workspace.empty_history">No active orbital streams found.</div>';
        return;
    }
    
    keys.forEach(id => {
        const messages = App.conversations[id];
        let preview = "New Isolated Session";
        if (messages.length > 0) {
            preview = messages[0].content.substring(0, 28) + "...";
        }
        
        const div = document.createElement('div');
        div.className = `history-item ${id === App.activeConversationId ? 'active' : ''}`;
        div.innerHTML = `<i class="fa-regular fa-comments"></i> <span>${preview}</span>`;
        div.onclick = () => loadOrbitSession(id);
        list.appendChild(div);
    });
}

export function loadOrbitSession(id) {
    App.activeConversationId = id;
    const messages = App.conversations[id];
    
    const container = document.getElementById('chat-bubble-stream');
    container.innerHTML = '';
    
    document.getElementById('arena-bubbles-left').innerHTML = '';
    document.getElementById('arena-bubbles-right').innerHTML = '';
    
    const welcomeScreen = document.getElementById('chat-welcome-screen');
    if (messages.length === 0) {
        if (App.arenaMode) {
            welcomeScreen.classList.add('hidden');
        } else {
            welcomeScreen.classList.remove('hidden');
        }
    } else {
        welcomeScreen.classList.add('hidden');
        messages.forEach(msg => appendBubble(msg.role, msg.content));
    }
    renderHistorySidebar();
}

export function startNewOrbit() {
    App.activeConversationId = 'conv_' + Date.now();
    App.conversations[App.activeConversationId] = [];
    
    document.getElementById('chat-bubble-stream').innerHTML = '';
    document.getElementById('arena-bubbles-left').innerHTML = '';
    document.getElementById('arena-bubbles-right').innerHTML = '';
    
    const welcomeScreen = document.getElementById('chat-welcome-screen');
    if (App.arenaMode) {
        welcomeScreen.classList.add('hidden');
    } else {
        welcomeScreen.classList.remove('hidden');
    }
    
    renderHistorySidebar();
}

export async function loadModels() {
    try {
        const resJson = await fetchModels(App.token);
        const models = resJson.data || [];
        App.modelsCache = models;
        if (models.length === 0) return;
        
        populateStandardSelector();
        populateArenaSelectors();
    } catch (e) {
        console.error("Admin dashboard failed to load", e);
    }
}

function buildModelGroups(models) {
    const groups = {};
    models.forEach(m => {
        const rawP = m.owned_by || "unknown";
        let pLabel = rawP.charAt(0).toUpperCase() + rawP.slice(1);
        
        if (rawP === "nvidia") pLabel = "NVIDIA NIM";
        else if (rawP === "openai") pLabel = "Official OpenAI API";
        else if (rawP === "google") pLabel = "Google Gemini Native";
        else if (rawP === "lmstudio") pLabel = "LM Studio (Local Host)";
        else if (rawP === "ollama") pLabel = "Ollama (Local Desktop)";
        else if (rawP === "groq") pLabel = "GroqCloud (LPU Acceleration)";
        
        if (!groups[pLabel]) groups[pLabel] = [];
        groups[pLabel].push(m);
    });
    return groups;
}

function renderGroupedSelector(selector, groups) {
    selector.innerHTML = '';
    const sortedKeys = Object.keys(groups).sort((a, b) => {
        const isANative = a.includes("Google") || a.includes("NVIDIA") || a.includes("Official OpenAI");
        const isBNative = b.includes("Google") || b.includes("NVIDIA") || b.includes("Official OpenAI");
        if (isANative && !isBNative) return -1;
        if (!isANative && isBNative) return 1;
        return a.localeCompare(b);
    });
    
    sortedKeys.forEach(lbl => {
        const optGroup = document.createElement('optgroup');
        optGroup.label = lbl;
        groups[lbl].forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            let cleanName = m.id;
            if (cleanName.includes("/")) cleanName = cleanName.split("/")[1];
            cleanName = cleanName.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            opt.textContent = cleanName;
            optGroup.appendChild(opt);
        });
        selector.appendChild(optGroup);
    });
}

export function populateStandardSelector() {
    const selector = document.getElementById('model-selector');
    if (selector && App.modelsCache) renderGroupedSelector(selector, buildModelGroups(App.modelsCache));
}

export function populateArenaSelectors() {
    const leftSel = document.getElementById('arena-model-left');
    const rightSel = document.getElementById('arena-model-right');
    if (!leftSel || !rightSel || !App.modelsCache) return;
    
    const groups = buildModelGroups(App.modelsCache);
    renderGroupedSelector(leftSel, groups);
    renderGroupedSelector(rightSel, groups);
    
    if (leftSel.options.length > 0) leftSel.selectedIndex = 0;
    if (rightSel.options.length > 1) rightSel.selectedIndex = 1;
    else if (rightSel.options.length > 0) rightSel.selectedIndex = 0;
}

export async function dispatchPrompt() {
    if (App.isGenerating) return;
    const input = document.getElementById('main-prompt-input');
    const text = input.value.trim();
    if (!text) return;
    
    App.isGenerating = true;
    document.getElementById('chat-welcome-screen').classList.add('hidden');
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('btn-send-prompt').disabled = true;
    
    if (App.arenaMode) return await dispatchDualPrompt(text);
    
    App.conversations[App.activeConversationId].push({ role: 'user', content: text });
    appendBubble('user', text);
    
    const bubbleHandle = appendBubble('assistant', 'Initializing dynamic cluster pipeline...');
    bubbleHandle.textContent = '';
    
    const activeModel = document.getElementById('model-selector').value;
    const useWebSearch = document.getElementById('web-search-toggle')?.checked || false;
    App.tallyPrompt += Math.ceil(text.length / 4);
    updateTelemetryDisplay();
    
    try {
        const response = await initiateChatStream(App.token, activeModel, App.conversations[App.activeConversationId], useWebSearch);
        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.error || errData.message || "Generation gateway failure.");
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let assistantAccumulator = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const rawText = decoder.decode(value);
            const lines = rawText.split('\n');
            for (const line of lines) {
                const cleanLine = line.trim();
                if (!cleanLine) continue;
                if (cleanLine === 'data: [DONE]') break;
                if (cleanLine.startsWith('data: ')) {
                    try {
                        const jsonStr = cleanLine.substring(6);
                        const payload = JSON.parse(jsonStr);
                        const textDelta = payload.choices[0]?.delta?.content || '';
                        
                        assistantAccumulator += textDelta;
                        bubbleHandle.textContent = assistantAccumulator;
                        
                        App.tallyComp += 1;
                        if (App.tallyComp % 10 === 0) updateTelemetryDisplay();
                        
                        const frame = document.getElementById('chat-scroll-frame');
                        frame.scrollTop = frame.scrollHeight;
                    } catch (e) { }
                }
            }
        }
        
        App.conversations[App.activeConversationId].push({ role: 'assistant', content: assistantAccumulator });
        renderHistorySidebar();
    } catch (err) {
        bubbleHandle.textContent = `❌ CRITICAL COMMS ERROR: ${err.message}`;
        bubbleHandle.style.color = 'var(--accent-error)';
    } finally {
        App.isGenerating = false;
        input.focus();
    }
}

async function dispatchDualPrompt(text) {
    appendBubble('user', text, 'arena-bubbles-left');
    appendBubble('user', text, 'arena-bubbles-right');
    
    const modelA = document.getElementById('arena-model-left').value;
    const modelB = document.getElementById('arena-model-right').value;
    
    const bubbleHandleA = appendBubble('assistant', '', 'arena-bubbles-left');
    const bubbleHandleB = appendBubble('assistant', '', 'arena-bubbles-right');
    
    App.tallyPrompt += Math.ceil(text.length / 4) * 2;
    updateTelemetryDisplay();
    
    const streamTask = async (modelId, bubbleHandle, targetColId) => {
        try {
            const useWebSearch = document.getElementById('web-search-toggle')?.checked || false;
            const response = await initiateChatStream(App.token, modelId, [{ role: 'user', content: text }], useWebSearch);
            if (!response.ok) throw new Error("Stream connection failed.");
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let accum = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const rawText = decoder.decode(value);
                const lines = rawText.split('\n');
                for (const line of lines) {
                    const cleanLine = line.trim();
                    if (!cleanLine || cleanLine === 'data: [DONE]') continue;
                    if (cleanLine.startsWith('data: ')) {
                        try {
                            const payload = JSON.parse(cleanLine.substring(6));
                            accum += payload.choices[0]?.delta?.content || '';
                            bubbleHandle.textContent = accum;
                            App.tallyComp += 1;
                            if (App.tallyComp % 20 === 0) updateTelemetryDisplay();
                            const column = document.getElementById(targetColId).parentElement;
                            column.scrollTop = column.scrollHeight;
                        } catch (e) {}
                    }
                }
            }
        } catch (err) {
            bubbleHandle.textContent = `❌ Error: ${err.message}`;
            bubbleHandle.style.color = 'var(--accent-error)';
        }
    };
    
    await Promise.all([
        streamTask(modelA, bubbleHandleA, 'arena-bubbles-left'),
        streamTask(modelB, bubbleHandleB, 'arena-bubbles-right')
    ]);
    App.isGenerating = false;
    document.getElementById('main-prompt-input').focus();
}

export function toggleArenaMode() {
    App.arenaMode = !App.arenaMode;
    const btn = document.getElementById('btn-arena-toggle');
    const singlePane = document.getElementById('single-model-pane');
    const dualPane = document.getElementById('dual-model-pane');
    const standardStream = document.getElementById('chat-bubble-stream');
    const arenaGrid = document.getElementById('arena-chat-grid');
    const welcomeScreen = document.getElementById('chat-welcome-screen');
    
    if (App.arenaMode) {
        btn.classList.add('active');
        singlePane.classList.add('hidden');
        dualPane.classList.remove('hidden');
        standardStream.classList.add('hidden');
        arenaGrid.classList.remove('hidden');
        welcomeScreen.classList.add('hidden');
        populateArenaSelectors();
    } else {
        btn.classList.remove('active');
        singlePane.classList.remove('hidden');
        dualPane.classList.add('hidden');
        standardStream.classList.remove('hidden');
        arenaGrid.classList.add('hidden');
        const activeMsgCount = App.conversations[App.activeConversationId]?.length || 0;
        if (activeMsgCount === 0) welcomeScreen.classList.remove('hidden');
    }
}

export async function handleShareOrbit() {
    const messages = App.conversations[App.activeConversationId];
    if (!messages || messages.length === 0) {
        alert("Cannot share an empty orbit.");
        return;
    }
    const btn = document.getElementById('btn-share-orbit');
    const ogHtml = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Linking...';
    try {
        const res = await generateShareLink(App.token, messages);
        if (res.success) {
            const fullUrl = window.location.origin + res.share_url;
            await navigator.clipboard.writeText(fullUrl);
            btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied Link!';
            setTimeout(() => btn.innerHTML = ogHtml, 2000);
        } else {
            alert(res.error || "Failed to share.");
            btn.innerHTML = ogHtml;
        }
    } catch (e) {
        alert("Network error creating share link.");
        btn.innerHTML = ogHtml;
    }
}

export async function loadMemoryRoster() {
    const roster = document.getElementById('memory-roster');
    roster.innerHTML = '<div style="color:var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Scanning tensor volumes...</div>';
    try {
        const res = await fetchMemoryCollections(App.token);
        roster.innerHTML = '';
        if (!res.collections || res.collections.length === 0) {
            roster.innerHTML = '<div style="color:var(--text-dim);">No semantic collections found in your isolated sandbox yet.</div>';
            return;
        }
        res.collections.forEach(col => {
            const d = new Date(col.created * 1000).toLocaleString();
            roster.innerHTML += `
                <div class="glass-panel" style="padding: 1rem; border-radius: var(--radius-sm); border-left: 3px solid var(--accent-blue);">
                    <div style="font-weight: 600; margin-bottom: 5px;"><i class="fa-solid fa-layer-group"></i> ${col.name}</div>
                    <div style="font-size: 0.8rem; color: var(--text-dim);">Created: ${d}</div>
                </div>
            `;
        });
    } catch (e) {
        roster.innerHTML = '<div style="color:var(--accent-error);">Critical error loading semantic volumes.</div>';
    }
}

export async function loadAdminDashboard() {
    const table = document.getElementById('admin-users-table');
    const statsContainer = document.getElementById('admin-stats-container');
    
    table.innerHTML = '<tr><td colspan="6" style="padding:10px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</td></tr>';
    
    try {
        const [usersRes, statsRes] = await Promise.all([
            fetchAdminUsers(App.token),
            fetchAdminStats(App.token)
        ]);
        
        if (usersRes.success) {
            table.innerHTML = '';
            usersRes.users.forEach(u => {
                const tierClass = u.key_type === 'admin_funded' ? 'admin' : 'byok';
                const tierLabel = u.key_type === 'admin_funded' ? 'Admin' : 'BYOK';
                const activeHtml = u.status === 'active' ? '<span style="color:var(--accent-success);">Active</span>' : 'Inactive';
                table.innerHTML += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 10px;">${u.id}</td>
                        <td style="padding: 10px; font-weight:600;">${u.username}</td>
                        <td style="padding: 10px; color:var(--text-muted);">${u.email}</td>
                        <td style="padding: 10px;"><span class="key-tag ${tierClass}">${tierLabel}</span></td>
                        <td style="padding: 10px;">${activeHtml}</td>
                        <td style="padding: 10px; color:var(--text-dim);">${u.created_at}</td>
                    </tr>
                `;
            });
        }
        
        if (statsRes.success) {
            const agg = statsRes.stats.aggregate;
            statsContainer.innerHTML = `
                <div style="display:flex; justify-content: space-between; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 8px;">
                    <span style="color:var(--text-muted);">Total Inbound Prompt Tokens:</span>
                    <span style="font-family:monospace; color:var(--accent-cyan);">${agg.total_prompt.toLocaleString()}</span>
                </div>
                <div style="display:flex; justify-content: space-between; padding-top: 8px;">
                    <span style="color:var(--text-muted);">Total Outbound Inference Tokens:</span>
                    <span style="font-family:monospace; color:var(--accent-success);">${agg.total_completion.toLocaleString()}</span>
                </div>
            `;
        }
    } catch (e) {
        table.innerHTML = '<tr><td colspan="6" style="padding:10px; color:var(--accent-error);">Fetch error.</td></tr>';
    }
}
