import os
import re
import shutil

# Target is one directory up from the scratch folder
scratch_dir = os.path.dirname(os.path.abspath(__file__))
target_dir = os.path.dirname(scratch_dir)

icon_source = r"C:\Users\user\.gemini\antigravity-ide\brain\c8ef3593-4c8d-4037-b96b-06b231379b7c\synora_studio_icon_1780205991069.png"
resources_dir = os.path.join(target_dir, "resources")
app_icon_dest = os.path.join(resources_dir, "app_icon.png")

ignore_dirs = {'.git', 'venv', 'node_modules', '__pycache__', 'dist', 'build', 'badge_cache', '.github', '.gemini'}
ignore_exts = {'.png', '.jpg', '.jpeg', '.ico', '.icns', '.zip', '.exe', '.db', '.pyc', '.vsix', '.svg', '.png'}

replacements = [
    (r"\bLLM Chat App\b", "Synora Studio"),
    (r"\bLLM_Chat_App\b", "Synora_Studio"),
    (r"\bllm_chat_app\b", "synora_studio"),
    (r"\bllmchatapp\b", "synorastudio"),
    (r"\bQuantum SaaS\b", "Synora Studio SaaS"),
    (r"\bQuantum Admin\b", "Synora Admin"),
    (r"quantum-saas\.local", "synora-studio.local"),
]

print(f"Targeting root directory: {target_dir}")
print("1. Renaming file contents...")
for root, dirs, files in os.walk(target_dir):
    dirs[:] = [d for d in dirs if d not in ignore_dirs]
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in ignore_exts or file == "rename_and_icon.py" or file == "rename_script.py":
            continue
            
        filepath = os.path.join(root, file)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue
            
        original = content
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
            
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  -> Updated contents: {filepath}")

print("\n2. Renaming .spec files...")
spec_files = [f for f in os.listdir(target_dir) if f.startswith("LLM_Chat_App_") and f.endswith(".spec")]
for spec in spec_files:
    old_path = os.path.join(target_dir, spec)
    new_name = spec.replace("LLM_Chat_App_", "Synora_Studio_")
    new_path = os.path.join(target_dir, new_name)
    os.rename(old_path, new_path)
    print(f"  -> Renamed {spec} to {new_name}")

print("\n3. Copying new icon and generating assets...")
if os.path.exists(icon_source):
    os.makedirs(resources_dir, exist_ok=True)
    shutil.copy2(icon_source, app_icon_dest)
    print("  -> Copied new app_icon.png")
    
    try:
        from PIL import Image
        img = Image.open(app_icon_dest)
        img.save(os.path.join(resources_dir, "app_icon.ico"), sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
        img.resize((256, 256)).save(os.path.join(resources_dir, "app_icon_linux.png"))
        print("  -> Successfully generated app_icon.ico and app_icon_linux.png")
    except ImportError:
        print("  -> PIL not installed, skipping .ico generation. Please install Pillow and run the script from README.")
else:
    print(f"  -> Icon source not found: {icon_source}")

# Attempt to clean up the root mistake script if it exists
mistake_script = os.path.join(target_dir, "rename_and_icon.py")
if os.path.exists(mistake_script):
    try:
        os.remove(mistake_script)
    except Exception:
        pass

print("\nApp successfully renamed to Synora Studio! You can delete this script.")
