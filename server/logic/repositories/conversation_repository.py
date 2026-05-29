# logic/repositories/conversation_repository.py
import logging
from typing import List, Dict, Any, Optional
from server.logic.services.base_service import ServiceRegistry

logger = logging.getLogger("QuantumConversationRepository")

class ConversationRepository:
    """
    6.1.3 Repository Pattern Isolation
    Completely decouples business logic from underlying storage drivers.
    Wraps the StorageService to provide pure domain interfaces for Conversation entities.
    """
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._storage_service = None

    @property
    def storage(self):
        if not self._storage_service:
            self._storage_service = ServiceRegistry.get("storage")
        return self._storage_service

    def save_conversation(self, conversation_data: List[Dict[str, Any]], title: str = "New Conversation",
                          conv_id: Optional[int] = None, model_id: str = "", messages_html: str = None) -> int:
        """
        Saves a conversation to the underlying storage.
        Handles Optimistic Concurrency Control silently inside the StorageService.
        """
        logger.debug(f"Repository saving conversation for tenant '{self.tenant_id}' (conv_id={conv_id})")
        return self.storage.save_conversation(
            tenant_id=self.tenant_id,
            conversation=conversation_data,
            title=title,
            conv_id=conv_id,
            model_id=model_id,
            messages_html=messages_html
        )

    def load_conversation(self, conv_id: int) -> Dict[str, Any]:
        """Loads a specific conversation by ID."""
        logger.debug(f"Repository loading conversation {conv_id} for tenant '{self.tenant_id}'")
        return self.storage.load_conversation(self.tenant_id, conv_id)

    def get_all_conversations(self) -> List[Dict[str, Any]]:
        """Returns a list of all conversations for the tenant."""
        return self.storage.get_all_conversations(self.tenant_id)

    def delete_conversation(self, conv_id: int) -> None:
        """Deletes a specific conversation by ID."""
        logger.debug(f"Repository deleting conversation {conv_id} for tenant '{self.tenant_id}'")
        self.storage.delete_conversation(self.tenant_id, conv_id)

    def clear_all(self) -> None:
        """Wipes all conversations for the tenant."""
        logger.warning(f"Repository clearing all conversations for tenant '{self.tenant_id}'")
        self.storage.clear_all(self.tenant_id)
