import logging

logger = logging.getLogger("QuantumServices")

class BaseService:
    """
    Abstract base service for all Synora Studio SaaS and Desktop background services.
    Enforces standardized initialization and shutdown lifecycles.
    """
    def __init__(self):
        self.is_initialized = False

    def initialize(self) -> bool:
        """Initialize resources, connections, or state."""
        if self.is_initialized:
            return True
        try:
            success = self.on_initialize()
            self.is_initialized = success
            return success
        except Exception as e:
            logger.error(f"Failed to initialize service {self.__class__.__name__}: {str(e)}")
            return False

    def shutdown(self) -> bool:
        """Gracefully release database connections, threads, or open file pointers."""
        if not self.is_initialized:
            return True
        try:
            success = self.on_shutdown()
            if success:
                self.is_initialized = False
            return success
        except Exception as e:
            logger.error(f"Failed to gracefully shutdown service {self.__class__.__name__}: {str(e)}")
            return False

    def on_initialize(self) -> bool:
        """Override in subclasses to perform specific initialization logic."""
        return True

    def on_shutdown(self) -> bool:
        """Override in subclasses to perform specific cleanup logic."""
        return True


class ServiceRegistry:
    """
    Thread-safe global service locator registry.
    Prevents circular imports between highly interdependent services (e.g. RAG, Storage, and Cache).
    """
    _instance = None
    _services = {}

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ServiceRegistry, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    def register(cls, name: str, service: BaseService) -> None:
        """Register a service instance."""
        cls._services[name] = service
        logger.info(f"Registered service: '{name}' ({service.__class__.__name__})")

    @classmethod
    def get(cls, name: str) -> BaseService:
        """Retrieve a registered service instance."""
        service = cls._services.get(name)
        if not service:
            raise KeyError(f"Service '{name}' has not been registered in the ServiceRegistry.")
        return service

    @classmethod
    def initialize_all(cls) -> bool:
        """Initialize all registered services in order."""
        success = True
        logger.info("Initializing all registered services in ServiceRegistry...")
        for name, service in cls._services.items():
            logger.info(f"Initializing service '{name}'...")
            if not service.initialize():
                logger.error(f"Failed to initialize service '{name}'")
                success = False
        return success

    @classmethod
    def shutdown_all(cls) -> bool:
        """Shutdown all registered services in order."""
        success = True
        logger.info("Shutting down all registered services in ServiceRegistry...")
        for name, service in list(cls._services.items()):
            logger.info(f"Shutting down service '{name}'...")
            if not service.shutdown():
                logger.error(f"Failed to shutdown service '{name}'")
                success = False
        return success

    @classmethod
    def clear(cls) -> None:
        """Clear all registered services."""
        cls._services.clear()

