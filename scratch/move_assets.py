import os
import shutil

base = r'c:\Users\user\OneDrive\Desktop\python\llm_chat_app\operator_tools'
mig_dir = os.path.join(base, 'migration')
rst_dir = os.path.join(base, 'admin_reset')

os.makedirs(mig_dir, exist_ok=True)
os.makedirs(rst_dir, exist_ok=True)

# 1. Move and update migration_companion.py
mig_src = os.path.join(base, 'migration_companion.py')
mig_dst = os.path.join(mig_dir, 'migration_companion.py')
if os.path.exists(mig_src):
    with open(mig_src, 'r', encoding='utf-8') as f:
        content = f.read()
    # Update the sys.path root calculation from 2 levels up to 3 levels up
    content = content.replace(
        "ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
        "ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"
    )
    # Update internal comment
    content = content.replace(
        "# operator_tools/migration_companion.py -> project_root/",
        "# operator_tools/migration/migration_companion.py -> project_root/"
    )
    with open(mig_dst, 'w', encoding='utf-8') as f:
        f.write(content)
    os.remove(mig_src)
    print(f"Moved and updated: {mig_dst}")

# 2. Move and update reset_admin.py
rst_src = os.path.join(base, 'reset_admin.py')
rst_dst = os.path.join(rst_dir, 'reset_admin.py')
if os.path.exists(rst_src):
    with open(rst_src, 'r', encoding='utf-8') as f:
        content = f.read()
    # Update the sys.path root calculation from 2 levels up to 3 levels up
    content = content.replace(
        "root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))",
        "root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))"
    )
    # Update internal comment
    content = content.replace(
        "# operator_tools/reset_admin.py is located under project_root/operator_tools/",
        "# operator_tools/admin_reset/reset_admin.py is located under project_root/operator_tools/admin_reset/"
    )
    with open(rst_dst, 'w', encoding='utf-8') as f:
        f.write(content)
    os.remove(rst_src)
    print(f"Moved and updated: {rst_dst}")

print("Asset isolation and path adjustments complete!")
