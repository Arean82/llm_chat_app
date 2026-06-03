# scratch/rename_companion.py
import os
import shutil
import sys
from pathlib import Path

def main():
    root_dir = Path(__file__).parent.parent.resolve()
    companion_dir = root_dir / "operator_tools" / "companion"
    
    targets_to_delete = [
        root_dir / "rename_companion.py",
        companion_dir / "operation_companion.py",
        companion_dir / "operation.py",
        companion_dir / "operation.spec",
        root_dir / "clean.py",
        root_dir / "build.py"
    ]
    
    print("==================================================")
    print("🧹 COMPANION OPERATION CLEANUP & VERIFICATION")
    print("==================================================")
    
    # 1. Delete redundant files from root and companion directories
    for path in targets_to_delete:
        if path.exists():
            try:
                path.unlink()
                print(f"✅ Successfully deleted obsolete file: {path.name}")
            except Exception as e:
                print(f"❌ Failed to delete {path.name}: {e}")
        else:
            print(f"ℹ️  {path.name} is already removed.")
            
    # 2. Delete redundant specs folder in desktop
    specs_dir = root_dir / "desktop" / "specs"
    if specs_dir.exists():
        try:
            shutil.rmtree(specs_dir)
            print("✅ Successfully deleted redundant specs folder: desktop/specs")
        except Exception as e:
            print(f"❌ Failed to delete specs folder: {e}")
            
    # 3. Verify companion/companion_operation.py exists
    operation_script = companion_dir / "companion_operation.py"
    if operation_script.exists():
        print(f"✅ Verified 'companion_operation.py' is present in {companion_dir}")
    else:
        print(f"❌ Error: 'companion_operation.py' not found in {companion_dir}")
        sys.exit(1)
        
    # 4. Verify desktop/desktop.spec exists
    desktop_spec = root_dir / "desktop" / "desktop.spec"
    if desktop_spec.exists():
        print(f"✅ Verified 'desktop.spec' is present in desktop folder")
    else:
        print(f"❌ Error: 'desktop.spec' not found in desktop folder")
        sys.exit(1)
        
    # 5. Verify root synora_studio.spec exists
    global_spec = root_dir / "synora_studio.spec"
    if global_spec.exists():
        print(f"✅ Verified global 'synora_studio.spec' is present in root folder")
    else:
        print(f"❌ Error: global 'synora_studio.spec' not found in root folder")
        sys.exit(1)
        
    # 6. Verify server/server.spec exists
    server_spec = root_dir / "server" / "server.spec"
    if server_spec.exists():
        print(f"✅ Verified 'server.spec' is present in server folder")
    else:
        print(f"❌ Error: 'server.spec' not found in server folder")
        sys.exit(1)
        
    # 7. Verify web/web.spec exists
    web_spec = root_dir / "web" / "web.spec"
    if web_spec.exists():
        print(f"✅ Verified 'web.spec' is present in web folder")
    else:
        print(f"❌ Error: 'web.spec' not found in web folder")
        sys.exit(1)
        
    # 8. Verify scripts/build.py exists
    build_script = root_dir / "scripts" / "build.py"
    if build_script.exists():
        print(f"✅ Verified 'build.py' is present in scripts folder")
    else:
        print(f"❌ Error: 'build.py' not found in scripts folder")
        sys.exit(1)
        
    print("\n🎉 Verification and cleanup completed successfully!")

if __name__ == "__main__":
    main()
