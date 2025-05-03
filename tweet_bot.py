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
import nltk

# ─── Configuration ─────────────────────────────────────────────────────────────
NLTK_DATA_PATH = "/home/runner/nltk_data"
HISTORY_FILE = "usage.json"
COUNTRIES = ['India', 'Pakistan', 'US', 'Gaza', 'Israel', 'China']
BREAKING_KEYWORDS = ['breaking', 'urgent', 'crisis', 'attack', 'summit', 'deadly']
MAX_POSTS = 1  # Default maximum posts per run
MIN_DELAY = 300  # 5 minutes between posts in seconds

# Initialize NLTK path
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
    def __init__(self, max_posts=MAX_POSTS, min_delay=MIN_DELAY):
        """Initialize bot with rate limit protection"""
        self.max_posts = max_posts
        self.min_delay = min_delay
        self.retry_count = 0
        
        # Twitter client with rate limit handling
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
            wait_on_rate_limit=True,
            wait_on_rate_limit_notify=True
        )
        
        # Initialize NLP and history
        self._init_nltk()
        self.history = self._load_history()

    def _init_nltk(self):
        """Initialize NLP resources with fallback"""
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', download_dir=NLTK_DATA_PATH, quiet=True)
        self.stop_words = set(stopwords.words('english'))

    def _load_history(self):
        """Load history with guaranteed structure"""
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            history = {'posts': {}, 'count': 0}
            
        # Ensure required structure
        history['posts'] = history.get('posts', {})
        history['count'] = history.get('count', 0)
        return history

    def _is_breaking_news(self, title: str) -> bool:
        """Advanced breaking news detection"""
        title_lower = title.lower()
        country_check = any(c.lower() in title_lower for c in COUNTRIES)
        keyword_check = any(kw in title_lower for kw in BREAKING_KEYWORDS)
        return country_check and keyword_check

    def _process_feed(self, url: str):
        """Fetch and filter RSS feed with error handling"""
        try:
            feed = feedparser.parse(url)
            return [
                entry for entry in feed.entries[:15]
                if self._is_breaking_news(entry.title)
            ][:3]  # Top 3 breaking news
        except Exception as e:
            logger.error(f"Feed error: {url} - {str(e)}")
            return []

    def _create_tweet(self, entry) -> str:
        """Format verified breaking news tweet"""
        return f"🚨 BREAKING: {entry.title}\n🔗 {entry.link}"

    def post_update(self, entry):
        """Post to Twitter with enhanced safety checks"""
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
            time.sleep(self.min_delay)  # Delay between posts
            return True
        except tweepy.TweepyException as e:
            if "Too Many Requests" in str(e):
                wait_time = 60 * (2 ** self.retry_count)  # Exponential backoff
                logger.warning(f"Rate limited - sleeping {wait_time} seconds")
                time.sleep(wait_time)
                self.retry_count += 1
                return self.post_update(entry)  # Retry
            logger.error(f"Twitter error: {str(e)}")
            return False

    def run(self):
        """Main execution flow with rate limit checks"""
        logger.info("=== AI X BOT ACTIVATED ===")
        
        # Rate limit pre-check
        try:
            limits = self.client.get_ratelimit_limits()
            if limits.statuses.posts.remaining < self.max_posts:
                logger.warning("Insufficient rate limit - skipping run")
                return
        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")

        # Process feeds
        with open('sources.txt') as f:
            sources = [s.strip() for s in f if s.strip()]

        with ThreadPoolExecutor(max_workers=3) as executor:
            results = executor.map(self._process_feed, sources)
            all_entries = [entry for feed in results for entry in feed]

        # Post updates
        new_posts = 0
        for entry in all_entries:
            if new_posts >= self.max_posts:
                break
            if self.post_update(entry):
                new_posts += 1

        # Save history
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)

        logger.info(f"Posted {new_posts} updates | Total posts: {self.history['count']}")
        logger.info("=== AI X BOT COMPLETED ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-posts", type=int, default=MAX_POSTS,
                       help=f"Maximum posts per run (default: {MAX_POSTS})")
    parser.add_argument("--min-delay", type=int, default=MIN_DELAY,
                       help=f"Minimum delay between posts in seconds (default: {MIN_DELAY})")
    args = parser.parse_args()

    bot = AIXBot(max_posts=args.max_posts, min_delay=args.min_delay)
    bot.run()
