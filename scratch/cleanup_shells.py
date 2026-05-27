import os
import shutil

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Rename build.sh -> build_linux.sh
old_linux = os.path.join(root_dir, "build.sh")
new_linux = os.path.join(root_dir, "build_linux.sh")
if os.path.exists(old_linux):
    shutil.move(old_linux, new_linux)
    print("✅ Renamed build.sh -> build_linux.sh")

# 2. Rename build_all_plugins.sh -> build_plugin.sh
old_plugin = os.path.join(root_dir, "build_all_plugins.sh")
new_plugin = os.path.join(root_dir, "build_plugin.sh")
if os.path.exists(old_plugin):
    shutil.move(old_plugin, new_plugin)
    print("✅ Renamed build_all_plugins.sh -> build_plugin.sh")

# 3. Delete unwanted scripts
unwanted = [
    "build_deb.sh",
    "build_appimage.sh",
    "clean.sh"
]

for f in unwanted:
    path = os.path.join(root_dir, f)
    if os.path.exists(path):
        os.remove(path)
        print(f"🗑️ Deleted: {f}")

print("\n✅ Verification - Current .sh files in Root:")
for f in os.listdir(root_dir):
    if f.endswith(".sh"):
        print(f"  - {f}")
