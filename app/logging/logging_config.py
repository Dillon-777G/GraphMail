# Python standard library imports
import logging
import logging.config
import os
import yaml


def setup_logging():
    """
    Setup logging configuration from the logging.yaml file
    """
    try:
        path = os.path.join(os.path.dirname(__file__), 'logging.yaml')
        
        if os.path.exists(path):
            with open(path, 'rt', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Ensure logs directory exists
            os.makedirs('logs', exist_ok=True)
            
            # Apply the config
            logging.config.dictConfig(config)
            
            # Test the logger
            logger = logging.getLogger(__name__)
            logger.info("Logging system initialized")
        else:
            logging.basicConfig(level=logging.INFO)
    except (yaml.YAMLError, OSError) as e:
        logging.basicConfig(level=logging.INFO)
        raise e