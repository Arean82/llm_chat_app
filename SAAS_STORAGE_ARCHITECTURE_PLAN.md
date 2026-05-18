# Isolated Multi-Tenant SaaS Portal Architecture Plan

This architecture plan governs the design and deployment of the high-concurrency, multi-user SaaS portal served from the headless API Server (Port 5000). It establishes a strict **Virtual Sandbox** model ensuring absolute data, configuration, and session privacy for registered users.

---

## 🛡️ The Isolated "Virtual Sandbox" Model
Every registered user operates inside an isolated sandbox, acting exactly as if they booted a completely private virtual desktop application instance all to themselves.

```mermaid
graph TD
    UserA["User A (Web Portal)"] -->|JWT: user_a| Gateway["API Server Gateway (Port 5000)"]
    UserB["User B (Web Portal)"] -->|JWT: user_b| Gateway
    
    Gateway -->|Verify Claims| Router{"Dynamic Routing Layer"}
    
    Router -->|Session: user_a| DriverA["PostgreSQLStorageDriver / LibSQLStorageDriver"]
    Router -->|Session: user_b| DriverB["PostgreSQLStorageDriver / LibSQLStorageDriver"]
    
    DriverA -->|Isolate Schema| DbA[("User A Database (Schema: user_a)")]
    DriverB -->|Isolate Schema| DbB[("User B Database (Schema: user_b)")]
    
    style DbA fill:#059669,stroke:#047857,stroke-width:2px,color:#fff
    style DbB fill:#0284c7,stroke:#0369a1,stroke-width:2px,color:#fff
    style Gateway fill:#4f46e5,stroke:#4338ca,stroke-width:2px,color:#fff
```

---

## 1. Multi-Tier Isolation Schema

### 🗄️ 1. Database-Level Isolation
* **Dynamic Tenant Sharding**: Storage connections are established using the abstract `BaseStorageDriver` implementing dynamic `{tenant_id}` path expansion.
* **libSQL/Turso**: Dynamically creates or routes to isolated database instances/directories for each tenant (e.g. `libsql://user_a-database.turso.io`).
* **PostgreSQL**: Routes connections to isolated database names or private schemas (e.g. `postgresql://user:pass@host:5432/user_a`).
* **Absolute Privacy**: Cross-tenant data reads or writes are blocked at the infrastructure level.

### 🔑 2. Settings & Credentials Isolation (BYOK)
* **Dedicated Settings Namespaces**: The settings loader isolates config files per active `tenant_id` namespace.
* **Isolated Provider Keys**: User A and User B manage their own Secure Provider API Keys (e.g. private Anthropic, OpenAI, or Gemini keys) independently.
* **Headless Hydration**: The LLM Client dynamically loads the provider keys belonging strictly to the active authenticated tenant session at runtime.

### 🎫 3. Session-Level Security (JWT Middleware)
* **Cryptographic Tokens**: Successful registration or authentication issues a signed JSON Web Token (JWT) encapsulating the user's `tenant_id` claim.
* **Claims Extraction**: The API Server middleware intercepts incoming requests, validates signature integrity, extracts the `tenant_id`, and binds it to the storage driver transaction pipeline.

---

## 2. SaaS Web Portal Asset Structure
The portal is served headlessly by the API Server as a stunning, zero-framework web app:

| Component | Technology | Visual & Functional Purpose |
| :--- | :--- | :--- |
| **Styling** | Vanilla CSS (HSL dark mode) | Modern dark charcoal charcoal backdrops, transparent glassmorphism panels, harmonious emerald/indigo accents, and responsive layout wrappers. |
| **Logic** | Asynchronous JS (Fetch API) | Executes dynamic API bridging to save configurations, fetch chats, and report database health dynamically without browser page reloads. |
| **Structure** | Semantic HTML5 | Structured grid dashboards containing the login gate, the BYOK key configurators, and real-time database connection telemetry cards. |

---

## 3. High-Concurrency Multi-Client Safety
* **Lock-Free Concurrency**: With SQLite completely bypassed, both Turso and PostgreSQL leverage Multiversion Concurrency Control (MVCC) to support parallel requests across CLI, GUI, and SaaS Portal interfaces.
* **Zero Shared State Leakage**: Every incoming connection thread acts on a stateless session instantiated per JWT claim, keeping memory footprints highly isolated and secure.
