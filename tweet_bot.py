import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import tweepy
import feedparser
from newspaper import Article
import nltk

# CRITICAL - Must be at the very top before any NLTK imports
nltk.data.path = ['/home/runner/nltk_data'] + nltk.data.path

# Now safe to import NLTK components
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Configuration
HISTORY_FILE = "usage.json"
CACHE_HOURS = 24
VIRAL_KEYWORDS = ['viral', 'breaking', 'outbreak', 'surge', 'alert', 'exclusive']
MIN_POST_INTERVAL = 7200  # 2 hours between posts

class NewsBot:
    def __init__(self):
        # Initialize NLTK with fallback download
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords', download_dir='/home/runner/nltk_data')
            self.stop_words = set(stopwords.words('english'))

        # Twitter client with rate limit handling
        self.client = tweepy.Client(
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
            bearer_token=os.getenv("BEARER_TOKEN"),
            wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True
        )
        
        self.usage_data = self.load_history()
        self.posted = self.usage_data.get('posted', {})
        self.last_post_time = 0
        self.usage_data['reads'] = self.usage_data.get('reads', 0) + 1

    def load_history(self):
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                if 'posted' in data:
                    data['posted'] = {
                        k: v for k, v in data['posted'].items()
                        if datetime.fromisoformat(v) > datetime.now() - timedelta(hours=CACHE_HOURS)
                    }
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {'reads': 0, 'writes': 0, 'posted': {}}

    def save_history(self):
        self.usage_data['posted'] = self.posted
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.usage_data, f, indent=2)

    def content_hash(self, content):
        return hashlib.md5(content.encode()).hexdigest()

    def clean_text(self, text):
        tokens = word_tokenize(text.lower())
        return ' '.join([t for t in tokens if t.isalnum() and t not in self.stop_words])

    def is_viral(self, title, content):
        combined = f"{title} {self.clean_text(content)}"
        return any(re.search(rf'\b{kw}\b', combined) for kw in VIRAL_KEYWORDS)

    def process_feed(self, url):
        try:
            feed = feedparser.parse(url)
            return [entry.link for entry in feed.entries[:5]]
        except Exception as e:
            print(f"Feed parsing error: {str(e)}")
            return []

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
            print(f"Article processing error: {str(e)}")
            return None

    def post_update(self, article):
        current_time = time.time()
        
        # Rate limit check
        if current_time - self.last_post_time < MIN_POST_INTERVAL:
            wait_time = MIN_POST_INTERVAL - (current_time - self.last_post_time)
            print(f"Rate limit cooldown: Waiting {wait_time/60:.1f} minutes")
            return False

        if article['hash'] in self.posted:
            return False

        try:
            prefix = "🔥 VIRAL: " if article['viral'] else "📰 Report: "
            tweet_text = f"{prefix}{article['title']}\n\n{article['content'][:250]}...\n\nSource: {article['url']}"
            response = self.client.create_tweet(text=tweet_text)
            self.posted[article['hash']] = datetime.now().isoformat()
            self.usage_data['writes'] += 1
            self.last_post_time = current_time
            print(f"Posted successfully: {response.data['id']}")
            return True
        except tweepy.TweepyException as e:
            print(f"Twitter API error: {str(e)}")
            if "Too Many Requests" in str(e):
                time.sleep(3600)  # Wait 1 hour on rate limit
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
                if new_posts >= 1:  # Limit to 1 post per run
                    break

        self.save_history()
        print(f"Posted {new_posts} updates (Total reads: {self.usage_data['reads']}, writes: {self.usage_data['writes']})")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=1, help="Maximum posts per run (1 recommended)")
    parser.add_argument("--min-length", type=int, default=400)
    args = parser.parse_args()

    print("=== Starting Twitter Bot ===")
    bot = NewsBot()
    bot.run(max_articles=args.max)
    print("=== Bot Completed ===")
