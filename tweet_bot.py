#!/usr/bin/env python3
import os
import time
import json
import hashlib
import argparse
import re
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import tweepy
import feedparser
from newspaper import Article
import nltk#!/usr/bin/env python3
import os
import time
import json
import hashlib
import argparse
import re
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import tweepy
import feedparser
from newspaper import Article
import nltk

# ─── Configuration ─────────────────────────────────────────────────────────────
NLTK_DATA_PATH = "/home/runner/nltk_data"
HISTORY_FILE = "usage.json"
CACHE_HOURS = 24
COUNTRIES = ['India', 'Pakistan', 'US', 'Gaza', 'Israel']
BREAKING_KEYWORDS = ['breaking', 'urgent', 'crisis', 'attack', 'summit', 'deadly']

# Initialize NLTK
nltk.data.path.insert(0, NLTK_DATA_PATH)
from nltk.corpus import stopwords

# ─── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - AI X BOT - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("AI_X_Bot")

class AIXBot:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET")
        )
        self._init_nltk()
        self.history = self._load_history()

    def _init_nltk(self):
        """Initialize NLP resources"""
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', download_dir=NLTK_DATA_PATH)
        self.stop_words = set(stopwords.words('english'))

    def _load_history(self):
        """Load posting history"""
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'posts': {}, 'count': 0}

    def _is_breaking_news(self, title: str) -> bool:
        """Detect breaking news patterns"""
        title_lower = title.lower()
        country_check = any(c.lower() in title_lower for c in COUNTRIES)
        keyword_check = any(kw in title_lower for kw in BREAKING_KEYWORDS)
        return country_check and keyword_check

    def _process_feed(self, url: str):
        """Fetch and filter RSS feed"""
        try:
            feed = feedparser.parse(url)
            return [
                entry for entry in feed.entries[:10]
                if self._is_breaking_news(entry.title)
            ][:3]  # Top 3 breaking news
        except Exception as e:
            logger.error(f"Feed error: {str(e)}")
            return []

    def _create_tweet(self, entry) -> str:
        """Format breaking news tweet"""
        return f"🚨 BREAKING: {entry.title}\n\n🔗 {entry.link}"

    def post_update(self, entry):
        """Post to Twitter with duplicate check"""
        content_hash = hashlib.md5(entry.title.encode()).hexdigest()
        
        if content_hash in self.history['posts']:
            logger.info(f"Skipping duplicate: {entry.title[:60]}...")
            return False

        try:
            tweet = self._create_tweet(entry)
            response = self.client.create_tweet(text=tweet)
            self.history['posts'][content_hash] = datetime.now().isoformat()
            self.history['count'] += 1
            logger.info(f"Posted: {entry.title[:80]}... (ID: {response.data['id']})")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Twitter error: {str(e)}")
            return False

    def run(self):
        """Main execution flow"""
        logger.info("=== AI X BOT ACTIVATED ===")
        
        with open('sources.txt') as f:
            sources = [s.strip() for s in f if s.strip()]

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = executor.map(self._process_feed, sources)
            all_entries = [entry for feed in results for entry in feed]

        # Post all breaking news
        for entry in all_entries:
            self.post_update(entry)

        # Save history
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)

        logger.info(f"Total posts this run: {len(all_entries)}")
        logger.info("=== AI X BOT COMPLETED ===")

if __name__ == "__main__":
    bot = AIXBot()
    bot.run()

# ─── CRITICAL: Set NLTK_DATA path before any nltk.download() ─────────────────
nltk_data_path = os.getenv("NLTK_DATA", "/home/runner/nltk_data")
nltk.data.path.insert(0, nltk_data_path)

# ─── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("NewsBot")

# ─── Now safe to import NLTK corpora ──────────────────────────────────────────
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# ─── Configuration ─────────────────────────────────────────────────────────────
HISTORY_FILE = "usage.json"
CACHE_HOURS = 48
VIRAL_KEYWORDS = ['viral', 'breaking', 'outbreak', 'surge', 'alert', 'exclusive']


