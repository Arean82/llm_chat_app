import os
import shutil
from pathlib import Path

base_dir = Path(r"c:\Users\user\OneDrive\Desktop\python\llm_chat_app")

old_ui = base_dir / "ui_designer" / "storage_manager.ui"
new_ui = base_dir / "operator_tools" / "migration" / "ui_assets" / "local_relocator.ui"

if old_ui.exists():
    shutil.move(str(old_ui), str(new_ui))
    print(f"✅ Moved {old_ui.name} to {new_ui}")
else:
    print(f"❌ Could not find {old_ui}")
