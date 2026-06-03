# Web SaaS Portal & Multi-Tenant Gateway

This directory hosts the web application portal, database routing switchboard, dynamic tenant sandboxing engines, and SaaS client management interfaces.

## Directory Structure
- **`app.py`**: The core Flask application controller handling routes, JWT authentications, tenant logins, session flows, and REST endpoints.
- **`run_web.py`**: Standard script runner that imports the `app` instance and fires up the server loop.
- **`core/`**: SaaS core helper modules (e.g. `launcher.py`, `agent_manager.py`, `config_manager.py`, `tenant_db.py`).
- **`tenant_drivers/`**: Middleware orchestrating schema isolations and cloud db migrations for multi-tenant users.
- **`static/` & `templates/`**: Pure HTML/CSS/JS frontend views, stylesheets, and dashboard screens.
- **`saas_docs/`**: Platform operating guidelines and administrative instructions.

## Key Architecture Notes
- **Zero GUI Overhead**: Strictly isolated from PySide6 and Qt components to run efficiently on headless production servers.
- **Micro-Gateway Routing**: Delegates intensive generation and embedding queries to the underlying `server/` layer.
