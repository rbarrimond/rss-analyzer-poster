""" Helper functions for text processing and engagement score calculation.
This module provides utility functions for calculating engagement scores,
formatting summaries, and truncating text by sentences or characters.
It includes functions to calculate engagement scores based on likes, shares,
and comments, format summaries for better readability, and truncate text
by sentences or characters.
"""
import nltk
from nltk.tokenize import sent_tokenize
from bs4 import BeautifulSoup
from bleach import clean
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

def clean_and_truncate_html_summary(html: str, max_sentences: int,
                                     max_characters: int, separator: str = PRIVATE_SEPARATOR) -> str:
    """
    Clean and truncate an HTML summary while preserving its structure.

    Args:
        html (str): The HTML content to clean and truncate.
        max_sentences (int): Maximum number of sentences to retain.
        max_characters (int): Maximum number of characters to retain.
        separator (str): Separator used for internal text processing.

    Returns:
        str: The cleaned and truncated HTML summary.
    """
    if not html:
        return html

    # Sanitize the HTML to remove unwanted tags and attributes
    allowed_tags = ['p', 'b', 'i', 'u', 'a', 'ul', 'ol', 'li', 'br', 'strong', 'em']
    allowed_attributes = {'a': ['href', 'title']}
    sanitized_html = clean(html, tags=allowed_tags, attributes=allowed_attributes, strip=True)

    # Parse the sanitized HTML
    soup = BeautifulSoup(sanitized_html, "html.parser")

    # Truncate the text content while preserving structure
    text_content = soup.get_text(separator=separator, strip=True)
    truncated_text = truncate_by_sentences(text_content, max_sentences, max_characters)

    # Replace the text content in the original HTML structure
    soup.clear()
    soup.append(BeautifulSoup(truncated_text, "html.parser"))

    logger.debug("Cleaned and truncated summary: %s", soup)
    return str(soup)

# Download the punkt tokenizer models for sentence tokenization
nltk.download('punkt_tab', quiet=True)
