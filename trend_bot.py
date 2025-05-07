import requests
import json
from bs4 import BeautifulSoup
from datetime import datetime

# Global trending topic extractor from Google News
GOOGLE_NEWS_URL = 'https://news.google.com/topstories?hl=en-IN&gl=IN&ceid=IN:en'


def extract_trending_topics():
    response = requests.get(GOOGLE_NEWS_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.select('article h3')
    headlines = [article.text.strip() for article in articles][:10]  # Top 10 headlines
    return headlines


def save_trending_to_json(trends):
    trending_data = [{"timestamp": str(datetime.utcnow()), "topic": t} for t in trends]
    with open('trending.json', 'w') as f:
        json.dump(trending_data, f, indent=4)


if __name__ == '__main__':
    trends = extract_trending_topics()
    save_trending_to_json(trends)
    print("[INFO] Trending topics saved to trending.json")

