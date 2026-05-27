import os
import shutil

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
admin_dir = os.path.join(root_dir, "operator_tools", "admin_reset")
ui_dir = os.path.join(admin_dir, "ui_assets")
core_dir = os.path.join(admin_dir, "core")

os.makedirs(ui_dir, exist_ok=True)
os.makedirs(core_dir, exist_ok=True)

old_ui = os.path.join(admin_dir, "reset_admin.ui")
new_ui = os.path.join(ui_dir, "reset_admin.ui")

if os.path.exists(old_ui):
    shutil.move(old_ui, new_ui)
    print(f"✅ Moved reset_admin.ui to {new_ui}")
else:
    print(f"⚠️ Could not find {old_ui}")

print("✅ Setup admin_reset MVC structure complete.")
