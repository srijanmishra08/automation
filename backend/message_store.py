"""
Message Store - Stores incoming WhatsApp messages for logging and analysis
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class MessageStore:
    """
    Simple file-based message storage
    In production, use a proper database
    """
    
    def __init__(self, store_path: str = "../data/messages.json"):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.store_path.exists():
            self._save_messages([])
    
    def store_message(
        self,
        sender: str,
        content: str,
        message_type: str = "text",
        metadata: dict = None
    ) -> dict:
        """
        Store a new message
        """
        message = {
            "id": str(uuid.uuid4()),
            "sender": sender,
            "content": content,
            "type": message_type,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        messages = self._load_messages()
        messages.append(message)
        
        # Keep only last 1000 messages
        if len(messages) > 1000:
            messages = messages[-1000:]
        
        self._save_messages(messages)
        return message
    
    def get_messages(
        self,
        sender: str = None,
        limit: int = 50,
        since: str = None
    ) -> list[dict]:
        """
        Get stored messages with optional filtering
        """
        messages = self._load_messages()
        
        # Filter by sender
        if sender:
            messages = [m for m in messages if m["sender"] == sender]
        
        # Filter by timestamp
        if since:
            messages = [m for m in messages if m["timestamp"] > since]
        
        # Sort by timestamp descending
        messages.sort(key=lambda m: m["timestamp"], reverse=True)
        
        # Apply limit
        return messages[:limit]
    
    def get_conversation(self, sender: str, limit: int = 20) -> list[dict]:
        """
        Get conversation history for a specific sender
        """
        return self.get_messages(sender=sender, limit=limit)
    
    def _load_messages(self) -> list[dict]:
        """Load messages from file"""
        try:
            with open(self.store_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_messages(self, messages: list[dict]):
        """Save messages to file"""
        with open(self.store_path, "w") as f:
            json.dump(messages, f, indent=2)
