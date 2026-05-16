# Headless & API Engine Guide (v7.0)

This guide explains how to use the **LLM Chat App** in Headless mode for IDE integration, API serving, and CLI model management.

---

## 1. Quick Start (Terminal)

To launch the application in headless mode, use the `--headless` flag:

```bash
python main.py --headless
```

### Initial Setup
If it is your first time running headless or you have logged out, the engine will automatically trigger the **CLI Authentication Gate**:
1. Select your provider (nvidia, google, openai).
2. Paste your API Key.
3. (Optional) Provide a custom Base URL.

Once authenticated, the engine will synchronize the model manifest and start the **Standalone API Server**.

---

## 2. CLI Model Management

The headless engine includes a modular model manager for terminal-based control.

### Listing Available Models
To see which models are currently cached in your local manifest:
```bash
python main.py --list-models
```

### Updating the Manifest
To fetch the latest models from your active provider:
```bash
python main.py --update-models
```

---

## 3. IDE Integration (VS Code / JetBrains)

The Headless Engine acts as the primary API provider for our IDE extensions. 

1. **Start the Engine**: Run `python main.py --headless`.
2. **Endpoint**: The engine listens on `http://localhost:5000` (default).
3. **Connectivity**: Once the engine is live, your VS Code or JetBrains extension will automatically connect to it to provide inline chat and code completions.

---

## 4. Key Features

*   **Zero-UI Dependency**: Can run on Linux servers without a desktop environment (X11/Wayland).
*   **Automatic Auth Recovery**: Uses the same OS Vault (Keyring) as the GUI version.
*   **Persistent API**: The server stays live until terminated with `Ctrl+C`, ensuring stable connections for long-running IDE sessions.
*   **Safe Shutdown**: Implements full thread-joining logic to prevent data corruption in the vector database or model manifest.

---

## 5. Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Port 5000 busy** | Ensure no other instances of the app or Flask servers are running. |
| **Auth Error** | Run `python main.py --headless` and re-enter your API key when prompted. |
| **No models shown** | Run `python main.py --update-models` to refresh the manifest. |

---
*Maintenance: Decoupled Logic v7.1. Base: arean82.llmchatapp.v6.1*
