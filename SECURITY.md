# 🛡️ Security & Privacy Policy

**Synora Studio** is built from the ground up around absolute user data privacy and localized operational integrity. As a workstation tool for AI interaction, it adopts strict, zero-compromise security principles.

---

## 🔐 1. OS-Level Credential Custody (No Plaintext)

* **Zero Plaintext Storage:** The application does not store your third-party API keys (NVIDIA, Google, OpenAI, Groq, etc.) in plain text, log files, or local JSON manifests.
* **Native Subsystem Encryption & Isolation:** All authentication tokens are partitioned and injected into your operating system's cryptographic vault using the standard Python `keyring` bridge:
  * **Credential Isolation:** Keys are stored using a unique `api_key_[sdk]_[ecosystem]` signature, ensuring that credentials for different providers (e.g., Groq vs OpenAI) are strictly isolated and never collide or leak across provider pipelines.
  * **Windows:** Windows Credential Manager (Safe Storage API)
  * **macOS:** Apple Keychain (SecKeychain Services)
  * **Linux:** Freedesktop Secret Service (via dbus/gnome-keyring)
* **Comprehensive Wiping:** Activating the "Logout" action triggers an immediate, hardware-flushed purge of the active ecosystem's security slots, ensuring zero trace remnants.
* **Universal Credential-Aware Visibility Gate:** To protect against accidental exposure of endpoints and models for providers that do not have authenticated credentials on the current system, the model manager and selection popups implement a credential-aware visibility filter. Models are only visible and loadable if a valid cryptographic vault API key matches their provider signature, enforcing strict credential custody before catalog display.

---

## 🧬 2. Local-First Data & Hybrid RAG Boundaries

* **Offline Vector Space:** The Retrieval-Augmented Generation (RAG) engine performs all dense vector encoding, parsing, and indexing strictly on your local hardware.
* **Native Vector Matrices:** We leverage specialized **NumPy** algebra and **Qdrant Vector Database** instances pinned strictly to your verified local filesystem. No document data, PDF snippets, or corporate CSV spreadsheets are ever transmitted to external cloud RAG services. Furthermore, all local vectors use deterministic MD5 hashing to guarantee consistency across process restarts.
* **Isolated SQLite Backend:** Chat logs, caches, and histories are stored in a transactional, zero-network SQLite backend operating in Write-Ahead Logging (WAL) mode. RAG queries leverage Jaccard-similarity semantic caches for high-speed resolution.

---

## 🛠️ 3. Isolated Execution Sandbox Isolation

* **Decoupled Runtime Process:** The "Run Prototype" engine converts LLM generated code into functioning GUI layouts.
* **OS Fork Injection:** To prevent memory corruption or thread locking, each sandbox session spawns an isolated, external host `QProcess` thread entirely independent of the main user interface event loop.
* **Safe Thread Signaling:** All concurrent background workers (e.g., streaming ingestion, vector syncs) utilize safe `requestInterruption()` signaling rather than forceful OS-level termination, guaranteeing absolute C++ state and memory stability.
* **Manual Triggering:** Code execution is strictly user-initiated via physical mouse interaction on generated anchor tags; arbitrary code block rendering never triggers passive execution.

---

## 🌐 4. Dynamic API Gateway & IDE Extension Trust

* **Local API Hard Disables & Key Regeneration:** The local Universal API Server provides full credential lifecycle control via the UI. Disabling the local API physically unbinds Port 5000 and destroys the socket thread, completely sealing the network attack surface. Regenerating the key instantly drops any active unauthorized network connections by invoking a hard socket restart. All API credential actions require explicit user confirmation and are executed instantly, independent of any deferred "save" routines.
* **Local Host Locking:** The integrated Flask local gateway binds strictly to the `127.0.0.1` loopback interface (localhost). It is structurally incapable of accepting requests over the public internet or local LAN.
* **Mandatory Auth Key Header:** All incoming IDE extension connections are validated against dynamic, secure secret tokens. Non-authenticating ingresses are rejected instantly with `401 Unauthorized`.
* **OS-Level Secrets Vaulting (V2.0.0+ IDE Extensions):** The IDE extensions completely eliminate hardcoded developer token keys. Instead, they integrate with native host OS keychains (using `ExtensionContext.secrets` in VS Code and the `PasswordSafe` / `CredentialAttributes` API in JetBrains IntelliJ) to store dynamic tenant Bearer Passports securely encrypted at rest.
* **SaaS Multi-Tenant Isolation:** Dynamic gateway queries include user-specific tenant passports in the `Authorization: Bearer <token>` header. The SaaS server intercepts these calls to route prompt queries and RAG operations into isolated physical sandboxes, preventing semantic or history cross-contamination between remote accounts. Web portals employ ephemeral `sessionStorage` (instead of `localStorage`) to protect against persistent XSS credential theft.

---

## 📡 5. Ecosystem Transport Security

* **Encrypted Piping:** All communication streams to remote AI providers (Google Vertex, OpenAI API, NVIDIA NIM) utilize mandatory **HTTPS TLS 1.3** pipelines.
* **Local Overrides:** For highly sensitive offline operations, the app seamlessly enables zero-key workflows targeting locally-hosted offline engines (e.g., Ollama, LM Studio) which operate 100% disconnected from the external internet.

---

## 🖥️ 6. Headless & CLI Engine Security

* **CLI Credential Vaulting:** The headless engine utilizes the same high-security `keyring` architecture as the GUI. Credentials provided via the terminal are immediately vaulted into the OS security subsystem and never cached in plaintext history.
* **Cross-Interface Vault Schema Alignment:** Patched CLI credentials storage routines to save concurrently to modern hierarchical status slots (`api_key_{sdk}_{ecosystem}`) and legacy compatibility slots, preventing vault schema mismatch security lockouts and guaranteeing uniform security postures between CLI and GUI.
* **Strict Post-Logout Security Gate:** If no active session variable exists (the user logged out or explicitly ended the session), the client's `hydrate()` routine *strictly refuses* to pull orphaned keys from the OS Keyring. This prevents any silent extraction of leftover credentials from previous sessions.
* **Unified Dynamic JSON Registry Protection:** All ecosystem endpoints are loaded dynamically from the centralized registry (`resources/api_providers.json`), preventing hardcoded endpoint manipulation or unauthorized proxy injection, ensuring secure and predictable API routing.
* **Process Space Isolation:** Running in `--headless` mode spawns a dedicated orchestrator process with restricted access to non-essential UI resources, minimizing the attack surface for server-side deployments.
* **Environment-Aware Auto-Detection:** Automatically identifies environment parameters (GUI display, SSH sessions, TTY states) to safely toggle interactive prompts vs daemonized background execution.
