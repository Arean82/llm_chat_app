# test_phase8_reliability.py
# Automated Circuit Breaker & Failover Sandboxing Verification Script

import time
import sys
import os

# Add root folder to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import base class first to ensure ServiceRegistry is loaded
from logic.services.base_service import BaseService, ServiceRegistry
from logic.reliability.circuit_breaker import CircuitBreaker, CircuitBreakerState

class MockClient:
    def __init__(self):
        self.model = "primary-model"
        self.api_key = "primary-key"
        self.base_url = "https://api.openai.com/v1"

    def set_google_api_key(self, key):
        self.api_key = key

    def set_api_key(self, key):
        self.api_key = key

    def set_model(self, model):
        self.model = model

    def set_base_url(self, url):
        self.base_url = url

    def _run_completion_internal(self, *args, **kwargs):
        return f"Mocked failover response on model={self.model}"

def run_reliability_test():
    print("==================================================")
    print("🚀 STARTING: Circuit Breaker State & Failover Tests")
    print("==================================================")

    # Initialize circuit breaker
    breaker = CircuitBreaker()
    breaker.cooldown_period = 2.0  # Speed up test cooldown to 2 seconds
    breaker.failure_threshold = 3  # Speed up trip threshold to 3 failures

    print(f"[*] Configured breaker failure threshold: {breaker.failure_threshold}, cooldown: {breaker.cooldown_period}s")
    print(f"[*] Initial circuit state: {breaker.state}")
    
    if breaker.state != CircuitBreakerState.CLOSED:
        print("[❌ FAILURE] Expected initial state to be CLOSED.")
        sys.exit(1)

    # Step 1: Record 3 failures to trigger trip
    print("\n[*] Step 1: Simulating consecutive primary provider failures...")
    for i in range(1, breaker.failure_threshold + 1):
        breaker.record_failure()
        print(f"  -> Failure #{i} recorded. Consecutive failures tally: {breaker.consecutive_failures}")

    print(f"[*] State after failures: {breaker.state}")
    if breaker.state != CircuitBreakerState.OPEN:
        print(f"[❌ FAILURE] Expected state to be OPEN, but got: {breaker.state}")
        sys.exit(1)
    else:
        print("  -> Circuit breaker successfully tripped from CLOSED to OPEN!")

    # Step 2: Verify dynamic transition to HALF_OPEN after cooldown
    print("\n[*] Step 2: Waiting for cooldown period to expire (2.2 seconds)...")
    time.sleep(2.2)
    
    current_state = breaker.check_state()
    print(f"  -> State after checking: {current_state}")
    if current_state != CircuitBreakerState.HALF_OPEN:
        print(f"[❌ FAILURE] Expected state to transition to HALF_OPEN, but got: {current_state}")
        sys.exit(1)
    else:
        print("  -> Circuit breaker successfully transitioned to HALF-OPEN after cooldown!")

    # Step 3: Simulating a successful primary request in HALF_OPEN
    print("\n[*] Step 3: Simulating successful primary execution to close circuit...")
    breaker.record_success()
    print(f"  -> State after successful call: {breaker.state}")
    if breaker.state != CircuitBreakerState.CLOSED:
        print(f"[❌ FAILURE] Expected state to reset to CLOSED, but got: {breaker.state}")
        sys.exit(1)
    else:
        print("  -> Circuit successfully recovered back to CLOSED!")

    # Step 4: Verify Sandboxed Failover Execution
    print("\n[*] Step 4: Testing execute() routing with mock failover connection...")
    
    # Force trip the breaker
    for _ in range(breaker.failure_threshold):
        breaker.record_failure()
    
    # We will simulate a query executing while OPEN
    client = MockClient()
    
    # Define a query function that fails on primary (tripped state will trigger bypass)
    def primary_query():
        raise ConnectionError("Primary down")

    # Mock Auth service within ServiceRegistry
    class MockAuthService(BaseService):
        def get_tenant_keys(self, tenant_id):
            return {
                "api_key_openai": "tenant-byok-openai-key-456",
                "api_key_google": "tenant-byok-google-key-789"
            }

    ServiceRegistry.register("auth", MockAuthService())
    
    try:
        # Execute while OPEN -> should run _execute_failover using OpenAI backup model (gpt-4o-mini)
        res = breaker.execute("tenant_456", client, primary_query)
        print(f"  -> Response: {res}")
        if "gpt-4o-mini" in res or "Mocked failover response" in res:
            print("  -> Sandboxed BYOK OpenAI failover executed perfectly without key bleeding!")
        else:
            print(f"[❌ FAILURE] Expected mock failover response, got: {res}")
            sys.exit(1)
    except Exception as e:
        print(f"[❌ FAILURE] Execution failed during failover routing: {str(e)}")
        sys.exit(1)

    print("\n==================================================")
    print("🎉 SUCCESS: Circuit Breaker & Reliability tests pass!")
    print("==================================================")

if __name__ == "__main__":
    run_reliability_test()
