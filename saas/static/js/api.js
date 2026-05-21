// api.js - Centralized fetch wrappers

export async function fetchModels(token) {
    const resp = await fetch('/v1/models', {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    if (!resp.ok) throw new Error("Model manifest retrieval failed");
    return resp.json();
}

export async function updateProfile(token, username, apiKey, password) {
    const resp = await fetch('/api/update_profile', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            username,
            api_key: apiKey || null,
            password: password || null
        })
    });
    return resp.json();
}

export async function initiateChatStream(token, model, messages, webSearch = false) {
    return fetch('/v1/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            model: model,
            messages: messages,
            stream: true,
            web_search: webSearch
        })
    });
}

export async function fetchAdminUsers(token) {
    const resp = await fetch('/api/admin/users', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    return resp.json();
}

export async function fetchAdminStats(token) {
    const resp = await fetch('/api/admin/stats', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    return resp.json();
}

export async function fetchMemoryCollections(token) {
    const resp = await fetch('/api/memory/list', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    return resp.json();
}

export async function generateShareLink(token, messages) {
    const resp = await fetch('/api/share', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ messages })
    });
    return resp.json();
}

export async function fetchTenantCredentials(token) {
    const resp = await fetch('/v1/tenant/credentials', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    return resp.json();
}

export async function saveTenantCredentials(token, credentials) {
    const resp = await fetch('/v1/tenant/credentials', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(credentials)
    });
    return resp.json();
}
