import yaml
import logging.config
import os

def setup_logging():
    """
    Setup logging configuration from the logging.yaml file
    """
    path = os.path.join(os.path.dirname(__file__), 'logging.yaml')
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = yaml.safe_load(f)
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=logging.INFO)