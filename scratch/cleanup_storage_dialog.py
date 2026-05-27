import os
from pathlib import Path

base_dir = Path(r"c:\Users\user\OneDrive\Desktop\python\llm_chat_app")
target_file = base_dir / "ui" / "storage_manager_dialog.py"

if target_file.exists():
    os.remove(target_file)
    print(f"✅ Deleted {target_file.name}")
else:
    print(f"⏭️ {target_file.name} already deleted.")
