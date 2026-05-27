import os
import shutil
from pathlib import Path

base_dir = Path(r"c:\Users\user\OneDrive\Desktop\python\llm_chat_app")

# 1. Setup MVC directories for Migration Companion
mig_dir = base_dir / "operator_tools" / "migration"
core_dir = mig_dir / "core"
ui_assets_dir = mig_dir / "ui_assets"

core_dir.mkdir(parents=True, exist_ok=True)
ui_assets_dir.mkdir(parents=True, exist_ok=True)
print("✅ Created operator_tools/migration/core/ and ui_assets/")

# 2. Rename and move original migration_companion.ui -> ui_assets/saas_db.ui
old_mig_ui = mig_dir / "migration_companion.ui"
new_saas_ui = ui_assets_dir / "saas_db.ui"

if old_mig_ui.exists():
    shutil.move(str(old_mig_ui), str(new_saas_ui))
    print(f"✅ Moved {old_mig_ui.name} to {new_saas_ui}")
else:
    print(f"⏭️ {old_mig_ui} not found. Already moved?")

# 3. We will do the same for the Storage Manager later, but let's prep the __init__.py files
(core_dir / "__init__.py").touch()
print("✅ Setup MVC complete.")
