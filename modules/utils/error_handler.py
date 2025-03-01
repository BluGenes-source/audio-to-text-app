import os
import logging
import functools
import time
from typing import Callable, Optional, TypeVar, Dict, Any
from dataclasses import dataclass
from datetime import datetime

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
    def __init__(self, max_retries: int = 3, 
                 delay: float = 1.0,
                 backoff_factor: float = 2.0,
                 exceptions: tuple = (Exception,)):
        self.max_retries = max_retries
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.exceptions = exceptions

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

def with_retry(retry_config: RetryConfig = None):
    """Decorator for implementing retry logic with exponential backoff"""
    if retry_config is None:
        retry_config = RetryConfig()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = retry_config.delay

            for attempt in range(retry_config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_config.exceptions as e:
                    last_exception = e
                    if attempt < retry_config.max_retries:
                        logging.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {delay:.1f} seconds..."
                        )
                        time.sleep(delay)
                        delay *= retry_config.backoff_factor
                    continue

            raise last_exception

        return wrapper
    return decorator

class ErrorHandler:
    def __init__(self, app_dir: str):
        self.tracker = ErrorTracker(app_dir)
        self.default_retry_config = RetryConfig()

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorContext:
        """Handle an error and log it"""
        error_context = ErrorContext(
            error_type=error.__class__.__name__,
            message=str(error),
            timestamp=datetime.now(),
            file_path=context.get('file_path') if context else None,
            additional_info=context
        )
        self.tracker.log_error(error_context)
        return error_context

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