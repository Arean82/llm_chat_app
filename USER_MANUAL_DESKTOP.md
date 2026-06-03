# 🖥️ Synora Studio - Desktop User Guide

Welcome to the **Synora Studio Desktop Client**, a sleek, high-performance workstation for interacting with the world's most powerful AI ecosystems including OpenAI, Google Gemini, Anthropic, Ollama, NVIDIA NIM, Groq, and custom local endpoints.

---

## 1. Getting Started

### Launching the Application
To launch the desktop client, run the following command in your terminal:
```bash
python main.py
```
*(You can also use the packaged desktop shortcut if provided by your administrator).*

### 🔑 The Secure Admin Login Gate
Upon launching the client, you will be greeted by the **Synora Admin Login Gateway**:
1. Log in with your Super Admin credentials (`admin` / `admin` by default). Your credentials are secure and validated against the partitioned database.
2. The login screen features a high-fidelity vector eyelash eye toggle button directly inside the password field to securely show or hide your typed password.

### 📸 The Ecosystem Selector Dialog
Once authenticated, if no active ecosystem has been configured yet, the **Switch Ecosystem** dialog appears:
1. Select your active AI provider ecosystem (e.g., Google Gemini, NVIDIA NIM, OpenAI, or Local Offline).
2. Enter your private API Key.
   - *Note: If you are using local models via Ollama or LM Studio, no key is required. The sweeper will automatically detect and bind your offline endpoints.*
3. Click Save. Your keys are immediately encrypted using zero-trust symmetric PBKDF2 ciphers derived dynamically from your master login password. Raw keys are never written to disk and exist only in transient system memory during runtime sessions.

---

## 2. Navigating the Interface

### The Main Chat Canvas
- **Message Input**: Type your query in the bottom input bar. Press `Enter` to send, or `Shift + Enter` for a new line.
- **Dynamic Formatting**: Responses are rendered in real-time with rich Markdown, tables, and syntax-highlighted code blocks.
- **File Attachments**: Click the 📎 icon to attach code files (`.py`, `.js`, etc.) or documents directly into the chat context.

### Sidebars & History
- **Conversation History**: Previous chats are automatically saved to your local SQLite database using Write-Ahead Logging (WAL) for maximum safety against corruption.
- **Model Selector**: Use the top-right dropdown to swap between available AI models on the fly. The UI will only show models that you have active keys for!

---

## 3. Advanced Features

### ⚔️ Model Arena (Benchmarking)
Want to test two AI models against each other?
1. Click the **Arena** button.
2. Select your two combatants (e.g., *GPT-4o vs Claude 3.5 Sonnet*).
3. Send a prompt. Both models will stream their responses side-by-side.
4. Evaluate their performance and declare a winner!

### 🧠 Semantic Memory (RAG Database)
Your app is equipped with a high-performance **Qdrant Vector Database**.
1. Open the **Memory Explorer** via the sidebar.
2. Upload a large document or codebase.
3. The AI will chunk, vectorize, and index the file. In future chats, the AI can "remember" and reference these precise documents!

### ⚙️ Generation Parameters & Reranking
Click the **Settings** gear icon to access advanced controls:
- **Temperature / Tokens**: Control the creativity and length of the AI's response.
- **System Instructions**: Set global rules (e.g., *"Always reply in Pirate speak"*).
- **2-Stage Reranking**: Improve the precision of document search by enabling a Cross-Encoder Reranker.

---

## 4. Headless & IDE Integration

For advanced users and developers, the desktop client features a fully functional **Local API Server**!

### Launching the API
In the **Settings > Local API Control** tab, you can enable the background API daemon. This spins up an OpenAI-compatible endpoint on port `5000`.

### Integrating with IDEs (VS Code / Cursor / PyCharm)
You can use the desktop application to route AI intelligence directly into your code editor!
1. Point your IDE's custom endpoint setting to: `http://localhost:5000/v1`
2. Use the Local API Key provided in your desktop app's Settings menu.
3. The IDE can now leverage your desktop's memory, context, and model configurations securely!

---

## 5. Operator Admin Tools

The following standalone utilities are exclusively reserved for the hosting administrator. They are **not distributed** with the public client bundle.

### 🔄 Companion Operation (Database Relocator)
Safely migrate your SaaS tenant database from Turso/libSQL to PostgreSQL or MySQL.

- **From the Desktop App**: Navigate to **Settings → Database Relocator (Companion Operation)**. This will auto-save your chat, close the main app to release database locks, and launch the companion utility.
- **CLI/Headless Mode**: For remote servers, run:
  ```bash
  python operator_tools/companion/companion_operation.py --headless
  ```
- **Production EXE**: Use `Companion_Operation.exe` (or `Companion_Operation.exe --headless` for terminal mode).

### 🔐 Master Password Reset
If you lose your Super Admin password, reset it to `admin` using:
```bash
python operator_tools/admin_reset/reset_admin.py
```
Or in production: `Admin_Reset.exe`

> **Note**: The legacy `scripts/reset_admin.py` is deprecated and automatically redirects to the canonical `operator_tools/admin_reset/reset_admin.py`.
