# SaaS IDE Integration Guide

This document is for developers actively editing and extending the `saas/` module.

## Modifying the Database
If you need to add columns to the SQLite `users` or `tenant_credentials` tables in `tenant_db.py`:
1. Ensure you hook into the `init_db()` migration pipeline. 
2. Use `try/except sqlite3.OperationalError:` blocks to handle graceful schema upgrades on boot so you don't corrupt existing `saas_tenants.db` files.

## Concurrency Warnings
The app relies heavily on PySide6 threads bridging into Flask context. 
- **Do not** instantiate global state variables without wrapping them in threading locks.
- **Circuit Breaker state** must be polled from the single active instance of the `CircuitBreaker` module in `ServiceRegistry`. 

## Adding New Endpoints
When modifying `saas/app.py` to add new routes, always secure them properly:
- If it's a web UI route, enforce the `@login_required` logic.
- If it's an API route, validate `request.headers.get("Authorization")` against the Passport vault before processing any business logic.
