# IDE Integration Guide

[Prerequisites](#-prerequisites) • [VS Code Integration](#-vs-code-integration) • [JetBrains IDEs](#-jetbrains-ides) • [Visual Studio 2022](#-visual-studio-2022) • [Troubleshooting](#-troubleshooting) • [API Reference](#-api-reference)

---

## Prerequisites

1. **Synora Studio must be running** with API server enabled (Tools → Universal API Server).
2. ✅ icon indicates server is running on `http://localhost:5000`.
3. 🔐 **API Key Management:** You can view, disable, or regenerate your Local API Key using the GUI Settings, the new CLI command `python main.py --api-manager`, or remotely via the SaaS Admin Dashboard (Node Config → Local API Control).

---

## VS Code Integration

### Option A: Continue Extension (Quick Setup)

1. Install **Continue** extension from VS Code marketplace
2. Create `~/.continue/config.json`:

```json
{
  "models": [{
    "title": "Synora Studio",
    "provider": "openai",
    "model": "any",
    "apiBase": "http://localhost:5000/v1",
    "apiKey": "llm-local-auth-82c4f3eb0d"
  }]
}
```

3. Restart VS Code

### Option B: Official LLM Chat Extension (V2.0.0 Multi-Tenant & Onboarding)

1. Download **[vscode-llm-chat-2.0.0.vsix](file:///c:/Users/user/OneDrive/Desktop/python/synora_studio/extension/vscode-llm-chat-2.0.0.vsix)** from the `extension/` folder in the project root.
2. VS Code → Extensions (Ctrl+Shift+X) → `...` → **Install from VSIX...**
3. On first load, if unconfigured or unreachable, it launches the interactive **Onboarding Gateway** panel. Enter your server URL (e.g. `http://localhost:5000` for offline local, or `http://localhost:8888` for SaaS Multi-Tenant Cloud), log in or register, and the plugin will securely save your Bearer Passport token directly inside VS Code's native OS keychain secrets vault.
4. You can manually adjust these inside VS Code Preferences under the `llmChat.apiUrl` and `llmChat.apiToken` settings.

**Commands available:**

| **Command** | **Shortcut** |
| :--- | :--- | 
| Send Selected Code | Right-click → LLM Chat |
| Send Current File | Right-click → LLM Chat |
| Send Entire Project | Command Palette |
| Fix This Code | Right-click on selection |
| Explain This Code | Right-click on selection |
| Generate Docstring | Right-click on function |
| Generate Unit Tests | Right-click on selection |
| Generate Commit Message | Git panel |
| Generate Terminal Command | Tools menu |

---

## JetBrains IDEs (IntelliJ, PyCharm, WebStorm, CLion, Rider)

### Supported IDEs
- IntelliJ IDEA (Ultimate/Community)
- PyCharm (Professional/Community)
- WebStorm
- PHPStorm
- CLion
- Rider
- GoLand
- Android Studio

### Installation & Onboarding (V2.0.0 Multi-Tenant & Onboarding)

1. Download **[jetbrains-llm-chat-2.0.0.zip](file:///c:/Users/user/OneDrive/Desktop/python/synora_studio/extension/jetbrains-llm-chat-2.0.0.zip)** from the `extension/` folder in the project root.
2. **File → Settings → Plugins** (or **Ctrl+Alt+S**)
3. Click ⚙️ → **Install Plugin from Disk...** and select the `.zip` file.
4. Restart your IDE.
5. On project startup, if unconfigured or offline, it opens the interactive **Onboarding Gateway** multi-tab dialog. Enter your SaaS/local server host URL, credentials (or dynamic register payloads), and the plugin will securely save your dynamic tenant Bearer Passport directly in your OS keychain vault via the IntelliJ `PasswordSafe` API.
6. You can manually check or run connectivity tests anytime inside IDE Preferences under **File | Settings | Tools | LLM Chat**.

### Features

| Feature | How to Access |
|---------|---------------|
| Send Selection | Right-click on selected code |
| Fix This Code | Right-click on selection |
| Explain This Code | Right-click on selection |
| Generate Docstring | Right-click on function |
| Generate Unit Tests | Right-click on selection |
| Generate Commit Message | Git commit dialog |
| Generate Terminal Command | Tools menu |
| View Telemetry Health | IDE Status Bar (Hooks into `/v1/system/telemetry`) |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Alt+S` | Send Selection to LLM |

---

## Visual Studio 2022

### Compatibility Note
Visual Studio 2022 uses a different extension model (.vsix for VS, not VS Code). The VS Code extension **will not work** in Visual Studio 2022.

### Alternative: REST API Client

Use any REST API client extension for Visual Studio 2022:

1. Install **REST API Client** from Marketplace
2. Configure endpoint: `http://localhost:5000/v1/chat/completions`
3. Send POST requests with body:

```json
{
  "messages": [{"role": "user", "content": "Your prompt here"}]
}
```

### Alternative: Use curl in Terminal

Open Visual Studio's Developer PowerShell:

```powershell
curl -X POST http://localhost:5000/v1/chat/completions `
  -H "Authorization: Bearer llm-local-auth-82c4f3eb0d" `
  -H "Content-Type: application/json" `
  -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Explain this code\"}]}'
```

### Future Support
A dedicated Visual Studio 2022 extension can be built using the same API. Request it via GitHub issues.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Failed to connect" | Ensure Synora Studio is running with API server enabled (✅ icon) |
| Port 5000 conflict | Port 5000 is mandatory for most integrations. On macOS, disable **AirPlay Receiver** in System Settings. On Windows, check for other web services. |
| No response | Check that a model is selected in Synora Studio |
| Model capability mismatch | Active chat selection popup strictly filters for Chat models (`type == "chat"`). For embeddings or rerankers, the server exposes them directly through specialized endpoints. |
| Timeout | Increase timeout in your IDE settings or check network connectivity |

---

## API Reference

For complete API documentation, see [API Documentation](API_SERVER.md)
