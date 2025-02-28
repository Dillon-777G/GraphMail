# Python standard library imports
import os
from typing import Dict

# Third party imports
from dotenv import load_dotenv

class EnvironmentConfig:
    """Centralized environment configuration for the application."""
    
    _config: Dict[str, str] = {}
    
    @classmethod
    def load_environment(cls) -> None:
        """
        Load and validate all environment variables at startup.
        
        Raises:
            ValueError: If required environment variables are missing
            FileNotFoundError: If .env file is not found
        """
        if not load_dotenv():
            raise FileNotFoundError("Error: .env file not found or failed to load.")
            
        # Database Configuration
        db_config = {
            "DB_USER": os.getenv("DB_USER"),
            "DB_PASSWORD": os.getenv("DB_PASSWORD"),
            "DB_HOST": os.getenv("DB_HOST_DOCKER") if cls._is_running_in_docker() else os.getenv("DB_HOST"),
            "DB_PORT": os.getenv("DB_PORT"),
            "DB_NAME": os.getenv("DB_NAME")
        }
        
        # Attachment Configuration
        attachment_config = {
            "ATTACHMENT_FILE_SYSTEM_PATH": os.getenv("ATTACHMENT_FILE_SYSTEM_PATH"),
            "TEST_ATTACHMENT_FILE_SYSTEM_PATH": os.getenv("TEST_ATTACHMENT_FILE_SYSTEM_PATH")
        }
        
        # Validate all required variables are present
        missing_vars = [key for key, value in {**db_config, **attachment_config}.items() if value is None]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        cls._config = {**db_config, **attachment_config}
    
    @classmethod
    def get(cls, key: str) -> str:
        """Get a configuration value."""
        if not cls._config:
            raise RuntimeError("Environment not loaded. Call load_environment() first.")
        return cls._config[key]
    
    @staticmethod
    def _is_running_in_docker() -> bool:
        """Check if the application is running in a Docker container."""
        try:
            with open("/proc/1/cgroup", "rt", encoding="utf-8") as f:
                return "docker" in f.read()
        except FileNotFoundError:
            return False 