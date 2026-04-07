
# LLM Chat App

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)  ![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-green)  ![License](https://img.shields.io/badge/License-MIT-yellow)

A sleek, dark-themed desktop chat application built with Python and PySide6. It interfaces with the NVIDIA NIM API (via the OpenAI SDK) to provide streaming LLM responses, markdown rendering, and conversation management.

[Features](#-features) • [Getting Started](#-getting-started) • [Usage](#-usage) • [Project Structure](#-project-structure) • [Tech Stack](#-tech-stack) •[-Configuration-&-Data-Storage](#-configuration-&-data-storage) • [Keyboard Shortcuts](#-keyboard-shortcuts) •[-Contributing](#-contributing) •[-Disclaimer](#-disclaimer) •[License](#-license)


---

## ✨ Features

- 🚀 **Real-Time Streaming:** Watch the AI generate responses token by token, with zero lag.
- 📊 **Live Performance Metrics:** Track AI speed with real-time stats (Time to First Token, Tokens/sec, and token usage) displayed beautifully after every response.
- 📎 **File Attachments:** Upload your code (`.py`, `.js`), text, or data files directly into the chat for instant AI analysis.
- 🔄 **Multi-Model Support:** Easily switch between powerful models like Llama 3, DeepSeek, Qwen, and Gemma via a clean UI popup.
- 🧠 **Reasoning Support:** Automatically detects and beautifully formats model "thinking/reasoning" tokens.
- 🎨 **Rich Markdown Rendering:** Stunning display of code blocks with syntax highlighting, tables, and bold formatting.
- 💾 **Conversation Manager:** Save your chat histories as JSON files and load them up anytime.
- 🚅 **Smart Offline Caching:** Local asset caching ensures instant UI loading, even on the very first run.
- 🔐 **Secure State Memory:** Remembers your API keys and selected models securely in your OS backend (no plain-text config files!).
- 🖥️ **Distraction-Free UI:** Forced maximized, clean light/dark interface so you can focus purely on your prompt.

---
## 🚀 Getting Started

### Prerequisites
- Python 3.8 or higher
- An NVIDIA NIM API Key (Get one free at [build.nvidia.com](https://build.nvidia.com/))

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Arean82/llm_chat_app.git
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

---

## 💡 Usage

1. Run the application:
   ```bash
   python main.py
   ```
2. 📸 **First Launch:** A secure login popup will prompt you for your NVIDIA API key (`nvapi-...`).
3. 🤖 **Select Model:** A popup will let you choose your desired AI model.
4. 💬 **Start Chatting:** Type your message and press `Enter`.
5. 📎 **Upload Files:** Click the attachment button to upload code/text for the AI to review.
6. ⏹️ **Stop Generation:** Click the red "Stop" button at any time to halt the response.

---

## 📁 Project Structure

```text
llm_chat_app/
│
├── main.py                 # 🚀 Entry point
├── resources/              # 📦 Static assets & caches
│   ├── models.json         # 🤖 Available model list
│   ├── styles.qss          # 🎨 Global stylesheet
│   └── badge_cache/        # ⚡ Auto-generated offline image cache
│
├── ui_designer/            # 🎨 Qt Designer UI files
│   ├── main_window.ui      
│   ├── model_popup.ui      
│   └── settings_dialog.ui  
│
├── ui/                     # 🧩 Python UI logic
│   ├── main_window.py      # Main app controller
│   ├── login_dialog.py     # API Key auth
│   ├── model_popup.py      # Model selector
│   └── file_viewer.py      # Readme/License viewer
│
├── logic/                  # ⚙️ Backend engine
│   ├── llm_client.py       # NVIDIA API wrapper
│   ├── chat_worker.py      # Threading for streaming
│   └── conversation_manager.py 
│
└── utils/                  # 🛠️ Helpers
    ├── constants.py        
    └── helpers.py          
```

---

## 🧱 Tech Stack

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)       ![Qt](https://img.shields.io/badge/PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=black)       ![OpenAI](https://img.shields.io/badge/OpenAI_SDK-412991?style=for-the-badge&logo=openai&logoColor=white)       ![NVIDIA](https://img.shields.io/badge/NVIDIA_NIM-76B900?style=for-the-badge&logo=nvidia&logoColor=white)       ![Markdown](https://img.shields.io/badge/markdown-%23000000.svg?style=for-the-badge&logo=markdown&logoColor=white)

---

## ⚙️ Configuration & Data Storage

This application does not use local `.env` files or plaintext config files for sensitive data.

- **API Keys & Settings:** Stored securely using `QSettings`.
  - *Windows:* Saved in the Registry (`HKEY_CURRENT_USER\Software\LLMChatApp\Settings`).
  - *macOS:* Saved in `~/Library/Preferences/com.LLMChatApp.Settings.plist`.
  - *Linux:* Saved in `~/.config/LLMChatApp/Settings.conf`.
- **Chat Histories:** Saved as standard `.json` files in `~/LLMChatApp/conversations/`.

---

## ⌨️ Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| `Enter` | Send message |
| `Stop` | Halt AI generation |
| `F11` | Toggle true Fullscreen |
| `Esc` | Exit true Fullscreen |

---

## 🤝 Contributing

Contributions, issues, and feature requests are highly welcome! Whether it's fixing a bug, improving the UI, or adding support for a new API, your help is appreciated.

To contribute:

1. **Fork** the Project
2. Create your **Feature Branch** (`git checkout -b feature/AmazingFeature`)
3. **Commit** your Changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the Branch (`git push origin feature/AmazingFeature`)
5. Open a **Pull Request**

**Guidelines:**
- Please follow standard Python [PEP 8](https://peps.python.org/pep-0008/) conventions.
- Keep the UI consistent with the current light/dark theme logic.
- If adding new API endpoints, ensure they are handled safely in the `logic/` folder without blocking the main UI thread.

---

## ⚠️ Disclaimer

This software is provided as-is, free of charge, for educational and personal use purposes. 

- **AI Accuracy:** This application interfaces with third-party Large Language Models (LLMs). The developers of this application do not control, endorse, or guarantee the accuracy, completeness, or appropriateness of the AI-generated responses. AI models can produce incorrect, biased, or offensive content.
- **User Responsibility:** You are solely responsible for any prompts you submit and any outputs you rely on. Always verify critical information generated by AI.
- **API Usage:** This app relies on the NVIDIA NIM API. You are responsible for managing your own API keys, adhering to NVIDIA's Terms of Service, and monitoring your own API usage limits and quotas.
- **No Liability:** The maintainers of this repository shall not be held liable for any damages, data loss, or issues arising from the use of this software.

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.




