# Python standard library imports
import logging
import time
from typing import Any, Dict

# Third party imports
from pydantic import BaseModel, Field

class BaseMetrics(BaseModel):
    """Base metrics class with common functionality."""
    
    emails_processed: int = 0
    start_time: float = Field(default_factory=time.time)
    processing_time: float = 0
    total_count: int = 0
    current_phase: str = "initializing"
    phase_progress: float = 0
    _processing_start: float = 0

    def start_processing(self):
        self._processing_start = time.time()

    def end_processing(self):
        self.processing_time = time.time() - self._processing_start

    def get_base_progress_info(self) -> Dict[str, Any]:
        """Get basic progress information common to all metric types."""
        return {
            "phase": self.current_phase,
            "total_emails": self.total_count,
            "processed_emails": self.emails_processed,
        }

    def log_base_metrics(self, logger: logging.Logger):
        """Log basic metrics common to all operations."""
        total_time = time.time() - self.start_time
        logger.info(
            "Performance Summary:\n"
            "  emails_processed=%d (took %.2fs)\n"
            "  total_time=%.2fs",
            self.emails_processed, self.processing_time, total_time
        )
