# Python standard library imports
import logging
import time
from typing import Any, Dict

# Third party imports
from pydantic import Field

# Local imports
from .base_metrics import BaseMetrics  # Assumes BaseMetrics provides any shared functionality

# pylint: disable=too-many-instance-attributes # This is a valid use case for this class
class BatchMetrics(BaseMetrics):
    """
    Metrics for batch operations including ID translation, pagination,
    and progress tracking for frontend updates.
    
    This class supports both:
      - A single final metrics log output (via log_final_metrics())
      - Frontend progress updates (via get_progress_info())
    """

    # Folder details
    folder_id: str = Field(default="None")
    
    # Counters and totals
    pages_fetched: int = Field(default=0)
    ids_translated: int = Field(default=0)
    emails_processed: int = Field(default=0)
    total_count: int = Field(default=0)  # Total number of emails to process
    
    # Timing fields
    translation_time: float = Field(default=0.0)
    processing_time: float = Field(default=0.0)
    start_time: float = Field(default_factory=time.time)
    
    # Internal start times (excluded from output)
    translation_start: float = Field(default=0.0, exclude=True)
    processing_start: float = Field(default=0.0, exclude=True)
    
    # Page details (single values instead of dictionaries)
    current_page_time: float = Field(default=0.0)
    current_page_items: int = Field(default=0)
    total_retries: int = Field(default=0)
    total_errors: int = Field(default=0)
    
    # Progress-tracking fields for frontend
    current_phase: str = Field(default="initializing")
    phase_progress: float = Field(default=0.0)
    
    # ---------------------- Timing Methods ---------------------- #
    def start_translation(self):
        self.translation_start = time.time()

    def end_translation(self):
        self.translation_time = time.time() - self.translation_start

    def start_processing(self):
        self.processing_start = time.time()

    def end_processing(self):
        self.processing_time = time.time() - self.processing_start

    # ---------------------- Page Metrics ---------------------- #
    def record_page_time(self, duration: float, items_count: int = 0):
        self.current_page_time = duration
        self.current_page_items = items_count

    def record_page_retry(self):
        self.total_retries = self.total_retries + 1

    def record_page_error(self):
        self.total_errors = self.total_errors + 1


    # ---------------------- Final Logging ---------------------- #
    def log_final_metrics(self, logger: logging.Logger):
        """
        Log a single, final summary of all metrics to the console.
        This output is kept concise.
        """
        total_time = time.time() - self.start_time
        separator = "-" * 40

        logger.info("\n\n%s", separator)
        logger.info("--- Final API Service Operation Metrics ---")
        logger.info("Folder ID: %s", self.folder_id)
        logger.info("Emails processed: %d (processing took %.2fs)",
                    self.emails_processed, self.processing_time)
        logger.info("IDs translated: %d (translation took %.2fs)",
                    self.ids_translated, self.translation_time)
        logger.info("Total time: %.2fs", total_time)
        logger.info("%s\n", separator)

    # ---------------------- Frontend Progress Methods ---------------------- #
    def calculate_overall_progress(self) -> float:
        """
        Calculate the overall progress as a percentage (0-100).
        The progress range is divided among the phases:
          - Fetching: up to 33%
          - Translating: 33%-66%
          - Processing: 66%-100%
        """
        if self.total_count == 0:
            return 0

        if self.current_phase == "fetching":
            # If available, use page_items from page 0; otherwise assume 0
            first_page_count = self.current_page_items
            return min(100 * (self.pages_fetched * first_page_count) / self.total_count, 33)
        if self.current_phase == "translating":
            base = 33
            translation_progress = (self.ids_translated / self.total_count) * 33
            return base + translation_progress
        if self.current_phase == "processing":
            base = 66
            processing_progress = (self.emails_processed / self.total_count) * 34
            return base + processing_progress
        return 0

    def get_progress_info(self) -> Dict[str, Any]:
        """
        Get the current progress information for frontend updates.
        This method returns a dictionary with key metrics.
        """
        return {
            "phase": self.current_phase,
            "progress": self.calculate_overall_progress(),
            "total_emails": self.total_count,
            "processed_emails": self.emails_processed,
            "pages_fetched": self.pages_fetched,
            "ids_translated": self.ids_translated
        }

    def set_phase(self, phase: str):
        """
        Update the current processing phase.
        Resets the phase progress.
        """
        self.current_phase = phase
        self.phase_progress = 0
