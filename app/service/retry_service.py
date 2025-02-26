import logging
import asyncio
import time
import random
from typing import TypeVar

from sqlalchemy.exc import IntegrityError

from kiota_abstractions.api_error import APIError

from app.models.retries.retry_context import RetryContext
from app.models.retries.retry_enums import RetryProfile, RetryConfigurations



"""
SUMMARY:

This class is designed for allowing retries on any function logic. It has a 
dependency on the retry context, the model allowing this to function. 

It is designed with a catch all exception block to make it widely usable.
"""
T = TypeVar('T')

class RetryService:
    def __init__(self, retry_profile: RetryProfile = RetryProfile.STANDARD):
        config = RetryConfigurations.get_config(retry_profile)
        self.max_retries = config.max_retries
        self.retry_delay = config.base_delay
        self.max_timeout = config.max_timeout
        self.logger = logging.getLogger(__name__)




    def _calculate_delay(self, attempt: int) -> float:
        """Calculate the delay for the current retry attempt using exponential backoff with jitter."""
        delay = self.retry_delay * (2 ** attempt)
        jitter = delay * 0.1
        delay += random.uniform(-jitter, jitter) # nosec B311 # this is needed...we aren't using this for secrets, Gitlab CI will fail if not 
        return max(0, delay)  # Ensure delay is never negative




    async def retry_operation(self, context: RetryContext) -> T:
        """
        Generic retry mechanism with exponential backoff.
        
        Args:
            context (RetryContext): Configuration for the retry operation
            
        Returns:
            T: Result from the successful operation execution
            
        Raises:
            Exception: If operation fails after all retries
        """
        start_time = time.time()
        self.logger.info("Starting retry operation for %s", context.operation.__name__)
        abort_exceptions = [APIError, IntegrityError]
        if context.abort_on_exceptions:
            abort_exceptions.extend(context.abort_on_exceptions)
        context.abort_on_exceptions = abort_exceptions
        
        for attempt in range(self.max_retries):
            try:
                if self.max_timeout and time.time() - start_time > self.max_timeout:
                    self.logger.info("Operation exceeded maximum timeout of %s seconds", self.max_timeout)
                    raise TimeoutError(
                        f"Operation exceeded maximum timeout of {self.max_timeout} seconds"
                    )
                self.logger.info("Attempt %d of %d", attempt + 1, self.max_retries)
                result = await context.operation()
                self.logger.info("Operation %s completed successfully", context.operation.__name__)
                return result

            except Exception as e: # pylint: disable=W0718
                # Check if this exception type should abort retries
                if context.abort_on_exceptions and any(
                    isinstance(e, abort_type) for abort_type in context.abort_on_exceptions
                ):
                    self.logger.info(
                        "Aborting retries due to exception type %s: %s",
                        type(e).__name__, str(e)
                    )
                    if context.error_recorder:
                        context.error_recorder()
                    if context.custom_exception:
                        raise context.custom_exception(
                            detail=f"Operation aborted: {str(e)}",
                            status_code=409 if isinstance(e, IntegrityError) else 500
                        ) from e
                    raise e

                if context.metrics_recorder:
                    context.metrics_recorder()
                    
                if attempt == self.max_retries - 1:
                    if context.error_recorder:
                        context.error_recorder()
                    self.logger.error("%s: %s", context.error_msg, str(e))
                    if context.custom_exception:
                        raise context.custom_exception(
                            detail=f"Operation failed after {self.max_retries} attempts: {str(e)}",
                            status_code=500
                        ) from e
                    raise e
                    
                delay = self._calculate_delay(attempt)
                self.logger.warning(
                    "Attempt %d failed, retrying in %.2f seconds: %s",
                    attempt + 1, delay, str(e)
                )
                await asyncio.sleep(delay)