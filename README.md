
# LLM Chat App

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)  ![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-green)  ![License](https://img.shields.io/badge/License-MIT-yellow)

A sleek, dark-themed desktop chat application built with Python and PySide6. It interfaces with the NVIDIA NIM API (via the OpenAI SDK) to provide streaming LLM responses, markdown rendering, and conversation management.

[Features](#-features) • [User Interface Highlights](#-user-interface-highlights) • [Getting Started](#-getting-started) • [Usage](#-usage) • [Project Structure](#-project-structure) • [Tech Stack](#-tech-stack) •[-Configuration-&-Data-Storage](#-configuration-&-data-storage) • [Log System](#-log-system) • [Keyboard Shortcuts](#-keyboard-shortcuts) •[-Contributing](#-contributing) •[-Disclaimer](#-disclaimer) •[-Building-from-Source-(Developer-Guide)](#-building-from-source-developer-guide) •[License](#-license)

---

## ✨ Features

- 🚀 **Real-Time Streaming:** Watch the AI generate responses token by token, with zero lag.
- 📊 **Live Performance Metrics:** Track AI speed with real-time stats (Time to First Token, Tokens/sec, and token usage) displayed beautifully after every response.
- 📎 **File Attachments:** Upload your code (`.py`, `.js`), text, or data files directly into the chat for instant AI analysis.
- 🔄 **Multi-Model Support:** Easily switch between powerful models like Llama 3, DeepSeek, Qwen, and Gemma via a clean UI popup.
- 📦 **Model Manager:** Add, edit, or remove models directly from the UI. Changes save instantly to `models.json` — no manual file editing needed.
- 🏷️ **System Instruction Library:** Manage custom AI personas and rules. Create instruction sets (e.g., 'Python Expert', 'Friendly Tutor') and toggle them on/off via the Settings menu.
- 🧠 **Reasoning Support:** Automatically detects and beautifully formats model "thinking/reasoning" tokens.
- 🎨 **Rich Markdown Rendering:** Stunning display of code blocks with syntax highlighting, tables, and bold formatting.
- 💾 **Smart Conversation Management:** Save and load chat histories as JSON files. It automatically saves and restores the exact model used for the session.
- 🚅 **Smart Offline Caching:** Local asset caching ensures instant UI loading, even on the very first run.
- 🔐 **Secure State Memory:** Remembers your API keys and selected models securely in your OS backend (no plain-text config files!).
- 🖥️ **Distraction-Free UI:** Forced maximized, clean light/dark interface so you can focus purely on your prompt.
- 🌓 **Adaptive Theming** – Instantly switch between Dark and Light modes.
- 📌 **Persistent Settings** – API keys, models, and theme preferences survive app restarts.
- 🌐 **Live Connection Status** – Real-time network monitoring with visual indicators (🌐/🔴); automatically recovers from silent disconnects, safely cleans up broken chat history, and instantly unlocks the UI.
- 🛡️ **Intelligent Error Handling:** Categorizes API errors (timeouts, network drops, rate limits) and shows friendly, actionable messages instead of raw error traces.
- 🧠 **Smart Context Buffering:** Proactively monitors chat length against model-specific context windows, warning you before the AI runs out of space to reply.
- 🔄 **Background Model Fetching:** Fetch and test all available NVIDIA models in the background. Model Manager closes automatically, progress visible in real-time via the Log menu.
- 📋 **Real-time Log Viewer:** Track model fetching progress, success/failures, and description generation with color-coded, filterable logs (INFO, WARNING, ERROR, SUCCESS, DEBUG).
- ✨ **AI-Powered Description Generation:** Generate one-sentence descriptions for any model using your choice of working model (Llama 4, Gemma 3, etc.). Descriptions persist across app restarts.
- 🏷️ **Developer Tabs:** Models are automatically grouped by developer (Google, Meta, NVIDIA, etc.) in the Model Manager for easier browsing.
- 💰 **Paid Model Support:** Fetch paid models (requires subscription) and merge them with existing free models without losing data.

---

## 🎨 User Interface Highlights

- 🌙 / ☀️ **Theme Toggle**: Click the icon in the top bar to switch themes instantly.
- 🏷️ **Model Info Label**: A subtle italic label next to the dropdown populates with the model description so you know its capabilities at a glance.
- 📋 **Log Menu:** View real-time update logs with filtering by log level. Clear logs when needed.
- ✨ **Generate Descriptions Button:** In Model Manager, select any working model to automatically generate descriptions for all models missing them.
- 📝 **System Instructions:** Access the Instruction Library via Settings to create, edit, and toggle system prompts.

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
4. 💬 **Start Chatting:** Type your message. Press `Enter` to send, or `Shift+Enter` for a new line.
5. 📎 **Upload Files:** Click the attachment button to upload code/text for the AI to review.
6. ⏹️ **Stop Generation:** Click the red "Stop" button at any time to halt the response.

---

## 📁 Project Structure

```text
llm_chat_app/
│
├── main.py                         # 🚀 Entry point
├── main_onedir.spec                # PyInstaller spec - One-dir build
├── main_onefile.spec               # PyInstaller spec - One-file build
├── main_combined.spec              # PyInstaller spec - Both builds
├── resources/                      # 📦 Static assets & caches
│   ├── models.json                 # 🤖 Available model list
│   ├── styles.qss                  # 🎨 Global stylesheet
│   └── badge_cache/                # ⚡ Auto-generated offline image cache
│        
├── ui_designer/                    # 🎨 Qt Designer UI files
│   ├── login_dialog.ui      
│   ├── main_window.ui  
│   ├── model_edit_dialog.ui
│   ├── model_manager.ui    
|   ├── system_prompt_manager.ui 
│   └── model_popup.ui
│
├── ui/                             # 🧩 Python UI logic
│   ├── file_viewer.py              # Readme/License viewer
│   ├── login_dialog.py             # API Key authentication
│   ├── main_window.py              # Main app controller
│   ├── model_edit_dialog.py        # Model add/edit/delete manager
│   ├── model_manager.py            # Model add/edit/delete manager
│   ├── system_prompt_manager.py    # System Prompt Manager Logi
│   └── model_popup.py              # Model selector
│
├── logic/                          # ⚙️ Backend engine
│   ├── llm_client.py               # NVIDIA API wrapper
│   ├── chat_worker.py              # Threading for streaming
│   └── conversation_manager.py 
├── workers/                        # 🧵 Background workers
│   ├── chat_worker.py              # Streaming responses
│   ├── model_fetch_worker.py       # Fetch & test models
│   ├── paid_model_fetch_worker.py  # Paid model support
│   ├── description_generator.py    # AI description generation
│   └── update_logger.py            # Real-time logging
│
└── utils/                          # 🛠️ Helpers
    ├── constants.py                
    ├── helpers.py                  
    ├── model_config.py             # 🧠 Model context limits
    └── path_utils.py               # 📁 PyInstaller & dev path resolver
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

## 📋 Log System

The application features a comprehensive logging system for background operations:

- **Real-time Updates:** All fetch and generation progress appears instantly in the Log Viewer
- **Color-coded Levels:** INFO (green), SUCCESS (blue), WARNING (yellow), ERROR (red), DEBUG (purple)
- **Filterable:** Toggle specific log levels on/off
- **Persistent Storage:** Logs saved to `resources/update_log.txt` and survive app restarts
- **Background Operations:** Model fetching and description generation run without blocking the UI

---

## ⌨️ Keyboard Shortcuts

| **Key** | **Action** |
| :--- | :--- |
| `Enter` | Send message |
| `Shift + Enter` | Insert new line |
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

## 🔨 Building from Source (Developer Guide)

If you want to build the distributable installers yourself, follow the OS-specific steps below. 

*Note: You must build on the target OS (Windows builds for Windows, Mac builds for Mac, Linux builds for Linux).*

### Prerequisites
1. Install the app dependencies: `pip install PySide6 openai markdown`
2. Install PyInstaller: `pip install pyinstaller`
3. Install Pillow for icon generation: `pip install Pillow`
4. Generate the required OS icon files from your source `resources/app_icon.png`:
   ```bash
   python -c "from PIL import Image; img = Image.open('resources/app_icon.png'); img.save('resources/app_icon.ico', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]); img.resize((256, 256)).save('resources/app_icon_linux.png'); print('Icons generated!')"
   ```
   *(Note: To generate the `.icns` for macOS, you must run `iconutil` on a Mac).*

### Step 1: Build the Executable (All OS)
Run this from the project root. The project includes three spec files for different build types:

```bash
# One-dir build (folder with exe + dependencies)
pyinstaller main_onedir.spec

# One-file build (single executable)
pyinstaller main_onefile.spec

# Combined build (creates both One-file and One-dir)
pyinstaller main_combined.spec
```

**Build outputs:**
- One-dir: `dist/LLM Chat App/` (folder containing the executable and all dependencies)
- One-file: `dist/LLM Chat App.exe` (single executable file)
- Combined: Both outputs are generated simultaneously

**Test the executable** before proceeding to package it!

### Step 2: Create the OS Installer

#### 🪟 Windows (Inno Setup)
1. Download and install [Inno Setup](https://jrsoftware.org/isdl.php).
2. Open the provided `installer_script.iss` file in Inno Setup.
3. Go to **Build > Compile** (or press `Ctrl+F9`).
4. *Output:* `installer_output/LLM_Chat_App_Setup_v3.0.0.exe`

#### 🐧 Linux (AppImage)
Linux does not use "installers" in the traditional sense. Instead, we package the app as a portable AppImage.
```bash
# Install AppImage dependencies (Ubuntu/Debian)
sudo apt install libfuse2

# Create the AppDir structure
mkdir -p LLMChatApp.AppDir/usr/bin
mkdir -p LLMChatApp.AppDir/usr/share/icons/hicolor/256x256/apps
cp -r "dist/LLM Chat App/"* LLMChatApp.AppDir/usr/bin/

# Create the Linux desktop shortcut
cat << 'EOF' > LLMChatApp.AppDir/LLMChatApp.desktop
[Desktop Entry]
Name=LLM Chat App
Exec=AppRun
Icon=app_icon
Type=Application
Categories=Utility;
EOF

# Add the icon
cp resources/app_icon_linux.png LLMChatApp.AppDir/usr/share/icons/hicolor/256x256/apps/app_icon.png
ln -s LLMChatApp.AppDir/usr/share/icons/hicolor/256x256/apps/app_icon.png LLMChatApp.AppDir/app_icon.png

# Download appimagetool and build the AppImage
wget -O appimagetool https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool
./appimagetool LLMChatApp.AppDir/
```
*Output: `LLMChatApp-x86_64.AppImage` (To "uninstall", the user simply deletes this file).*

#### 🍎 macOS (DMG)
Because our `main.spec` auto-detects Windows icons, we explicitly pass the Mac icon via command line:
```bash
pyinstaller --onedir --windowed \
    --name "LLM Chat App" \
    --icon "resources/app_icon.icns" \
    --add-data "resources:resources" \
    --add-data "ui_designer:ui_designer" \
    --hidden-import markdown --hidden-import openai --hidden-import certifi --hidden-import urllib3 \
    --exclude-module PyQt5 --exclude-module PyQt6 --exclude-module tkinter \
    main.py

# Package into a DMG
hdiutil create -volname "LLM Chat App" -srcfolder "dist/LLM Chat App.app" -ov -format UDZO "LLM_Chat_App_Mac.dmg"
```
*Output: `LLM_Chat_App_Mac.dmg`*

### 📂 How User Data is Handled
To prevent permission errors (especially on Windows `Program Files`), the compiled app **separates read-only app files from writable user data**:
- **Read-Only (Internal):** UI files and stylesheets are loaded from the `_internal` folder.
- **Writable (User Data):** Custom models (`models.json`) and cached images are saved to the OS's secure user data directory:
  - *Windows:* `C:\Users\<User>\AppData\Roaming\LLMChatApp\`
  - *macOS:* `~/Library/Application Support/LLMChatApp/`
  - *Linux:* `~/.local/share/LLMChatApp/`

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.




