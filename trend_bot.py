# trend_bot.py
import json
from datetime import datetime
import feedparser

def extract_trending_topics():
    feed = feedparser.parse("https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en")
    headlines = [entry.title for entry in feed.entries[:10]]
    return headlines

def save_trending_to_json(trends):
    trending_data = [{"timestamp": str(datetime.utcnow()), "topic": t} for t in trends]
    with open('trending.json', 'w') as f:
        json.dump(trending_data, f, indent=4)

if __name__ == '__main__':
    trends = extract_trending_topics()
    save_trending_to_json(trends)
    print("[INFO] Trending topics saved to trending.json")
