// saas/static/js/system_health.js
import { App } from './state.js';
import { fetchAdminTelemetry, fetchAdminDLQ, retryDLQJob } from './api.js';

let systemHealthPollerInterval = null;

window.showSystemHealthModal = async function() {
    document.getElementById('system-health-modal').style.display = 'flex';
    
    // Clear any existing poller first
    if (systemHealthPollerInterval) {
        clearInterval(systemHealthPollerInterval);
        systemHealthPollerInterval = null;
    }
    
    // Run initial diagnostics immediately
    await pollSystemHealth();
    
    // Set 2-second interval to mirror PySide6 timer
    systemHealthPollerInterval = setInterval(pollSystemHealth, 2000);
};

window.closeSystemHealthModal = function() {
    document.getElementById('system-health-modal').style.display = 'none';
    if (systemHealthPollerInterval) {
        clearInterval(systemHealthPollerInterval);
        systemHealthPollerInterval = null;
    }
};

async function pollSystemHealth() {
    const modal = document.getElementById('system-health-modal');
    if (!modal || modal.style.display === 'none') {
        if (systemHealthPollerInterval) {
            clearInterval(systemHealthPollerInterval);
            systemHealthPollerInterval = null;
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

            // 1. Update Core Connection Status LEDs (Modern green/red)
            if (m.health) {
                const setLedStyle = (id, healthy) => {
                    const el = document.getElementById(id);
                    if (el) {
                        el.style.backgroundColor = healthy ? '#10b981' : '#ef4444';
                    }
                };

                setLedStyle('led-storage', m.health.storage === 'HEALTHY');
                setLedStyle('led-vector', m.health.vector_db === 'HEALTHY');
                setLedStyle('led-cache', m.health.cache === 'HEALTHY');
                setLedStyle('led-queue', m.health.queue === 'HEALTHY');
                setLedStyle('led-llm', m.health.llm === 'HEALTHY');
            }

            // 2. Circuit Breaker Failover Banner Warning
            const banner = document.getElementById('modal-health-failover-banner');
            if (banner) {
                if (m.circuit_breaker_state === 'OPEN') {
                    banner.classList.remove('hidden');
                } else {
                    banner.classList.add('hidden');
                }
            }

            // 3. Populate Active Worker Threads table
            const workersTbody = document.getElementById('health-active-workers-tbody');
            if (workersTbody) {
                if (!m.active_jobs || m.active_jobs.length === 0) {
                    workersTbody.innerHTML = `
                        <tr>
                            <td colspan="4" style="padding: 15px; text-align: center; color: var(--text-dim);">No active jobs running in worker pool.</td>
                        </tr>
                    `;
                } else {
                    workersTbody.innerHTML = '';
                    m.active_jobs.forEach(job => {
                        const stateColor = job.status === 'RUNNING' ? 'var(--accent-success)' : 'var(--text-dim)';
                        workersTbody.innerHTML += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td style="padding: 8px; font-weight: 600;">${job.name}</td>
                                <td style="padding: 8px; font-family: monospace; font-size: 0.8rem; color: var(--accent-cyan);">${job.job_id}</td>
                                <td style="padding: 8px;">${job.task_type}</td>
                                <td style="padding: 8px; color: ${stateColor}; font-weight: 600;">${job.status}</td>
                            </tr>
                        `;
                    });
                }
            }
        }

        // 4. Populate Dead Letter Queue (DLQ) table
        if (dlqRes.success && dlqRes.dlq) {
            const dlqTbody = document.getElementById('health-dlq-tbody');
            if (dlqTbody) {
                if (dlqRes.dlq.length === 0) {
                    dlqTbody.innerHTML = `
                        <tr>
                            <td colspan="5" style="padding: 15px; text-align: center; color: var(--text-dim);">No failed jobs found in DLQ container.</td>
                        </tr>
                    `;
                } else {
                    dlqTbody.innerHTML = '';
                    dlqRes.dlq.forEach(entry => {
                        dlqTbody.innerHTML += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                                <td style="padding: 8px; text-align: center;">
                                    <input type="radio" name="modal-dlq-select" value="${entry.job_id}" style="cursor: pointer; accent-color: var(--accent-success);">
                                </td>
                                <td style="padding: 8px; font-family: monospace; font-size: 0.8rem; color: var(--accent-cyan);">${entry.job_id}</td>
                                <td style="padding: 8px;"><span style="background: rgba(231, 76, 60, 0.15); color: #e74c3c; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">${entry.task_type}</span></td>
                                <td style="padding: 8px; max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${entry.error}">
                                    <code style="color: #e74c3c; font-size: 0.8rem;">${entry.error}</code>
                                </td>
                                <td style="padding: 8px; color: var(--text-dim); font-size: 0.8rem;">${entry.timestamp}</td>
                            </tr>
                        `;
                    });
                }
            }
        }
    } catch (e) {
        console.error("[Telemetry UI] Error updating health state:", e);
    }
}

window.retryModalSelectedDLQJob = async function() {
    const selected = document.querySelector('input[name="modal-dlq-select"]:checked');
    if (!selected) {
        alert("Please select a failed job from the Dead Letter Queue table first.");
        return;
    }
    
    const jobId = selected.value;
    const btn = document.getElementById('btn-modal-health-retry');
    const ogHtml = btn.innerHTML;
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Dispatched...';
    
    try {
        const res = await retryDLQJob(App.token, jobId);
        if (res.success) {
            alert(res.message || `Job '${jobId}' removed from DLQ and resubmitted successfully.`);
            // Refresh modal instantly
            await pollSystemHealth();
        } else {
            alert("Retry Failed: " + (res.error || "Internal server error"));
        }
    } catch (err) {
        alert("Network error retrying job: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = ogHtml;
    }
};
