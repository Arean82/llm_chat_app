# Local Admin GUI & Desktop Client

This directory houses the PySide6 standalone graphical user interface, functioning as the local administrator's "Mission Control" panel.

## Directory Structure
- **`main.py`**: Entry point orchestrating native application startup parameters, CLI handlers, and window bounds loading.
- **`ui/`**: PySide6 window view controllers, thread loops, custom custom widget bindings, and event handlers.
- **`ui_designer/`**: Pure XML `.ui` description schemas generated from Qt Designer.
- **`specs/`**: Multi-platform PyInstaller `.spec` packaging scripts (onedir, onefile, macOS configurations).
- **`headless/`**: Local CLI chat prompts and background terminal loops.

## Key Features
- **Bypass Control**: Directly configures active storage setups, databases, and LLM providers locally without relying on the public API gateway.
- **SSH Tunnel Manager**: Instantly establishes encrypted SSH/VPN forwarding connections to remote cloud clusters (Redis, Postgres, Godmode API).
- **Zero SaaS Packaging Bloat**: Compiles cleanly using PyInstaller by strictly ignoring `web/` routing assets.
