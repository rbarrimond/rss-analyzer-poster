"""
This module provides a utility function to configure logging for different modules.
"""

import logging

class LoggerFactory:
    """Factory class for creating and configuring loggers."""

    @staticmethod
    def create_logger(module_name: str, handler_level: int = logging.INFO, 
                      log_to_file: bool = False, file_name: str = None) -> logging.Logger:
        """
        Create and configure a logger for a given module.

        Args:
            module_name (str): Name of the module.
            handler_level (int): Logging level for the handler (default: logging.INFO).
            log_to_file (bool): Whether to log to a file (default: False).
            file_name (str): Name of the log file (if log_to_file is True, defaults to "<module_name>.log").

        Returns:
            logging.Logger: Configured logger instance.
        """
        logger = logging.getLogger(module_name)
        logger.setLevel(logging.DEBUG)
        
        # Avoid adding handlers more than once
        if not logger.handlers:
            # Formatter definition
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            # Stream handler
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(handler_level)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

            # File handler with sensible default
            if log_to_file:
                file_name = file_name or f"{module_name}.log"
                file_handler = logging.FileHandler(file_name)
                file_handler.setLevel(handler_level)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

        return logger

    @staticmethod
    def update_handler_level(logger: logging.Logger, new_level: int):
        """
        Update the logging level for all handlers of the logger.

        Args:
            logger (logging.Logger): The logger instance to update.
            new_level (int): The new logging level.
        """
        for handler in logger.handlers:
            handler.setLevel(new_level)
