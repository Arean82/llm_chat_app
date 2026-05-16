# Working Plan: Attaining v7.0 (Master Progress Log)

This is the tactical manual for evolving the **fixed v6.5 foundation** into the v7.0 Headless/SaaS architecture.

---

## 🟢 Phase 1: The Headless Engine

### 1.1 UI-Neutral Logic (Decoupling)
| # | Task | Status |
| :--- | :--- | :--- |
| **1.1.1** | **Storage Isolation**: Replace `QSettings` with native `JSONSettings` | ✅ **DONE** |
| **1.1.2** | **Worker Decoupling**: Refactor workers to use universal callbacks | ✅ **DONE** |
| **1.1.3** | **Utility Purge**: Move GUI helpers out of the `utils/` directory | ✅ **DONE** |

**Technical Notes (1.1):**
*   **Storage**: Created `utils/config_loader.py` implementing `JSONSettings`. This allows the engine to resolve its Data Root and read/write configurations without needing a `QApplication` instance.
*   **Inference**: Refactored `ChatWorker` from `QThread` to `threading.Thread`. Replaced Qt `Signals` with a **Universal Callback Pattern** (`on_chunk`, `on_response`). This allows the same logic to drive a GUI, a CLI, or an API.
*   **Dependency Cleanup**: Relocated `set_app_icon` to `ui/shared_widgets.py`. Verified that all `logic/` and `utils/` files are free of `PySide6` imports.

---

### 1.2 Headless Execution (Intelligence)
| # | Task | Status |
| :--- | :--- | :--- |
| **1.2.1** | **Intelligent Env Detection**: Inject `detect_environment` in `main.py` | ✅ **DONE** |
| **1.2.2** | **Standalone API Logic**: Implement Conditional UI logic for API stability | 🔵 **NO CHANGE NEEDED** |
| **1.2.3** | **Headless Startup Path**: Enable starting server without `MainWindow` | ✅ **DONE** |

**Technical Notes (1.2):**
*   **Intelligence**: `main.py` now detects `DISPLAY` (Linux) or `--headless` flags to determine mode.
*   **Conditional UI (User Recommendation)**: Formally adopted the strategy of wrapping UI-specific logic in environment checks. `api_server.py` was audited and found clean; any future UI features (like tray icons) will be gated by `detect_environment() == "GUI"`.
*   **Isolation**: Created `logic/headless_engine.py` to house the background request handler. Cleaned `main.py` by moving GUI-specific imports (`MainWindowClass`) inside conditional blocks to prevent crashes on systems without Qt.

---

### 1.3 CLI Mode (Direct Interaction)
| # | Task | Status |
| :--- | :--- | :--- |
| **1.3.1** | **CLI Implementation**: Integrate interactive terminal chat into `main.py` | ⏳ PENDING |

**Technical Notes (1.3):**
*   **Logic**: Instead of a separate file, `main.py` will handle a `--cli` flag. This will launch a direct, interactive terminal session using the core engine, allowing for zero-lag chat without a GUI or API server.

---

## 🔵 Phase 2: The SaaS Platform

### 2.1 Multi-Tenancy (Data Isolation)
| # | Task | Status |
| :--- | :--- | :--- |
| **2.1.1** | **Multi-Tenant SQL Schema**: Add indexed `user_id` columns | ⏳ PENDING |
| **2.1.2** | **Multi-Tenant CRUD Logic**: Update queries with `WHERE user_id = ?` | ⏳ PENDING |

### 2.2 Enterprise Security (Auth)
| # | Task | Status |
| :--- | :--- | :--- |
| **2.2.1** | **JWT Middleware**: Integrate token validation in API server | ⏳ PENDING |
| **2.2.2** | **User Mapping**: Map JWT identity to database `user_id` | ⏳ PENDING |

---

> [!IMPORTANT]
> **Audit Note**: **3 Hours 25 Minutes** of session time wasted due to AI speculation and overstepping. This record is kept to ensure strict adherence to step-by-step instructions moving forward.

*Next Action: Awaiting instruction for Step 1.3.1.*
