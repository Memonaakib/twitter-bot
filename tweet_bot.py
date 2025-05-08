import json
import tweepy
import logging
import feedparser
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - AI X BOT - %(levelname)s - %(message)s')

# Load Twitter API credentials from environment
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

# Tweepy client for API v2
client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET,
    wait_on_rate_limit=True
)

# Trending RSS feeds
RSS_FEEDS = [
    'https://www.livemint.com/rss/news',
    'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
    'https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en'
]

TWEET_LOG_FILE = "tweet_log.json"

def fetch_articles():
    articles = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({
                "title": entry.title.strip(),
                "link": entry.link.strip()
            })
    return articles

def has_already_posted(title):
    if not os.path.exists(TWEET_LOG_FILE):
        return False
    with open(TWEET_LOG_FILE, 'r') as f:
        posted = json.load(f)
    return title in posted

def log_posted_article(title):
    if os.path.exists(TWEET_LOG_FILE):
        with open(TWEET_LOG_FILE, 'r') as f:
            posted = json.load(f)
    else:
        posted = []
    posted.append(title)
    with open(TWEET_LOG_FILE, 'w') as f:
        json.dump(posted, f)

def format_tweet(article):
    emojis = ["🔥", "🚨", "⚠️", "📰", "💥"]
    tweet = f"{emojis[0]} *BREAKING NEWS* {emojis[1]}\n\n{article['title']}\n\nRead more: {article['link']} {emojis[4]}"
    return tweet

def post_tweet(tweet):
    try:
        client.create_tweet(text=tweet)
        logging.info(f"Tweet posted: {tweet}")
    except tweepy.errors.Forbidden as e:
        logging.warning(f"Twitter error: 403 Forbidden - {e}")
    except Exception as e:
        logging.error(f"Tweet post failed: {e}")

def main():
    articles = fetch_articles()
    for article in articles:
        if has_already_posted(article['title']):
            continue
        tweet = format_tweet(article)
        post_tweet(tweet)
        log_posted_article(article['title'])
        break  # Only one tweet per run

if __name__ == '__main__':
    main()
