
# LLM Chat App

A sleek, dark-themed desktop chat application built with Python and PySide6. It interfaces with the NVIDIA NIM API (via the OpenAI SDK) to provide streaming LLM responses, markdown rendering, and conversation management.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- **NVIDIA NIM Integration:** Uses the free NVIDIA NIM API tier (40 requests/minute).
- **Streaming Responses:** Watch the AI generate text in real-time.
- **Multiple Models:** Easily switch between supported NVIDIA models via a popup selector.
- **Thinking/Reasoning Support:** Displays model reasoning tokens (if supported by the selected model).
- **Markdown Rendering:** Beautiful rendering of code blocks, tables, and formatting.
- **Conversation Management:** Save and load chat histories as JSON files.
- **Persistent Settings:** Remembers your API key and selected model between sessions (stored in OS registry/config).
- **Forced Maximized UI:** Clean, fullscreen-locked interface without distracting window controls.

## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- An NVIDIA NIM API Key (Get one free at [build.nvidia.com](https://build.nvidia.com/))

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/llm_chat_app.git
   cd llm_chat_app
   ```

2. **Create and activate a virtual environment (Optional but recommended):**  

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```
3. **Install dependencies:**

   ```bash
   pip install PySide6 openai markdown
   ```

### Usage

1. Run the application:
   ```bash
   python main.py
   ```
2. On first launch, a **Login** popup will appear. Paste your NVIDIA API key (must start with `nvapi-`).
3. Next, a **Model Selection** popup will appear. Select a model (e.g., Llama 3.3 70B).
4. Start chatting! Press `Enter` to send, or click the Send button.
5. While generating, the Send button turns into a red **Stop** button to halt generation.

## 📁 Project Structure

```text
llm_chat_app/
│
├── main.py                 # Entry point, initializes PySide6 App
│
├── resources/              # Static assets
│   ├── models.json         # List of available NVIDIA models
│   └── styles.qss          # Global dark theme stylesheet
│
├── ui_designer/            # Qt Designer .ui files
│   ├── main_window.ui      # Main chat interface layout
│   ├── model_popup.ui      # Model selection dialog layout
│   └── settings_dialog.ui  # API Key login dialog layout
│
├── ui/                     # Python UI logic (loads .ui files)
│   ├── main_window.py      # Main window class, chat handling, streaming logic
│   ├── login_dialog.py     # Settings/Login dialog logic
│   └── model_popup.py      # Model selection table logic
│
├── logic/                  # Backend business logic
│   ├── llm_client.py       # OpenAI client wrapper for NVIDIA API
│   ├── chat_worker.py      # QThread for non-blocking API streaming
│   └── conversation_manager.py # Save/Load JSON conversations
│
└── utils/                  # Miscellaneous helpers
    ├── constants.py        # App version, default URLs, timeouts
    └── helpers.py          # Timestamp formatters, text truncators
```

## ⚙️ Configuration & Data Storage

This application does not use local `.env` files or plaintext config files for sensitive data.

- **API Keys & Settings:** Stored securely using `QSettings`.
  - *Windows:* Saved in the Registry (`HKEY_CURRENT_USER\Software\LLMChatApp\Settings`).
  - *macOS:* Saved in `~/Library/Preferences/com.LLMChatApp.Settings.plist`.
  - *Linux:* Saved in `~/.config/LLMChatApp/Settings.conf`.
- **Chat Histories:** Saved as standard `.json` files in `~/LLMChatApp/conversations/`.

## ⌨️ Keyboard Shortcuts

- `Enter` - Send message
- `Stop` (while generating) - Click the red button to halt generation
- `F11` - Toggle true Fullscreen
- `Escape` - Exit true Fullscreen

## 🛠️ Tech Stack

- **GUI:** PySide6 (Qt for Python)
- **API Client:** OpenAI Python SDK (pointed to NVIDIA base URL)
- **Parsing:** Markdown (Python-Markdown)

## 📝 License

This project is licensed under the MIT License.


