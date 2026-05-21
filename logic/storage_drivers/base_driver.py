# logic/storage_drivers/base_driver.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class ConcurrencyError(Exception):
    """
    Raised when an optimistic concurrency control (OCC) check fails.
    This indicates that the target row was modified by another writer
    between the time it was read and the attempted write-back.
    """
    pass

class BaseStorageDriver(ABC):
    """
    Abstract Base Class defining the required storage interface for the application.
    All pluggable database drivers (local SQLite, cloud libSQL/Turso, and PostgreSQL)
    must subclass this and implement these methods to ensure database-agnostic operations.
    """

    @abstractmethod
    def init_db(self) -> None:
        """
        Initializes the database schema (creates tables, indexes, and applies migrations).
        This must be safe to execute multiple times (idempotent).
        """
        pass

    @abstractmethod
    def save_conversation(self, conversation: list, title: str = "New Conversation", 
                          conv_id: int = None, model_id: str = "", 
                          messages_html: str = None, timestamp: str = None,
                          expected_version: int = None) -> Optional[int]:
        """
        Saves or updates a conversation thread in the database.
        
        Args:
            conversation (list): A list of dictionaries representing the chat messages.
            title (str): The display title of the conversation.
            conv_id (int): The unique database ID of the conversation if updating; None if creating a new one.
            model_id (str): The ID of the model used in the session.
            messages_html (str): Pre-rendered HTML cache of the conversation stream.
            timestamp (str): Optional. A pre-set timestamp representing when the conversation occurred (useful for imports/migrations).
            expected_version (int): Optional. The version number the caller expects the row to currently hold.
                If provided during an update (conv_id is not None), the driver will enforce an OCC check:
                the UPDATE will only succeed if the stored version matches expected_version.
                On success, the version is incremented atomically. On mismatch, ConcurrencyError is raised.

        Returns:
            Optional[int]: The database conversation ID (newly inserted or updated).

        Raises:
            ConcurrencyError: If expected_version is provided and the stored version does not match.
        """
        pass

    @abstractmethod
    def load_conversation(self, conv_id: int) -> Optional[dict]:
        """
        Loads a single conversation thread from the database by its ID.

        Args:
            conv_id (int): The unique database ID of the conversation.

        Returns:
            Optional[dict]: A dictionary containing conversation metadata and history:
                {
                    "id": int,
                    "title": str,
                    "timestamp": str,
                    "model_id": str,
                    "messages": list,
                    "messages_html": str,
                    "version": int
                }
                Returns None if not found.
        """
        pass

    @abstractmethod
    def get_all_conversations(self) -> List[tuple]:
        """
        Retrieves a lightweight summary list of all conversations, ordered by most recent.

        Returns:
            List[tuple]: A list of tuples containing metadata summary, typically:
                [(id, title, timestamp), ...]
        """
        pass

    @abstractmethod
    def delete_conversation(self, conv_id: int) -> None:
        """
        Deletes a specific conversation thread and all its history from the database by its ID.

        Args:
            conv_id (int): The unique database ID of the conversation.
        """
        pass

    @abstractmethod
    def clear_all(self) -> None:
        """
        Wipes all conversations from the database tables. Used for global cleanups.
        """
        pass
