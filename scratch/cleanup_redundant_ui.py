import os

base = r'c:\Users\user\OneDrive\Desktop\python\llm_chat_app\ui_designer'

redundant_files = [
    os.path.join(base, 'migration_companion.ui'),
    os.path.join(base, 'reset_admin.ui')
]

print("🧹 Cleaning up redundant global UI files...")
for file_path in redundant_files:
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"  ✅ Deleted: {file_path}")
    else:
        print(f"  ⏭️ Already removed: {file_path}")

print("✨ Cleanup complete! File structure is perfectly isolated.")
