import json
import os
import time
import requests
from bs4 import BeautifulSoup
from tweet_bot import AIXBot  # Make sure tweet_bot.py is in same directory

USED_KEYWORDS_FILE = "keywords.json"
MAX_POSTS_PER_DAY = 18

def load_used_keywords():
    if os.path.exists(USED_KEYWORDS_FILE):
        with open(USED_KEYWORDS_FILE, 'r') as file:
            return json.load(file)
    return []

def save_used_keywords(keywords):
    with open(USED_KEYWORDS_FILE, 'w') as file:
        json.dump(keywords[-100:], file)  # keep last 100 entries

def fetch_trending_topics():
    url = "https://news.google.com/home?hl=en-IN&gl=IN&ceid=IN:en"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    topics = []
    for item in soup.find_all("a", attrs={"class": "DY5T1d RZIKme"}):
        text = item.get_text().strip()
        if text:
            topics.append(text)
    return list(set(topics))[:25]  # Deduplicate and limit

def main():
    used_keywords = load_used_keywords()
    topics = fetch_trending_topics()
    
    bot = AIXBot()
    count = 0

    for topic in topics:
        if topic in used_keywords:
            continue

        success = bot.post_tweet(f"Trending: {topic}")
        if success:
            used_keywords.append(topic)
            save_used_keywords(used_keywords)
            count += 1
            print(f"Posted: {topic}")
            if count >= MAX_POSTS_PER_DAY:
                break
            time.sleep(1800)  # 30 mins pause between posts (optional)

if __name__ == "__main__":
    main()
