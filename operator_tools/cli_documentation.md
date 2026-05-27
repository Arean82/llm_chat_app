# Official CLI / Headless Operations Manual

This documentation covers how to securely operate the **Migration Companion** and the **Admin Reset** gateway in headless/CLI environments (e.g., remote SSH terminals, cron jobs, or automated CI/CD pipelines) without requiring a desktop GUI.

## 1. Migration Companion CLI

The `migration_companion.exe` (or `migration_companion.py`) supports a highly robust `--headless` mode. You can run it interactively via a terminal menu or use direct scriptable arguments for automation.

### Interactive Terminal Mode
Run the tool with the `--headless` flag to enter the interactive console menu:
```bash
./migration_companion.exe --headless
```
This will present a text-based wizard guiding you through:
1. SaaS Database Relocation
2. Local Storage Relocation
3. System Daemon / Service Installation
4. Database Backups

### Fully Scriptable Mode (Non-Interactive)
For automated environments, you can bypass the interactive menu by passing an `--action`. 

**Automated Backup Example**:
```bash
./migration_companion.exe --headless --action=backup --target-dir=C:\backups\saas_dumps
```
*Note: If the active database is PostgreSQL or MySQL, this will autonomously reach into `saas/config.ini`, extract the password, execute the native `pg_dump`/`mysqldump`, and securely save the dump to `C:\backups\saas_dumps`.*

---

## 2. Universal Admin Reset CLI

The `reset_admin.exe` tool allows you to reset the Master Admin Credentials across all environments.

### Execution
Run the following command to securely invoke the reset sequence:
```bash
./reset_admin.exe --headless
```
*(You may also use `--cli` interchangeably with `--headless`)*

### Behavior & Expected Output
When executed, the tool bypasses PySide6/GUI dependencies completely and directly interfaces with the SQLite/PostgreSQL `TenantDatabaseManager`. It will output the following to `stdout`:
```text
======================================================================
 🚀 UNIVERSAL MASTER PASSWORD RESET SEQUENCE (CLI MODE)
======================================================================
Resolving project root directory: C:\path\to\llm_chat_app
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
