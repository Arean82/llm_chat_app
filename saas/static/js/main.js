// main.js - Application Bootstrap and Event Routing
import { App, saveSession, loadSession, clearSession } from './state.js';
import { login, register, validatePassport } from './auth.js';
import { updateProfile } from './api.js';
import { 
    fillPrompt, toggleArenaMode, startNewOrbit, loadModels,
    dispatchPrompt, handleShareOrbit, loadMemoryRoster, loadAdminDashboard
} from './workspace.js';

export function initMainApp() {
    console.log("System initialized. Quantum client loaded.");
    setupEventListeners();
    
    if (loadSession()) {
        launchWorkspace();
    } else {
        clearSessionState();
    }
    
    const promptInput = document.getElementById('main-prompt-input');
    promptInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        const sendBtn = document.getElementById('btn-send-prompt');
        sendBtn.disabled = !this.value.trim();
    });
}

// Ensure globally accessible for inline onclicks in HTML
window.fillPrompt = fillPrompt;
window.togglePasswordVisibility = function(id) {
    const input = document.getElementById(id);
    input.type = input.type === 'password' ? 'text' : 'password';
};

function clearSessionState() {
    clearSession();
    switchView('auth-screen');
    switchStep('login-portal-step');
}

export function switchView(viewId) {
    document.querySelectorAll('.view-container').forEach(el => el.classList.add('hidden'));
    document.getElementById(viewId).classList.remove('hidden');
}

function switchStep(stepId) {
    document.querySelectorAll('.auth-step').forEach(el => el.classList.add('hidden'));
    document.getElementById(stepId).classList.remove('hidden');
}

function setupEventListeners() {
    document.getElementById('link-switch-login').addEventListener('click', (e) => {
        e.preventDefault();
        switchStep('login-portal-step');
    });
    
    document.getElementById('link-switch-register').addEventListener('click', (e) => {
        e.preventDefault();
        switchStep('passport-validation-step');
    });

    document.getElementById('form-validate-passport').addEventListener('submit', handlePassportValidation);
    document.getElementById('form-register').addEventListener('submit', handleRegistration);
    document.getElementById('form-login').addEventListener('submit', handleLogin);
    document.getElementById('form-update-settings').addEventListener('submit', handleSettingsUpdate);
    
    document.getElementById('btn-signout').addEventListener('click', clearSessionState);
    document.getElementById('btn-new-chat').addEventListener('click', startNewOrbit);
    document.getElementById('btn-send-prompt').addEventListener('click', dispatchPrompt);
    document.getElementById('btn-arena-toggle').addEventListener('click', toggleArenaMode);
    
    document.getElementById('btn-open-settings').addEventListener('click', openSettingsModal);
    document.getElementById('btn-close-settings').addEventListener('click', closeSettingsModal);
    document.getElementById('btn-cancel-settings').addEventListener('click', closeSettingsModal);
    
    document.getElementById('main-prompt-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            dispatchPrompt();
        }
    });

    document.getElementById('nav-chat').addEventListener('click', () => switchView('workspace-screen'));
    document.getElementById('nav-memory').addEventListener('click', () => {
        switchView('memory-screen');
        loadMemoryRoster();
    });
    document.getElementById('nav-admin').addEventListener('click', () => {
        switchView('admin-screen');
        loadAdminDashboard();
    });
    
    document.getElementById('btn-share-orbit').addEventListener('click', handleShareOrbit);
}

function openSettingsModal() {
    if (!App.user) return;
    document.getElementById('set-username').value = App.user.username;
    document.getElementById('set-email').value = App.user.email;
    document.getElementById('set-api-key').value = '';
    document.getElementById('set-password').value = '';
    
    const feedback = document.getElementById('settings-feedback');
    feedback.className = 'status-box hidden';
    feedback.textContent = '';
    
    document.getElementById('settings-modal').classList.remove('hidden');
}

function closeSettingsModal() {
    document.getElementById('settings-modal').classList.add('hidden');
}

