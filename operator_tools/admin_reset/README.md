# Universal Admin Credentials Resetter (v9.0)

This tool allows server administrators to securely reset the Master Admin Credentials across all environments.

## Features
- **Dual-Mode Execution**:
  - **GUI Mode**: Spawns a high-fidelity PySide6 wizard dialog for local desktop environments.
  - **CLI/Headless Mode**: Bypasses GUI dependencies entirely using `--headless` or `--cli`, making it perfect for remote SSH terminals, automation scripts, and cron jobs.
- **Dynamic Password Options**:
  - `--random-password`: Generates a secure, randomized 12-character alphanumeric password.
  - `--custom-password "your_password"`: Sets a specific, custom password string.
  - Defaults to `admin` password if no option is specified.
- **Auto Driver Detection**: Automatically reads connection information and resolves driver parameters from `saas/config.ini` or the environment.

## Local Configuration & Packaging Files
To support decoupled modular compilation, this directory contains its own self-contained packaging files:
- **`reset_admin.spec`**: PyInstaller spec file specific to packaging the admin reset tool.
- **`build.py`**: Local Python build script executing PyInstaller commands targeting `reset_admin.spec`. (Global orchestrator is in `scripts/build.py`).
- **`file_version_info.txt`**: OS-level metadata defining the executable's version (v9.0.0.0), copyrights, and descriptions.
- **`installer_script.iss`**: Local Inno Setup configuration to package the compiled admin reset tool.

## Execution

### CLI/Headless Mode:
```bash
python reset_admin.py --headless
```

### PyInstaller Spec
To compile the standalone binary `Admin_Reset` using PyInstaller:
```bash
pyinstaller reset_admin.spec
```
This isolates the password reset functionality from public client distributions, keeping administrative keys secure.
