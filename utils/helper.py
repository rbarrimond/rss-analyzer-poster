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
