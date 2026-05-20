# Headless & API Engine Guide (v6.7)

This guide explains how to use the **LLM Chat App** in Headless mode for IDE integration, API serving, and CLI model management.

---

## 1. Quick Start (Terminal Modes)

### 🚀 100% Automatic Environment Auto-Detection
The application features complete environment self-awareness across Windows, macOS, and Linux out-of-the-box:
- **Zero Configuration Fallback:** If you launch the application on a headless server, remote SSH terminal, or Docker container without standard display drivers, the system **automatically catches graphical display connection failures and boots directly into Headless server mode** without a single crash!
- **Interactive SSH shells:** Launching the app within an SSH session automatically detects interactive terminal handles, booting either the direct CLI Chat Loop or the Headless API daemon seamlessly.

The Headless Engine supports two primary manual execution workflows from the terminal:

### A. Standalone API Server (for IDE Extensions)
To launch the background server on Port 5000:
```bash
python main.py --headless
```

### B. Interactive Terminal Chat (Direct CLI Mode)
To launch a direct chat loop inside your command line:
```bash
python main.py --cli
```

### Dynamic CLI Authentication Gate
If running headless modes for the first time or after a manual logout, the engine will launch the secure **CLI Authentication Gate** directly in your terminal:

1. **Step 1: Select Platform/SDK Group**:
   You will select your target driver interface from the index:
   ```text
   Step 1: Select Platform/SDK Group:
     [1] OpenAI Compatible SDK
     [2] Google Gemini SDK
     [3] Groq LPU Acceleration
     [4] Anthropic Claude SDK
     ...
   ```
2. **Step 2: Select Ecosystem**:
   You will select your specific endpoint provider (e.g., under `OpenAI Compatible SDK`):
   ```text
   Step 2: Select Ecosystem under OpenAI Compatible SDK:
     [1] NVIDIA NIM
     [2] Official OpenAI
     [3] OpenRouter
     [4] DeepSeek
     ...
   ```
3. **Automatic URL Configuration**:
   All endpoints use **static, predefined Base URLs**. The user is never prompted to input a base URL; the system resolves and writes it behind the scenes automatically.
4. **API Key Entry**:
   You will be prompted to paste your API Key. The key is immediately saved securely into your OS native Keyring (Vault) and synchronized with the GUI.

*Note for local/offline ecosystems (like Ollama): If you select an offline provider, the setup completes immediately without prompting you for an API key.*

---

## 2. Interactive CLI Mode Operations

When you launch `python main.py --cli`, you enter a fully interactive terminal prompt.

### Chat & Streaming
* Type normal messages. The engine streams the assistant's response to your terminal in real-time.
* Fully maintains conversational memory for the duration of the terminal session.

### Special Commands
You can control the active engine on-the-fly by typing commands prefixed with a `/` slash:

* **`/list`**: Lists all available model IDs currently registered in the synchronized local manifests.
* **`/model <model_id>`**: Instantly switches the active chat model to the specified ID.
  * *Example:* `/model meta/llama-3.1-405b-instruct`
* **`/help`**: Prints a quick roster of all available terminal commands.
* **`/exit` or `/quit`**: Safely terminates the interactive session.

---

## 3. CLI Model Management

The headless engine includes a modular model manager for terminal-based control.

### Listing Available Models
To see which models are currently cached in your local manifest:
```bash
python main.py --list-models
```
*Note: Models are grouped dynamically by their capability categories (`chat`, `embedding`, `reranking`, `audio`) and display their specialized capability markers and auto-generated descriptions.*

### Updating the Manifest
To fetch the latest models from your active provider and write them straight to your local manifest shards:
```bash
python main.py --update-models
```

---

## 4. IDE Integration (VS Code / JetBrains)

The Headless Engine acts as the primary API provider for our IDE extensions. 

1. **Start the Engine**: Run `python main.py --headless`.
2. **Endpoint**: The engine listens on `http://localhost:5000` (default).
3. **Connectivity**: Once the engine is live, your VS Code or JetBrains extension will automatically connect to it to provide inline chat and code completions.

---

## 5. Security & Session Integrity

The application enforces absolute cryptographic session boundaries between the CLI and the GUI:

* **OS-Level Keyring Custody**: API keys are always stored inside your system's native OS credential vault (Windows Credential Manager / Apple Keychain / Linux Secret Service) rather than plain-text configs.
* **Post-Logout Security Gate**: When you click "Logout" in the GUI or explicitly reset settings, the active provider session variable is deleted. The logic-tier `hydrate()` mechanism enforces a strict security block: if no active session exists, it **refuses** to silently fetch or pull keys from the Keyring vault, forcing a fresh, secure login prompt.
* **RAM Flushing**: Explicit logout sequences automatically trigger clean memory erasure and application restarts to guarantee zero diagnostic credential remnants in volatile memory.

---

## 6. Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Port 5000 busy** | Ensure no other instances of the app or Flask servers are running. |
| **Auth Prompt Loop** | Run `python main.py --cli` once, select your ecosystem, enter your key, and verify completion. |
| **No models shown** | Run `python main.py --update-models` to refresh the local sharded manifests. |

---
*Maintenance: Decoupled Logic v6.7. Base: arean82.llmchatapp.v6.7*
