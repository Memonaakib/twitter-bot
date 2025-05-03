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
        """Initialize bot with proper history defaults"""
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
            history = {}
            
        # Ensure required structure
        history['posts'] = history.get('posts', {})
        history['count'] = history.get('count', 0)
        return history

    def _is_breaking_news(self, title: str) -> bool:
        """Advanced breaking news detection"""
        title_lower = title.lower()
        has_country = any(c.lower() in title_lower for c in COUNTRIES)
        has_keyword = any(kw in title_lower for kw in BREAKING_KEYWORDS)
        return has_country and has_keyword

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
        # Initialize posts if missing
        if 'posts' not in self.history:
            self.history['posts'] = {}
            
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
            logger.error(f"Twitter API error: {str(e)}")
            if "Too Many Requests" in str(e):
                logger.warning("Rate limit hit - sleeping for 1 hour")
                time.sleep(3600)
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
        new_posts = 0
        for entry in all_entries:
            if self.post_update(entry):
                new_posts += 1

        # Save history
        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)

        logger.info(f"Posted {new_posts} updates | Total posts: {self.history['count']}")
        logger.info("=== AI X BOT COMPLETED ===")

if __name__ == "__main__":
    bot = AIXBot()
    bot.run()
