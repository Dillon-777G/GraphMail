from enum import Enum
from dataclasses import dataclass
from typing import Optional

class RetryProfile(Enum):
    """Predefined retry profiles for different types of operations"""
    
    # Quick retries for time-sensitive operations
    FAST = "FAST"
    
    # Standard profile for most operations
    STANDARD = "STANDARD"

    # More patient retries for batch operations
    BATCH = "BATCH"
    
    # Aggressive retries for critical operations
    CRITICAL = "CRITICAL"

@dataclass
class RetryConfig:
    """Configuration parameters for retry behavior"""
    max_retries: int
    base_delay: int  # in seconds
    max_timeout: Optional[int] = None  # in seconds

class RetryConfigurations:
    """
    Centralized configurations for retry behavior across services.
    These can be adjusted based on operational requirements.
    """
    
    PROFILES = {
        RetryProfile.FAST: RetryConfig(
            # FAST Profile - Optimized for user-facing, single-item operations
            # Examples: Fetching a single attachment, getting a single folder
            #
            # max_retries=2:
            # - Minimizes user wait time while still providing resilience
            # - Total retry attempts (1 initial + 2 retries = 3 attempts)
            # - With base_delay=1: Retries at ~1s and ~2s after initial attempt
            #
            # base_delay=1:
            # - Quick first retry to handle momentary glitches
            # - Short enough that user might not notice the delay
            # - Exponential backoff gives delays of 1s, then 2s
            #
            # max_timeout=5:
            # - 5 seconds is generally accepted maximum for good UX
            # - Allows for initial attempt plus both retries within UX threshold
            # - Fails fast if operation isn't succeeding quickly
            max_retries=2,
            base_delay=1,
            max_timeout=5
        ),
        
        RetryProfile.STANDARD: RetryConfig(
            # STANDARD Profile - Balanced approach for routine operations
            # Examples: Listing folders, fetching email metadata
            #
            # max_retries=3:
            # - More resilient than FAST (1 initial + 3 retries = 4 attempts)
            # - Balanced between reliability and responsiveness
            # - Sufficient for most transient failures and brief service hiccups
            #
            # base_delay=2:
            # - Longer initial delay allows temporary issues to resolve
            # - With exponential backoff: 2s, 4s, 8s between retries
            # - Total potential retry time ~14s before timeout
            #
            # max_timeout=30:
            # - 30 seconds covers full retry cycle plus overhead
            # - Standard timeout for most web operations
            # - Allows for reasonable API latency and processing time
            max_retries=3,
            base_delay=2,
            max_timeout=30
        ),
        
        RetryProfile.BATCH: RetryConfig(
            # BATCH Profile - Designed for long-running, multi-item operations
            # Examples: Email batch processing
            #
            # max_retries=5:
            # - Maximum resilience (1 initial + 5 retries = 6 attempts)
            # - Crucial for operations processing large amounts of data
            # - Handles intermittent failures in longer-running operations
            #
            # base_delay=3:
            # - Longer delays between attempts for rate limiting and throttling
            # - With exponential backoff: 3s, 9s, 27s, 81s, 243s between retries
            # - Allows API quotas to reset between attempts
            #
            # max_timeout=300:
            # - 5 minutes total allowed for completion
            # - Accommodates large data sets and API throttling
            # - Matches Microsoft Graph API's typical timeout for batch operations
            # - Allows for multiple retry cycles even with longer backoff periods
            max_retries=5,
            base_delay=3,
            max_timeout=300
        )
    }
    @classmethod
    def get_config(cls, profile: RetryProfile) -> RetryConfig:
        """Get retry configuration for a specific profile"""
        return cls.PROFILES[profile]

    @classmethod
    def get_default_config(cls) -> RetryConfig:
        """Get the standard retry configuration"""
        return cls.PROFILES[RetryProfile.STANDARD]