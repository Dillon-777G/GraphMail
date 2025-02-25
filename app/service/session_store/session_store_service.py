from typing import Dict, Optional
import time
from dataclasses import dataclass

@dataclass
class SessionData:
    order_id: str
    timestamp: float

class SessionStore:
    """Session store for managing order IDs across concurrent API requests"""
    
    def __init__(self, expiry_seconds: int = 300):  # 5 minute default expiry
        self._sessions: Dict[str, SessionData] = {}
        self._expiry_seconds = expiry_seconds
        
    def store_order_id(self, state: str, order_id: str) -> None:
        """Store order ID with state as key"""
        self._cleanup_expired()
        self._sessions[state] = SessionData(
            order_id=order_id,
            timestamp=time.time()
        )
            
    def get_order_id(self, state: str) -> Optional[str]:
        """Retrieve order ID for given state"""
        self._cleanup_expired()
        if state in self._sessions:
            return self._sessions[state].order_id
        return None
            
    def remove_session(self, state: str) -> None:
        """Remove a session after it's been used"""
        self._sessions.pop(state, None)
            
    def _cleanup_expired(self) -> None:
        """Remove expired sessions"""
        current_time = time.time()
        expired = [
            state for state, data in self._sessions.items()
            if current_time - data.timestamp > self._expiry_seconds
        ]
        for state in expired:
            self._sessions.pop(state)