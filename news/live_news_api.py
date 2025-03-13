import requests
import os

NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Store your key in an environment variable
NEWS_URL = "https://newsapi.org/v2/everything"  # ✅ Use "everything" for keyword filtering

def fetch_live_news(query="war", page_size=5):
    """
    Fetches live news articles based on a query.
    Returns a list of (headline, URL) tuples.
    """
    params = {
        "q": query,  # ✅ Now works since we switched to "everything"
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": NEWS_API_KEY
    }

    try:
        response = requests.get(NEWS_URL, params=params)
        data = response.json()

        if data.get("status") != "ok":
            return [("⚠️ Error fetching news.", None)]

        articles = data.get("articles", [])
        news_data = [(f"📰 {article['title']}", article["url"]) for article in articles if article.get("title")]

        return news_data if news_data else [("⚠️ No news found.", None)]
    except Exception as e:
        return [(f"⚠️ Error: {e}", None)]
