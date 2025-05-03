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
MAX_POSTS = 1  # Strict 1 post per run
POST_INTERVAL = 3600  # 1 hour between posts

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
    def __init__(self):
        """Initialize bot with proper rate limiting"""
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self._init_nltk()
        self.history = self._load_history()
        self.last_post_time = 0

    def _init_nltk(self):
        """Initialize NLP resources"""
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', download_dir=NLTK_DATA_PATH, quiet=True)
        self.stop_words = set(stopwords.words('english'))

    def _load_history(self):
        """Load history with guaranteed structure"""
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'posts': {}, 'count': 0}

    def _is_breaking_news(self, title: str) -> bool:
        """Breaking news detection"""
        title_lower = title.lower()
        country_check = any(c.lower() in title_lower for c in COUNTRIES)
        keyword_check = any(kw in title_lower for kw in BREAKING_KEYWORDS)
        return country_check and keyword_check

    def _process_feed(self, url: str):
        """Process RSS feed safely"""
        try:
            feed = feedparser.parse(url)
            return [
                entry for entry in feed.entries[:10]
                if self._is_breaking_news(entry.title)
            ][:1]  # Only top 1 entry
        except Exception as e:
            logger.error(f"Feed error: {str(e)}")
            return []

    def _create_tweet(self, entry) -> str:
        """Create formatted tweet"""
        return f"🚨 BREAKING: {entry.title}\n🔗 {entry.link}"

    def _can_post(self):
        """Check post timing constraints"""
        time_since_last = time.time() - self.last_post_time
        if time_since_last < POST_INTERVAL:
            logger.warning(f"Too soon to post. Wait {POST_INTERVAL - time_since_last:.0f}s")
            return False
        return True

    def post_update(self, entry):
        """Safe post with rate control"""
        if not self._can_post():
            return False

        content_hash = hashlib.md5(entry.title.encode()).hexdigest()
        if content_hash in self.history['posts']:
            logger.info(f"Skipping duplicate: {entry.title[:60]}...")
            return False

        try:
            tweet = self._create_tweet(entry)
            self.client.create_tweet(text=tweet)
            self.history['posts'][content_hash] = datetime.now().isoformat()
            self.history['count'] += 1
            self.last_post_time = time.time()
            logger.info(f"Posted: {entry.title[:80]}...")
            return True
        except tweepy.TweepyException as e:
            logger.error(f"Twitter error: {str(e)}")
            return False

    def run(self):
        """Main execution flow"""
        logger.info("=== AI X BOT STARTED ===")
        
        with open('sources.txt') as f:
            sources = [s.strip() for s in f if s.strip()]

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = executor.map(self._process_feed, sources)
            all_entries = [entry for feed in results for entry in feed]

        # Post with rate control
        new_posts = 0
        for entry in all_entries:
            if new_posts >= MAX_POSTS:
                break
            if self.post_update(entry):
                new_posts += 1
                time.sleep(POST_INTERVAL)  # Enforce delay

        # Save history
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)

        logger.info(f"Total posts: {self.history['count']}")
        logger.info("=== AI X BOT COMPLETED ===")

if __name__ == "__main__":
    bot = AIXBot()
    bot.run()
