import os
import json
import time
import logging
import threading
from server.logic.services.base_service import BaseService, ServiceRegistry

# Optional OpenTelemetry imports
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

logger = logging.getLogger("QuantumTelemetry")

class TelemetryManager(BaseService):
    """
    Central system observability and telemetry orchestrator.
    Gathers structured JSON execution metrics, tracks latencies and throughput,
    and runs diagnostic health checks on key external dependencies.
    """
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        
        # Real-time metrics store
        self.metrics = {
            "total_requests": 0,
            "error_count": 0,
            "cumulative_latency": 0.0,
            "cumulative_tokens": 0,
            "active_connections": 0,
            "rate_limit_blocks": 0
        }
        
        # In-memory history for rolling throughput (timestamp, success_bool)
        self._request_history = []
        
        # Setup telemetry directory and files
        from server.utils.storage_config import StorageManager
        self.telemetry_log_path = StorageManager.get_instance().get_storage_root() / "data" / "telemetry_logs.jsonl"
        self.telemetry_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.tracer = None
        self._init_opentelemetry()

    def _init_opentelemetry(self):
        """Initializes OpenTelemetry Tracer if available."""
        if OTEL_AVAILABLE:
            try:
                provider = TracerProvider()
                processor = SimpleSpanProcessor(ConsoleSpanExporter())
                provider.add_span_processor(processor)
                trace.set_tracer_provider(provider)
                self.tracer = trace.get_tracer(__name__)
                logger.info("OpenTelemetry configured successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenTelemetry: {e}")

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Telemetry Observability Service...")
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Telemetry Observability Service...")
        return True

    def record_request(self, tenant_id: str, latency: float, tokens: int, error: bool = False) -> None:
        """Log a structured JSON line record and update real-time telemetry tables."""
        now = time.time()
        with self._lock:
            self.metrics["total_requests"] += 1
            if error:
                self.metrics["error_count"] += 1
            self.metrics["cumulative_latency"] += latency
            self.metrics["cumulative_tokens"] += tokens
            
            # Keep rolling history for throughput (limit to last 1000 items)
            self._request_history.append((now, not error))
            if len(self._request_history) > 1000:
                self._request_history.pop(0)

        # Structured JSON Log Record
        log_entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tenant_id": tenant_id,
            "latency_seconds": round(latency, 3),
            "tokens": tokens,
            "status": "error" if error else "success"
        }
        
        # OpenTelemetry Trace Emit (Optional)
        if self.tracer:
            with self.tracer.start_as_current_span("record_request") as span:
                span.set_attribute("tenant_id", tenant_id)
                span.set_attribute("latency_seconds", latency)
                span.set_attribute("tokens", tokens)
                span.set_attribute("error", error)
        
        try:
            with open(self.telemetry_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to append to telemetry log file: {str(e)}")

    def record_rate_limit_block(self) -> None:
        with self._lock:
            self.metrics["rate_limit_blocks"] += 1

    def increment_connections(self) -> None:
        with self._lock:
            self.metrics["active_connections"] += 1

    def decrement_connections(self) -> None:
        with self._lock:
            self.metrics["active_connections"] = max(0, self.metrics["active_connections"] - 1)

    def get_realtime_metrics(self) -> dict:
        """Calculate throughput, cache ratios, and connection metrics."""
        now = time.time()
        with self._lock:
            total = self.metrics["total_requests"]
            errors = self.metrics["error_count"]
            avg_latency = (self.metrics["cumulative_latency"] / total) if total > 0 else 0.0
            avg_tokens = (self.metrics["cumulative_tokens"] / total) if total > 0 else 0.0
            
            # Throughput in last 60 seconds
            one_min_ago = now - 60.0
            rolling_reqs = [req for req in self._request_history if req[0] >= one_min_ago]
            rpm_throughput = len(rolling_reqs)

        # Fetch cache hit metrics dynamically
        cache_hit_ratio = 0.0
        try:
            cache_service = ServiceRegistry.get("cache")
            if cache_service:
                cache_hit_ratio = cache_service.get_hit_ratio()
        except KeyError:
            pass

        return {
            "http_throughput_rpm": rpm_throughput,
            "average_latency_seconds": round(avg_latency, 3),
            "total_requests": total,
            "error_count": errors,
            "active_connections": self.metrics["active_connections"],
            "cache_hit_ratio_percent": cache_hit_ratio,
            "average_tokens_per_req": round(avg_tokens, 1),
            "rate_limit_blocks": self.metrics.get("rate_limit_blocks", 0)
        }

    def export_prometheus_metrics(self) -> str:
        """
        6.1.2 OpenTelemetry Upgrades: 
        Exposes metrics in standard Prometheus text format for /metrics endpoints.
        """
        metrics = self.get_realtime_metrics()
        lines = [
            "# HELP quantum_http_throughput_rpm Requests per minute",
            "# TYPE quantum_http_throughput_rpm gauge",
            f"quantum_http_throughput_rpm {metrics['http_throughput_rpm']}",
            
            "# HELP quantum_average_latency_seconds Average request latency in seconds",
            "# TYPE quantum_average_latency_seconds gauge",
            f"quantum_average_latency_seconds {metrics['average_latency_seconds']}",
            
            "# HELP quantum_total_requests_total Total number of processed requests",
            "# TYPE quantum_total_requests_total counter",
            f"quantum_total_requests_total {metrics['total_requests']}",
            
            "# HELP quantum_error_count_total Total number of errors",
            "# TYPE quantum_error_count_total counter",
            f"quantum_error_count_total {metrics['error_count']}",
            
            "# HELP quantum_active_connections Current number of active connections",
            "# TYPE quantum_active_connections gauge",
            f"quantum_active_connections {metrics['active_connections']}",
            
            "# HELP quantum_cache_hit_ratio_percent Cache hit ratio",
            "# TYPE quantum_cache_hit_ratio_percent gauge",
            f"quantum_cache_hit_ratio_percent {metrics['cache_hit_ratio_percent']}"
        ]
        return "\n".join(lines) + "\n"

    def run_health_checks(self) -> dict:
        """
        Executes active connectivity scans against external system units.
        Returns explicit health state flags for dashboard LED indicators.
        """
        health_status = {
            "storage": "HEALTHY",
            "vector_db": "HEALTHY",
            "cache": "HEALTHY",
            "queue": "HEALTHY",
            "llm": "HEALTHY"
        }

        # 1. Storage health check
        try:
            storage_service = ServiceRegistry.get("storage")
            # Try to fetch default connection driver to check file access/db pools
            driver = storage_service.get_driver("default_user")
            # Simple select test depending on driver structure
            if hasattr(driver, "get_all_conversations"):
                driver.get_all_conversations()
        except Exception as e:
            logger.error(f"Health Check failure on Storage dependency: {str(e)}")
            health_status["storage"] = "DEGRADED"

        # 2. Vector DB health check
        try:
            from server.logic.vector_db import VectorDatabase
            db = VectorDatabase.get_instance()
            if not db or not db.client:
                health_status["vector_db"] = "DEGRADED"
        except Exception as e:
            logger.error(f"Health Check failure on Vector Database dependency: {str(e)}")
            health_status["vector_db"] = "DEGRADED"

        # 3. Cache health check
        try:
            cache_service = ServiceRegistry.get("cache")
            if not cache_service or not cache_service.is_initialized:
                health_status["cache"] = "DEGRADED"
        except Exception as e:
            health_status["cache"] = "DEGRADED"

        # 4. Job queue health check
        try:
            from server.logic.queue.job_queue import JobQueueEngine
            queue_engine = JobQueueEngine()
            if queue_engine.executor._shutdown:
                health_status["queue"] = "DEGRADED"
        except Exception as e:
            health_status["queue"] = "DEGRADED"

        # 5. LLM Provider health check
        try:
            circuit_breaker = ServiceRegistry.get("circuit_breaker")
            if circuit_breaker.state == "OPEN":
                health_status["llm"] = "DEGRADED"
        except Exception:
            pass

        return health_status


# Register TelemetryManager automatically
ServiceRegistry.register("telemetry", TelemetryManager())
