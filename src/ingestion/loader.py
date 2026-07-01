import requests
import os
import json
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
from newspaper import Article

load_dotenv()
def fetch_news(query, max_articles=10):
    api_key = os.getenv("NEWS_API_KEY")
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=publishedAt&pageSize={max_articles}&apiKey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        articles = []
        for item in data.get("articles", []):
            content = item.get("content", "") or item.get("description", "")
            articles.append({
                "title": item.get("title", ""),
                "content": content,
                "source": item.get("source", {}).get("name", ""),
                "url": item.get("url", ""),
                "date": item.get("publishedAt", "")
            })
        return articles
    except Exception as e:
        print(f"Error fetching news for {query}: {e}")
        return []
    
def fetch_multiple_queries(queries):
    all_articles = []          # start with empty list
    for query in queries:
        articles = fetch_news(query)    # fetch for this query
        all_articles.extend(articles)   # ADD to combined list, don't overwrite
    return all_articles



def load_from_file(file_path):
    """
    Load news data from a JSON file.
    """
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'r') as file:
        try:
            data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            return []
def clean_html(text):
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()
if __name__ == "__main__":
    import sys
    queries = sys.argv[1:] if len(sys.argv) > 1 else ["technology news", "stock market India"]
    articles = fetch_multiple_queries(queries)
    for article in articles:
        print(f"{article['title']} | {article['source']}")
        print(f"Content: {clean_html(article['content'])}")
        print(f"URL: {article['url']}")
        print(f"Date: {article['date']}")
        print("-" * 80)