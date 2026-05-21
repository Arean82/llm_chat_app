// auth.js - Authentication flow utilities
export async function login(usernameOrEmail, password) {
  const resp = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username_or_email: usernameOrEmail, password })
  });
  return resp.json();
}

export async function register(userInfo) {
  const resp = await fetch('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userInfo)
  });
  return resp.json();
}

export async function validatePassport(provider, apiKey) {
  const resp = await fetch('/api/validate_passport', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, api_key: apiKey })
  });
  return resp.json();
}
