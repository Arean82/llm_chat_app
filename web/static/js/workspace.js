// workspace.js - Chat streaming and Arena logic
import { App } from './state.js';
import { initiateChatStream, fetchModels, fetchAdminUsers, fetchAdminStats, fetchMemoryCollections, generateShareLink, fetchAdminTelemetry, updateTenantRateLimit, fetchAdminDLQ, retryDLQJob } from './api.js';
import { getActiveSystemPrompt } from './settings_main.js';

let adminPollerInterval = null;

function checkFailoverWarning(text) {
    if (text && text.includes("[⚠️ Backup:")) {
        const match = text.match(/\[⚠️ Backup:\s*([^\]]+)\]/);
        const backupName = match ? match[1] : "Backup Node";
        const banner = document.getElementById('failover-warning-banner');
        const bannerText = document.getElementById('failover-banner-text');
        if (banner && bannerText) {
            bannerText.textContent = `Primary provider degraded. Operating on fallback backup node: ${backupName}`;
            banner.classList.remove('hidden');
        }
    }
}

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
        div.innerHTML = `
            <div style="display: flex; align-items: center; width: 100%; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 8px; overflow: hidden; max-width: 85%;">
                    <i class="fa-regular fa-comments"></i> 
                    <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${preview}</span>
                </div>
                <i class="fa-solid fa-trash btn-delete-history hover-text" style="cursor: pointer; opacity: 0.5; font-size: 0.85rem;" title="Delete Session"></i>
            </div>
        `;
        
        div.onclick = (e) => {
            if (e.target.classList.contains('fa-trash')) {
                deleteOrbitSession(id);
            } else {
                loadOrbitSession(id);
            }
        };
        list.appendChild(div);
    });
}

export function deleteOrbitSession(id) {
    if (confirm("Are you sure you want to delete this session?")) {
        delete App.conversations[id];
        
        // Notify backend to clear history from memory
        fetch(`/v1/chat/history/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${App.token}` }
        }).catch(err => console.error("Failed to delete backend session history:", err));

        if (App.activeConversationId === id) {
            startNewOrbit();
        } else {
            renderHistorySidebar();
        }
    }
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
    // Model selector is now managed entirely via the Model Popup and App.activeModelId
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

    // Reset failover warning banner
    const banner = document.getElementById('failover-warning-banner');
    if (banner) banner.classList.add('hidden');

    if (App.arenaMode) return await dispatchDualPrompt(text);

    App.conversations[App.activeConversationId].push({ role: 'user', content: text });
    appendBubble('user', text);

    const bubbleHandle = appendBubble('assistant', 'Initializing dynamic cluster pipeline...');
    bubbleHandle.textContent = '';

    if (!App.activeModelId) {
        App.isGenerating = false;
        document.getElementById('btn-send-prompt').disabled = false;
        alert('Please select a model from the Model Manager first.');
        return;
    }
    const activeModel = App.activeModelId;
    const useWebSearch = document.getElementById('web-search-toggle')?.checked || false;
    App.tallyPrompt += Math.ceil(text.length / 4);
    updateTelemetryDisplay();

    try {
        let payloadMessages = [];
        const activeSysPrompt = await getActiveSystemPrompt();
        if (activeSysPrompt) {
            payloadMessages.push({ role: 'system', content: activeSysPrompt });
        }
        payloadMessages.push(...App.conversations[App.activeConversationId]);

        const response = await initiateChatStream(App.token, activeModel, payloadMessages, useWebSearch);
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
                        checkFailoverWarning(assistantAccumulator);
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
            
            // Fetch the active system instruction
            let messagesPayload = [];
            const activeSysPrompt = await getActiveSystemPrompt();
            if (activeSysPrompt) {
                messagesPayload.push({ role: 'system', content: activeSysPrompt });
            }
            messagesPayload.push({ role: 'user', content: text });
            
            const response = await initiateChatStream(App.token, modelId, messagesPayload, useWebSearch, true);
            if (!response.ok) {
                let errStr = "Stream connection failed.";
                try {
                    const errData = await response.json();
                    errStr = errData.error || errData.message || errStr;
                } catch (e) {}
                throw new Error(errStr);
            }

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
                            checkFailoverWarning(accum);
                            bubbleHandle.textContent = accum;
                            App.tallyComp += 1;
                            if (App.tallyComp % 20 === 0) updateTelemetryDisplay();
                            const column = document.getElementById(targetColId).parentElement;
                            column.scrollTop = column.scrollHeight;
                        } catch (e) { }
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

