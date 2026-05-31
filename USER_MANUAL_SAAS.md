# ☁️ Synora Studio - SaaS Multi-Tenant Guide

Welcome to the **Synora Studio SaaS Multi-Tenant Gateway**. This platform allows organizations to centrally host and orchestrate LLM inference across hundreds of concurrent users, offering enterprise-grade telemetry, isolated sandboxes, and hybrid authentication models.

---

## 1. Getting Started & Authentication

### Platform Architecture
The SaaS platform operates on a dual-tier trust model:
1. **Admin Vault:** Administrators log in using a central "master" key. All inference costs are subsidized by the central admin's budget.
2. **BYOK Tier (Bring Your Own Key):** Guest users or developers can connect and log in by providing their own personal API Keys, entirely offloading cost to the tenant.

### Accessing the Portal
1. Navigate to your organization's SaaS portal URL (default: `http://localhost:8000`).
2. **Key-Passport Validation:** 
   - Select your Inference Provider.
   - Enter your secure API Key.
   - The platform will execute a Pre-Flight validation handshake to ensure your credentials are valid.
3. Once validated, set your localized Display Name and Email to provision your secure workspace!

---

## 2. Navigating the SaaS Dashboard

The SaaS interface utilizes a stunning glassmorphic design that intelligently adapts to Light and Dark modes.

### Your Workspace
- **Physical Sandboxed Streams:** All conversations are physically isolated. When you launch a new stream, a dedicated orchestration sandbox is assigned to you.
- **Model Deployment Selector:** Swap between active models using the dropdown in the header. Only models natively supported by your authenticated ecosystem will appear here.
- **Telemetry Engine:** Watch real-time execution statistics directly in your header, showing your active status and exact Token counts.

### Chat Interface
- Type prompts in the dynamic input canvas at the bottom of the screen.
- Enjoy full Markdown rendering, code execution visualizations, and error-handling alerts cleanly inside the web UI.

---

## 3. Administrative Controls (Node Config)

If you are authenticated as an **Admin Vault** user, you gain access to the secure **Node Config** terminal. Click the Settings icon in the sidebar to access these modules:

### Telemetry & System Health
- **Live Worker Metrics:** View concurrent background threads and HTTP transaction success rates.
- **Latency & Throughput:** Monitor the literal speed of your AI endpoints in RPM (Requests Per Minute) and milliseconds.
- **Dead Letter Queue (DLQ):** Analyze dropped, corrupted, or rate-limited requests that failed to reach the LLM provider.

### Model Parameters & Instructions
- **System Instructions:** Broadcast global behavioral rules to all users utilizing the Admin Vault.
- **Generation Parameters:** Force ceiling limits on Output Tokens and Temperature to strictly manage costs across the organization.

### 🔌 Local API Control
Want to expose your local desktop configuration to external automated scripts, or use it as a middle-tier for other software?
1. Navigate to the **Local API Control** tab.
2. **Disable/Enable:** Instantly toggle the active connection state of your local desktop port (5000).
3. **Regenerate Key:** Instantly destroy the old key and mint a secure new token. *Warning: This forces a hard server restart and severs all active connections.*

---

## 4. Tenant Management

Administrators can physically view the load their platform is experiencing:
- Go to the **Tenants** tab inside the Node Config.
- View a live roster of all active users, their authentication tier (Admin vs BYOK), and their connection stability.
- Quickly identify "freeloaders" or troubleshoot connectivity issues for your BYOK developers.
