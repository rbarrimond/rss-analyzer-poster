import feedparser

def parse_rss_feed(url):
    """
    Parse the RSS feed from the given URL.
    """
    return feedparser.parse(url)

def extract_feed_entries(feed):
    """
    Extract entries from the parsed RSS feed.
    """
    return feed.entries
