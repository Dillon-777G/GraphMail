from typing import Optional
import logging
from .base_metrics import BaseMetrics

class AttachmentMetrics(BaseMetrics):
    """Metrics for attachment operations, focusing on download performance."""
    
    attachments_processed: int = 0
    total_bytes_downloaded: int = 0
    folder_id: str = ""
    message_id: str = ""
    download_time: Optional[float] = None  # Single duration value
    download_size: Optional[int] = None    # Single size value
    retry_count: int = 0                   # Single retry counter

    def record_download(self, size: int):
        """Record metrics for a successful download."""
        self.download_size = size
        self.total_bytes_downloaded += size
        self.attachments_processed += 1

    def record_retry(self):
        """Record a retry attempt."""
        self.retry_count += 1

    def record_fetch(self, attachment_count: int):
        """Record metrics for fetching attachments from a message."""
        self.attachments_processed = attachment_count

    def log_metrics_fetch(self, logger: logging.Logger):
        """Log fetch metrics for attachments in a clean, delimited block."""
        separator = "-" * 40
        logger.info("\n%s", separator)
        logger.info("--- Fetch Attachments Metrics ---")
        logger.info("Attachments fetched: %d", self.attachments_processed)
        logger.info("Total time: %.2fs", self.processing_time)
        logger.info("Current phase: %s", self.current_phase)
        logger.info("%s\n", separator)

    def log_metrics_download(self, logger: logging.Logger):
        """Log download metrics for attachments in a clean, delimited block."""
        separator = "-" * 40
        total_mb = self.total_bytes_downloaded / (1024 * 1024)
        avg_speed = total_mb / self.processing_time if self.processing_time > 0 else 0
        total_retries = self.retry_count
        logger.info("\n%s", separator)
        logger.info("--- Attachment Download Metrics ---")
        logger.info("Folder ID: %s", self.folder_id)
        logger.info("Message ID: %s", self.message_id)
        logger.info("Attachments processed: %d", self.attachments_processed)
        logger.info("Total size: %.2f MB", total_mb)
        logger.info("Average speed: %.2f MB/s", avg_speed)
        logger.info("Retries: %d", total_retries)
        logger.info("Total time: %.2fs", self.processing_time)
        logger.info("Current phase: %s", self.current_phase)
        logger.info("%s\n", separator)
