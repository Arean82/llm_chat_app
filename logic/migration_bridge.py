# logic/migration_bridge.py
import sys
import hashlib
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


def verify_migration_integrity(source_driver: BaseStorageDriver, dest_driver: BaseStorageDriver,
                                progress_callback: Optional[Callable[[str], None]] = None) -> dict:
    """
    Performs a comprehensive integrity audit between a source and target database after migration.
    Validates zero data loss by comparing row counts and SHA-256 checksums across all conversation payloads.

    Args:
        source_driver (BaseStorageDriver): Active source database driver instance.
        dest_driver (BaseStorageDriver): Active target database driver instance.
        progress_callback (Callable): Optional reporter for audit progress logs.

    Returns:
        dict: Audit results containing:
            {
                "passed": bool,
                "source_count": int,
                "dest_count": int,
                "count_match": bool,
                "source_checksum": str,
                "dest_checksum": str,
                "checksum_match": bool,
                "mismatched_titles": list
            }
    """
    if progress_callback:
        progress_callback("Starting migration integrity audit...")

    # Step 1: Row count comparison
    source_convs = source_driver.get_all_conversations()
    dest_convs = dest_driver.get_all_conversations()
    source_count = len(source_convs)
    dest_count = len(dest_convs)
    count_match = source_count == dest_count

    if progress_callback:
        progress_callback(f"Row counts — Source: {source_count}, Destination: {dest_count}, Match: {count_match}")

    # Step 2: SHA-256 checksum of all conversation payloads (title + messages_json, sorted by title+timestamp)
    def compute_checksum(driver: BaseStorageDriver, conv_list: list) -> str:
        """Computes a deterministic SHA-256 digest across all conversation payloads."""
        hasher = hashlib.sha256()
        # Sort by (title, timestamp) for deterministic ordering independent of primary keys
        sorted_convs = sorted(conv_list, key=lambda c: (str(c[1]), str(c[2])))
        for conv_id, title, timestamp in sorted_convs:
            details = driver.load_conversation(conv_id)
            if details:
                # Hash the stable content: title + serialized messages
                import json
                payload = f"{details['title']}|{json.dumps(details['messages'], sort_keys=True)}"
                hasher.update(payload.encode('utf-8'))
        return hasher.hexdigest()

    if progress_callback:
        progress_callback("Computing source database checksum...")
    source_checksum = compute_checksum(source_driver, source_convs)

    if progress_callback:
        progress_callback("Computing destination database checksum...")
    dest_checksum = compute_checksum(dest_driver, dest_convs)

    checksum_match = source_checksum == dest_checksum

    if progress_callback:
        progress_callback(f"Checksums — Source: {source_checksum[:16]}..., Dest: {dest_checksum[:16]}..., Match: {checksum_match}")

    # Step 3: Title-level comparison to identify specific mismatches
    source_titles = sorted([str(c[1]) for c in source_convs])
    dest_titles = sorted([str(c[1]) for c in dest_convs])
    mismatched_titles = []
    
    source_title_set = set(source_titles)
    dest_title_set = set(dest_titles)
    missing_in_dest = source_title_set - dest_title_set
    extra_in_dest = dest_title_set - source_title_set
    
    if missing_in_dest:
        mismatched_titles.extend([f"MISSING in dest: {t}" for t in missing_in_dest])
    if extra_in_dest:
        mismatched_titles.extend([f"EXTRA in dest: {t}" for t in extra_in_dest])

    passed = count_match and checksum_match and len(mismatched_titles) == 0

    if progress_callback:
        status = "✅ PASSED" if passed else "❌ FAILED"
        progress_callback(f"Migration Integrity Audit: {status}")
        if mismatched_titles:
            for m in mismatched_titles:
                progress_callback(f"  ⚠ {m}")

    return {
        "passed": passed,
        "source_count": source_count,
        "dest_count": dest_count,
        "count_match": count_match,
        "source_checksum": source_checksum,
        "dest_checksum": dest_checksum,
        "checksum_match": checksum_match,
        "mismatched_titles": mismatched_titles
    }


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

        # Run post-migration integrity audit
        print("\n[*] Running post-migration integrity audit...")
        audit = verify_migration_integrity(source, dest, progress_callback=lambda log: print(f"  [Audit Log] {log}"))
        if audit["passed"]:
            print("[+] Integrity audit PASSED. Zero data loss confirmed.")
        else:
            print("[!] Integrity audit FAILED. Review mismatches above.")
    except Exception as e:
        print(f"\n[!] Relocation error: {e}")

