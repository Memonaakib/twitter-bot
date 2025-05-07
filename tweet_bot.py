import json
import tweepy
import time
import logging
import feedparser
import os

# Twitter API keys from environment
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

# RSS feeds from top news sources
RSS_FEEDS = [
    'https://www.livemint.com/rss/news',
    'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
    'https://www.indiatoday.in/rss/home',
    'https://www.ndtv.com/rss',
    'https://www.moneycontrol.com/rss/latestnews.xml'
]

# Tweet log file
TWEET_LOG_FILE = "tweet_log.json"

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - AI X BOT - %(levelname)s - %(message)s')

def fetch_articles():
    articles = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({"title": entry.title, "link": entry.link})
    return articles

def format_tweet(title, link):
    return f"** {title.strip()} **\n\nRead more: {link}"

def decorate_tweet(tweet):
    return f"🔥 {tweet} 🔗"

def post_tweet(tweet):
    try:
        auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
        api = tweepy.API(auth)
        api.update_status(tweet)
        logging.info(f"Posted: {tweet}")
    except tweepy.errors.Forbidden:
        logging.warning("Twitter error: 403 Forbidden - Possibly duplicate content")
    except Exception as e:
        logging.error(f"Tweet post failed: {e}")

def has_already_posted(title):
    if not os.path.exists(TWEET_LOG_FILE):
        return False
    with open(TWEET_LOG_FILE, 'r') as f:
        posted_titles = json.load(f)
    return title in posted_titles

def log_posted_article(title):
    if os.path.exists(TWEET_LOG_FILE):
        with open(TWEET_LOG_FILE, 'r') as f:
            posted_titles = json.load(f)
    else:
        posted_titles = []
    posted_titles.append(title)
    with open(TWEET_LOG_FILE, 'w') as f:
        json.dump(posted_titles, f)

def main():
    articles = fetch_articles()
    for article in articles:
        title = article['title']
        link = article['link']
        if not has_already_posted(title):
            tweet = decorate_tweet(format_tweet(title, link))
            if len(tweet) <= 280:
                post_tweet(tweet)
                log_posted_article(title)
                break

if __name__ == '__main__':
    main()
