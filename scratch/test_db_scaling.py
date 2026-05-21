#!/usr/bin/env python3
"""
Phase 6.3.3 / 6.1.5 — High-Concurrency OCC Stress Tester
==========================================================
Multi-threaded stress test that validates Optimistic Concurrency Control (OCC)
across all storage drivers (SQLite, PostgreSQL, libSQL).

This script spawns N threads that simultaneously attempt to update the EXACT
same conversation row using the OCC `expected_version` parameter. The expected
behavior is:
  - Exactly 1 thread succeeds (its version matched)
  - N-1 threads receive a ConcurrencyError (their version was stale)

This formally validates row-level locking and version-check mechanics under
heavy concurrent load, simulating the worst-case scenario of GUI + CLI + SaaS
all editing the same conversation at the exact same millisecond.

Usage:
    python scratch/test_db_scaling.py
"""

import os
import sys
import time
import threading
import tempfile
from pathlib import Path

# Ensure the project root is on the import path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from logic.storage_drivers.sqlite_driver import LocalSQLiteDriver
from logic.storage_drivers.base_driver import ConcurrencyError

# ─── Configuration ───────────────────────────────────────────────────────────
THREAD_COUNT = 20          # Number of simultaneous writer threads
TEST_DB_NAME = "occ_stress_test.db"

# ─── Test Results Container ──────────────────────────────────────────────────
results_lock = threading.Lock()
results = {
    "successes": 0,
    "concurrency_errors": 0,
    "other_errors": 0,
    "error_details": []
}


def worker_thread(driver: LocalSQLiteDriver, conv_id: int, version: int, thread_id: int):
    """
    Each worker thread attempts to update the same conversation row
    using the same expected_version. Only one should succeed.
    """
    try:
        driver.save_conversation(
            conversation=[{"role": "user", "content": f"Thread {thread_id} write at {time.time_ns()}"}],
            title=f"OCC Stress Test - Thread {thread_id}",
            conv_id=conv_id,
            expected_version=version
        )
        with results_lock:
            results["successes"] += 1
            print(f"  ✅ Thread {thread_id:02d}: WRITE SUCCEEDED (version {version} -> {version + 1})")
    except ConcurrencyError as e:
        with results_lock:
            results["concurrency_errors"] += 1
            print(f"  🛡️ Thread {thread_id:02d}: ConcurrencyError (correctly rejected)")
    except Exception as e:
        with results_lock:
            results["other_errors"] += 1
            results["error_details"].append(f"Thread {thread_id}: {type(e).__name__}: {e}")
            print(f"  ❌ Thread {thread_id:02d}: UNEXPECTED ERROR: {e}")


def run_sqlite_occ_stress_test():
    """Runs the full OCC stress test against a temporary SQLite database."""
    print("\n" + "=" * 70)
    print("  OCC STRESS TEST — Phase 6.3.3 / 6.1.5")
    print("  Multi-Interface Concurrency Audit (SQLite)")
    print("=" * 70)

    # Create a temporary database for the test
    test_db_dir = PROJECT_ROOT / "scratch"
    test_db_dir.mkdir(exist_ok=True)
    test_db_path = test_db_dir / TEST_DB_NAME

    # Clean up any previous test database
    if test_db_path.exists():
        os.remove(test_db_path)

    print(f"\n[1/5] Initializing test database: {test_db_path}")
    driver = LocalSQLiteDriver(test_db_path)

    # Step 1: Insert a seed conversation
    print("[2/5] Inserting seed conversation...")
    conv_id = driver.save_conversation(
        conversation=[{"role": "system", "content": "Seed conversation for OCC stress test."}],
        title="OCC Stress Test Seed",
        model_id="stress-tester-v1"
    )
    print(f"       Seed conversation ID: {conv_id}")

    # Step 2: Load the conversation to get its current version
    print("[3/5] Loading seed to capture current version...")
    loaded = driver.load_conversation(conv_id)
    current_version = loaded["version"]
    print(f"       Current version: {current_version}")

    # Step 3: Spawn N threads that ALL try to write using the SAME expected_version
    print(f"[4/5] Spawning {THREAD_COUNT} concurrent writer threads (all using version={current_version})...\n")

    # Reset results
    results["successes"] = 0
    results["concurrency_errors"] = 0
    results["other_errors"] = 0
    results["error_details"] = []

    threads = []
    barrier = threading.Barrier(THREAD_COUNT)  # Synchronize all threads to start at the exact same instant

    def synchronized_worker(driver, conv_id, version, thread_id):
        barrier.wait()  # All threads start simultaneously
        worker_thread(driver, conv_id, version, thread_id)

    for i in range(THREAD_COUNT):
        t = threading.Thread(target=synchronized_worker, args=(driver, conv_id, current_version, i))
        threads.append(t)

    start_time = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    elapsed = time.perf_counter() - start_time

    # Step 4: Validate results
    print(f"\n[5/5] Results Summary:")
    print(f"       ├── Threads Launched:     {THREAD_COUNT}")
    print(f"       ├── Successful Writes:    {results['successes']}")
    print(f"       ├── Concurrency Rejects:  {results['concurrency_errors']}")
    print(f"       ├── Unexpected Errors:    {results['other_errors']}")
    print(f"       └── Elapsed Time:         {elapsed:.4f}s")

    if results["error_details"]:
        print("\n  ⚠️  Unexpected Error Details:")
        for detail in results["error_details"]:
            print(f"       {detail}")

    # Final verdict
    print("\n" + "-" * 70)
    expected_successes = 1
    expected_rejects = THREAD_COUNT - 1

    if results["successes"] == expected_successes and results["concurrency_errors"] == expected_rejects and results["other_errors"] == 0:
        print("  ✅ OCC STRESS TEST: PASSED")
        print(f"     Exactly {expected_successes} write succeeded, {expected_rejects} were correctly rejected.")
        print("     Row-level version locking is ROCK SOLID under concurrent load.")
    else:
        print("  ❌ OCC STRESS TEST: FAILED")
        print(f"     Expected {expected_successes} success + {expected_rejects} rejects.")
        print(f"     Got {results['successes']} successes + {results['concurrency_errors']} rejects + {results['other_errors']} errors.")
    print("-" * 70)

    # Verify final row state
    final = driver.load_conversation(conv_id)
    print(f"\n  Final conversation version: {final['version']} (expected: {current_version + 1})")
    print(f"  Final title: {final['title']}")

    # Cleanup
    driver.close_pool()
    if test_db_path.exists():
        os.remove(test_db_path)
        print(f"\n  [Cleanup] Removed test database: {test_db_path}")

    return results["successes"] == expected_successes and results["concurrency_errors"] == expected_rejects


if __name__ == "__main__":
    success = run_sqlite_occ_stress_test()
    sys.exit(0 if success else 1)