async function handleSettingsUpdate(e) {
    e.preventDefault();
    const newUsername = document.getElementById('set-username').value.trim();
    const newApiKey = document.getElementById('set-api-key').value.trim();
    const newPassword = document.getElementById('set-password').value.trim();
    const feedback = document.getElementById('settings-feedback');
    
    feedback.className = 'status-box hidden';
    if (!newUsername) {
        feedback.textContent = "Display Name cannot be empty.";
        feedback.className = 'status-box error';
        return;
    }
    
    try {
        const data = await updateProfile(App.token, newUsername, newApiKey, newPassword);
        if (data.success) {
            feedback.textContent = data.message;
            feedback.className = 'status-box success';
            
            saveSession(data.user, data.user.passport_token || App.token);
            document.getElementById('display-username').textContent = App.user.username;
            
            setTimeout(() => closeSettingsModal(), 1500);
        } else {
            feedback.textContent = data.error || "Failed to synchronize profile.";
            feedback.className = 'status-box error';
        }
    } catch (err) {
        feedback.textContent = "Network timeout communicating with Security Node.";
        feedback.className = 'status-box error';
    }
}

let _validatedKeyCache = null;

async function handlePassportValidation(e) {
    e.preventDefault();
    const provider = document.getElementById('provider-select').value;
    const apiKey = document.getElementById('passport-key-input').value.trim();
    const feedback = document.getElementById('passport-feedback');
    
    const btn = document.getElementById('btn-run-validation');
    const idleText = btn.querySelector('.idle-text');
    const loadText = btn.querySelector('.loading-text');

    idleText.classList.add('hidden');
    loadText.classList.remove('hidden');
    feedback.classList.add('hidden');
    
    try {
        const data = await validatePassport(provider, apiKey);
        if (data.success) {
            _validatedKeyCache = apiKey;
            switchStep('account-provision-step');
        } else {
            feedback.textContent = data.error || "Verification failure.";
            feedback.className = "status-box error";
        }
    } catch (err) {
        feedback.textContent = "Host gateway connection failed. Is server running?";
        feedback.className = "status-box error";
    } finally {
        idleText.classList.remove('hidden');
        loadText.classList.add('hidden');
    }
}

async function handleRegistration(e) {
    e.preventDefault();
    if (!_validatedKeyCache) return switchStep('passport-validation-step');
    
    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value.trim();
    const feedback = document.getElementById('register-feedback');
    feedback.classList.add('hidden');
    
    try {
        const data = await register({
            api_key: _validatedKeyCache,
            username, email, password, key_type: 'byok'
        });
        
        if (data.success) {
            alert("SaaS Grid Workspace Provisioned successfully! Redirecting to login...");
            switchStep('login-portal-step');
        } else {
            feedback.textContent = data.error || "Registration failed.";
            feedback.className = "status-box error";
        }
    } catch (err) {
        feedback.textContent = "Critical network link failure.";
        feedback.className = "status-box error";
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const identifier = document.getElementById('login-id').value.trim();
    const password = document.getElementById('login-pass').value.trim();
    const feedback = document.getElementById('login-feedback');
    
    const btn = document.getElementById('btn-run-login');
    const idleText = btn.querySelector('.idle-text');
    const loadText = btn.querySelector('.loading-text');
    
    feedback.classList.add('hidden');
    idleText.classList.add('hidden');
    loadText.classList.remove('hidden');
    
    try {
        const data = await login(identifier, password);
        if (data.success) {
            saveSession(data.user, data.user.passport_token);
            launchWorkspace();
        } else {
            feedback.textContent = data.error || "Unauthorized.";
            feedback.className = "status-box error";
        }
    } catch (err) {
        feedback.textContent = "Link failure.";
        feedback.className = "status-box error";
    } finally {
        idleText.classList.remove('hidden');
        loadText.classList.add('hidden');
    }
}

function launchWorkspace() {
    switchView('workspace-screen');
    document.getElementById('display-username').textContent = App.user.username;
    
    const tierBadge = document.getElementById('display-tier');
    tierBadge.className = `key-tag ${App.user.key_type}`;
    tierBadge.textContent = App.user.key_type === 'admin_funded' ? 'Admin Vault' : 'BYOK Tier';
    
    if (App.user.key_type === 'admin_funded') {
        document.getElementById('nav-admin').classList.remove('hidden');
    } else {
        document.getElementById('nav-admin').classList.add('hidden');
    }
    
    loadModels();
    
    if (App.user.usage) {
         App.tallyPrompt = App.user.usage.prompt_tokens || 0;
         App.tallyComp = App.user.usage.comp_tokens || 0;
         document.getElementById('counter-prompt').textContent = App.tallyPrompt.toLocaleString();
         document.getElementById('counter-comp').textContent = App.tallyComp.toLocaleString();
    }
    
    startNewOrbit();
}

if (document.readyState === 'loading') {
    document.addEventListener("DOMContentLoaded", initMainApp);
} else {
    initMainApp();
}
