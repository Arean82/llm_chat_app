# Headless & API Engine Guide (v9.0)

This guide explains how to use the **Synora Studio** in Headless mode for IDE integration, API serving, and CLI model management.

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

## 2. CLI Command Reference

The `main.py` entry point accepts several flags to control the Headless and API environments directly:

| Command | Description |
| :--- | :--- |
| `--headless` | Launch the standalone API Server (Port 5000). |
| `--cli` | Launch the interactive terminal chat session. |
| `--list-models` | List all models currently in the local manifest. |
| `--update-models` | Fetch latest models from the active provider. |
| `--migrate` | Migrate chat history transactionally between databases. |
| `--reset-admin` | Reset the SaaS admin credentials to default. |
| `--api-manager` | Manage the Local API Server (Port 5000) settings interactively. |
| `--help` / `-h` | Show the detailed help message. |

---

## 3. Interactive CLI Mode Operations

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

## 4. CLI Model Management

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

## 5. Local API Server Management

You can configure the standalone Universal API Server (Port 5000) directly from the command line using the built-in API Manager.

To view the current API status, regenerate your key, or forcefully enable/disable the server:
```bash
python main.py --api-manager
```
This launches an interactive menu:
1. **Status Overview:** Displays whether the API is `[ENABLED]` or `[DISABLED]`, and prints your current secure API Key.
2. **Toggle Control:** Disabling the API will shut down Port 5000 and prevent IDE extensions from connecting. 
3. **Key Regeneration:** Instantly generates a new secure UUID key for the server.

*Note: Changes made in the CLI update the secure Vault instantly, but require restarting any active `--headless` engine processes to apply network changes.*

---

## 6. IDE Integration (VS Code / JetBrains)

The Headless Engine acts as the primary API provider for our IDE extensions. 

1. **Start the Engine**: Run `python main.py --headless`.
2. **Endpoint**: The engine listens on `http://localhost:5000` (default).
3. **Connectivity**: Once the engine is live, your VS Code or JetBrains extension will automatically connect to it to provide inline chat and code completions.

---

## 7. Security & Session Integrity

The application enforces absolute cryptographic session boundaries between the CLI and the GUI:

* **OS-Level Keyring Custody**: API keys are always stored inside your system's native OS credential vault (Windows Credential Manager / Apple Keychain / Linux Secret Service) rather than plain-text configs.
* **Post-Logout Security Gate**: When you click "Logout" in the GUI or explicitly reset settings, the active provider session variable is deleted. The logic-tier `hydrate()` mechanism enforces a strict security block: if no active session exists, it **refuses** to silently fetch or pull keys from the Keyring vault, forcing a fresh, secure login prompt.
* **RAM Flushing**: Explicit logout sequences automatically trigger clean memory erasure and application restarts to guarantee zero diagnostic credential remnants in volatile memory.

---

## 8. ARM & Cloud IaaS Deployment Guide (Oracle / Raspberry Pi)

If deploying the Headless Engine to an `aarch64` / ARM Linux environment (like Oracle Cloud Ampere or Raspberry Pi), you must install specific OS-level dependencies *before* running `pip install -r requirements.txt`.

### 1. OS-Level Requirements
ARM environments often lack pre-built PyPI wheels for PySide6 and need an active Secret Service for the Keyring vault. Install these native packages to prevent compilation crashes:
```bash
sudo apt update
sudo apt install -y python3-pyside6.qtcore python3-pyside6.qtwidgets \
                    build-essential python3-dev \
                    libsecret-1-0 dbus-x11 gnome-keyring
```
*(By installing PySide6 natively via apt, pip will skip attempting to compile Qt6 from C++ source, saving hours of downtime).*

### 2. Qdrant Docker Engine
The embedded Python Qdrant server utilizes Rust bindings that often fail to compile on ARM Linux. It is highly recommended to run the official Qdrant Docker container instead:
```bash
sudo docker run -d -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```
Then, link the application to the container using the environment variable:
```bash
export QDRANT_URL="http://localhost:6333"
python main.py --headless
```

---

## 9. Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Port 5000 busy** | Ensure no other instances of the app or Flask servers are running. |
| **Auth Prompt Loop** | Run `python main.py --cli` once, select your ecosystem, enter your key, and verify completion. |
| **No models shown** | Run `python main.py --update-models` to refresh the local sharded manifests. |

---
*Maintenance: SaaS Web Architecture v9.0. Base: arean82.synorastudio.v9.0*
