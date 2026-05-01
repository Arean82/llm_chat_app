# 🌐 LLM Chat App: Universal API Server

The **Universal API Server** acts as a bridge between your local LLM and any external IDE or application. It exposes an **OpenAI-compatible REST API**, allowing you to integrate powerful local intelligence into your existing development workflow.

[Features](#-features) • [Getting Started](#-getting-started) • [API Endpoints](#-api-endpoints) • [Health Check Example](#-health-check-example) • [Chat Completions](#-chat-completions) • [Code Integration](#-code-integration) • [Testing the API](#-testing-the-api) • [](#-ide-integration-guide) • [Key Technical Notes](#-key-technical-notes)


VS Code extension `.vsix` file is available in the `extension/` folder.
---

## ✨ Features

- 🚀 **Real-time Streaming:** Watch the AI generate responses token by token, with zero lag.
- 🧠 **Conversation History:** Maintain context across requests with session tracking.
- 🌡️ **Temperature Control:** Adjust creativity level (0.0 to 1.0) per request.
- 📏 **Max Tokens Control:** Set response length limit per request.
- 💬 **System Messages:** Support for custom system instructions per conversation.
- 🔄 **Session Management:** Clear conversation history via API endpoint.
---

## 🚀 Getting Started

1.  **Enable Server:** Navigate to `Tools` → `Universal API Server`.  
2.  **Verify Status:** A ✅ icon indicates the server is active.  
3.  **Base URL:** All requests should be directed to:  
    `http://localhost:5000`  

---

## 🛣️ API Endpoints

| **Endpoint** | **Method** | **Description** |
| :--- | :--- | :--- |
| `/health` | `GET` | Verifies server status and active model. |
| `/v1/models` | `GET` | Lists available OpenAI-compatible models. |
| `/v1/chat/completions` | `POST` | Sends a message and receives an AI response. |
| `/v1/chat/history/<session_id>` | `DELETE` | Clear conversation history for a session |

---

## 🏥 Health Check Example
**Response:**
```json
{
  "status": "running",
  "model": "meta/llama-3.3-70b-instruct"
}
```

---

## 🗣️ Chat Completions 

### Request Body Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `messages` | array | Required | Chat messages with `role` and `content` |
| `stream` | boolean | `false` | Enable token-by-token streaming |
| `temperature` | float | `0.7` | Creativity (0.0 = deterministic, 1.0 = creative) |
| `max_tokens` | integer | `4096` | Maximum response length |
| `session_id` | string | `"default"` | Maintain conversation history per session |

### Example with all parameters

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are a coding assistant"},
      {"role": "user", "content": "Write a Python function"}
    ],
    "stream": true,
    "temperature": 0.5,
    "max_tokens": 1000,
    "session_id": "my-session"
  }'
```

### Clear Conversation History

```bash
curl -X DELETE http://localhost:5000/v1/chat/history/my-session
```

---

## 💻 Code Integration

### 🐚 cURL (Terminal)
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Explain Python in one sentence"}]}'
```

---

### 🐍 Python
```python
import requests

payload = {"messages": [{"role": "user", "content": "Hello"}]}
response = requests.post("http://localhost:5000/v1/chat/completions", json=payload)

print(response.json()["choices"][0]["message"]["content"])
```

---

### 📜 JavaScript
```javascript
const response = await fetch('http://localhost:5000/v1/chat/completions', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    messages: [{"role": "user", "content": "Hello"}]
  })
});
const data = await response.json();
console.log(data.choices[0].message.content);
```

---
## 🧪 Testing the API

To ensure your **Universal API Server** is configured correctly, follow these steps:

---

### 1. Enable the Server
Navigate to **Tools** → **Universal API Server**. A ✅ indicates the server is active and listening on `http://localhost:5000`.

### 2. Verify Server Health
Open your terminal and run the following command to check the status:
```bash
curl http://localhost:5000/health
```
**Expected Response:**
```json
{"status": "running", "model": "your-selected-model"}
```

### 3. Test Chat Completions
Send a test prompt to verify the LLM integration:
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "Say hello"}]}'
```

> **Note:** The server is only accessible via `localhost` for security. Ensure no firewall is blocking port **5000**.

---

## 🛠️ IDE Integration Guide

Easily connect your favorite editor using OpenAI-compatible plugins.

### 🔹 VS Code (Continue Extension)
Modify `~/.continue/config.json`:
```json
{
  "models": [{
    "title": "LLM Chat App",
    "provider": "openai",
    "model": "any",
    "apiBase": "http://localhost:5000/v1",
    "apiKey": "local-dev"
  }]
}
```

### 🔹 IntelliJ / PyCharm (CodeGPT)
1. Install **CodeGPT** plugin.
2. Add a **Custom OpenAI** provider.
3. Set URL to `http://localhost:5000/v1`.

### 🔹 Eclipse (LlamaWhip)
1. Install **LlamaWhip** from the marketplace.
2. Configure the API endpoint to `http://localhost:5000/v1`.

---

## 📝 Key Technical Notes

* **🔒 Security:** The server binds strictly to `localhost`. It is not accessible from external networks.
* **⚙️ Model Selection:** The API automatically uses whichever model is currently active in the main application UI.
* **⏳ Performance:** Responses are synchronous. The default request timeout is **60 seconds**.
* **🔑 Auth:** No API key is required, but you can pass any dummy value (e.g., `sk-123`) if your plugin requires one.
* **🌡️ Temperature Range:** 0.0 (focused/deterministic) to 1.0 (creative/diverse).
* **📏 Token Limits:** Max tokens per response defaults to 4096, configurable per request.
* **💾 Session Management:** Use `session_id` to maintain separate conversation contexts.
* **🧹 History Cleanup:** Send `DELETE` request to `/v1/chat/history/<session_id>` to clear context.