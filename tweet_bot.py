import json
import tweepy
import feedparser
import random
import os
import logging

# Twitter API keys
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

# Authenticate with Twitter
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

# RSS Feeds from top sources
RSS_FEEDS = {
    'Mint': 'https://www.livemint.com/rss/news',
    'Reuters': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
    'Google News': 'https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en'
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AI X BOT - %(levelname)s - %(message)s')

TWEET_LOG_FILE = "tweet_log.json"


def fetch_articles():
    articles = []
    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "source": source
            })
    return articles


def decorate_tweet(title, link, source):
    prefixes = ["Breaking:", "Just in:", "Hot Story:", "Trending Now:", "Update:"]
    emojis = ["🔥", "⚡", "🚨", "📢", "🗞️"]
    tweet = f"{random.choice(emojis)} {random.choice(prefixes)} {title} (via {source})\n{link}"
    return tweet[:280]  # Ensure within tweet limit


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


def post_tweet(tweet):
    try:
        api.update_status(tweet)
        logging.info(f"Tweeted: {tweet}")
    except tweepy.errors.Forbidden as e:
        logging.warning(f"Twitter error: 403 Forbidden - {e.api_codes} - {e.response.text}")
    except Exception as e:
        logging.error(f"Tweet post failed: {e}")


def main():
    articles = fetch_articles()
    for article in articles:
        if has_already_posted(article['title']):
            continue
        tweet = decorate_tweet(article['title'], article['link'], article['source'])
        post_tweet(tweet)
        log_posted_article(article['title'])
        break  # Post only one tweet per run


if __name__ == '__main__':
    main()
