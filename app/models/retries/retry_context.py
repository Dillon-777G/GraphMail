# Python standard library imports
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Type

@dataclass
class RetryContext:
    """Model for retry operation configuration.
    
    Attributes:
        operation: Async function to execute with retry logic
        error_msg: Error message to log if all retries fail
        metrics_recorder: Optional function to record retry metrics
        error_recorder: Optional function to record error metrics
        abort_on_exceptions: Optional list of Exceptions that allows for aborting retries 
        on specific exceptions 
    """
    operation: Callable[[], Any]
    error_msg: str
    metrics_recorder: Optional[Callable[[], None]] = None
    error_recorder: Optional[Callable[[], None]] = None 
    abort_on_exceptions: Optional[List[Type[Exception]]] = None 