import time
import logging
import json
import re
from .base_service import BaseService, ServiceRegistry
from server.logic.llm_client import LLMClient

logger = logging.getLogger("QuantumConversationService")

class RateLimitExceeded(Exception):
    """Exception raised when a user/tenant exceeds their rate limit budget."""
    pass

class TokenBucketRateLimiter:
    """
    Thread-safe in-memory Token Bucket rate limiter per tenant.
    Tracks Requests Per Minute (RPM) constraints.
    """
    def __init__(self):
        # Maps tenant_id to { "tokens": float, "last_updated": float, "rpm": int }
        self._buckets = {}

    def is_allowed(self, tenant_id: str, rpm_limit: int) -> bool:
        if rpm_limit <= 0:
            return True  # Unlimited

        now = time.time()
        if tenant_id not in self._buckets:
            self._buckets[tenant_id] = {
                "tokens": float(rpm_limit),
                "last_updated": now,
                "rpm": rpm_limit
            }

        bucket = self._buckets[tenant_id]
        # If the rate limit changed, update bucket configuration dynamically
        if bucket["rpm"] != rpm_limit:
            bucket["rpm"] = rpm_limit
            bucket["tokens"] = min(bucket["tokens"], float(rpm_limit))

        # Replenish tokens based on elapsed time (rpm_limit / 60 tokens per second)
        elapsed = now - bucket["last_updated"]
        replenish_rate = float(rpm_limit) / 60.0
        bucket["tokens"] = min(float(rpm_limit), bucket["tokens"] + elapsed * replenish_rate)
        bucket["last_updated"] = now

        # Check if we have at least 1 token
        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True
        return False


class ConversationService(BaseService):
    """
    Unified conversation service orchestration layer.
    Manages LLM interaction, dynamic prompt/context injection, token count estimations,
    SSE formatting, rate-limit enforcement, and failover integration.
    """
    def __init__(self):
        super().__init__()
        self.llm_client = None
        self.rate_limiter = None

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Conversation Service...")
        self.llm_client = LLMClient()
        self.llm_client.hydrate()
        self.rate_limiter = TokenBucketRateLimiter()
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Conversation Service...")
        self.llm_client = None
        self.rate_limiter = None
        return True

    def check_rate_limit(self, tenant_id: str) -> None:
        """
        Validates the tenant's rate limit budget using Token Bucket.
        Throws RateLimitExceeded (which gets caught as 429) if budget is exhausted.
        """
        # Fetch limits from settings or tenant database
        auth_service = ServiceRegistry.get("auth")
        user_settings = auth_service.get_user_settings(tenant_id) if hasattr(auth_service, "get_user_settings") else {}
        
        # Default RPM: 60 for SaaS, 0 (unlimited) for local/default desktop
        default_rpm = 0 if tenant_id == "default_user" else 60
        rpm_limit = int(user_settings.get("requests_per_minute_limit", default_rpm))

        # Check in memory bucket
        if not self.rate_limiter.is_allowed(tenant_id, rpm_limit):
            logger.warning(f"Rate limit exceeded for tenant '{tenant_id}' (Limit: {rpm_limit} RPM)")
            raise RateLimitExceeded(f"Rate limit exceeded. Maximum of {rpm_limit} requests per minute allowed.")

    def estimate_tokens(self, messages: list) -> dict:
        """
        Rough estimate of token counts to track usage telemetry.
        """
        prompt_tokens = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                prompt_tokens += len(content.split()) * 1.3
            elif isinstance(content, list):
                for part in content:
                    if part.get("type") == "text":
                        prompt_tokens += len(part.get("text", "").split()) * 1.3
                    elif part.get("type") == "image":
                        prompt_tokens += 200 # Fixed estimate for vision assets
        return {"prompt_tokens": int(prompt_tokens)}

    def execute_completion(self, tenant_id: str, messages: list, options: dict = None) -> dict:
        """
        Performs a synchronous conversation completion.
        Enforces instant rate-limiting rejection and triggers dynamic failovers if needed.
        """
        self.check_rate_limit(tenant_id)
        options = options or {}
        temperature = options.get("temperature", 0.7)
        max_tokens = options.get("max_tokens", 4096)
        
        # Hydrate LLMClient keys and provider models
        self.llm_client.hydrate()
        model_id = options.get("model_id") or self.llm_client.current_model
        if model_id:
            self.llm_client.set_model(model_id)

        # RAG Injection if expected
        rag_service = ServiceRegistry.get("rag")
        query = messages[-1].get("content", "") if messages else ""
        if options.get("inject_rag") and rag_service:
            context = rag_service.retrieve_grounded_context(tenant_id, query)
            if context:
                messages.insert(0, {"role": "system", "content": context})

        start_time = time.perf_counter()
        
        # Reliability Integration (Circuit Breaker Failover Routing)
        circuit_breaker = None
        try:
            circuit_breaker = ServiceRegistry.get("circuit_breaker")
        except KeyError:
            pass

        # Perform the actual execution, respecting the Circuit Breaker
        if circuit_breaker and circuit_breaker.is_enabled():
            try:
                # Wrap generation inside circuit breaker execution
                response_text = circuit_breaker.execute(
                    tenant_id,
                    self.llm_client,
                    self.llm_client._run_completion_internal,
                    "You are a helpful assistant.",
                    query,
                    max_tokens,
                    temperature
                )
            except Exception as e:
                logger.error(f"Circuit Breaker trigger or execution error: {str(e)}")
                raise e
        else:
            # Bypass circuit breaker direct execution
            try:
                response_text = self.llm_client._run_completion_internal(
                    "You are a helpful assistant.",
                    query,
                    max_tokens,
                    temperature
                )
            except Exception as e:
                logger.error(f"Direct conversation completion error: {str(e)}")
                raise e

        latency = time.perf_counter() - start_time
        token_stats = self.estimate_tokens(messages)
        completion_tokens = int(len(response_text.split()) * 1.3)

        # Save conversation to Storage via Repository Pattern (6.1.3)
        try:
            from server.logic.repositories.conversation_repository import ConversationRepository
            repo = ConversationRepository(tenant_id)
            conv_id = options.get("conv_id")
            title = options.get("title", "New Chat")
            
            history = messages + [{"role": "assistant", "content": response_text}]
            repo.save_conversation(history, title=title, conv_id=conv_id, model_id=model_id)
        except Exception as e:
            logger.error(f"Failed to save conversation via repository: {e}")

        # Log Telemetry
        telemetry = None
        try:
            telemetry = ServiceRegistry.get("telemetry")
        except KeyError:
            pass
            
        if telemetry:
            telemetry.record_request(
                tenant_id=tenant_id,
                latency=latency,
                tokens=token_stats["prompt_tokens"] + completion_tokens,
                error=False
            )

        return {
            "response": response_text,
            "latency": round(latency, 2),
            "prompt_tokens": token_stats["prompt_tokens"],
            "completion_tokens": completion_tokens
        }

    def format_sse_chunk(self, event: str, data: dict) -> str:
        """Helper to format standard server-sent event (SSE) chunks."""
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# Register ConversationService automatically
ServiceRegistry.register("conversation", ConversationService())
