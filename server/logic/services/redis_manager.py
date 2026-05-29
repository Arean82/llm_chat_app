# logic/services/redis_manager.py

import logging
import threading
import time
from .base_service import BaseService, ServiceRegistry
from server.utils.path_utils import get_app_settings

logger = logging.getLogger("QuantumRedisManager")

# Gracefully handle missing redis package
REDIS_AVAILABLE = False
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("The 'redis' package is not installed. All Redis operations will run in Mock Fallback Mode.")

class MockPubSub:
    """A thread-safe mock PubSub client for offline event loop fallback."""
    def __init__(self, manager):
        self.manager = manager
        self.subscribed_channels = set()
        self.queue = []
        self.lock = threading.Lock()
        self.cv = threading.Condition(self.lock)

    def subscribe(self, *args, **kwargs):
        with self.lock:
            for channel in args:
                self.subscribed_channels.add(channel)
                if channel not in self.manager._mock_subscribers:
                    self.manager._mock_subscribers[channel] = set()
                self.manager._mock_subscribers[channel].add(self)
            logger.debug(f"MockPubSub subscribed to channels: {args}")

    def unsubscribe(self, *args, **kwargs):
        with self.lock:
            for channel in args:
                if channel in self.subscribed_channels:
                    self.subscribed_channels.remove(channel)
                if channel in self.manager._mock_subscribers and self in self.manager._mock_subscribers[channel]:
                    self.manager._mock_subscribers[channel].remove(self)
            logger.debug(f"MockPubSub unsubscribed from channels: {args}")

    def push_message(self, channel, data):
        with self.lock:
            message = {
                'type': 'message',
                'pattern': None,
                'channel': channel.encode('utf-8') if isinstance(channel, str) else channel,
                'data': data.encode('utf-8') if isinstance(data, str) else data
            }
            self.queue.append(message)
            self.cv.notify_all()

    def listen(self):
        while True:
            with self.lock:
                while not self.queue:
                    # Non-blocking wait with a timeout to allow graceful exits
                    if not self.cv.wait(timeout=1.0):
                        yield {'type': 'ping', 'data': b'pong'}
                        continue
                yield self.queue.pop(0)

    def get_message(self, ignore_subscribe_messages=False, timeout=0.0):
        with self.lock:
            if self.queue:
                return self.queue.pop(0)
            return None


class MockRedis:
    """Thread-safe in-memory Redis client mock to ensure zero crashes in standalone mode."""
    def __init__(self):
        self._db = {}
        self._ttls = {}
        self._lock = threading.Lock()
        self._mock_subscribers = {} # { channel: set(MockPubSub) }

    def ping(self) -> bool:
        return True

    def get(self, name: str) -> bytes:
        with self._lock:
            name_str = str(name)
            # Handle TTL expiration
            if name_str in self._ttls:
                if time.time() > self._ttls[name_str]:
                    self._db.pop(name_str, None)
                    self._ttls.pop(name_str, None)
                    return None
            val = self._db.get(name_str)
            if val is None:
                return None
            return val if isinstance(val, bytes) else str(val).encode('utf-8')

    def set(self, name: str, value: str, ex=None, px=None, nx=False, xx=False) -> bool:
        with self._lock:
            name_str = str(name)
            if nx and name_str in self._db:
                return False
            if xx and name_str not in self._db:
                return False
            
            self._db[name_str] = value
            if ex:
                self._ttls[name_str] = time.time() + ex
            elif px:
                self._ttls[name_str] = time.time() + (px / 1000.0)
            else:
                self._ttls.pop(name_str, None)
            return True

    def delete(self, *names) -> int:
        count = 0
        with self._lock:
            for name in names:
                name_str = str(name)
                if name_str in self._db:
                    self._db.pop(name_str, None)
                    self._ttls.pop(name_str, None)
                    count += 1
        return count

    def exists(self, name: str) -> bool:
        with self._lock:
            name_str = str(name)
            if name_str in self._ttls and time.time() > self._ttls[name_str]:
                self._db.pop(name_str, None)
                self._ttls.pop(name_str, None)
                return False
            return name_str in self._db

    def keys(self, pattern: str = "*") -> list:
        # Simple pattern matching (only support prefix matching or * matching)
        with self._lock:
            active_keys = []
            for k in list(self._db.keys()):
                if k in self._ttls and time.time() > self._ttls[k]:
                    self._db.pop(k, None)
                    self._ttls.pop(k, None)
                    continue
                active_keys.append(k)
            
            if pattern == "*":
                return [k.encode('utf-8') for k in active_keys]
            elif pattern.endswith("*"):
                prefix = pattern[:-1]
                return [k.encode('utf-8') for k in active_keys if k.startswith(prefix)]
            return [k.encode('utf-8') for k in active_keys if k == pattern]

    def publish(self, channel: str, message: str) -> int:
        count = 0
        channel_str = str(channel)
        with self._lock:
            subscribers = self._mock_subscribers.get(channel_str, set())
            for sub in list(subscribers):
                try:
                    sub.push_message(channel_str, message)
                    count += 1
                except Exception as e:
                    logger.error(f"Error publishing to mock subscriber: {str(e)}")
        return count

    def pubsub(self, *args, **kwargs) -> MockPubSub:
        return MockPubSub(self)

    def flushall(self) -> bool:
        with self._lock:
            self._db.clear()
            self._ttls.clear()
        return True


