# Python standard library imports
import logging
from typing import Any, Dict

# Local imports
from .base_metrics import BaseMetrics


class PaginatedMetrics(BaseMetrics):
    """Metrics specifically for paginated email operations."""

    # Additional pagination-specific metrics
    current_page: int = 0
    items_per_page: int = 0
    total_pages: int = 0

    def get_progress_info(self) -> Dict[str, Any]:
        """Get progress information for paginated operations."""
        base_info = self.get_base_progress_info()
        base_info.update({
            "current_page": self.current_page,
            "total_pages": self.total_pages,
            "items_per_page": self.items_per_page
        })
        return base_info

    def log_final_metrics(self, logger: logging.Logger):
        """Log a final, clean summary for paginated operations."""
        separator = "-" * 40
        logger.info("\n%s", separator)
        logger.info("--- Paginated Email Metrics ---")
        logger.info("Total emails processed: %d", self.emails_processed if self.emails_processed else 0)
        logger.info("Total pages: %d", self.total_pages if self.total_pages else 0)
        logger.info("Current page: %d", self.current_page if self.current_page else 0)
        logger.info("Items per page: %d", self.items_per_page if self.items_per_page else 0)
        logger.info("Processing time: %.2f seconds", self.processing_time if self.processing_time else 0)
        logger.info("Current phase: %s", self.current_phase if self.current_phase else None)
        logger.info("%s\n", separator)