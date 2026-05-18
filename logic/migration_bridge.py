# logic/migration_bridge.py
import sys
from typing import Callable, Optional
from logic.storage_drivers.base_driver import BaseStorageDriver

def migrate_database(source_driver: BaseStorageDriver, dest_driver: BaseStorageDriver, 
                     progress_callback: Optional[Callable[[str], None]] = None) -> int:
    """
    Safely migrates all chat conversation history transactionally from a source storage driver
    to a destination storage driver. This operation is non-destructive (source database is left unaltered).

    Args:
        source_driver (BaseStorageDriver): Active source database driver instance.
        dest_driver (BaseStorageDriver): Active target database driver instance.
        progress_callback (Callable): Optional reporter for migration progress logs.

    Returns:
        int: Number of conversations successfully transferred.
    """
    if progress_callback:
        progress_callback("Extracting conversation list from source...")
        
    conversations = source_driver.get_all_conversations()
    total = len(conversations)
    
    if progress_callback:
        progress_callback(f"Found {total} threads to migrate.")
        
    migrated_count = 0
    for idx, (conv_id, title, timestamp) in enumerate(conversations, 1):
        if progress_callback:
            progress_callback(f"[{idx}/{total}] Fetching details for Thread: {title} (ID: {conv_id})...")
            
        details = source_driver.load_conversation(conv_id)
        if details:
            # Write transactionally to the destination
            dest_driver.save_conversation(
                conversation=details["messages"],
                title=details["title"],
                conv_id=None, # Inserts as a new record to avoid primary key conflicts
                model_id=details.get("model_id", ""),
                messages_html=details.get("messages_html", ""),
                timestamp=details["timestamp"]
            )
            migrated_count += 1
            
    if progress_callback:
        progress_callback(f"Migration completed. Successfully transferred {migrated_count} of {total} threads.")
        
    return migrated_count

def run_interactive_cli_migration():
    """
    Launches an interactive command-line wizard to relocate chat histories.
    """
    print("\n" + "="*70)
    print("  LLM CHAT APP - LIVE DATABASE RELOCATION & MIGRATION BRIDGE (CLI)")
    print("="*70)
    print("Choose SOURCE Database Driver:")
    print("  1. libSQL / Turso Cloud (Default)")
    print("  2. PostgreSQL Server")
    src_choice = input("Enter choice (1-2) [1]: ").strip() or "1"
    
    src_url = input("Enter SOURCE Database URL: ").strip()
    src_token = ""
    if src_choice == "1":
        src_token = input("Enter SOURCE Auth Token (optional): ").strip()
        
    print("\nChoose TARGET Database Driver:")
    print("  1. libSQL / Turso Cloud (Default)")
    print("  2. PostgreSQL Server")
    dst_choice = input("Enter choice (1-2) [1]: ").strip() or "1"
    
    dst_url = input("Enter TARGET Database URL: ").strip()
    dst_token = ""
    if dst_choice == "1":
        dst_token = input("Enter TARGET Auth Token (optional): ").strip()
        
    try:
        if src_choice == "1":
            from logic.storage_drivers.libsql_driver import LibSQLStorageDriver
            source = LibSQLStorageDriver(src_url, src_token)
        else:
            from logic.storage_drivers.postgres_driver import PostgreSQLStorageDriver
            source = PostgreSQLStorageDriver(src_url)
            
        if dst_choice == "1":
            from logic.storage_drivers.libsql_driver import LibSQLStorageDriver
            dest = LibSQLStorageDriver(dst_url, dst_token)
        else:
            from logic.storage_drivers.postgres_driver import PostgreSQLStorageDriver
            dest = PostgreSQLStorageDriver(dst_url)
            
        print("\nInitializing dynamic database migration pipeline...")
        count = migrate_database(source, dest, progress_callback=lambda log: print(f"  [Migration Log] {log}"))
        print(f"\n[+] Relocation completed! Successfully transferred {count} conversations.")
    except Exception as e:
        print(f"\n[!] Relocation error: {e}")
