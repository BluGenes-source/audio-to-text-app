import logging
import queue

def setup_logging(log_queue):
    """Set up logging with a queue handler"""
    class QueueHandler(logging.Handler):
        def __init__(self, log_queue):
            super().__init__()
            self.log_queue = log_queue

        def emit(self, record):
            self.log_queue.put(self.format(record))

    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Create queue handler
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(queue_handler)
    
    return logger