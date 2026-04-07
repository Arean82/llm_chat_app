# logic/conversation_manager.py
# ConversationManager is responsible for saving and loading conversations to/from JSON files. It creates a directory for conversations if it doesn't exist and provides methods to save a conversation with a timestamped filename or load a conversation from a specified file path. 

import json
from datetime import datetime
from pathlib import Path


class ConversationManager:
    def __init__(self):
        self.conversations_dir = Path.home() / "LLMChatApp" / "conversations"
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
    def save_conversation(self, conversation: list, file_path: str = None):
        if file_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.conversations_dir / f"conversation_{timestamp}.json"
        else:
            file_path = Path(file_path)
            
        data = {
            "timestamp": datetime.now().isoformat(),
            "messages": conversation
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(file_path)
        
    def load_conversation(self, file_path: str) -> list:
        file_path = Path(file_path)
        if not file_path.exists():
            return []
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("messages", [])