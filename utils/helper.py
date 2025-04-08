""" Helper functions for text processing and engagement score calculation.
This module provides utility functions for calculating engagement scores,
formatting summaries, and truncating text by sentences or characters.
It includes functions to calculate engagement scores based on likes, shares,
and comments, format summaries for better readability, and truncate text
by sentences or characters.
"""
from nltk.tokenize import sent_tokenize

from utils.logger import LoggerFactory

logger = LoggerFactory.get_logger(__name__)
PRIVATE_SEPARATOR = "\uE000"  # Placeholder character for internal text processing

def calculate_engagement_score(likes, shares, comments):
    """
    Calculate the engagement score based on likes, shares, and comments.
    """
    return likes * 0.4 + shares * 0.4 + comments * 0.2

def format_summary(summary):
    """
    Format the summary text for better readability.
    """
    return summary.strip().capitalize()

def truncate_by_sentences(text: str, max_sentences: int, max_chars: int) -> str:
    """Truncate text to a specified number of sentences or characters.
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
