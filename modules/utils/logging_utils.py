import logging
import queue
import os

class QueueHandler(logging.Handler):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                msg = "ERROR: " + msg
            elif record.levelno >= logging.WARNING:
                msg = "WARNING: " + msg
            elif record.levelno >= logging.INFO:
                msg = "INFO: " + msg
            self.queue.put(msg)
        except Exception:
            self.handleError(record)

def setup_logging(log_queue, config=None):
    """Set up logging configuration with both file and queue handlers"""
    # Determine logs directory
    if config and hasattr(config, 'logs_folder'):
        logs_dir = config.logs_folder
    else:
        # Fallback to default logs directory
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger
    root_logger.setLevel(logging.INFO)
    
    # Define log files
    log_files = {
        'audio_converter': os.path.join(logs_dir, 'audio_converter.log'),
        'text_to_speech': os.path.join(logs_dir, 'text_to_speech.log'),
        'conversion_errors': os.path.join(logs_dir, 'conversion_errors.log'),
        'audio_conversion': os.path.join(logs_dir, 'audio_conversion.log')
    }
    
    # Add file handlers for each log file
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')
    for log_name, log_path in log_files.items():
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
    
    # Add queue handler for GUI
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    queue_handler.setLevel(logging.INFO)
    root_logger.addHandler(queue_handler)

    return root_logger