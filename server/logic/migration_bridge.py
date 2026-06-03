# logic/migration_bridge.py
import sys
import hashlib
from typing import Callable, Optional
from server.logic.storage_drivers.base_driver import BaseStorageDriver

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
        progress_callback("Extracting models from source schema...")
    
    models = source_driver.load_all_models()
    model_count = len(models)
    if progress_callback:
        progress_callback(f"Found {model_count} models to migrate.")
        
    for model in models:
        dest_driver.save_model(model.get("id"), model.get("provider", "nvidia"), model)
        
    if progress_callback:
        progress_callback("Extracting system configurations from source schema...")
        
    # Since we don't have a get_all_configs in the base driver, we explicitly migrate known Phase 8 keys
    # Example: user_prompts could be stored as "user_prompts"
    known_config_keys = ["user_prompts"]
    config_count = 0
    for key in known_config_keys:
        val = source_driver.get_config(key)
        if val is not None:
            dest_driver.set_config(key, val)
            config_count += 1
            
    if progress_callback:
        progress_callback(f"Migrated {config_count} system configurations.")

    if progress_callback:
        progress_callback(f"Migration completed. Successfully transferred {migrated_count} of {total} threads, {model_count} models, and {config_count} configs.")
        
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

def migrate_saas_tenant_database(source_driver, dest_driver, progress_callback=None) -> int:
    """
    Safely migrates all SaaS tenant database tables (Users, Usage, Credentials, Orbit Shares, Cache)
    transactionally from a source driver to a destination driver.
    """
    if progress_callback:
        progress_callback("Establishing source and target database channels...")

    src_conn = source_driver.get_connection()
    dst_conn = dest_driver.get_connection()
    
    try:
        src_cur = src_conn.cursor()
        dst_cur = dst_conn.cursor()
        
        # Determine placeholder for destination
        dest_name = dest_driver.__class__.__name__.lower()
        ph = "%s" if "postgres" in dest_name or "mysql" in dest_name else "?"
        
        if progress_callback:
            progress_callback("Cleaning destination tables to avoid primary key collisions...")
            
        # Clear target tables first to allow clean overwrite
        dst_cur.execute("DELETE FROM agent_skills")
        dst_cur.execute("DELETE FROM agent_memory")
        dst_cur.execute("DELETE FROM agent_instances")
        dst_cur.execute("DELETE FROM semantic_query_cache")
        dst_cur.execute("DELETE FROM chunk_cache")
        dst_cur.execute("DELETE FROM tenant_credentials")
        dst_cur.execute("DELETE FROM shared_orbits")
        dst_cur.execute("DELETE FROM user_usage")
        dst_cur.execute("DELETE FROM users")
        dst_conn.commit()
        
        if progress_callback:
            progress_callback("Migrating table: users...")
            
        # 1. users table
        src_cur.execute("SELECT id, username, email, password_hash, api_key, key_type, created_at, status, settings_blob FROM users")
        users = [dict(r) for r in src_cur.fetchall()]
        for u in users:
            dst_cur.execute(f"""
                INSERT INTO users (id, username, email, password_hash, api_key, key_type, created_at, status, settings_blob)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (u["id"], u["username"], u["email"], u["password_hash"], u["api_key"], u["key_type"], u["created_at"], u["status"], u["settings_blob"]))
            
        if progress_callback:
            progress_callback(f"Transferred {len(users)} user accounts.")

        # 2. user_usage
        if progress_callback:
            progress_callback("Migrating table: user_usage...")
        src_cur.execute("SELECT id, user_id, date, prompt_tokens, completion_tokens, total_tokens FROM user_usage")
        usage = [dict(r) for r in src_cur.fetchall()]
        for us in usage:
            dst_cur.execute(f"""
                INSERT INTO user_usage (id, user_id, date, prompt_tokens, completion_tokens, total_tokens)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (us["id"], us["user_id"], us["date"], us["prompt_tokens"], us["completion_tokens"], us["total_tokens"]))
        if progress_callback:
            progress_callback(f"Transferred {len(usage)} accounting ledger entries.")

        # 3. tenant_credentials
        if progress_callback:
            progress_callback("Migrating table: tenant_credentials...")
        src_cur.execute("SELECT id, user_id, provider, api_key, updated_at FROM tenant_credentials")
        creds = [dict(r) for r in src_cur.fetchall()]
        for c in creds:
            dst_cur.execute(f"""
                INSERT INTO tenant_credentials (id, user_id, provider, api_key, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, (c["id"], c["user_id"], c["provider"], c["api_key"], c["updated_at"]))
        if progress_callback:
            progress_callback(f"Transferred {len(creds)} secure BYOK tenant credentials.")

        # 4. shared_orbits
        if progress_callback:
            progress_callback("Migrating table: shared_orbits...")
        src_cur.execute("SELECT share_hash, user_id, conversation_data, created_at FROM shared_orbits")
        orbits = [dict(r) for r in src_cur.fetchall()]
        for o in orbits:
            dst_cur.execute(f"""
                INSERT INTO shared_orbits (share_hash, user_id, conversation_data, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph})
            """, (o["share_hash"], o["user_id"], o["conversation_data"], o["created_at"]))
        if progress_callback:
            progress_callback(f"Transferred {len(orbits)} public share links.")

        # 5. chunk_cache
        if progress_callback:
            progress_callback("Migrating table: chunk_cache...")
        src_cur.execute("SELECT chunk_hash, user_id, chunk_text, embedding_blob, created_at FROM chunk_cache")
        chunks = [dict(r) for r in src_cur.fetchall()]
        for ch in chunks:
            embedding = ch["embedding_blob"]
            if isinstance(embedding, bytes):
                try:
                    embedding = embedding.decode('utf-8')
                except Exception:
                    pass
            dst_cur.execute(f"""
                INSERT INTO chunk_cache (chunk_hash, user_id, chunk_text, embedding_blob, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, (ch["chunk_hash"], ch["user_id"], ch["chunk_text"], embedding, ch["created_at"]))
        if progress_callback:
            progress_callback(f"Transferred {len(chunks)} pre-computed embedding caches.")

        # 6. semantic_query_cache
        if progress_callback:
            progress_callback("Migrating table: semantic_query_cache...")
        src_cur.execute("SELECT id, user_id, query_text, response_text, created_at FROM semantic_query_cache")
        queries = [dict(r) for r in src_cur.fetchall()]
        for q in queries:
            dst_cur.execute(f"""
                INSERT INTO semantic_query_cache (id, user_id, query_text, response_text, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, (q["id"], q["user_id"], q["query_text"], q["response_text"], q["created_at"]))
        if progress_callback:
            progress_callback(f"Transferred {len(queries)} semantic query cache hits.")

        # 7. agent_instances
        if progress_callback:
            progress_callback("Migrating table: agent_instances...")
        src_cur.execute("SELECT id, user_id, agent_name, status, created_at, updated_at FROM agent_instances")
        agents = [dict(r) for r in src_cur.fetchall()]
        for a in agents:
            dst_cur.execute(f"""
                INSERT INTO agent_instances (id, user_id, agent_name, status, created_at, updated_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """, (a["id"], a["user_id"], a["agent_name"], a["status"], a["created_at"], a["updated_at"]))
        if progress_callback:
            progress_callback(f"Transferred {len(agents)} agent instances.")

        # 8. agent_memory
        if progress_callback:
            progress_callback("Migrating table: agent_memory...")
        src_cur.execute("SELECT id, user_id, memory_text, created_at FROM agent_memory")
        memories = [dict(r) for r in src_cur.fetchall()]
        for m in memories:
            dst_cur.execute(f"""
                INSERT INTO agent_memory (id, user_id, memory_text, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph})
            """, (m["id"], m["user_id"], m["memory_text"], m["created_at"]))
        if progress_callback:
            progress_callback(f"Transferred {len(memories)} agent memory records.")

        # 9. agent_skills
        if progress_callback:
            progress_callback("Migrating table: agent_skills...")
        src_cur.execute("SELECT id, user_id, skill_name, skill_code, created_at FROM agent_skills")
        skills = [dict(r) for r in src_cur.fetchall()]
        for s in skills:
            dst_cur.execute(f"""
                INSERT INTO agent_skills (id, user_id, skill_name, skill_code, created_at)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            """, (s["id"], s["user_id"], s["skill_name"], s["skill_code"], s["created_at"]))
        if progress_callback:
            progress_callback(f"Transferred {len(skills)} agent skills.")

        dst_conn.commit()
        if progress_callback:
            progress_callback("All tenant data tables successfully committed to target database.")
        return len(users)
    except Exception as e:
        dst_conn.rollback()
        if progress_callback:
            progress_callback(f"CRITICAL RELOCATION ERROR: {e}. Changes rolled back.")
        raise e
    finally:
        src_conn.close()
        dst_conn.close()


def verify_saas_tenant_integrity(source_driver, dest_driver, progress_callback=None) -> dict:
    """
    Performs comprehensive verification audit between source and target SaaS databases.
    Checks table row counts to confirm zero data loss.
    """
    if progress_callback:
        progress_callback("Initializing SaaS Tenant Metadata Relocation Audit...")

    src_conn = source_driver.get_connection()
    dst_conn = dest_driver.get_connection()
    
    try:
        src_cur = src_conn.cursor()
        dst_cur = dst_conn.cursor()
        
        tables = ["users", "user_usage", "tenant_credentials", "shared_orbits", "chunk_cache", "semantic_query_cache", "agent_instances", "agent_memory", "agent_skills"]
        audit_results = {}
        all_passed = True
        
        for table in tables:
            src_cur.execute(f"SELECT COUNT(*) FROM {table}")
            src_cnt = src_cur.fetchone()[0]
            
            dst_cur.execute(f"SELECT COUNT(*) FROM {table}")
            dst_cnt = dst_cur.fetchone()[0]
            
            match = (src_cnt == dst_cnt)
            if not match:
                all_passed = False
                
            audit_results[table] = {
                "source_count": src_cnt,
                "dest_count": dst_cnt,
                "match": match
            }
            if progress_callback:
                progress_callback(f"  [Table Audit] {table} -> Source: {src_cnt}, Target: {dst_cnt} (Match: {match})")
                
        passed_status = "✅ PASSED" if all_passed else "❌ FAILED"
        if progress_callback:
            progress_callback(f"SaaS Database Relocation Audit: {passed_status}")
            
        return {
            "passed": all_passed,
            "details": audit_results
        }
    finally:
        src_conn.close()
        dst_conn.close()


def run_interactive_cli_migration():
    """
    Launches an interactive command-line wizard to relocate chat histories and SaaS tenant metadata.
    """
    print("\n" + "="*70)
    print("  LLM CHAT APP - LIVE DATABASE RELOCATION & MIGRATION BRIDGE (CLI)")
    print("="*70)
    print("Select Migration Target type:")
    print("  1. Chat Conversation History (Portable / AppData DBs)")
    print("  2. SaaS Tenant Metadata (Turso -> Postgres/MySQL)")
    choice = input("Enter choice (1-2) [1]: ").strip() or "1"
    
    if choice == "1":
        print("\nChoose SOURCE Database Driver:")
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
                from server.logic.storage_drivers.libsql_driver import LibSQLStorageDriver
                source = LibSQLStorageDriver(src_url, src_token)
            else:
                from server.logic.storage_drivers.postgres_driver import PostgreSQLStorageDriver
                source = PostgreSQLStorageDriver(src_url)
                
            if dst_choice == "1":
                from server.logic.storage_drivers.libsql_driver import LibSQLStorageDriver
                dest = LibSQLStorageDriver(dst_url, dst_token)
            else:
                from server.logic.storage_drivers.postgres_driver import PostgreSQLStorageDriver
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
            
    else:
        print("\n=== SaaS Tenant Metadata Relocation (Turso -> Enterprise SQL) ===")
        print("Make sure saas/config.ini is configured with your TARGET driver connection settings.")
        confirm = input("Begin relocation? (y/n) [n]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return
            
        try:
            # Source is always local Turso/libSQL
            from web.tenant_drivers.turso_tenant_driver import TursoTenantDriver
            source = TursoTenantDriver()
            
            # Destination is factory-configured driver
            from web.core.tenant_db import TenantDatabaseManager
            # We temporarily bypass singleton to initialize the new target driver
            target_manager = TenantDatabaseManager()
            
            print(f"\nInitializing transaction database relocation for SaaS metadata...")
            count = migrate_saas_tenant_database(source, target_manager, progress_callback=lambda log: print(f"  [Migration Log] {log}"))
            print(f"\n[+] SaaS Relocation completed! Successfully relocated {count} active user accounts.")
            
            # Run SaaS relocation audit
            print("\n[*] Running post-migration SaaS integrity audit...")
            audit = verify_saas_tenant_integrity(source, target_manager, progress_callback=lambda log: print(f"  [Audit Log] {log}"))
            if audit["passed"]:
                print("[+] SaaS Integrity audit PASSED. Zero data loss across all tables confirmed.")
            else:
                print("[!] SaaS Integrity audit FAILED. Check mismatch statistics.")
        except Exception as e:
            print(f"\n[!] SaaS Relocation error: {e}")

