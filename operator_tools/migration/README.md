# Migration Companion & Service Daemon Installer

The Migration Companion is a dual-mode administrative utility that facilitates platform migration, local data relocations, database backups, and system service daemon generation.

## Features
- **Database Relocation**: Autonomously migrates all schemas and data from local bootstrap environments (Turso/libSQL SQLite) up to production enterprise clusters (PostgreSQL).
- **Automated Service Generation (Daemon Installer)**:
  - Generates native background daemon configurations.
  - **Windows (NSSM)**: Generates a PowerShell script (`install_<name>.ps1`) that automatically downloads NSSM, configures execution, locks down permissions, and installs the API as a Windows Service.
  - **Linux (systemd)**: Generates a `.service` file and automated bash script (`install_<name>.sh`) that configures systemd, sets up dedicated service users, and configures security hardening (such as `PrivateTmp`, `ProtectHome`, and restricted capabilities).
- **Dual-Mode Execution**:
  - **GUI Mode**: PySide6 step-by-step wizard panel.
  - **CLI Mode**: Interactive terminal wizard or scriptable actions (e.g. `--action=backup`).

## Execution

### CLI Mode:
```bash
python migration_companion.py --headless
```

### PyInstaller Spec
A standalone binary `Migration Companion.exe` can be compiled using PyInstaller:
```bash
pyinstaller migration.spec
```
This ensures private operator tools are compiled separate from the main desktop user bundle.
