import hashlib
import json
import os
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import tweepy
import feedparser
from newspaper import Article
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Configuration
HISTORY_FILE = "posted.json"
CACHE_HOURS = 24
VIRAL_KEYWORDS = ['viral', 'breaking', 'outbreak', 'surge', 'alert', 'exclusive']

class NewsBot:
    def __init__(self):
        self.client = tweepy.Client(
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.posted = self.load_history()
        self.stop_words = set(stopwords.words('english'))

    def load_history(self):
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                # Auto-clear old entries
                return {k:v for k,v in data.items() 
                       if datetime.fromisoformat(v) > datetime.now() - timedelta(hours=CACHE_HOURS)}
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_history(self):
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.posted, f)

    def content_hash(self, content):
        return hashlib.md5(content.encode()).hexdigest()

    def clean_text(self, text):
        tokens = word_tokenize(text.lower())
        return ' '.join([t for t in tokens if t.isalnum() and t not in self.stop_words])

    def is_viral(self, title, content):
        combined = f"{title} {self.clean_text(content)}"
        return any(re.search(rf'\b{kw}\b', combined) for kw in VIRAL_KEYWORDS)

    def process_feed(self, url):
        feed = feedparser.parse(url)
        return [entry.link for entry in feed.entries[:5]]

    def analyze_article(self, url):
        try:
            article = Article(url, fetch_images=False, memoize_articles=True)
            article.download()
            article.parse()
            
            if not article.text or len(article.text) < 400:
                return None
                
            return {
                'title': article.title,
                'content': article.text,
                'url': url,
                'hash': self.content_hash(article.title + self.clean_text(article.text)),
                'viral': self.is_viral(article.title, article.text)
            }
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            return None

    def post_update(self, article):
        if article['hash'] in self.posted:
            return False

        try:
            prefix = "🔥 VIRAL: " if article['viral'] else "📰 Report: "
            tweet_text = f"{prefix}{article['title']}\n\n{article['content'][:250]}...\n\nSource: {article['url']}"
            self.client.create_tweet(text=tweet_text)
            self.posted[article['hash']] = datetime.now().isoformat()
            return True
        except tweepy.TweepyException as e:
            print(f"API Error: {str(e)}")
            return False

    def run(self, max_articles=5):
        with open('sources.txt') as f:
            sources = [line.strip() for line in f if line.strip()]

        articles = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            feed_urls = [url for source in sources for url in self.process_feed(source)]
            results = executor.map(self.analyze_article, feed_urls[:max_articles*2])
            articles = [a for a in results if a]

        new_posts = 0
        for article in sorted(articles, key=lambda x: x['viral'], reverse=True)[:max_articles]:
            if self.post_update(article):
                new_posts += 1

        self.save_history()
        print(f"Successfully posted {new_posts} updates")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=5)
    parser.add_argument("--min-length", type=int, default=400)
    args = parser.parse_args()

    bot = NewsBot()
    bot.run(max_articles=args.max)
