"""
This module provides utility functions for parsing various data types.

Functions:
    parse_date(date_str: str | int | float | None) -> datetime:
        Parses a date string, timestamp, or None into a datetime object.
        - If the input is None, returns None.
        - If the input is an integer or float, treats it as a timestamp.
        - If the input is a string, attempts to parse it as a date string.
        Logs and returns a default value of None if parsing fails.
"""
from datetime import datetime
from dateutil import parser

from utils.decorators import log_and_return_default


@log_and_return_default(default_value=None, message="Failed to parse date")
def parse_date(date_str: str | int | float | None) -> datetime:
    """
    Parses a date string, timestamp, or None into a datetime object.

    - If the input is None, returns None.
    - If the input is an integer or float, treats it as a Unix timestamp.
    - If the input is a string, attempts to parse it as a date string using dateutil.parser.
    - Logs and returns a default value of None if parsing fails.

    Args:
        date_str (str | int | float | None): The date string, timestamp, or None to parse.

    Returns:
        datetime: The parsed datetime object, or None if parsing fails.
    """
    if date_str is None:
        return None
    if isinstance(date_str, (int, float)):
        return datetime.fromtimestamp(date_str)
    if isinstance(date_str, str):
        date_str = date_str.strip()
        return parser.parse(date_str)
    return None
