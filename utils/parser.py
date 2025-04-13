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
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import sent_tokenize
import html2text

from utils.decorators import log_and_return_default

# Download the punkt tokenizer models for sentence tokenization
nltk.download('punkt_tab', quiet=True)

@log_and_return_default(default_value=None, message="Failed to parse date")
def parse_date(date_str: str | int | float | datetime | None) -> datetime:
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
    if date_str is None or isinstance(date_str, datetime):
        return date_str
    if isinstance(date_str, (int, float)):
        return datetime.fromtimestamp(date_str)
    if isinstance(date_str, str):
        date_str = date_str.strip()
        return parser.parse(date_str)
    return None

def normalize_html(html: str) -> str:
    """
    Normalize HTML or plain text content. If the content lacks meaningful HTML structure,
    wraps it in a <p> tag to ensure consistency downstream.

    Args:
        html (str): Raw HTML or plain text.

    Returns:
        str: Normalized HTML.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    if not any(tag.name not in ("html", "body") for tag in soup.find_all()):
        html = f"<p>{html.strip()}</p>"
        soup = BeautifulSoup(html, "html.parser")

    return str(soup)

def html_to_markdown(html: str) -> str:
    """
    Convert HTML to Markdown while preserving structure.
    """
    if not html:
        return ""
    
    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.ignore_images = False
    converter.body_width = 0
    converter.skip_internal_links = True
    converter.single_line_break = True

    return converter.handle(html).strip()

def truncate_markdown(markdown: str, max_sentences: int = 0, max_chars: int = 0) -> str:
    """
    Truncate Markdown text by sentence or character count.
    """
    if not markdown:
        return ""
    
    truncated = markdown

    if max_sentences > 0:
        sentences = sent_tokenize(truncated)
        truncated = " ".join(sentences[:max_sentences])
    
    if max_chars > 0 and len(truncated) > max_chars:
        truncated = truncated[:max_chars].rsplit('\n', 1)[0].strip()
    
    return truncated
