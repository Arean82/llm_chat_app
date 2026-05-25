# 🖥️ LLM Chat App - Desktop User Guide

Welcome to the **LLM Chat App Desktop Client**, a sleek, high-performance workstation for interacting with the world's most powerful AI ecosystems including OpenAI, Google Gemini, Anthropic, Ollama, NVIDIA NIM, Groq, and custom local endpoints.

---

## 1. Getting Started

### Launching the Application
To launch the desktop client, run the following command in your terminal:
```bash
python main.py
```
*(You can also use the packaged desktop shortcut if provided by your administrator).*

### The API Management Gate
Upon your first launch, you will be greeted by the **API Key Setup Screen**. 
1. Select your desired ecosystem (e.g., `OpenAI Compatible`, `Google Gemini`, or `Local Offline Providers`).
2. Enter your private API Key.
   - *Note: If you are using local models via Ollama or LM Studio, no key is required. The system will automatically detect and bind to your offline endpoints.*
3. Your key is securely encrypted and stored natively in your Operating System's credentials vault.

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
