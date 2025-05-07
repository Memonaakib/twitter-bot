import json
import openai
import tweepy
import time
import logging
import feedparser
from newspaper import Article
import os

# Twitter API keys
import os

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")


# OpenAI key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Sources
RSS_FEEDS = [
    'https://www.livemint.com/rss/news',
    'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best'
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - AI X BOT - %(levelname)s - %(message)s')

def fetch_articles():
    articles = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({"title": entry.title, "link": entry.link})
    return articles  # Return the first relevant article
    return None


def summarize_article(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        article_text = article.text[:4000]

        # Use GPT-4 to summarize
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Summarize the article as a viral tweet under 280 characters."},
                {"role": "user", "content": article_text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Summarization failed: {e}")
        return None


def post_tweet(tweet):
    try:
        auth = tweepy.OAuth1UserHandler(
            TWITTER_API_KEY, TWITTER_API_SECRET,
            TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET
        )
        api = tweepy.API(auth)
        api.update_status(tweet)
        logging.info(f"Posted: {tweet}")
    except tweepy.errors.Forbidden:
        logging.error("Twitter error: 403 Forbidden - Duplicate content")
    except Exception as e:
        logging.error(f"Tweet post failed: {e}")


TWEET_LOG_FILE = "tweet_log.json"

def has_already_posted(title):
    if not os.path.exists(TWEET_LOG_FILE):
        return False
    with open(TWEET_LOG_FILE, 'r') as f:
        logged = json.load(f)
    return title in logged


def log_posted_article(title):
    if os.path.exists(TWEET_LOG_FILE):
        with open(TWEET_LOG_FILE, 'r') as f:
            logged = json.load(f)
    else:
        logged = []
    logged.append(title)
    with open(TWEET_LOG_FILE, 'w') as f:
        json.dump(logged, f)


def main():
    trending_keywords = load_trending_keywords()
    articles = fetch_articles()
    for article in articles:
        if any(keyword in article['title'].lower() for keyword in trending_keywords):
            if has_already_posted(article['title']):
                continue
            summary = summarize_article(article['link'])
            if summary:
                post_tweet(summary)
                log_posted_article(article['title'])
                break


if __name__ == '__main__':
    main()
