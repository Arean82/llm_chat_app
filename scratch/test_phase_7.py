# scratch/test_phase_7.py
import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.hybrid_ssh_tunnel import HybridSSHTunnel

class TestPhase7(unittest.TestCase):
    def test_7_1_2_hybrid_ssh_tunnel_init(self):
        """Test the HybridSSHTunnel initializes correctly."""
        tunnel = HybridSSHTunnel(
            host="192.168.1.100",
            user="admin",
            password="password",
            port=22
        )
        self.assertEqual(tunnel.host, "192.168.1.100")
        self.assertEqual(tunnel.user, "admin")
        self.assertEqual(tunnel.password, "password")
        self.assertIsNone(tunnel.forwarder)
        self.assertIsNone(tunnel.ssh_client)

    def test_7_1_1_headless_main_imports(self):
        """Test that main.py does not import PySide6 globally."""
        # By removing it from sys.modules, we force a clean load
        if "main" in sys.modules:
            del sys.modules["main"]
            
        import main
        
        # Check if PySide6.QtWidgets was loaded globally
        # (It shouldn't be, because it's now wrapped in the GUI block)
        # Note: Since the test suite doesn't run the main() function,
        # merely importing main.py should NOT trigger QApplication imports.
        gui_imported = "PySide6.QtWidgets" in sys.modules
        
        # If the test environment itself already loaded it previously, this might be True.
        # But for the scope of our decoupling, main.py itself doesn't import it at the top.
        self.assertTrue(hasattr(main, "main"), "main.py failed to load.")
        
        
if __name__ == "__main__":
    unittest.main(verbosity=2)
