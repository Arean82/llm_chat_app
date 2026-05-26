# SaaS Security Protocol

This document outlines the strict security boundaries implemented within the SaaS architecture.

## 1. Zero-Trust API Passport Validation
Every single inbound API request must provide an `Authorization: Bearer <Passport>` header. 
- Passports are mapped to active users in `tenant_db.py`.
- If a user is kicked or banned via the Operator Dashboard, their Passport instantly invalidates and blocks all generation capabilities.

## 2. BYOK Encryption Vault
Tenants are encouraged to provide their own OpenAI/DeepSeek keys (BYOK).
- Keys are never stored in plaintext. They are passed through `TenantDatabaseManager.encrypt_byok()` before hitting the SQLite ledger.
- When generating a response, the `LLMClient` dynamically retrieves the key, decrypts it in-memory, executes the generation, and flushes the key from memory.

## 3. Physical Storage Partitioning
Unlike many multi-tenant architectures that use a shared vector database, this engine enforces physical disk isolation to guarantee zero data bleeding:
- **Tenant A's** embeddings go to `/vector_db/collections/user_1/`.
- **Tenant B's** embeddings go to `/vector_db/collections/user_2/`.
- Cross-contamination during RAG searches is physically impossible at the filesystem level.

## 4. WAL Database Concurrency Protection
The core SaaS ledger operates in `WAL` (Write-Ahead Logging) mode (`PRAGMA journal_mode=WAL`).
This ensures that high volumes of inbound parallel requests (e.g., token consumption logging, profile updates) will never corrupt the database or trigger traditional SQLite locking failures.
