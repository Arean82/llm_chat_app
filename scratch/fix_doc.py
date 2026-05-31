import os
import subprocess

doc_path = r'c:\Users\user\OneDrive\Desktop\python\synora_studio\WORKING_DOCUMENT_V8_ATTAINMENT.md'

# 1. Restore file from git to undo the corruption
subprocess.run(['git', 'checkout', 'WORKING_DOCUMENT_V8_ATTAINMENT.md'], cwd=os.path.dirname(doc_path))

# 2. Read the clean file
with open(doc_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 3. Apply the 7.3 -> 7.4 bump (from our earlier step)
text = text.replace('v7.3 Headless/SaaS architecture', 'v7.4 Headless/SaaS architecture')

# 4. Apply the Phase 10 COMPLETED status
text = text.replace('## 🔴 Phase 10: Desktop Native Authentication & Ecosystem Refactoring [STATUS: IN PROGRESS]',
                    '## 🟢 Phase 10: Desktop Native Authentication & Ecosystem Refactoring [STATUS: COMPLETED]')

# 5. Append Phase 11
phase_11 = """
---

## 🔴 Phase 11: Operator Orchestration & Service Decoupling [STATUS: IN PROGRESS]

Phase 11 strips environment-setup logic out of the main desktop client, ensuring the client remains a pure chat application. All data relocation and headless daemon configuration will be moved into the isolated `operator_tools` suite, which will be structurally refactored into dedicated modules with segmented build strategies.

### 11.1 Structural Refactoring & Build Orchestration

| #          | Task                                                                                                                                                                                            | Status     |
| :--------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------- |
| **11.1.1** | **Asset Isolation**: Move the Migration Companion to `operator_tools/migration/migration_companion.py` and the password resetter to `operator_tools/admin_reset/reset_admin.py` to support future modular assets. | [ ]        |
| **11.1.2** | **Path Adjustments**: Update all relative `sys.path` append commands in the relocated scripts to resolve three-levels up to the project root. Update `main.py` cleanup logic.                 | [ ]        |
| **11.1.3** | **Segmented Spec Strategy**: Create distinct PyInstaller `.spec` profiles: `LLM_Chat_App_single.spec` (distributes just the Chat App) and `LLM_Chat_App_full.spec` (bundles Chat App + Reset Admin + Migration Companion). | [ ]        |

### 11.2 Feature Decoupling (The Migration Companion Expansion)

| #          | Task                                                                                                                                                                                            | Status     |
| :--------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------- |
| **11.2.1** | **Transplant Local Storage Manager**: Decouple `ui/storage_manager_dialog.py` logic from the main application and integrate it into the standalone Migration Companion as a new tab/mode.       | [ ]        |
| **11.2.2** | **Main App Cleanup**: Remove the Storage Manager trigger from the main application GUI. The main app should strictly *read* the `storage/data_root` config without altering it.                 | [ ]        |
| **11.2.3** | **Service Setup Wizard**: Build an OS-native service installer into the Companion. Automate the creation of a Windows Service (via Win32/NSSM) or Linux daemon (via `systemd`) for the API.      | [ ]        |
| **11.2.4** | **Unified Admin Dashboard**: Expand the Migration Companion's GUI to feature a multi-tabbed layout: SaaS DB Migration, Local Storage Relocation, and Background Service Orchestration.          | [ ]        |

**Technical Notes (Phase 11):**
* **Zero Client Pollution**: Moving gigabytes of vector caches or modifying service registries is inherently risky to perform while the main app is running. Doing this from the standalone operator suite guarantees that the main application is cleanly shut down, preventing OS file locks and database corruption.
* **Separation of Concerns**: End-users receive the `single` build (just `Synora Studio.exe`) without the ability to accidentally corrupt their install path or install services. The hosting administrator compiles the `full` suite to orchestrate the environment.
"""

text = text.strip() + "\n" + phase_11

# 6. Write back to file
with open(doc_path, 'w', encoding='utf-8') as f:
    f.write(text)

print("Document restored and Phase 11 accurately appended.")
