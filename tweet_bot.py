#!/usr/bin/env python3
import os
import time
import json
import hashlib
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import tweepy
import feedparser
from newspaper import Article
import nltk

# ─── Configuration ──────────────────────────────────────────────
NLTK_DATA_PATH = "/home/runner/nltk_data"
HISTORY_FILE = "usage.json"
TRENDS_FILE = "trends.json"
COUNTRIES = ['India', 'Pakistan', 'US', 'Gaza', 'Israel', 'China']
BREAKING_KEYWORDS = [
    'breaking', 'urgent', 'crisis', 'attack', 'summit', 'deadly', 'neet', 'cbse',
    'exam', 'results', 'modi', 'bjp', 'election', 'vote', 'gaza', 'israel', 'tariff',
    'blast', 'shooting', 'strike', 'trump', 'white house'
]
MAX_POSTS = 3
POST_INTERVAL = 30  # seconds between posts

# ─── Logging Setup ──────────────────────────────────────────────
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
            access_token_secret=os.getenv("ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self._init_nltk()
        self.history = self._load_history()
        self.trends = self._load_trends()
        self.last_post_time = 0

    def _init_nltk(self):
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords', download_dir=NLTK_DATA_PATH, quiet=True)

    def _load_history(self):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'posts': {}, 'count': 0}

    def _load_trends(self):
        try:
            with open(TRENDS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []

    def _is_breaking_news(self, title: str) -> bool:
        title_lower = title.lower()
        matched = []

        for word in COUNTRIES + BREAKING_KEYWORDS + self.trends:
            if word.lower() in title_lower:
                matched.append(word.lower())

        if matched:
            logger.info(f"Matched keywords in title: {matched}")
            return True
        return False

    def _process_feed(self, url: str):
        try:
            feed = feedparser.parse(url)
            return [
                entry for entry in feed.entries[:10]
                if self._is_breaking_news(entry.title)
            ][:2]
        except Exception as e:
            logger.error(f"Feed error: {str(e)}")
            return []

    def _create_tweet(self, entry) -> str:
        return f"🚨 BREAKING: {entry.title}\n🔗 {entry.link}"

    def _can_post(self):
        time_since_last = time.time() - self.last_post_time
        if time_since_last < POST_INTERVAL:
            logger.warning(f"Too soon to post. Wait {POST_INTERVAL - time_since_last:.0f}s")
            return False
        return True

    def post_update(self, entry):
        if not self._can_post():
            return False

        content_hash = hashlib.md5(entry.title.encode()).hexdigest()
        if content_hash in self.history['posts']:
            logger.info(f"SKIPPED: Already posted: {entry.title[:60]}...")
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
        logger.info("=== AI X BOT STARTED ===")
        with open('sources.txt') as f:
            sources = [s.strip() for s in f if s.strip()]

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = executor.map(self._process_feed, sources)
            all_entries = [entry for feed in results for entry in feed]

        new_posts = 0
        for entry in all_entries:
            if new_posts >= MAX_POSTS:
                break
            if self.post_update(entry):
                new_posts += 1
                time.sleep(POST_INTERVAL)

        with open(HISTORY_FILE, 'w') as f:
            json.dump(self.history, f, indent=2)

        logger.info(f"Total posts: {self.history['count']}")
        logger.info("=== AI X BOT COMPLETED ===")

if __name__ == "__main__":
    bot = AIXBot()
    bot.run()
