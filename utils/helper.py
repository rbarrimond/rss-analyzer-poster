""" Helper functions for text processing and engagement score calculation.
This module provides utility functions for calculating engagement scores,
formatting summaries, and truncating text by sentences or characters.
It includes functions to calculate engagement scores based on likes, shares,
and comments, format summaries for better readability, and truncate text
by sentences or characters.
"""
from nltk.tokenize import sent_tokenize

PRIVATE_SEPARATOR = "\uE000"  # Placeholder character for internal text processing

def calculate_engagement_score(likes, shares, comments):
    """
    Calculate the engagement score based on likes, shares, and comments.

    Args:
        likes (int): The number of likes.
        shares (int): The number of shares.
        comments (int): The number of comments.

    Returns:
        float: The calculated engagement score.
    """
    return likes * 0.4 + shares * 0.4 + comments * 0.2

def format_summary(summary):
    """
    Format the summary text for better readability.

    Args:
        summary (str): The summary text to format.

    Returns:
        str: The formatted summary text.
    """
    return summary.strip().capitalize()

def truncate_by_sentences(text: str, max_sentences: int, max_chars: int) -> str:
    """
    Truncate text to a specified number of sentences or characters.

    Args:
        text (str): The text to truncate.
        max_sentences (int): Maximum number of sentences to include.
        max_chars (int): Maximum number of characters to include.

    Returns:
        str: The truncated text.
    """
    sentences = sent_tokenize(text)
    result = ''
    for sentence in sentences[:max_sentences]:
        if len(result) + len(sentence) > max_chars:
            break
        result += sentence + ' '
    return result.strip()

def str_to_bool(val: str) -> bool:
    """
    Convert a string to a boolean, or return the boolean if already provided.

    Accepts string values: 'true', 't', 'yes', '1' → True; 
    'false', 'f', 'no', '0' → False.

    Args:
        val (str): The value to convert to a boolean.

    Returns:
        bool: The converted boolean value.

    Raises:
        ValueError: If the value cannot be interpreted as a boolean.
    """
    if isinstance(val, bool):
        return val
    if val is None:
        return False  # Default to False if the value is None
    val = val.strip().lower()
    if val in ("true", "t", "yes", "1"):
        return True
    elif val in ("false", "f", "no", "0"):
        return False
    else:
        raise ValueError(f"Invalid boolean value: {val}")
