import json
import tweepy
import logging
import feedparser
import os
import random
import string
from collections import defaultdict

# Twitter API v2 credentials from environment
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET
)

RSS_FEEDS = [
    'https://www.livemint.com/rss/news',
    'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
    'https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en',
    'https://timesofindia.indiatimes.com/rssfeedstopstories.cms',
    'https://feeds.bbci.co.uk/news/world/rss.xml'
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AI X BOT - %(levelname)s - %(message)s')
TWEET_LOG_FILE = "tweet_log.json"

def clean_title(title):
    # Normalize title for deduplication
    title = title.lower()
    title = title.translate(str.maketrans('', '', string.punctuation))
    return title.strip()

def fetch_articles_grouped():
    article_map = defaultdict(list)
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            key = clean_title(entry.title)
            article_map[key].append({
                "title": entry.title,
                "link": entry.link,
                "content": entry.summary  # Capture the content of the article
            })
    return article_map

def has_already_posted(title):
    if not os.path.exists(TWEET_LOG_FILE):
        return False
    with open(TWEET_LOG_FILE, 'r') as f:
        posted_titles = json.load(f)
    return clean_title(title) in posted_titles

def log_posted_article(title):
    if os.path.exists(TWEET_LOG_FILE):
        with open(TWEET_LOG_FILE, 'r') as f:
            posted_titles = json.load(f)
    else:
        posted_titles = []
    posted_titles.append(clean_title(title))
    with open(TWEET_LOG_FILE, 'w') as f:
        json.dump(posted_titles, f)

def post_random_engagement():
    # Predefined random engagement posts like jokes, quotes, and questions
    posts = [
        "Why don't skeletons fight each other? They don't have the guts! 😂",
        "Here's a motivational quote: 'Success is not final, failure is not fatal: It is the courage to continue that counts.' – Winston Churchill",
        "Quiz time! What’s the capital of France? 🇫🇷",
        "If you could have dinner with any historical figure, who would it be and why? 🤔",
        "Life’s too short to waste time. What’s one thing you’d love to do more of this year? ✨"
    ]
    tweet = random.choice(posts)
    try:
        client.create_tweet(text=tweet)
        logging.info(f"Engagement post posted: {tweet}")
    except Exception as e:
        logging.error(f"Post failed: {e}")

def main():
    grouped_articles = fetch_articles_grouped()

    # Check if there are articles to post
    for group in grouped_articles.values():
        if len(group) >= 2:  # At least 2 sources have the same story
            article = group[0]  # Pick from one of the matching sources
            if has_already_posted(article['title']):
                continue
            tweet = f"🚨 {article['title']} 🚨\n\nRead more: {article['link']}"
            try:
                client.create_tweet(text=tweet)
                log_posted_article(article['title'])
                logging.info(f"Tweet posted: {tweet}")
            except Exception as e:
                logging.error(f"Tweet post failed: {e}")
            break
    else:
        # If no article found, post an engaging random post
        post_random_engagement()

if __name__ == '__main__':
    main()
