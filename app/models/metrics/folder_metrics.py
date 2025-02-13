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
    
    # Track last failure instead of a dictionary
    last_failed_folder_id: Optional[str] = None
    last_error_message: Optional[str] = None
    failure_count: int = 0
    
    def record_retrieval(self, child_folder_count: int) -> None:
        """Record metrics for a successful folder retrieval."""
        self.successful_retrievals += 1
        self.child_folder_count = child_folder_count

    def record_retrieval_failure(self, folder_id: str, error: str) -> None:
        """Record a failed folder retrieval."""
        self.last_failed_folder_id = folder_id
        self.last_error_message = error
        self.failure_count += 1

    def log_metrics_retrieval(self, logger: logging.Logger, operation: str, folder_id: str = "root") -> None:
        """Log the folder retrieval metrics in a clean, delimited block."""
        separator = "-" * 40
        logger.info("\n%s", separator)
        logger.info("--- %s Metrics for folder '%s' ---", operation, folder_id)
        logger.info("Processing time: %.2f seconds", self.processing_time)
        logger.info("Child folders found: %d", self.child_folder_count)
        logger.info("Failures: %d", self.failure_count)
        logger.info("Current phase: %s", self.current_phase)
        if self.last_failed_folder_id:
            logger.info("Last failure: folder '%s' - %s", 
                       self.last_failed_folder_id, self.last_error_message)
        logger.info("%s\n", separator)
