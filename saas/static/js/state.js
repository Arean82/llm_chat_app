// state.js - Central Application State
export const App = {
    user: null,
    token: null,
    activeConversationId: null,
    conversations: {},
    isGenerating: false,
    arenaMode: false,
    tallyPrompt: 0,
    tallyComp: 0,
    modelsCache: null
};

export function saveSession(user, token) {
    App.user = user;
    App.token = token;
    localStorage.setItem('quantum_user', JSON.stringify(user));
    localStorage.setItem('quantum_token', token);
}

export function loadSession() {
    const savedUser = localStorage.getItem('quantum_user');
    const savedToken = localStorage.getItem('quantum_token');
    if (savedUser && savedToken) {
        try {
            App.user = JSON.parse(savedUser);
            App.token = savedToken;
            return true;
        } catch (e) {
            clearSession();
        }
    }
    return false;
}

export function clearSession() {
    localStorage.removeItem('quantum_user');
    localStorage.removeItem('quantum_token');
    App.user = null;
    App.token = null;
}
