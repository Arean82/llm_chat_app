# logic/services/security_service.py

import logging
from .base_service import BaseService, ServiceRegistry

logger = logging.getLogger("QuantumSecurityService")

class SecurityService(BaseService):
    """
    Decoupled Security Management Service.
    Enforces Role-Based Access Controls (RBAC) and coordinates structured Audit Logging.
    """
    def __init__(self):
        super().__init__()

    def on_initialize(self) -> bool:
        logger.info("Initializing Quantum Security Service...")
        return True

    def on_shutdown(self) -> bool:
        logger.info("Shutting down Quantum Security Service...")
        return True

    def check_permission(self, user: dict, required_role: str) -> bool:
        """
        Validates whether the user's role parameters permit access.
        - user: dict representation of the user context.
        - required_role: "admin" or "user".
        """
        if not user or not isinstance(user, dict):
            return False

        status = user.get("status", "inactive")
        if status != "active":
            logger.warning(f"Access denied: User '{user.get('username')}' status is '{status}' (expected 'active')")
            return False

        key_type = user.get("key_type", "byok")

        if required_role == "admin":
            # admin role requires admin_funded key type
            return key_type == "admin_funded"
        elif required_role == "user":
            # standard user requires active account
            return True

        logger.warning(f"Access denied: Unknown required role '{required_role}'")
        return False

    def log_audit(self, user_id: str, action: str, details: str, status: str) -> None:
        """
        Writes a structured security log event to the standard logger for observability.
        - user_id: String or integer ID of the tenant.
        - action: HTTP endpoint, process invocation, or system event name.
        - details: Description of the action parameters or error.
        - status: "SUCCESS", "FAILED", or "SUSPICIOUS".
        """
        event_dict = {
            "user_id": str(user_id) if user_id else "anonymous",
            "action": action,
            "details": details,
            "status": status
        }
        log_msg = f"[AUDIT] [Status: {status}] User: {event_dict['user_id']} | Action: {action} | Details: {details}"
        
        if status == "FAILED":
            logger.warning(log_msg)
        elif status == "SUSPICIOUS":
            logger.error(log_msg)
        else:
            logger.info(log_msg)

# Auto-register SecurityService
ServiceRegistry.register("security", SecurityService())
