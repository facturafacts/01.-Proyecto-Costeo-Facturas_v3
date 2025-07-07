import logging
import os

# Define the log file path relative to the p62 folder
log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'p62_processing.log')

def get_p62_logger():
    """Configures and returns a logger for the P62 processing module."""
    logger = logging.getLogger('p62_processor')
    logger.setLevel(logging.DEBUG)

    # Prevent logs from propagating to the root logger
    logger.propagate = False

    # Create a file handler to write logs to a file
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)

    # Create a console handler to display logs in the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create a formatter and set it for both handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger, but only if they haven't been added before
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

logger = get_p62_logger() 