from typing import Optional
import logging
from app.models.metrics.base_metrics import BaseMetrics

class FolderMetrics(BaseMetrics):
    """Metrics for folder operations."""
    
    # Track retrieval counts and timing info
    successful_retrievals: int = 0
    processing_start: float = 0
    processing_time: float = 0
    child_folder_count: int = 0
    folder_display_name: str = "None"
    folder_id: str = "None"
    parent_folder_id: str = "None"
    
    # Track last failure instead of a dictionary
    last_failed_folder_id: Optional[str] = None
    last_error_message: Optional[str] = None
    failure_count: int = 0
    
    def record_retrieval(self, child_folder_count: int = 0,
                         folder_id: str = "None",
                          parent_folder_id: str = "None",
                           folder_display_name: str = "None") -> None:
        """Record metrics for a successful folder retrieval."""
        self.successful_retrievals += 1
        self.child_folder_count = child_folder_count
        self.folder_id = folder_id
        self.folder_display_name = folder_display_name
        self.parent_folder_id = parent_folder_id

    def record_retrieval_failure(self, folder_id: str, error: str) -> None:
        """Record a failed folder retrieval."""
        self.last_failed_folder_id = folder_id
        self.last_error_message = error
        self.failure_count += 1

    def log_metrics_retrieval(self, logger: logging.Logger, operation: str) -> None:
        """Log the folder retrieval metrics in a clean, delimited block."""
        separator = "-" * 40
        logger.info("\n\n%s", separator)
        logger.info("--- %s Metrics for folder '%s' ---", operation, self.folder_display_name)
        logger.info("Processing time: %.2f seconds", self.processing_time if self.processing_time else 0)
        logger.info("Folder ID: %s", self.folder_id if self.folder_id else "None")
        logger.info("Parent folder ID: %s", self.parent_folder_id if self.parent_folder_id else "None")
        logger.info("Child folders found: %d", self.child_folder_count if self.child_folder_count else 0)
        logger.info("Failures: %d", self.failure_count if self.failure_count else 0)
        logger.info("Current phase: %s", self.current_phase if self.current_phase else "None")
        if self.last_failed_folder_id:
            logger.info("Last failure: folder '%s' - %s", 
                       self.last_failed_folder_id, self.last_error_message)
        logger.info("%s\n", separator)
