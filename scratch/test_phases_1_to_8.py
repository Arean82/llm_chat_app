# scratch/test_phases_1_to_8.py
import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_all_tests():
    """Discovers and runs all test suites for Phases 1 through 8."""
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_files = [
        "test_phases_1_to_5.py",
        "test_phase_5_2.py",
        "test_phase_6.py",
        "test_phase_7.py",
        "test_phase_8.py"
    ]
    
    scratch_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("🚀 INITIATING MASTER TEST SUITE (PHASES 1 - 8)")
    print("=" * 60)
    
    for test_file in test_files:
        file_path = os.path.join(scratch_dir, test_file)
        if os.path.exists(file_path):
            print(f"[*] Loading test suite: {test_file}")
            tests = loader.discover(start_dir=scratch_dir, pattern=test_file)
            suite.addTests(tests)
        else:
            print(f"[!] Warning: Test file not found: {test_file}")
            
    print("-" * 60)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("-" * 60)
    if result.wasSuccessful():
        print("✅ ALL PHASES (1-8) PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("❌ MASTER TEST SUITE FAILED. See errors above.")
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
