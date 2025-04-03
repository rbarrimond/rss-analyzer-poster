"""
Updated logging configuration utility module.
"""
import os
import logging
from logging.handlers import RotatingFileHandler

def str_to_bool(val: str) -> bool:
    """
    Convert a string to a boolean.
    
    Accepts: 'true', 't', 'yes', '1' → True;
             'false', 'f', 'no', '0' → False.
    Raises:
         ValueError if the value cannot be interpreted.
    """
    if isinstance(val, bool):
        return val
    val = val.strip().lower()
    if val in ("true", "t", "yes", "1"):
        return True
    elif val in ("false", "f", "no", "0"):
        return False
    else:
        raise ValueError(f"Invalid boolean value: {val}")

class LoggerFactory:
    """Factory for creating and configuring loggers with standardized handlers."""

    @staticmethod
    def get_logger(module_name: str, handler_level: int | str = os.getenv('LOG_LEVEL', 'INFO'),
                   log_to_file: bool | str = os.getenv("LOG_TO_FILE"), file_name: str = None) -> logging.Logger:
        """
        Initialize and configure a logger for a specified module.
        
        Parameters:
            module_name (str): Name of the module for which the logger is created.
            handler_level (int or str): Logging level for handlers. Accepts numeric levels or level names 
                                        (e.g., 'INFO', 'DEBUG'). Defaults to the value of the environment variable
                                        LOG_LEVEL or 'INFO' if not set.
            log_to_file (bool): If True, attaches a file handler to the logger.
            file_name (str): Optional file name for logging; defaults to '<module_name>.log' if not provided when log_to_file is True.
        
        Returns:
            logging.Logger: Configured logger instance with stream (and optionally file) handler.
        """
        # Validate input parameters
        if not module_name or not isinstance(module_name, str):
            raise ValueError("module_name must be a non-empty string")
        if all([log_to_file, file_name]) and not isinstance(file_name, str):
            raise ValueError("file_name must be a string when log_to_file is True")

        handler_level = LoggerFactory._parse_log_level(handler_level)
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.DEBUG)
        
        # Return early if logger is already configured
        if logger.handlers:
            return logger
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(handler_level)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        if str_to_bool(log_to_file):
            file_name = file_name or f"{module_name}.log"
            log_file_path = os.getenv("LOG_FILE_PATH", "")
            if log_file_path:
                full_file_path = os.path.join(log_file_path, file_name)
            else:
                full_file_path = file_name
            # Using RotatingFileHandler: 5MB per file with 3 backups
            file_handler = RotatingFileHandler(full_file_path, maxBytes=5 * 1024 * 1024, backupCount=3)
            file_handler.setLevel(handler_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger

    @staticmethod
    def update_handler_level(logger: logging.Logger, new_level: int | str) -> None:
        """
        Update the logging level for all handlers attached to the provided logger.
        
        Parameters:
            logger (logging.Logger): The logger whose handlers will be updated.
            new_level (int or str): The new logging level to apply to all handlers.
        
        Raises:
            ValueError: If new_level is None.
        """
        new_level = LoggerFactory._parse_log_level(new_level)
        for handler in logger.handlers:
            handler.setLevel(new_level)

    @staticmethod
    def _parse_log_level(level: int | str | None) -> int:
        """
        Parse the log level input into a valid logging level integer.

        Parameters:
            level (int, str, or None): The log level as an int, a level name as a string, or None.
        
        Returns:
            int: The corresponding logging level.
        
        Raises:
            ValueError: If the provided level is None or invalid.
        """
        if level is None:
            raise ValueError("Log level cannot be None.")
        if isinstance(level, int):
            return level
        if isinstance(level, str):
            level_mapping = {
                "CRITICAL": logging.CRITICAL,
                "ERROR": logging.ERROR,
                "WARNING": logging.WARNING,
                "INFO": logging.INFO,
                "DEBUG": logging.DEBUG
            }
            if level.upper() not in level_mapping:
                raise ValueError(
                    f"Invalid log level '{level}'. Allowed values: {', '.join(level_mapping.keys())}"
                )
            return level_mapping[level.upper()]
        raise ValueError("Log level must be an int or a str representing a valid log level.")
