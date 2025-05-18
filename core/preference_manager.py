"""
Module for managing user preferences.
"""
import json
import os
import uuid
from typing import Dict, Any, List
from pathlib import Path
from sentence_transformers import SentenceTransformer 
import faiss
import datetime
PREFERENCES_FILE = os.path.join("data", "preferences.json")
EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
_embedding_model = None

class PreferenceManager:
    def __init__(self, storage_path: str = PREFERENCES_FILE):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.preferences = self._load_preferences()

    
    def _load_preferences(self) -> List[Dict]:
        """Load preferences from storage."""
        if not self.storage_path.exists():
            return []
        try:
            with open(self.storage_path, 'r') as f:
                data = f.read().strip()
                if not data or data == '{}':
                    return []
                return json.loads(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def _save_preferences(self):
        """Save preferences to storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.preferences, f, indent=2)
            # Ensure file is actually written to disk
            f.flush()
            os.fsync(f.fileno())
    
    def add_preference(self, preference_text: str, source: str = "manual_chat") -> Dict[str, Any]:
        """
        Add a new preference.
        
        Args:
            preference_text: The text of the preference
            source: The source of the preference (e.g., "manual_chat", "extracted")
            
        Returns:
            Dict[str, Any]: The added preference with its ID
        """
        new_pref = {
            "text": preference_text,
            "source": source,
            "id": str(uuid.uuid4())
        }
        self.preferences.append(new_pref)
        self._save_preferences()
        return new_pref
    
    def get_preferences(self) -> List[Dict[str, Any]]:
        """Get all preferences."""
        return self.preferences
    
    def get_timestamp(self) -> str:
        """Generate a timestamp for preferences."""
        return datetime.datetime.now().isoformat()
    
    def get_preference_by_id(self, pref_id: str) -> Dict[str, Any]:
        """Get a specific preference by its ID."""
        for pref in self.preferences:
            if pref.get("id") == pref_id:
                return pref
        return None
    
    def delete_preference(self, pref_id: str) -> bool:
        """
        Delete a preference by its ID.
        
        Returns:
            bool: True if the preference was found and deleted, False otherwise
        """
        initial_length = len(self.preferences)
        self.preferences = [p for p in self.preferences if p.get("id") != pref_id]
        if len(self.preferences) < initial_length:
            self._save_preferences()
            return True
        return False 