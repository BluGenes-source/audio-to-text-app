import logging
import queue

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

def setup_logging(log_queue):
    """Set up logging configuration with both file and queue handlers"""
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Configure root logger
    root_logger.setLevel(logging.INFO)
    
    # Add file handler
    file_handler = logging.FileHandler('audio_converter.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(file_handler)
    
    # Add queue handler for GUI
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
    queue_handler.setLevel(logging.INFO)
    root_logger.addHandler(queue_handler)

    return root_logger