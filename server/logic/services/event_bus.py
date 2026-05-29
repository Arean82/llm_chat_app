# logic/services/event_bus.py

import json
import logging
import threading
from .base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumEventBus")

class EventBusService(BaseService):
    """
    Decoupled Pub/Sub event bus service mapping to Redis Pub/Sub,
    with automatic fallbacks for local thread-safe operation.
    """
    def __init__(self):
        super().__init__()
        self.redis_svc = None
        self.client = None
        self.pubsub = None
        self._subscribers = {} # { channel_str: set(callback_funcs) }
        self._lock = threading.Lock()
        self._listener_thread = None
        self._stop_event = threading.Event()

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Event Bus Service...")
        self._stop_event.clear()
        
        try:
            # Fetch the registered Redis manager
            self.redis_svc = ServiceRegistry.get("redis")
            self.client = self.redis_svc.get_client()
            
            # Setup a pubsub listener client
            self.pubsub = self.client.pubsub()
            
            # Start background thread to listen to messages
            self._listener_thread = threading.Thread(
                target=self._listen_loop,
                name="QuantumEventBusListener",
                daemon=True
            )
            self._listener_thread.start()
            logger.info("Event Bus message listener thread spawned successfully.")
            
        except Exception as e:
            logger.error(f"Event Bus initialization failed: {str(e)}")
            return False
            
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Event Bus Service...")
        self._stop_event.set()
        
        # Unsubscribe all
        if self.pubsub:
            try:
                self.pubsub.close()
            except Exception:
                pass
            self.pubsub = None
            
        # Clean local callbacks
        with self._lock:
            self._subscribers.clear()
            
        self.client = None
        self.redis_svc = None
        return True

    def publish(self, channel: str, payload: dict) -> bool:
        """
        Broadcasting an event message asynchronously.
        Accepts any JSON-serializable dictionary.
        """
        if not self.is_initialized or not self.client:
            logger.warning("Event Bus not initialized. Unable to publish message.")
            return False
            
        try:
            payload_str = json.dumps(payload)
            logger.debug(f"Broadcasting event on '{channel}': {payload_str}")
            self.client.publish(channel, payload_str)
            return True
        except Exception as e:
            logger.error(f"Failed to publish event on channel '{channel}': {str(e)}")
            return False

    def subscribe(self, channel: str, callback: callable) -> None:
        """
        Subscribes a callback callable to a channel.
        Triggered when messages are received on the target channel.
        """
        if not callback:
            return
            
        channel_str = str(channel)
        with self._lock:
            if channel_str not in self._subscribers:
                self._subscribers[channel_str] = set()
                # Issue subscribe command to Redis/Mock backend
                if self.pubsub:
                    try:
                        self.pubsub.subscribe(channel_str)
                    except Exception as e:
                        logger.error(f"Failed subscribing to Redis channel '{channel_str}': {str(e)}")
            
            self._subscribers[channel_str].add(callback)
            logger.info(f"Subscribed callback to channel '{channel_str}'. Total: {len(self._subscribers[channel_str])}")

    def unsubscribe(self, channel: str, callback: callable) -> None:
        """Unsubscribes a callback from a channel."""
        channel_str = str(channel)
        with self._lock:
            if channel_str in self._subscribers and callback in self._subscribers[channel_str]:
                self._subscribers[channel_str].remove(callback)
                logger.info(f"Unsubscribed callback from channel '{channel_str}'. Remaining: {len(self._subscribers[channel_str])}")
                
                # If no more subscribers, unsubscribe from backend to save bandwidth
                if not self._subscribers[channel_str]:
                    self._subscribers.pop(channel_str)
                    if self.pubsub:
                        try:
                            self.pubsub.unsubscribe(channel_str)
                        except Exception as e:
                            logger.error(f"Failed unsubscribing from Redis channel '{channel_str}': {str(e)}")

    def _listen_loop(self):
        """Background loop reading from pubsub stream and dispatching events to local callbacks."""
        logger.info("Event Bus listener loop started.")
        
        while not self._stop_event.is_set():
            if not self.pubsub:
                time.sleep(0.5)
                continue
                
            try:
                # Read messages blocking
                for message in self.pubsub.listen():
                    if self._stop_event.is_set():
                        break
                        
                    if not message or message.get('type') != 'message':
                        continue
                        
                    channel = message.get('channel')
                    data = message.get('data')
                    
                    if not channel or not data:
                        continue
                        
                    # Decode from bytes if needed
                    channel_str = channel.decode('utf-8') if isinstance(channel, bytes) else str(channel)
                    data_str = data.decode('utf-8') if isinstance(data, bytes) else str(data)
                    
                    try:
                        payload = json.loads(data_str)
                    except json.JSONDecodeError:
                        payload = {"raw_data": data_str}
                        
                    self._dispatch_event(channel_str, payload)
                    
            except Exception as e:
                # Catch closed pubsub or socket disconnects and wait for service recovery
                if not self._stop_event.is_set():
                    logger.debug(f"Event Bus loop read encountered temporary halt: {str(e)}. Re-establishing in 2 seconds...")
                    time.sleep(2.0)
                    
                    # Refresh references if redis recovered
                    if self.redis_svc:
                        try:
                            self.client = self.redis_svc.get_client()
                            self.pubsub = self.client.pubsub()
                            # Re-subscribe to existing keys
                            with self._lock:
                                for ch in self._subscribers.keys():
                                    self.pubsub.subscribe(ch)
                        except Exception:
                            pass
                            
        logger.info("Event Bus listener loop terminated cleanly.")

    def _dispatch_event(self, channel: str, payload: dict):
        """Thread-safe routing to subscribers."""
        callbacks_to_fire = []
        with self._lock:
            subscribers = self._subscribers.get(channel, set())
            callbacks_to_fire = list(subscribers)
            
        if not callbacks_to_fire:
            return
            
        logger.debug(f"Dispatching event on '{channel}' to {len(callbacks_to_fire)} subscribers.")
        for cb in callbacks_to_fire:
            try:
                cb(payload)
            except Exception as e:
                logger.error(f"Error firing callback for channel '{channel}': {str(e)}")


# Auto-register EventBusService
ServiceRegistry.register("event_bus", EventBusService())
