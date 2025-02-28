# Python standard library imports
from typing import Dict, Optional
import logging
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
        self.logger = logging.getLogger(__name__)

    def store_order_id(self, state: str, order_id: str) -> None:
        """Store order ID with state as key"""
        self.logger.info("Storing order ID: %s for state: %s", order_id, state)
        self._cleanup_expired()
        self._sessions[state] = SessionData(
            order_id=order_id,
            timestamp=time.time()
        )
            
    def get_order_id(self, state: str) -> Optional[str]:
        """Retrieve order ID for given state"""
        self.logger.info("Getting order ID for state: %s", state)
        self._cleanup_expired()
        if state in self._sessions:
            self.logger.info("Order ID found for state: %s", state)
            return self._sessions[state].order_id
        self.logger.info("No order ID found for state: %s", state)
        return None
            
    def remove_session(self, state: str) -> None:
        """Remove a session after it's been used"""
        self.logger.info("Removing session for state: %s", state)
        self._sessions.pop(state, None)
            
    def _cleanup_expired(self) -> None:
        """Remove expired sessions"""
        self.logger.info("Cleaning up expired sessions")
        current_time = time.time()
        expired = [
            state for state, data in self._sessions.items()
            if current_time - data.timestamp > self._expiry_seconds
        ]
        for state in expired:
            self.logger.info("Removing expired session for state: %s", state)
            self._sessions.pop(state)