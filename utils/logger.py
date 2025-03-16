"""
This module provides a utility function to configure logging for different modules.
"""

import logging

def configure_logging(module_name: str, handler_level: int = logging.INFO):
    """
    Configures and returns a logger for the specified module.

    Args:
        module_name (str): The name of the module for which the logger is being configured.
        handler_level (int): The logging level for the handler. Defaults to logging.INFO.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(logging.DEBUG)

    # Check if the logger already has handlers to avoid adding multiple handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(handler_level)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

def update_handler_level(logger: logging.Logger, new_level: int):
    """
    Updates the handler level for the specified logger.

    Args:
        logger (logging.Logger): The logger instance to update.
        new_level (int): The new logging level for the handler.
    """
    for handler in logger.handlers:
        handler.setLevel(new_level)
