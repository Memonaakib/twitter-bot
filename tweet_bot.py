import feedparser
import json
import time
from datetime import datetime
from collections import Counter
import hashlib
import os

from tweet_bot import AIXBot  # Make sure your main class is imported

# Settings
RSS_FEEDS = [
    "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "https://www.reddit.com/r/worldnews/.rss"
]
MAX_DAILY_POSTS = 18
TREND_THRESHOLD = 3  # Minimum keyword frequency to be considered trending
KEYWORDS_TO_TRACK = ['india', 'israel', 'gaza', 'modi', 'bjp', 'neet', 'china', 'iran', 'elon', 'crisis']

HISTORY_FILE = "usage.json"

def load_history():
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return {'posts': {}, 'count': 0, 'date': datetime.now().strftime('%Y-%m-%d')}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def reset_daily_counter_if_needed(history):
    today = datetime.now().strftime('%Y-%m-%d')
    if history.get("date") != today:
        history['count'] = 0
        history['posts'] = {}
        history['date'] = today
    return history

def extract_keywords(title):
    words = [word.lower() for word in title.split() if len(word) > 3]
    return [word for word in words if word in KEYWORDS_TO_TRACK]

def fetch_articles():
    entries = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        entries.extend(feed.entries[:10])
    return entries

def detect_trending_keywords(entries):
    all_keywords = []
    for entry in entries:
        all_keywords += extract_keywords(entry.title)
    keyword_counts = Counter(all_keywords)
    trending = [kw for kw, count in keyword_counts.items() if count >= TREND_THRESHOLD]
    return trending

def run_trend_bot():
    history = load_history()
    history = reset_daily_counter_if_needed(history)

    if history['count'] >= MAX_DAILY_POSTS:
        print("Daily post limit reached.")
        return

    entries = fetch_articles()
    trending_keywords = detect_trending_keywords(entries)
    print(f"Trending keywords: {trending_keywords}")

    bot = AIXBot()
    for entry in entries:
        keywords = extract_keywords(entry.title)
        if any(kw in trending_keywords for kw in keywords):
            content_hash = hashlib.md5(entry.title.encode()).hexdigest()
            if content_hash in history['posts']:
                continue
            if bot.post_update(entry):
                history['posts'][content_hash] = datetime.now().isoformat()
                history['count'] += 1
                save_history(history)
                time.sleep(2)  # Small gap
            if history['count'] >= MAX_DAILY_POSTS:
                break

if __name__ == "__main__":
    run_trend_bot()
