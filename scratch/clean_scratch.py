import os
import shutil

scratch_dir = os.path.dirname(os.path.abspath(__file__))

print("=== Cleaning Up Unwanted Scratch Scripts ===")
files_to_delete = [
    "clean_descriptions.py",
    "fix_doc.py",
    "generate_specs.py",
    "refactor_web.py",
    "rename_and_icon.py",
    "process_icon.py",
    "test_service_installer.py"
]

# Identify all test scripts starting with "test_" and ending with ".py"
for filename in os.listdir(scratch_dir):
    if filename.startswith("test_") and filename.endswith(".py"):
        files_to_delete.append(filename)

deleted_count = 0
for filename in files_to_delete:
    filepath = os.path.join(scratch_dir, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"[-] Deleted: {filename}")
            deleted_count += 1
        except Exception as e:
            print(f"[!] Error deleting {filename}: {e}")

print(f"=== Cleanup complete. Deleted {deleted_count} files ===")
