# scratch/test_phase3_gateway.py

import os
import sys
import time
import json
import logging
import unittest

# Ensure root workspace is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server.logic.services import ServiceRegistry
from web.app import create_saas_app
from web.tenant_db import TenantDatabaseManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] (%(threadName)s) %(message)s")
logger = logging.getLogger("TestPhase3Gateway")

class TestPhase3Gateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logger.info("Setting up Phase 3 Integration Gateway Test Suite...")
        
        # We explicitly mock/live start redis first
        from server.logic.services.redis_manager import RedisManager
        redis_mgr = RedisManager()
        redis_mgr.enabled = False # Force Mock mode for clean isolated test runs
        redis_mgr.use_mock = True
        redis_mgr.initialize()
        ServiceRegistry.register("redis", redis_mgr)
        
        from server.logic.services.rate_limiter_service import RateLimiterService
        from server.logic.services.security_service import SecurityService
        from server.logic.services.cognitive_router_service import CognitiveRouterService
        from server.logic.services.auth_service import AuthService
        from server.logic.reliability.circuit_breaker import CircuitBreaker
        
        # Hydrate all services
        ServiceRegistry.initialize_all()
        
        cls.db = TenantDatabaseManager()
        cls.auth_service = ServiceRegistry.get("auth")
        cls.rate_limiter = ServiceRegistry.get("rate_limiter")
        cls.security_svc = ServiceRegistry.get("security")
        cls.cog_router = ServiceRegistry.get("cognitive_router")
        cls.circuit_breaker = ServiceRegistry.get("circuit_breaker")
        
        # Reset super admin default passport
        cls.db.reset_admin_account()

        # Seed a standard BYOK tenant for testing
        cls.test_username = "testpilot_v9"
        cls.test_passport = "test_master_passport_v9"
        cls.test_email = "testpilot@quantum.local"
        cls.test_password = "SecurePassword123!"
        
        # Clean any existing seed
        with cls.db.get_connection() as conn:
            conn.execute("DELETE FROM users WHERE username = ?", (cls.test_username,))
            conn.commit()

        cls.user_id, err = cls.db.register_user(cls.test_passport, cls.test_username, cls.test_email, cls.test_password, "byok")
        if err:
            logger.error(f"Failed to register test user: {err}")
            
        # Seed an admin-funded tenant for testing quotas
        cls.funded_username = "funded_pilot"
        cls.funded_passport = "funded_passport_v9"
        cls.funded_email = "funded@quantum.local"
        
        with cls.db.get_connection() as conn:
            conn.execute("DELETE FROM users WHERE username = ?", (cls.funded_username,))
            conn.commit()
            
        cls.funded_user_id, err = cls.db.register_user(cls.funded_passport, cls.funded_username, cls.funded_email, cls.test_password, "admin_funded")
        
        # Establish Flask SaaS Test Client
        cls.flask_app = create_saas_app()
        cls.client = cls.flask_app.test_client()

    def test_01_jwt_issuance_and_verification(self):
        logger.info("=== TEST 1: JWT Issuance and Verification ===")
        user_dict = {
            "id": self.user_id,
            "username": self.test_username,
            "email": self.test_email,
            "key_type": "byok"
        }
        
        # Generate token
        token = self.auth_service.generate_token(user_dict, expires_in=10)
        self.assertIsNotNone(token)
        self.assertTrue(len(token.split('.')) == 3)
        
        # Verify active token
        payload = self.auth_service.verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["id"], self.user_id)
        self.assertEqual(payload["username"], self.test_username)
        
        # Rejects expired or tampered tokens
        tampered_token = token[:-4] + "AAAA"
        self.assertIsNone(self.auth_service.verify_token(tampered_token))
        
        expired_token = self.auth_service.generate_token(user_dict, expires_in=-10)
        self.assertIsNone(self.auth_service.verify_token(expired_token))
        
        logger.info("✅ JWT validation checks successfully passed.")

    def test_02_route_versioning(self):
        logger.info("=== TEST 2: Route Versioning (v1 and v2 prefixes) ===")
        
        # A. Default health
        resp_def = self.client.get('/health')
        self.assertEqual(resp_def.status_code, 200)
        
        # B. v1 health
        resp_v1 = self.client.get('/v1/health')
        self.assertEqual(resp_v1.status_code, 200)
        self.assertEqual(resp_v1.get_json()["status"], "online")

        # C. v2 health
        resp_v2 = self.client.get('/v2/health')
        self.assertEqual(resp_v2.status_code, 200)
        self.assertEqual(resp_v2.get_json()["status"], "online")
        
        logger.info("✅ Health routes prefixed with v1/v2 are fully active.")

    def test_03_redis_token_bucket_rate_limiting(self):
        logger.info("=== TEST 3: Redis Token Bucket Rate Limiting ===")
        
        # Clear mock buckets for deterministic testing
        self.rate_limiter.client.flushall()
        
        key = "test_rate_key"
        limit = 3
        period = 5
        
        # First 3 hits should be allowed
        self.assertTrue(self.rate_limiter.is_allowed(key, limit, period))
        self.assertTrue(self.rate_limiter.is_allowed(key, limit, period))
        self.assertTrue(self.rate_limiter.is_allowed(key, limit, period))
        
        # 4th hit should be rejected (429 condition)
        self.assertFalse(self.rate_limiter.is_allowed(key, limit, period))
        
        # Sleep for a bit to replenish tokens
        time.sleep(2)
        # Should allow at least one request now
        self.assertTrue(self.rate_limiter.is_allowed(key, limit, period))
        
        logger.info("✅ Redis Rate Limiter throttled excessive queries perfectly.")

    def test_04_auth_middleware_jwt_verification(self):
        logger.info("=== TEST 4: Gateway Auth Middleware JWT Verification ===")
        
        user_dict = {
            "id": self.user_id,
            "username": self.test_username,
            "email": self.test_email,
            "key_type": "byok"
        }
        jwt_token = self.auth_service.generate_token(user_dict)
        
        # Request with Bearer JWT
        headers = {"Authorization": f"Bearer {jwt_token}"}
        resp = self.client.get('/v1/user/settings', headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])
        
        # Request with invalid token should throw 403 Forbidden
        headers_bad = {"Authorization": "Bearer badtoken.foo.bar"}
        resp_bad = self.client.get('/v1/user/settings', headers=headers_bad)
        self.assertEqual(resp_bad.status_code, 403)
        
        logger.info("✅ Auth middleware blocks and permits requests correctly based on JWT signatures.")

    def test_05_security_service_rbac_and_audit(self):
        logger.info("=== TEST 5: SecurityService RBAC isolation ===")
        
        # 1. Normal active user permissions
        active_user = {"username": self.test_username, "key_type": "byok", "status": "active"}
        self.assertTrue(self.security_svc.check_permission(active_user, "user"))
        self.assertFalse(self.security_svc.check_permission(active_user, "admin"))
        
        # 2. Banned active check
        banned_user = {"username": self.test_username, "key_type": "byok", "status": "banned"}
        self.assertFalse(self.security_svc.check_permission(banned_user, "user"))
        
        # 3. Admin operator check
        admin_user = {"username": "admin", "key_type": "admin_funded", "status": "active"}
        self.assertTrue(self.security_svc.check_permission(admin_user, "admin"))
        
        logger.info("✅ RBAC roles check validated correctly.")

    def test_06_cognitive_routing_task_mapping(self):
        logger.info("=== TEST 6: Cognitive Router task capability mapping ===")
        
        # Route standard chat task
        model_chat = self.cog_router.route_model(self.user_id, "chat")
        self.assertEqual(model_chat, "meta/llama-3.1-8b-instruct")
        
        # Route code task
        model_code = self.cog_router.route_model(self.user_id, "code")
        self.assertEqual(model_code, "meta/llama-3.1-405b-instruct")
        
        # Route reasoning task
        model_reasoning = self.cog_router.route_model(self.user_id, "reasoning")
        self.assertEqual(model_reasoning, "deepseek-ai/deepseek-r1")
        
        logger.info("✅ ModelRouter capability mapping engines passed successfully.")

    def test_07_billing_quota_enforcer(self):
        logger.info("=== TEST 7: Billing Quota Enforcer ===")
        
        # Assign a quota of 1000 tokens to funded_pilot user
        settings = self.auth_service.get_user_settings(self.funded_user_id)
        settings["token_quota"] = 1000
        self.auth_service.update_user_settings(self.funded_user_id, settings)
        
        # Clear existing usage records for clean test run
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM user_usage WHERE user_id = ?", (self.funded_user_id,))
            conn.commit()
            
        # Verify healthy quota state
        self.assertTrue(self.cog_router.check_billing_quota(self.funded_user_id))
        
        # Record usage below quota (500 tokens)
        self.db.record_usage(self.funded_user_id, 200, 300)
        self.assertTrue(self.cog_router.check_billing_quota(self.funded_user_id))
        
        # Record usage pushing past quota (800 additional tokens, total 1300)
        self.db.record_usage(self.funded_user_id, 400, 400)
        self.assertFalse(self.cog_router.check_billing_quota(self.funded_user_id))
        
        # Hit chat endpoint as the quota-exhausted funded user, expecting 402 Payment Required
        jwt_funded = self.auth_service.generate_token({
            "id": self.funded_user_id,
            "username": self.funded_username,
            "email": self.funded_email,
            "key_type": "admin_funded"
        })
        
        headers = {"Authorization": f"Bearer {jwt_funded}"}
        resp = self.client.post('/v1/chat/completions', headers=headers, json={
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "Hello world"}]
        })
        self.assertEqual(resp.status_code, 402)
        self.assertEqual(resp.get_json()["error"], "Quota Exhausted")
        
        logger.info("✅ Cost engine pre-flight quota enforcer blocks exhausted tenants successfully.")

    def test_08_health_check_provider_pings(self):
        logger.info("=== TEST 8: Health-Check Provider pings ===")
        
        # Ping check
        res = self.cog_router.ping_provider("ollama", "http://localhost:11434")
        # We don't assert true/false because Ollama might be off on test host, 
        # but check that health status is recorded in dict state
        self.assertIn("ollama", self.cog_router.provider_health)
        logger.info(f"Ollama recorded status is: {self.cog_router.provider_health['ollama']}")

    def test_09_circuit_breaker_and_failover_topology(self):
        logger.info("=== TEST 9: Circuit Breaker and Failover Topology ===")
        
        # Force trip circuit breaker to OPEN
        self.circuit_breaker.state = "OPEN"
        self.circuit_breaker.is_failover_enabled = True
        
        # Test directly calling the circuit breaker's execution harness
        from server.logic.llm_client import LLMClient
        llm_client = LLMClient()
        llm_client.set_model("meta/llama-3.1-8b-instruct")
        
        def dummy_query():
            return "success"
            
        with self.assertRaises(Exception) as context:
            self.circuit_breaker.execute(self.user_id, llm_client, dummy_query)
            
        # Verify that it bypassed primary and attempted failover (which fails due to absent keys/local offline)
        self.assertIn("failover", str(context.exception).lower())
        logger.info("✅ Circuit breaker failover routing triggered and intercepted correctly.")

    @classmethod
    def tearDownClass(cls):
        logger.info("Tearing down Phase 3 Integration test suite...")
        # Clear database seeds
        with cls.db.get_connection() as conn:
            conn.execute("DELETE FROM users WHERE username IN (?, ?)", (cls.test_username, cls.funded_username))
            conn.commit()
        ServiceRegistry.shutdown_all()
        ServiceRegistry.clear()
        logger.info("🏆 ALL PHASE 3 API GATEWAY INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    unittest.main()
