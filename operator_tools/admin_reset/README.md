# Universal Admin Credentials Resetter

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

## Execution

### CLI/Headless Mode:
```bash
python reset_admin.py --headless
```

### PyInstaller Spec
A standalone binary `reset_admin.exe` can be compiled using PyInstaller:
```bash
pyinstaller reset_admin.spec
```
This isolates the password reset functionality from public client distributions, keeping administrative keys secure.
