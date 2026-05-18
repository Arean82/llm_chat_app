# logic/storage_drivers/base_driver.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

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
                          messages_html: str = None, timestamp: str = None) -> Optional[int]:
        """
        Saves or updates a conversation thread in the database.
        
        Args:
            conversation (list): A list of dictionaries representing the chat messages.
            title (str): The display title of the conversation.
            conv_id (int): The unique database ID of the conversation if updating; None if creating a new one.
            model_id (str): The ID of the model used in the session.
            messages_html (str): Pre-rendered HTML cache of the conversation stream.
            timestamp (str): Optional. A pre-set timestamp representing when the conversation occurred (useful for imports/migrations).

        Returns:
            Optional[int]: The database conversation ID (newly inserted or updated).
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
                    "messages_html": str
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
