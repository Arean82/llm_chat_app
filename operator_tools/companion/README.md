# Companion Operation & Service Daemon Installer (v9.0)

The Companion Operation is a dual-mode administrative utility that facilitates platform migration, local data relocations, database backups, network/web configuration, and system service daemon generation.

## Features
- **Database Relocation**: Autonomously migrates all schemas and data from local bootstrap environments (Turso/libSQL SQLite) up to production enterprise clusters (PostgreSQL).
- **Network/Web Configuration**: Programmatically update host binding and ports for the SaaS Web Portal via GUI or CLI.
- **Automated Service Generation (Daemon Installer)**:
  - Generates native background daemon configurations.
  - **Windows (NSSM)**: Generates a PowerShell script (`install_<name>.ps1`) that automatically downloads NSSM, configures execution, locks down permissions, and installs the API as a Windows Service.
  - **Linux (systemd)**: Generates a `.service` file and automated bash script (`install_<name>.sh`) that configures systemd, sets up dedicated service users, and configures security hardening (such as `PrivateTmp`, `ProtectHome`, and restricted capabilities).
- **Dual-Mode Execution**:
  - **GUI Mode**: PySide6 step-by-step wizard panel.
  - **CLI Mode**: Interactive terminal wizard or scriptable actions (e.g. `--action=backup`).

## Local Configuration & Packaging Files
To support decoupled modular compilation, this directory contains its own self-contained packaging files:
- **`companion_operation.spec`**: PyInstaller spec file specific to packaging the Companion Operation tool.
- **`build.py`**: Local Python build script executing PyInstaller commands targeting `companion_operation.spec`. (Global orchestrator is in `scripts/build.py`).
- **`file_version_info.txt`**: OS-level metadata defining the executable's version (v9.0.0.0), copyrights, and descriptions.
- **`installer_script.iss`**: Local Inno Setup configuration to package the compiled Companion Operation tool.

## Execution

### CLI Mode:
```bash
python companion_operation.py --headless
```

### PyInstaller Spec
To compile the standalone binary `Companion_Operation` using PyInstaller:
```bash
pyinstaller companion_operation.spec
```
This ensures private operator tools are compiled separate from the main desktop user bundle.