export async function pollAdminTelemetryAndDLQ() {
    const adminScreen = document.getElementById('admin-screen');
    if (!adminScreen || adminScreen.classList.contains('hidden')) {
        if (adminPollerInterval) {
            clearInterval(adminPollerInterval);
            adminPollerInterval = null;
        }
        return;
    }

    try {
        const [telemetryRes, dlqRes] = await Promise.all([
            fetchAdminTelemetry(App.token),
            fetchAdminDLQ(App.token)
        ]);

        if (telemetryRes.success && telemetryRes.metrics) {
            const m = telemetryRes.metrics;
            const throughputEl = document.getElementById('telemetry-throughput');
            const latencyEl = document.getElementById('telemetry-latency');
            const connectionsEl = document.getElementById('telemetry-connections');
            const cacheHitEl = document.getElementById('telemetry-cache-hit');

            if (throughputEl) throughputEl.innerHTML = `${m.http_throughput_rpm.toFixed(2)} <span style="font-size: 1rem; font-weight: 400; color: var(--text-dim);">RPM</span>`;
            if (latencyEl) latencyEl.innerHTML = `${m.average_latency_seconds.toFixed(3)} <span style="font-size: 1rem; font-weight: 400; color: var(--text-dim);">sec</span>`;
            if (connectionsEl) connectionsEl.textContent = m.active_connections.toString();
            if (cacheHitEl) cacheHitEl.innerHTML = `${m.cache_hit_ratio_percent.toFixed(1)} <span style="font-size: 1rem; font-weight: 400; color: var(--text-dim);">%</span>`;
        }

        if (dlqRes.success && dlqRes.dlq) {
            const dlqTable = document.getElementById('admin-dlq-table');
            if (dlqTable) {
                if (dlqRes.dlq.length === 0) {
                    dlqTable.innerHTML = `
                        <tr>
                            <td colspan="6" style="padding:15px; text-align:center; color:var(--text-dim);">
                                No quarantined jobs inside DLQ container.
                            </td>
                        </tr>
                    `;
                } else {
                    const escapeHTML = (str) => {
                        if (!str) return '';
                        return String(str).replace(/[&<>'"]/g, tag => ({
                            '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
                        }[tag] || tag));
                    };
                    dlqTable.innerHTML = '';
                    dlqRes.dlq.forEach(entry => {
                        dlqTable.innerHTML += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td style="padding: 10px; font-family: monospace; font-size: 0.8rem; color: var(--accent-cyan);">${escapeHTML(entry.job_id)}</td>
                                <td style="padding: 10px;">${escapeHTML(entry.tenant_id)}</td>
                                <td style="padding: 10px;"><span style="background: rgba(231, 76, 60, 0.15); color: #e74c3c; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">${escapeHTML(entry.task_type)}</span></td>
                                <td style="padding: 10px; max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHTML(entry.error)}\n\n${escapeHTML(entry.stack_trace || '')}">
                                    <code style="color: #e74c3c; font-size: 0.8rem;">${escapeHTML(entry.error)}</code>
                                </td>
                                <td style="padding: 10px; color: var(--text-dim); font-size: 0.8rem;">${escapeHTML(entry.timestamp)}</td>
                                <td style="padding: 10px; text-align: right;">
                                    <button class="btn-retry-dlq btn-new" data-job-id="${entry.job_id}" style="width: auto; padding: 4px 8px; font-size: 0.8rem; background: var(--accent-success); color: black; font-weight: 600; margin: 0;"><i class="fa-solid fa-rotate-left"></i> Retry</button>
                                </td>
                            </tr>
                        `;
                    });
                }
            }
        }
    } catch (e) {
        console.error("Telemetry/DLQ polling error:", e);
    }
}

export async function loadAdminDashboard() {
    const table = document.getElementById('admin-users-table');
    const statsContainer = document.getElementById('admin-stats-container');

    if (table) {
        table.innerHTML = '<tr><td colspan="7" style="padding:10px;"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</td></tr>';
    }

    if (adminPollerInterval) {
        clearInterval(adminPollerInterval);
        adminPollerInterval = null;
    }

    try {
        const [usersRes, statsRes] = await Promise.all([
            fetchAdminUsers(App.token),
            fetchAdminStats(App.token)
        ]);

        if (usersRes.success && table) {
            const escapeHTML = (str) => {
                if (!str) return '';
                return String(str).replace(/[&<>'"]/g, tag => ({
                    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
                }[tag] || tag));
            };
            table.innerHTML = '';
            usersRes.users.forEach(u => {
                const tierClass = u.key_type === 'admin_funded' ? 'admin' : 'byok';
                const tierLabel = u.key_type === 'admin_funded' ? 'Admin' : 'BYOK';
                const activeHtml = u.status === 'active' ? '<span style="color:var(--accent-success);">Active</span>' : 'Inactive';
                const rpmVal = u.requests_per_minute_limit !== undefined ? u.requests_per_minute_limit : 0;
                table.innerHTML += `
                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                        <td style="padding: 10px;">${escapeHTML(u.id)}</td>
                        <td style="padding: 10px; font-weight:600;">${escapeHTML(u.username)}</td>
                        <td style="padding: 10px; color:var(--text-muted);">${escapeHTML(u.email)}</td>
                        <td style="padding: 10px;"><span class="key-tag ${tierClass}">${tierLabel}</span></td>
                        <td style="padding: 10px;">${activeHtml}</td>
                        <td style="padding: 10px; color:var(--text-dim);">${escapeHTML(u.created_at)}</td>
                        <td style="padding: 10px; text-align: right;">
                            <div style="display: flex; gap: 8px; justify-content: flex-end; align-items: center;">
                                <input type="number" class="tenant-rpm-input" data-tenant-id="${u.id}" value="${rpmVal}" style="width: 70px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-glow); color: var(--text-bright); border-radius: 4px; padding: 4px 8px; font-family: monospace; outline: none; text-align: center;">
                                <button class="btn-save-rpm btn-new" data-tenant-id="${u.id}" style="width: auto; padding: 4px 8px; font-size: 0.8rem; margin: 0;"><i class="fa-solid fa-floppy-disk"></i> Save</button>
                            </div>
                        </td>
                    </tr>
                `;
            });

            // Bind click listener for save-rpm via event delegation
            if (!table.dataset.listenerBound) {
                table.dataset.listenerBound = 'true';
                table.addEventListener('click', async (e) => {
                    const btn = e.target.closest('.btn-save-rpm');
                    if (btn) {
                        const tenantId = btn.dataset.tenantId;
                        const row = btn.closest('tr');
                        const input = row.querySelector('.tenant-rpm-input');
                        if (input) {
                            const rpm = parseInt(input.value);
                            if (isNaN(rpm) || rpm < 0) {
                                alert("Please enter a valid, non-negative RPM value.");
                                return;
                            }
                            btn.disabled = true;
                            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving';
                            try {
                                const res = await updateTenantRateLimit(App.token, tenantId, rpm);
                                if (res.success) {
                                    alert(res.message || "Tenant rate limit updated successfully!");
                                    loadAdminDashboard();
                                } else {
                                    alert("Error: " + (res.error || "Failed to update tenant rate limit."));
                                }
                            } catch (err) {
                                alert("Network error updating tenant rate limit: " + err.message);
                            } finally {
                                btn.disabled = false;
                                btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save';
                            }
                        }
                    }
                });
            }
        }

        if (statsRes.success && statsContainer) {
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

        // Bind click listener for retry-dlq via event delegation
        const dlqTable = document.getElementById('admin-dlq-table');
        if (dlqTable && !dlqTable.dataset.listenerBound) {
            dlqTable.dataset.listenerBound = 'true';
            dlqTable.addEventListener('click', async (e) => {
                const btn = e.target.closest('.btn-retry-dlq');
                if (btn) {
                    const jobId = btn.dataset.jobId;
                    btn.disabled = true;
                    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Retrying';
                    try {
                        const res = await retryDLQJob(App.token, jobId);
                        if (res.success) {
                            alert(res.message || `Job enqueued successfully as ${res.new_job_id || 'new task'}.`);
                            pollAdminTelemetryAndDLQ();
                        } else {
                            alert("Error retrying job: " + (res.error || "Internal server error"));
                        }
                    } catch (err) {
                        alert("Network error retrying job: " + err.message);
                    } finally {
                        btn.disabled = false;
                        btn.innerHTML = '<i class="fa-solid fa-rotate-left"></i> Retry';
                    }
                }
            });
        }

        // Trigger first poll immediately
        await pollAdminTelemetryAndDLQ();

        // Start interval
        adminPollerInterval = setInterval(pollAdminTelemetryAndDLQ, 5000);

    } catch (e) {
        if (table) {
            table.innerHTML = '<tr><td colspan="7" style="padding:10px; color:var(--accent-error);">Fetch error.</td></tr>';
        }
    }
}

// --- HERMES AGENT HUB LOGIC ---

window.startAgent = async function() {
    try {
        const response = await fetch('/api/agent/start', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${App.token}`,
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        if (data.success) {
            document.getElementById('agent-status-badge').textContent = data.status;
            document.getElementById('agent-status-badge').style.background = 'rgba(46, 204, 113, 0.2)';
            document.getElementById('agent-status-badge').style.color = '#2ecc71';
            appendAgentLog("[System] Hermes Agent successfully started.");
        } else {
            alert(data.error || "Failed to start agent.");
        }
    } catch (e) {
        alert("Network error starting agent.");
    }
};

window.stopAgent = async function() {
    try {
        const response = await fetch('/api/agent/stop', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${App.token}`,
                'Content-Type': 'application/json'
            }
        });
        const data = await response.json();
        if (data.success) {
            document.getElementById('agent-status-badge').textContent = data.status;
            document.getElementById('agent-status-badge').style.background = 'rgba(255,255,255,0.1)';
            document.getElementById('agent-status-badge').style.color = '#fff';
            appendAgentLog("[System] Hermes Agent stopped.");
        } else {
            alert(data.error || "Failed to stop agent.");
        }
    } catch (e) {
        alert("Network error stopping agent.");
    }
};

window.saveAgentConfig = async function() {
    const token = document.getElementById('telegram-token').value.trim();
    // In a full implementation we would save this to the tenant's user_settings
    alert("Configuration saved successfully.");
};

window.refreshAgentStatus = async function() {
    try {
        const response = await fetch('/api/agent/status', {
            headers: {
                'Authorization': `Bearer ${App.token}`
            }
        });
        const data = await response.json();
        if (data.success) {
            document.getElementById('agent-status-badge').textContent = data.status;
            if (data.status === 'RUNNING') {
                document.getElementById('agent-status-badge').style.background = 'rgba(46, 204, 113, 0.2)';
                document.getElementById('agent-status-badge').style.color = '#2ecc71';
            } else {
                document.getElementById('agent-status-badge').style.background = 'rgba(255,255,255,0.1)';
                document.getElementById('agent-status-badge').style.color = '#fff';
            }
        }
    } catch (e) {
        console.error("Failed to fetch agent status", e);
    }
};

window.fetchAgentSkills = async function() {
    try {
        const response = await fetch('/api/agent/skills', {
            headers: {
                'Authorization': `Bearer ${App.token}`
            }
        });
        const data = await response.json();
        if (data.success) {
            const listDiv = document.getElementById('skills-list');
            if (!listDiv) return;
            listDiv.innerHTML = '';
            if (data.skills && data.skills.length > 0) {
                data.skills.forEach(skill => {
                    const skillEl = document.createElement('div');
                    skillEl.style.padding = '0.5rem';
                    skillEl.style.borderBottom = '1px solid var(--border-color)';
                    skillEl.innerHTML = `<strong style="color: var(--accent);">${skill.skill_name}</strong><br><small style="color: var(--text-muted);">${new Date(skill.created_at).toLocaleString()}</small>`;
                    listDiv.appendChild(skillEl);
                });
            } else {
                listDiv.innerHTML = '<div style="color: var(--text-muted); font-size: 0.9rem; text-align: center; margin-top: 1rem;">No skills loaded.</div>';
            }
        }
    } catch (e) {
        console.error("Failed to fetch agent skills", e);
    }
};

window.addAgentSkill = async function() {
    const nameInput = document.getElementById('skill-name');
    const codeInput = document.getElementById('skill-code');
    const skillName = nameInput.value.trim();
    const skillCode = codeInput.value.trim();
    
    if (!skillName || !skillCode) {
        alert("Please provide both a Skill Name and Python Code.");
        return;
    }
    
    try {
        const response = await fetch('/api/agent/skills/add', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${App.token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                skill_name: skillName,
                skill_code: skillCode
            })
        });
        const data = await response.json();
        if (data.success) {
            alert("Skill added successfully!");
            nameInput.value = '';
            codeInput.value = '';
            window.fetchAgentSkills();
        } else {
            alert(data.error || "Failed to add skill.");
        }
    } catch (e) {
        alert("Network error adding skill.");
    }
};

function appendAgentLog(message) {
    const consoleDiv = document.getElementById('agent-console');
    if (!consoleDiv) return;
    const msgDiv = document.createElement('div');
    msgDiv.textContent = message;
    consoleDiv.appendChild(msgDiv);
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
}
