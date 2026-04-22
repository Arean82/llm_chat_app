# IDE Integration Guide

## Prerequisites

1. **LLM Chat App must be running** with API server enabled (Tools → Universal API Server)
2. ✅ icon indicates server is running on `http://localhost:5000`

---

## VS Code Integration

### Option A: Continue Extension (Quick Setup)

1. Install **Continue** extension from VS Code marketplace
2. Create `~/.continue/config.json`:

```json
{
  "models": [{
    "title": "LLM Chat App",
    "provider": "openai",
    "model": "any",
    "apiBase": "http://localhost:5000/v1",
    "apiKey": "dummy"
  }]
}
```

3. Restart VS Code

### Option B: Official LLM Chat Extension (Full Features)

1. Download `vscode-llm-chat-1.0.0.vsix` from `vscode-llm-chat/` folder
2. VS Code → Extensions (Ctrl+Shift+X) → `...` → Install from VSIX
3. Reload VS Code

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

### Installation

1. Download `jetbrains-llm-chat-1.0.0.zip` from `jetbrains-llm-chat/build/distributions/`
2. **File → Settings → Plugins** (or **Ctrl+Alt+S**)
3. Click ⚙️ → **Install Plugin from Disk**
4. Select the `.zip` file
5. Restart IDE

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
  -H "Content-Type: application/json" `
  -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Explain this code\"}]}'
```

### Future Support
A dedicated Visual Studio 2022 extension can be built using the same API. Request it via GitHub issues.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Failed to connect" | Ensure LLM Chat App is running with API server enabled (✅ icon) |
| Port 5000 conflict | Change port in API server settings (future feature) |
| No response | Check model is selected in LLM Chat App |
| Timeout | Increase timeout or check network |

---

## API Reference

For complete API documentation, see [API Documentation](API_SERVER.md)