class NewsBot:
    def __init__(self):
        logger.info("Initializing bot and loading stopwords…")
        try:
            self.stop_words = set(stopwords.words('english'))
        except LookupError:
            nltk.download('stopwords', download_dir=nltk_data_path, quiet=True)
            self.stop_words = set(stopwords.words('english'))
        logger.info(f"Stopwords loaded: {len(self.stop_words)} words")

        # Twitter API client
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET")
        )

        # Load or initialize history
        self.usage_data = self.load_history()
        self.posted = self.usage_data.get('posted', {})
        self.last_post_time = self.usage_data.get('last_post_time', 0)
        self.min_post_interval = 7200  # 2 hours
        self.usage_data['reads'] = self.usage_data.get('reads', 0) + 1

    def load_history(self):
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
            # prune old entries
            cutoff = datetime.now() - timedelta(hours=CACHE_HOURS)
            data['posted'] = {
                k: v for k, v in data.get('posted', {}).items()
                if datetime.fromisoformat(v) > cutoff
            }
            return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {'reads': 0, 'writes': 0, 'last_post_time': 0, 'posted': {}}

    def save_history(self):
        self.usage_data['posted'] = self.posted
        self.usage_data['last_post_time'] = self.last_post_time
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.usage_data, f, indent=2)

    @staticmethod
    def content_hash(content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def clean_text(self, text: str) -> str:
        tokens = word_tokenize(text.lower())
        return ' '.join([t for t in tokens if t.isalnum() and t not in self.stop_words])

    def is_viral(self, title: str, content: str) -> bool:
        combined = f"{title} {self.clean_text(content)}"
        return any(re.search(rf'\b{kw}\b', combined) for kw in VIRAL_KEYWORDS)

    def process_feed_with_retry(self, url: str, retries: int = 2):
        for attempt in range(1, retries + 1):
            try:
                feed = feedparser.parse(url)
                if feed.entries:
                    return [e.link for e in feed.entries[:3]]
            except Exception as e:
                logger.warning(f"Feed error ({attempt}/{retries}) at {url}: {e}")
                time.sleep(1)
        return []

    def analyze_article(self, url: str):
        try:
            art = Article(url, fetch_images=False, memoize_articles=True)
            art.download()
            art.parse()
            if not hasattr(art, 'text') or len(art.text) < 300:
                return None
            title, content = art.title, art.text
            hash_ = self.content_hash(title + self.clean_text(content))
            return {
                'title': title,
                'content': content,
                'url': url,
                'hash': hash_,
                'viral': self.is_viral(title, content)
            }
        except Exception as e:
            logger.warning(f"Article error at {url}: {e}")
            return None

    def post_update(self, article: dict) -> bool:
        now = time.time()
        # rate‐limit check
        if now - self.last_post_time < self.min_post_interval:
            remaining = (self.min_post_interval - (now - self.last_post_time)) / 60
            logger.info(f"Cooldown: {remaining:.1f} min left before next post")
            return False
        if article['hash'] in self.posted:
            logger.info(f"Skipping duplicate: {article['title'][:50]}…")
            return False

        prefix = "🔥 VIRAL: " if article['viral'] else "📰 Report: "
        tweet = f"{prefix}{article['title']}\n\n{article['content'][:220]}...\n\nSource: {article['url']}"
        try:
            resp = self.client.create_tweet(text=tweet)
            self.posted[article['hash']] = datetime.now().isoformat()
            self.usage_data['writes'] = self.usage_data.get('writes', 0) + 1
            self.last_post_time = now
            logger.info(f"Posted: {article['title'][:60]}… (ID {resp.data['id']})")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Twitter error: {e}")
            if "Too Many Requests" in str(e):
                time.sleep(3600)
            return False

    def run(self, max_posts: int = 1):
        logger.info("=== Bot run started ===")
        if self.last_post_time:
            logger.info(f"Last post at: {datetime.fromtimestamp(self.last_post_time)}")
        else:
            logger.info("No previous posts")

        with open('sources.txt') as f:
            sources = [s.strip() for s in f if s.strip()]

        # Fetch and analyze
        with ThreadPoolExecutor(max_workers=3) as ex:
            feeds = [link for src in sources for link in self.process_feed_with_retry(src)]
            articles = filter(None, ex.map(self.analyze_article, feeds[:6]))

        # Sort by viral and post
        new = 0
        for art in sorted(articles, key=lambda x: x['viral'], reverse=True):
            if self.post_update(art):
                new += 1
                if new >= max_posts:
                    break

        self.save_history()
        logger.info(f"Run summary: Posted {new}, Reads {self.usage_data['reads']}, Writes {self.usage_data['writes']}")
        logger.info("=== Bot run complete ===\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-posts", type=int, default=1,
                        help="Maximum posts per run (recommended: 1)")
    args = parser.parse_args()

    bot = NewsBot()
    bot.run(max_posts=args.max_posts)
