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
        companion_dir / "operation.spec"
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
            
    # 2. Verify companion/companion_operation.py exists
    operation_script = companion_dir / "companion_operation.py"
    if operation_script.exists():
        print(f"✅ Verified 'companion_operation.py' is present in {companion_dir}")
    else:
        print(f"❌ Error: 'companion_operation.py' not found in {companion_dir}")
        sys.exit(1)
        
    print("\n🎉 Verification and cleanup completed successfully!")

if __name__ == "__main__":
    main()
