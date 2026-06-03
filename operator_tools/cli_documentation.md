# Official CLI / Headless Operations Manual

This documentation covers how to securely operate the **Operation Companion** and the **Admin Reset** gateway in headless/CLI environments (e.g., remote SSH terminals, cron jobs, or automated CI/CD pipelines) without requiring a desktop GUI.

## 1. Operation Companion CLI

The `operation_companion.exe` (or `operation_companion.py`) supports a highly robust `--headless` mode. You can run it interactively via a terminal menu or use direct scriptable arguments for automation.

### Interactive Terminal Mode
Run the tool with the `--headless` flag to enter the interactive console menu:
```bash
./operation_companion.exe --headless
```
This will present a text-based wizard guiding you through:
1. SaaS Database Relocation
2. Local Storage Relocation
3. System Daemon / Service Installation
4. Database Backups
5. Network/Web Config

### Fully Scriptable Mode (Non-Interactive)
For automated environments, you can bypass the interactive menu by passing an `--action`. 

**Automated Backup Example**:
```bash
./operation_companion.exe --headless --action=backup --target-dir=C:\backups\saas_dumps
```
*Note: If the active database is PostgreSQL or MySQL, this will autonomously reach into `saas/config.ini`, extract the password, execute the native `pg_dump`/`mysqldump`, and securely save the dump to `C:\backups\saas_dumps`.*

**Automated Web/Port Config Example**:
```bash
./operation_companion.exe --headless --action=web-config --host=0.0.0.0 --port=8080
```

---

## 2. Universal Admin Reset CLI

The `reset_admin.exe` tool allows you to reset the Master Admin Credentials across all environments.

### Execution
Run the following command to securely invoke the reset sequence with the default "admin" password:
```bash
./reset_admin.exe --headless
```
*(You may also use `--cli` interchangeably with `--headless`)*

You can also specify how the password should be generated using the following flags:
- `--random-password`: Generates a secure, randomized 12-character alphanumeric password.
- `--custom-password "your_pass_here"`: Sets an explicit custom password string.

**Example: Dynamic Password Reset**
```bash
./reset_admin.exe --headless --random-password
```

### Behavior & Expected Output
When executed, the tool bypasses PySide6/GUI dependencies completely and directly interfaces with the SQLite/PostgreSQL `TenantDatabaseManager`. It will output the following to `stdout`:
```text
======================================================================
 🚀 UNIVERSAL MASTER PASSWORD RESET SEQUENCE (CLI MODE)
======================================================================
Resolving project root directory: C:\path\to\synora_studio
Detecting active database driver from 'saas/config.ini'...

✅ Successfully synchronized default Master Credentials across ALL ecosystems!
...
  Username: admin
  Password: admin
  API Key:  admin_master_passport
```

### Exit Codes
The tool is strictly compliant with standard POSIX exit codes, making it perfect for pipeline scripts:
- **`0`**: Success
- **`1`**: Failure / Critical Exception

> [!WARNING]
> **Privilege Constraints**
> Both of these tools parse enterprise configuration files (`saas/config.ini`) and modify system states. When running them on a remote server, ensure the user executing the process has sufficient read/write privileges (e.g., `sudo` on Linux or Administrator on Windows).
