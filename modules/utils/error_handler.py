import os
import logging
import functools
import time
from typing import Callable, Optional, TypeVar, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import traceback

T = TypeVar('T')

@dataclass
class ErrorContext:
    error_type: str
    message: str
    timestamp: datetime
    file_path: Optional[str] = None
    retry_count: int = 0
    additional_info: Dict[str, Any] = None

class RetryConfig:
    """Configuration for retry decorator"""
    def __init__(self, max_retries=3, delay=1.0):
        self.max_retries = max_retries
        self.delay = delay

def with_retry(config):
    """Decorator for retrying a function on exception"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            last_exception = None
            
            while attempts < config.max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    last_exception = e
                    logging.warning(f"Attempt {attempts} failed for {func.__name__}: {e}")
                    if attempts < config.max_retries:
                        time.sleep(config.delay)
            
            # Re-raise the last exception after all retries are exhausted
            logging.error(f"Function {func.__name__} failed after {config.max_retries} attempts")
            raise last_exception
        return wrapper
    return decorator

class ErrorTracker:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self.errors: Dict[str, ErrorContext] = {}
        self._setup_logging()

    def _setup_logging(self):
        """Set up error logging"""
        os.makedirs(self.log_dir, exist_ok=True)
        self.error_log = os.path.join(self.log_dir, "error_log.txt")

    def log_error(self, context: ErrorContext):
        """Log an error with its context"""
        error_id = f"{context.error_type}_{context.timestamp.strftime('%Y%m%d_%H%M%S')}"
        self.errors[error_id] = context
        
        with open(self.error_log, "a", encoding="utf-8") as f:
            f.write(f"\n[{context.timestamp}] {context.error_type}: {context.message}\n")
            if context.file_path:
                f.write(f"File: {context.file_path}\n")
            if context.additional_info:
                for key, value in context.additional_info.items():
                    f.write(f"{key}: {value}\n")
            f.write("-" * 50 + "\n")

    def get_errors(self, error_type: Optional[str] = None) -> Dict[str, ErrorContext]:
        """Get all errors or filter by type"""
        if error_type:
            return {k: v for k, v in self.errors.items() if v.error_type == error_type}
        return self.errors

class ErrorHandler:
    """Handle and log errors"""
    def __init__(self, app_dir):
        self.app_dir = app_dir
        self.error_log_path = os.path.join(app_dir, "error_log.txt")
        
    def handle_error(self, error, context=None):
        """Handle an error, logging it to file and console"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_message = f"{timestamp} - ERROR: {str(error)}"
            
            if context:
                error_message += f"\nContext: {context}"
            
            error_message += f"\n{traceback.format_exc()}\n"
            
            # Log to console
            logging.error(error_message)
            
            # Log to file
            with open(self.error_log_path, 'a', encoding='utf-8') as f:
                f.write(f"{error_message}\n{'='*50}\n")
                
        except Exception as e:
            # If error handling itself fails, log to console
            logging.critical(f"Error in error handler: {e}")
            print(f"Error in error handler: {e}")

    def create_retry_config(self, **kwargs) -> RetryConfig:
        """Create a custom retry configuration"""
        config_dict = vars(self.default_retry_config).copy()
        config_dict.update(kwargs)
        return RetryConfig(**config_dict)

    def get_error_summary(self) -> Dict[str, int]:
        """Get a summary of errors by type"""
        summary = {}
        for error in self.tracker.errors.values():
            summary[error.error_type] = summary.get(error.error_type, 0) + 1
        return summary