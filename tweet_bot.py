import os
import time
import json
import hashlib
import argparse
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
CACHE_HOURS = 48  # Longer cache duration
VIRAL_KEYWORDS = ['viral', 'breaking', 'outbreak', 'surge', 'alert', 'exclusive']

class NewsBot:
    def __init__(self):
        # Initialize NLTK with fallback download
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords', download_dir='/home/runner/nltk_data')
            self.stop_words = set(stopwords.words('english'))

        # Twitter client with enhanced rate limit handling
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        
        self.usage_data = self.load_history()
        self.posted = self.usage_data.get('posted', {})
        self.last_post_time = self.usage_data.get('last_post_time', 0)
        self.usage_data['reads'] = self.usage_data.get('reads', 0) + 1
        self.min_post_interval = 7200  # 2 hours between posts

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
            return {
                'reads': 0,
                'writes': 0,
                'last_post_time': 0,
                'posted': {}
            }

    def save_history(self):
        self.usage_data['posted'] = self.posted
        self.usage_data['last_post_time'] = self.last_post_time
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
            feed = feedparser.parse(url, timeout=10)
            return [entry.link for entry in feed.entries[:3]]  # Reduced from 5 to 3
        except Exception as e:
            print(f"⚠️ Feed error ({url}): {str(e)}")
            return []

    def analyze_article(self, url):
        try:
            article = Article(url, fetch_images=False, memoize_articles=True)
            article.download()
            article.parse()
            
            if not article.text or len(article.text) < 300:  # Reduced minimum length
                return None
                
            return {
                'title': article.title,
                'content': article.text,
                'url': url,
                'hash': self.content_hash(article.title + self.clean_text(article.text)),
                'viral': self.is_viral(article.title, article.text)
            }
        except Exception as e:
            print(f"⚠️ Article error ({url}): {str(e)}")
            return None

    def post_update(self, article):
        current_time = time.time()
        
        # Enhanced rate limit check
        if current_time - self.last_post_time < self.min_post_interval:
            wait_time = self.min_post_interval - (current_time - self.last_post_time)
            print(f"⏳ Rate limit cooldown: {wait_time/60:.1f} minutes remaining")
            return False

        if article['hash'] in self.posted:
            print(f"⏩ Skipping duplicate: {article['title'][:50]}...")
            return False

        try:
            prefix = "🔥 VIRAL: " if article['viral'] else "📰 Report: "
            tweet_text = f"{prefix}{article['title']}\n\n{article['content'][:220]}...\n\nSource: {article['url']}"
            
            response = self.client.create_tweet(text=tweet_text)
            self.posted[article['hash']] = datetime.now().isoformat()
            self.usage_data['writes'] = self.usage_data.get('writes', 0) + 1
            self.last_post_time = current_time
            
            print(f"✅ Posted: {article['title'][:60]}... (ID: {response.data['id']})")
            return True
            
        except tweepy.TweepyException as e:
            print(f"❌ Twitter error: {str(e)}")
            if "Too Many Requests" in str(e):
                time.sleep(3600)  # Wait 1 hour on rate limit
            return False

    def run(self, max_posts=1):  # Changed from max_articles to max_posts
        print("\n=== Starting Bot ===")
        print(f"Last post time: {datetime.fromtimestamp(self.last_post_time) if self.last_post_time else 'Never'}")

        with open('sources.txt') as f:
            sources = [line.strip() for line in f if line.strip()]

        articles = []
        with ThreadPoolExecutor(max_workers=3) as executor:  # Reduced from 4 workers
            feed_urls = [url for source in sources for url in self.process_feed(source)]
            results = executor.map(self.analyze_article, feed_urls[:6])  # Reduced from max_articles*2
            articles = [a for a in results if a]

        new_posts = 0
        for article in sorted(articles, key=lambda x: x['viral'], reverse=True):
            if self.post_update(article):
                new_posts += 1
                if new_posts >= max_posts:
                    break

        self.save_history()
        print(f"\n=== Summary ===")
        print(f"Posts this run: {new_posts}")
        print(f"Total runs: {self.usage_data['reads']}")
        print(f"Total posts: {self.usage_data['writes']}")
        print("=================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-posts", type=int, default=1, help="Maximum posts per run (recommended: 1)")
    args = parser.parse_args()

    bot = NewsBot()
    bot.run(max_posts=args.max_posts)