class RedisManager(BaseService):
    """
    Manages the thread-safe connection pool for Redis / Memurai.
    Enforces a graceful Mock fallback if Redis is unconfigured or unreachable.
    """
    def __init__(self):
        super().__init__()
        self.pool = None
        self._mock_client = MockRedis()
        self.use_mock = True
        self.host = "127.0.0.1"
        self.port = 6379
        self.password = ""
        self.enabled = False

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Redis Manager Service...")
        settings = get_app_settings()
        
        # Load configurations
        self.enabled = str(settings.value("redis_enabled", "false")).lower() == "true"
        self.host = str(settings.value("redis_host", "127.0.0.1")).strip()
        self.port = int(settings.value("redis_port", 6379))
        self.password = str(settings.value("redis_password", "")).strip()

        if not self.enabled:
            logger.info("Redis is disabled in settings. Swapping to Mock Fallback Mode.")
            self.use_mock = True
            return True

        if not REDIS_AVAILABLE:
            logger.warning("Redis is enabled but 'redis' library is missing. Swapping to Mock Fallback Mode.")
            self.use_mock = True
            return True

        try:
            logger.info(f"Attempting connection to Memurai/Redis at {self.host}:{self.port}...")
            
            # Setup pool with strict timeouts to prevent startup GUI lockup
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password if self.password else None,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
                decode_responses=False # Keep raw bytes standard
            )
            
            # Test ping
            client = redis.Redis(connection_pool=self.pool)
            if client.ping():
                logger.info("Successfully established connection to Redis/Memurai service.")
                self.use_mock = False
            else:
                raise ConnectionError("Redis ping did not return True")
                
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}. Gracefully falling back to Mock Mode.")
            self.use_mock = True
            if self.pool:
                try:
                    self.pool.disconnect()
                except Exception:
                    pass
                self.pool = None
                
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Redis Manager Service...")
        if self.pool:
            try:
                self.pool.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting Redis pool: {str(e)}")
            self.pool = None
        self.use_mock = True
        return True

    def get_client(self):
        """Returns a thread-safe connection to live Redis or the mock emulator client."""
        if self.use_mock:
            return self._mock_client
        return redis.Redis(connection_pool=self.pool)

    def is_live(self) -> bool:
        """Helper diagnostics to check if connecting to a real Redis server."""
        return not self.use_mock


# Auto-register RedisManager
ServiceRegistry.register("redis", RedisManager())
