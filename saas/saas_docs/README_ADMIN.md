# Operator & Administrator Guide

Welcome to the **SaaS Operator Guide**. This document explains how to bootstrap, manage, and monitor the Headless SaaS architecture.

## 1. Bootstrapping the SaaS Engine

The SaaS module is driven by Flask and nested securely inside a PySide6 QThread (in desktop mode) or as a standalone gunicorn/waitress worker in headless mode.

### Default Super Admin Credentials
When `tenant_db.py` is initialized for the first time on a fresh database (`data/saas_tenants.db`), it automatically provisions a secure super admin account.
- **Username**: `admin`
- **Email**: `admin@quantum-saas.local`
- **Password**: Auto-generated via `secrets.token_urlsafe(12)`. Printed to the console strictly *once* upon the very first initialization.

> [!WARNING]
> If you lose the admin password, you can run the reset script via the `TenantDatabaseManager.reset_admin_account()` hook to safely forcefully override it back to `admin`.

## 2. Multi-Tenancy Architecture

The system uses **SQLite in WAL (Write-Ahead Logging) mode** (`PRAGMA journal_mode=WAL`) allowing high-concurrency read/write operations. 

Each user receives absolute partitioned isolation:
- Chat history logs are stored in `conversations/user_{user_id}`
- Semantic Vector caches are stored in `vector_db/collections/user_{user_id}`

## 3. Telemetry and Resource Monitoring

As an admin, you have access to exclusive `admin_funded` API endpoints. You can hook into the `/api/admin/stats` and `/api/admin/users` endpoints to scrape real-time usage metrics.
The `user_usage` table securely records daily rolling burndown of tokens processed by each tenant.

## 4. Failovers & Circuit Breakers

If a specific third-party provider experiences an outage, the `CircuitBreaker` will automatically trip and reroute tenant queries to offline/stable models like `meta/llama-3.1-8b-instruct`.
To inspect the circuit breaker state, poll the `/api/admin/telemetry` endpoint.
