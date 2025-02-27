from typing import Optional
import logging
from .base_metrics import BaseMetrics

class AttachmentMetrics(BaseMetrics):
    """Metrics for attachment operations, focusing on download performance."""
    
    attachment_id: Optional[str] = None
    folder_id: str = ""
    message_id: str = ""
    download_time: Optional[float] = None  # Single duration value
    download_size: Optional[int] = None    # Single size value
    attachments_processed: Optional[int] = None
    retry_count: int = 0                   # Single retry counter
    last_error: Optional[str] = None       # Track last error message
    failure_count: int = 0                 # Track number of failures

    def record_download(self, size: int):
        """Record metrics for a successful download."""
        self.download_size = size

    def record_download_failure(self, error_message: str):
        """Record metrics for a failed download attempt."""
        self.last_error = error_message
        self.failure_count += 1

    def record_retry(self):
        """Record a retry attempt."""
        self.retry_count += 1

    def log_metrics_fetch(self, logger: logging.Logger):
        """Log fetch metrics for attachments in a clean, delimited block."""
        separator = "-" * 40
        logger.info("\n%s", separator)
        logger.info("--- Fetch Attachments Metrics ---")
        logger.info("Total time: %.2fs", self.processing_time)
        logger.info("Attachments processed: %d", self.attachments_processed)
        logger.info("Current phase: %s", self.current_phase)
        logger.info("%s\n", separator)

    def log_metrics_download(self, logger: logging.Logger):
        """Log download metrics for attachments in a clean, delimited block."""
        separator = "-" * 40
        
        # Add null check for download_size
        total_mb = 0
        avg_speed = 0
        if self.download_size is not None:
            total_mb = self.download_size / (1024 * 1024)
            avg_speed = total_mb / self.processing_time if self.processing_time > 0 else 0
        
        total_retries = self.retry_count
        logger.info("\n%s", separator)
        logger.info("--- Attachment Download Metrics ---")
        logger.info("Folder ID: %s", self.folder_id)
        logger.info("Message ID: %s", self.message_id)
        logger.info("Attachment ID: %s", self.attachment_id)
        logger.info("Total size: %.2f MB", total_mb)
        logger.info("Average speed: %.2f MB/s", avg_speed)
        logger.info("Retries: %d", total_retries)
        if self.failure_count > 0:
            logger.info("Failures: %d", self.failure_count)
            if self.last_error:
                logger.info("Last error: %s", self.last_error)
        logger.info("Total time: %.2fs", self.processing_time)
        logger.info("Current phase: %s", self.current_phase)
        logger.info("%s\n\n", separator)
