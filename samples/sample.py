import feedparser
import random
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# Rationalized Column Headers
csv_data = {
    "Title": [],
    "URL": [],
    "Summary": [],
    "Entry_ID": [],
    "Published_Date": [],
    "Full_Content": [],
    "Categories": [],
    "Author": [],
    "Keywords": [],
    "Sentiment": [],
    "Readability_Score": [],
    "Engagement_Score": [],
    "Processed": [],
    "Engagement_Type": [],
    "Response_Received": []
}

# Sample RSS Feed URL
FEED_URL = "https://www.wired.com/feed/category/artificial-intelligence/rss"


def fetch_full_content(url):
    """Fetch and extract full content from the given URL."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # Try different methods to extract article content
        article = soup.find("article") or soup.find(
            "div", class_="post-content") or soup.find("div", class_="entry-content")

        if article:
            return " ".join(p.get_text() for p in article.find_all("p"))
        else:
            return "Content extraction failed"

    except requests.RequestException as e:
        return f"Error fetching content: {str(e)}"


# Fetch feed and process a few entries
feed = feedparser.parse(FEED_URL)
entries = feed.entries[:]  # Taking first 5 entries as sample data

for entry in entries:
    title = entry.get("title", "No Title")
    url = entry.get("link", "No URL")
    summary = entry.get("summary", "No Summary")
    entry_id = entry.get("id", url)  # Use URL if no ID is available
    published_date = entry.get("published", "Unknown Date")
    categories = ", ".join(tag["term"] for tag in entry.get(
        "tags", [])) if "tags" in entry else "Uncategorized"
    author = entry.get("author", "Unknown Author")

    # Fetch the full article content
    full_content = fetch_full_content(url)

    # Simulated AI-related keyword extraction (random selection)
    keywords = random.choice(["LLM, Deep Learning", "Neural Networks, NLP",
                             "Transformers, AI Ethics", "Autonomous Systems, AGI"])

    # Random sentiment classification
    sentiment = random.choice(["Positive", "Neutral", "Negative"])

    # Simulated readability score
    readability_score = round(random.uniform(30, 80), 2)

    # Simulated virality signals
    engagement_score = random.randint(0, 1000)

    # Engagement and response flags
    processed = random.choice([True, False])
    engagement_type = random.choice(["Commented", "Liked", "Shared", "None"])
    response_received = random.choice(["Engaged", "Not Engaged"])

    # Append data to the CSV structure
    csv_data["Title"].append(title)
    csv_data["URL"].append(url)
    csv_data["Summary"].append(summary)
    csv_data["Entry_ID"].append(entry_id)
    csv_data["Published_Date"].append(published_date)
    csv_data["Full_Content"].append(full_content)
    csv_data["Categories"].append(categories)
    csv_data["Author"].append(author)
    csv_data["Keywords"].append(keywords)
    csv_data["Sentiment"].append(sentiment)
    csv_data["Readability_Score"].append(readability_score)
    csv_data["Engagement_Score"].append(engagement_score)
    csv_data["Processed"].append(processed)
    csv_data["Engagement_Type"].append(engagement_type)
    csv_data["Response_Received"].append(response_received)

    # Respect website scraping policies by adding a small delay
    time.sleep(2)

# Convert to DataFrame
df = pd.DataFrame(csv_data)

# Save as CSV for Microsoft Lists import
df.to_csv("rss_feed_engagement_with_content.csv", index=False)

print("CSV file generated: rss_feed_engagement_with_content.csv")
