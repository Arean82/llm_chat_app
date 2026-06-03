# Local Admin GUI & Desktop Client (v9.0)

This directory houses the PySide6 standalone graphical user interface, functioning as the local administrator's "Mission Control" panel.

## Directory Structure
- **`main.py`**: Entry point orchestrating native application startup parameters, CLI handlers, and window bounds loading.
- **`ui/`**: PySide6 window view controllers, thread loops, custom widget bindings, and event handlers.
- **`ui_designer/`**: Pure XML `.ui` description schemas generated from Qt Designer.
- **`headless/`**: Local CLI chat prompts and background terminal loops.

## Local Configuration & Packaging Files
To support decoupled modular compilation, this directory contains its own self-contained packaging files:
- **`desktop.spec`**: PyInstaller spec file specific to packaging the Desktop client.
- **`build.py`**: Local Python build script executing PyInstaller commands targeting `desktop.spec`. (Global orchestrator is in `scripts/build.py`).
- **`file_version_info.txt`**: OS-level metadata defining the executable's version (v9.0.0.0), copyrights, and descriptions.
- **`installer_script.iss`**: Local Inno Setup configuration to package the compiled desktop application.

## Key Features
- **Bypass Control**: Directly configures active storage setups, databases, and LLM providers locally without relying on the public API gateway.
- **SSH Tunnel Manager**: Instantly establishes encrypted SSH/VPN forwarding connections to remote cloud clusters (Redis, Postgres, Godmode API).
- **Zero SaaS Packaging Bloat**: Compiles cleanly using PyInstaller by strictly ignoring `web/` routing assets.

## Executable Compilation
To compile the standalone binary `Synora_Studio.exe` using PyInstaller:
```bash
pyinstaller desktop.spec
```
