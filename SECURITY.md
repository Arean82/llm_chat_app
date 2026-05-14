# 🛡️ Security & Privacy Policy

**LLM Chat App** is built from the ground up around absolute user data privacy and localized operational integrity. As a workstation tool for AI interaction, it adopts strict, zero-compromise security principles.

---

## 🔐 1. OS-Level Credential Custody (No Plaintext)

* **Zero Plaintext Storage:** The application does not store your third-party API keys (NVIDIA, Google, OpenAI, Groq, etc.) in plain text, log files, or local JSON manifests.
* **Native Subsystem Encryption & Isolation:** All authentication tokens are partitioned and injected into your operating system's cryptographic vault using the standard Python `keyring` bridge:
  * **Credential Isolation:** Keys are stored using a unique `api_key_[sdk]_[ecosystem]` signature, ensuring that credentials for different providers (e.g., Groq vs OpenAI) are strictly isolated and never collide or leak across provider pipelines.
  * **Windows:** Windows Credential Manager (Safe Storage API)
  * **macOS:** Apple Keychain (SecKeychain Services)
  * **Linux:** Freedesktop Secret Service (via dbus/gnome-keyring)
* **Comprehensive Wiping:** Activating the "Logout" action triggers an immediate, hardware-flushed purge of the active ecosystem's security slots, ensuring zero trace remnants.

---

## 🧬 2. Local-First Data & Hybrid RAG Boundaries

* **Offline Vector Space:** The Retrieval-Augmented Generation (RAG) engine performs all dense vector encoding, parsing, and indexing strictly on your local hardware.
* **Native Vector Matrices:** We leverage specialized **NumPy** algebra and **Qdrant Vector Database** instances pinned strictly to your verified local filesystem. No document data, PDF snippets, or corporate CSV spreadsheets are ever transmitted to external cloud RAG services.
* **Isolated SQLite Backend:** Chat logs, caches, and histories are stored in a transactional, zero-network SQLite database operating in Write-Ahead Logging (WAL) mode.

---

## 🛠️ 3. Isolated Execution Sandbox Isolation

* **Decoupled Runtime Process:** The "Run Prototype" engine converts LLM generated code into functioning GUI layouts.
* **OS Fork Injection:** To prevent memory corruption or thread locking, each sandbox session spawns an isolated, external host `QProcess` thread entirely independent of the main user interface event loop.
* **Manual Triggering:** Code execution is strictly user-initiated via physical mouse interaction on generated anchor tags; arbitrary code block rendering never triggers passive execution.

---

## 🌐 4. Local-Only Gateway Constraints (Universal API Server)

* **Local Host Locking:** The integrated Flask gateway binds strictly to the `127.0.0.1` loopback interface (localhost). It is structurally incapable of accepting requests over the public internet or local LAN.
* **Mandatory Auth Key Header:** All incoming IDE extension connections are validated against a persistent, randomized local secret token. Non-authenticating ingresses are rejected instantly with `401 Unauthorized`.

---

## 📡 5. Ecosystem Transport Security

* **Encrypted Piping:** All communication streams to remote AI providers (Google Vertex, OpenAI API, NVIDIA NIM) utilize mandatory **HTTPS TLS 1.3** pipelines.
* **Local Overrides:** For highly sensitive offline operations, the app seamlessly enables zero-key workflows targeting locally-hosted offline engines (e.g., Ollama, LM Studio) which operate 100% disconnected from the external internet.
