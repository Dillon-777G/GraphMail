from typing import Dict, List, Optional
import time
import logging
from dataclasses import dataclass

from app.models.email import Email

"""
SUMMARY:

Due to a time crunch and more inaccuracies in the Graph documentation,
I have elected to use a cache to reduce our dependencies on Graph API calls 
as much as possible. Batch calling was introducing more complexity then necessary
for this service and we already will have the data we need in the get response. 

If you want to try batching with the sdk, be prepared to dig your own grave.

"""

@dataclass
class CacheEntry:
    """Represents a cached folder's email contents"""
    emails: Dict[str, Email]  # Map of source_id to Email object
    timestamp: float
    folder_id: str

class EmailCacheService:
    """Service for caching email contents from folders"""
    
    def __init__(self, cache_ttl: int = 300):  # 5 minute default TTL
        self.cache: Dict[str, CacheEntry] = {}
        self.cache_ttl = cache_ttl
        self.logger = logging.getLogger(__name__)

    def store_folder_emails(self, folder_id: str, emails: List[Email]) -> None:
        """
        Store emails from a folder in the cache
        
        Args:
            folder_id: The ID of the folder
            emails: List of Email objects to cache
        """
        # Create a map of source_id to Email object for quick lookups
        email_map = {email.source_id: email for email in emails}
        
        self.cache[folder_id] = CacheEntry(
            emails=email_map,
            timestamp=time.time(),
            folder_id=folder_id
        )
        self.logger.info("Cached %d emails for folder %s", len(emails), folder_id)

    def get_emails_by_ids(self, folder_id: str, source_ids: List[str]) -> List[Email]:
        """
        Retrieve specific emails from the cache by their IDs
        
        Args:
            folder_id: The ID of the folder
            source_ids: List of source IDs to retrieve
            
        Returns:
            List[Email]: The requested emails that were found in cache
        """
        if not self._is_folder_cached(folder_id):
            self.logger.info("No cache entry found for folder %s", folder_id)
            return []
            
        cache_entry = self.cache[folder_id]
        found_emails = []
        
        for msg_id in source_ids:
            if msg_id in cache_entry.emails:
                found_emails.append(cache_entry.emails[msg_id])
            else:
                self.logger.warning("Message %s not found in cache for folder %s", msg_id, folder_id)
                
        return found_emails

    def clear_folder_cache(self, folder_id: str) -> None:
        """Clear the cache for a specific folder"""
        if folder_id in self.cache:
            del self.cache[folder_id]
            self.logger.info("Cleared cache for folder %s", folder_id)

    def clear_all_cache(self) -> None:
        """Clear the entire cache"""
        self.cache.clear()
        self.logger.info("Cleared all email cache")

    def _is_folder_cached(self, folder_id: str) -> bool:
        """
        Check if a folder's contents are cached and not expired
        
        Args:
            folder_id: The ID of the folder to check
            
        Returns:
            bool: True if the folder is cached and not expired
        """
        if folder_id not in self.cache:
            return False
            
        cache_entry = self.cache[folder_id]
        is_expired = time.time() - cache_entry.timestamp > self.cache_ttl
        
        if is_expired:
            self.clear_folder_cache(folder_id)
            return False
            
        return True

    def get_cache_info(self, folder_id: str) -> Optional[Dict]:
        """
        Get information about a folder's cache status
        
        Args:
            folder_id: The ID of the folder
            
        Returns:
            Optional[Dict]: Cache information if folder is cached
        """
        if not self._is_folder_cached(folder_id):
            return None
            
        cache_entry = self.cache[folder_id]
        return {
            "folder_id": folder_id,
            "email_count": len(cache_entry.emails),
            "cache_age": time.time() - cache_entry.timestamp,
            "cache_ttl": self.cache_ttl
        }