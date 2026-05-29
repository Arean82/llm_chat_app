# scratch/test_phase_6.py
import unittest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.logic.services.base_service import ServiceRegistry

class TestPhase6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ServiceRegistry.initialize_all()

    @classmethod
    def tearDownClass(cls):
        ServiceRegistry.shutdown_all()

    def test_6_1_1_feature_store(self):
        """Test the FeatureStore dynamically caches features."""
        fs = ServiceRegistry.get("feature_store")
        self.assertIsNotNone(fs)
        
        # Test default load
        self.assertFalse(fs.get_flag("enable_agents", default=False))
        
        # Test update and retrieval
        self.assertTrue(fs.set_flag("enable_agents", True))
        self.assertTrue(fs.get_flag("enable_agents"))
        
        # Test arbitrary dict
        self.assertTrue(fs.set_flag("custom_config", {"timeout": 30}))
        config = fs.get_flag("custom_config")
        self.assertIsInstance(config, dict)
        self.assertEqual(config.get("timeout"), 30)

    def test_6_1_2_opentelemetry_metrics(self):
        """Test TelemetryManager exports Prometheus format string."""
        telemetry = ServiceRegistry.get("telemetry")
        self.assertIsNotNone(telemetry)
        
        # Record a dummy request
        telemetry.record_request("tenant_A", 1.5, 100, error=False)
        telemetry.record_request("tenant_A", 0.5, 50, error=True)
        
        prom_metrics = telemetry.export_prometheus_metrics()
        self.assertIsInstance(prom_metrics, str)
        self.assertIn("quantum_http_throughput_rpm", prom_metrics)
        self.assertIn("quantum_error_count_total", prom_metrics)
        self.assertIn("quantum_total_requests_total", prom_metrics)
        
    def test_6_1_3_conversation_repository(self):
        """Test ConversationRepository wraps StorageService correctly."""
        from server.logic.repositories.conversation_repository import ConversationRepository
        repo = ConversationRepository("test_tenant")
        
        # Save a conversation
        history = [{"role": "user", "content": "hello"}]
        conv_id = repo.save_conversation(history, title="Repo Test")
        self.assertIsNotNone(conv_id)
        
        # Load it back
        loaded = repo.load_conversation(conv_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.get("title"), "Repo Test")
        
        # Cleanup
        repo.delete_conversation(conv_id)
        
if __name__ == "__main__":
    unittest.main(verbosity=2)
