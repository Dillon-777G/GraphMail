from dataclasses import dataclass
from typing import Optional, Callable, Type, Any, List

@dataclass
class RetryContext:
    """Model for retry operation configuration.
    
    Attributes:
        operation: Async function to execute with retry logic
        error_msg: Error message to log if all retries fail
        custom_exception: Custom exception to raise on final failure
        metrics_recorder: Optional function to record retry metrics
        error_recorder: Optional function to record error metrics
        abort_on_exceptions: Optional list of Exceptions that allows for aborting retries 
        on specific exceptions 
    """
    operation: Callable[[], Any]
    error_msg: str
    custom_exception: Type[Exception] = None
    metrics_recorder: Optional[Callable[[], None]] = None
    error_recorder: Optional[Callable[[], None]] = None 
    abort_on_exceptions: Optional[List[Type[Exception]]] = None 