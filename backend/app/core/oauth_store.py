"""
OAuth session storage for state, nonce, and PKCE parameters.
In production, this should be replaced with Redis or similar persistent storage.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import threading
import time

from ..core.logging import get_logger

logger = get_logger(__name__)

class OAuthSessionStore:
    """In-memory store for OAuth session data."""
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()
    
    def store_session(self, session_id: str, data: Dict[str, Any], expires_in_seconds: int = 600) -> None:
        """Store OAuth session data with expiration."""
        with self._lock:
            self._store[session_id] = {
                **data,
                "expires_at": datetime.utcnow() + timedelta(seconds=expires_in_seconds)
            }
            self._cleanup_expired()
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve OAuth session data."""
        with self._lock:
            self._cleanup_expired()
            
            if session_id not in self._store:
                return None
            
            session_data = self._store[session_id]
            
            # Check if expired
            if datetime.utcnow() > session_data["expires_at"]:
                del self._store[session_id]
                return None
            
            return session_data
    
    def delete_session(self, session_id: str) -> bool:
        """Delete OAuth session data."""
        with self._lock:
            if session_id in self._store:
                del self._store[session_id]
                return True
            return False
    
    def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        self._last_cleanup = current_time
        now = datetime.utcnow()
        expired_keys = [
            key for key, data in self._store.items()
            if now > data["expires_at"]
        ]
        
        for key in expired_keys:
            del self._store[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired OAuth sessions")

# Global instance
oauth_store = OAuthSessionStore()
