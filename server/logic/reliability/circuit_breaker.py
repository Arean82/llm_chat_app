import time
import logging
import threading
from server.logic.services.base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumCircuitBreaker")

class CircuitBreakerState:
    CLOSED = "CLOSED"      # Primary connection is healthy, routing all queries
    OPEN = "OPEN"          # Primary failed, routing directly to local/BYOK fallbacks
    HALF_OPEN = "HALF_OPEN" # Testing primary with a single request to see if it recovered


class CircuitBreaker(BaseService):
    """
    Thread-safe Circuit Breaker pattern implementation.
    Monitors outbound LLM queries, transitions state based on error thresholds,
    and handles isolated tenant-level failovers without budget leakage (No Key Bleeding).
    """
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        
        # State settings
        self.state = CircuitBreakerState.CLOSED
        self.consecutive_failures = 0
        self.failure_threshold = 5      # Trip after 5 failures
        self.cooldown_period = 10.0      # Seconds to stay OPEN before checking again
        self.last_state_change = time.time()
        
        # Operator controls
        self.is_failover_enabled = True

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Circuit Breaker Service...")
        # Sync initial state from system configurations if needed
        from server.utils.path_utils import get_app_settings
        settings = get_app_settings()
        self.is_failover_enabled = str(settings.value("failover_enabled", "true")).lower() == "true"
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Circuit Breaker Service...")
        return True

    def is_enabled(self) -> bool:
        return self.is_failover_enabled

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.is_failover_enabled = enabled
            logger.info(f"Operator toggled auto-failover system state to: {enabled}")

    def record_success(self) -> None:
        """Reset failures on successful execution."""
        with self._lock:
            self.consecutive_failures = 0
            if self.state != CircuitBreakerState.CLOSED:
                logger.info("Primary provider connections recovered. Restoring circuit state to CLOSED.")
                self.state = CircuitBreakerState.CLOSED
                self.last_state_change = time.time()

    def record_failure(self) -> None:
        """Increment failure counts and trip if threshold is reached."""
        with self._lock:
            self.consecutive_failures += 1
            now = time.time()
            logger.warning(f"Recorded failure {self.consecutive_failures}/{self.failure_threshold} on primary provider.")
            
            if self.state == CircuitBreakerState.CLOSED and self.consecutive_failures >= self.failure_threshold:
                logger.error(f"Circuit Breaker tripped to OPEN! Consecutive failures reached limit. Cooldown: {self.cooldown_period}s.")
                self.state = CircuitBreakerState.OPEN
                self.last_state_change = now
            elif self.state == CircuitBreakerState.HALF_OPEN:
                logger.error("Primary retry failed in HALF-OPEN state. Resetting back to OPEN.")
                self.state = CircuitBreakerState.OPEN
                self.last_state_change = now

    def check_state(self) -> str:
        """Transition state from OPEN to HALF_OPEN dynamically if cooldown expired."""
        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                elapsed = time.time() - self.last_state_change
                if elapsed >= self.cooldown_period:
                    logger.info("Cooldown period elapsed. Transitioning circuit state to HALF-OPEN to test primary connectivity.")
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.last_state_change = time.time()
            return self.state

    def execute(self, tenant_id: str, client_instance, query_fn, *args, **kwargs) -> str:
        """
        Executes query_fn under circuit monitoring.
        If tripped or failed, intercepts execution and executes sandboxed local/BYOK provider failover.
        """
        current_state = self.check_state()

        if current_state == CircuitBreakerState.OPEN:
            logger.warning(f"Circuit is OPEN for tenant '{tenant_id}'. Bypassing primary. Initiating failover sequence.")
            return self._execute_failover(tenant_id, client_instance, query_fn, *args, **kwargs)

        try:
            # Attempt execution on primary provider
            result = query_fn(*args, **kwargs)
            
            # If successful, reward circuit
            self.record_success()
            return result
            
        except Exception as primary_error:
            logger.error(f"Execution error on primary LLM provider: {str(primary_error)}")
            self.record_failure()
            
            # If failovers are enabled, execute backup sequence immediately
            if self.is_failover_enabled:
                logger.info("Triggering transparent failover following primary connection fault...")
                return self._execute_failover(tenant_id, client_instance, query_fn, *args, **kwargs)
            raise primary_error

    def _execute_failover(self, tenant_id: str, client_instance, query_fn, *args, **kwargs) -> str:
        """
        Executes sandboxed provider failover routing.
        Allows auto-failover ONLY to tenant-owned BYOK keys or offline local models.
        Strictly prevents leaking budget onto Admin-funded API pools.
        """
        logger.info(f"Resolving custom failover routing map for tenant '{tenant_id}'...")
        
        # Load tenant settings and credentials to see provider priorities and actually owned keys
        auth_service = ServiceRegistry.get("auth")
        user_settings = auth_service.get_user_settings(tenant_id) if hasattr(auth_service, "get_user_settings") else {}
        tenant_credentials = auth_service.get_tenant_keys(tenant_id) if hasattr(auth_service, "get_tenant_keys") else {}
        
        # Priority list defined in settings, defaulting dynamically based strictly on owned BYOK credentials
        failover_sequence_str = user_settings.get("failover_provider_sequence", "")
        if failover_sequence_str:
            failover_sequence = str(failover_sequence_str).split(",")
            failover_sequence = [p.strip().lower() for p in failover_sequence if p.strip()]
        else:
            # Build sequence dynamically based strictly on keys they actually registered
            failover_sequence = [p.lower() for p in tenant_credentials.keys()]

        for provider in failover_sequence:
            logger.info(f"Checking failover viability for provider: '{provider}'")
            
            # Guard Rule: Tenant key check for paid hosts (e.g. google, openai)
            if provider == "google":
                # Check if tenant has a valid BYOK Google API Key
                tenant_credentials = auth_service.get_tenant_keys(tenant_id) if hasattr(auth_service, "get_tenant_keys") else {}
                gk = tenant_credentials.get("api_key_google")
                if gk:
                    logger.info("Found tenant-owned Google BYOK credential. Initiating Google failover routing.")
                    try:
                        # Reconfigure LLM Client dynamically for Google failover
                        client_instance.set_google_api_key(gk)
                        client_instance.set_model("gemini-1.5-flash") # Stable lightweight backup model
                        
                        # Set active model and execute
                        result = client_instance._run_completion_internal(*args, **kwargs)
                        logger.info("Successfully completed query via tenant Google BYOK failover connection!")
                        return f"[⚠️ Backup: Google Flash] {result}"
                    except Exception as e:
                        logger.warning(f"Google BYOK failover attempt failed: {str(e)}")
                else:
                    logger.info("Tenant Google BYOK key absent. Skipping Google failover.")

            elif provider in ("openai", "nvidia"):
                # Check if tenant has a custom Nvidia/OpenAI key
                tenant_credentials = auth_service.get_tenant_keys(tenant_id) if hasattr(auth_service, "get_tenant_keys") else {}
                ak = tenant_credentials.get("api_key_openai") or tenant_credentials.get("api_key_nvidia")
                if ak:
                    logger.info("Found tenant-owned OpenAI/Nvidia BYOK credential. Initiating failover.")
                    try:
                        client_instance.set_api_key(ak)
                        client_instance.set_model("gpt-4o-mini")
                        result = client_instance._run_completion_internal(*args, **kwargs)
                        logger.info("Successfully completed query via OpenAI BYOK failover connection!")
                        return f"[⚠️ Backup: OpenAI Mini] {result}"
                    except Exception as e:
                        logger.warning(f"OpenAI BYOK failover attempt failed: {str(e)}")
                else:
                    logger.info("Tenant OpenAI BYOK key absent. Skipping.")

            elif provider in ("ollama", "local", "lm_studio"):
                # Offline/Local models don't leak budgets! Standard Ollama failover.
                
                # --- SECURITY BLOCK (SSRF) ---
                is_admin = False
                try:
                    all_tenants = auth_service.db.get_all_tenants()
                    for t in all_tenants:
                        if str(t['id']) == str(tenant_id) and t['username'] == 'admin':
                            is_admin = True
                            break
                except Exception:
                    pass
                    
                if not is_admin:
                    logger.warning(f"Local fallback '{provider}' denied for non-admin tenant '{tenant_id}'.")
                    continue
                # -----------------------------
                
                logger.info("Initiating local offline model failover query route (Ollama/LM Studio)...")
                try:
                    # Point to standard local address
                    client_instance.set_base_url("http://localhost:11434/v1")
                    client_instance.set_api_key("ollama")
                    client_instance.set_model("llama3") # standard local tag
                    
                    result = client_instance._run_completion_internal(*args, **kwargs)
                    logger.info("Successfully completed query via local offline Ollama failover connection!")
                    return f"[⚠️ Backup: Local Offline] {result}"
                except Exception as e:
                    logger.warning(f"Local offline model failover attempt failed: {str(e)}")

        # No failovers succeeded
        raise ConnectionError("Primary provider is down, and all sandboxed local/BYOK failover routes failed or were unconfigured.")


# Register CircuitBreaker automatically
ServiceRegistry.register("circuit_breaker", CircuitBreaker())
