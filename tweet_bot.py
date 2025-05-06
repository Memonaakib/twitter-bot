#!/usr/bin/env python3
import os
import json
import time
import hashlib
import logging
from datetime import datetime

import tweepy

# ─── Configuration ──────────────────────────────────────────────
TREND_FILE = "trending.json"
HISTORY_FILE = "usage.json"
MAX_POSTS_PER_DAY = 18

# ─── Logging Setup ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - AI X BOT - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("AI_X_TweetBot")

class TweetBot:
    def __init__(self):
        self.client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_SECRET"),
            wait_on_rate_limit=True
        )
        self.history = self._load_json(HISTORY_FILE, default={'posts': {}, 'count': 0})
        self.trends = self._load_json(TREND_FILE, default=[])

    def _load_json(self, path, default):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def _save_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _already_posted(self, title: str) -> bool:
        content_hash = hashlib.md5(title.encode()).hexdigest()
        return content_hash in self.history['posts']

    def _mark_as_posted(self, title: str):
        content_hash = hashlib.md5(title.encode()).hexdigest()
        self.history['posts'][content_hash] = datetime.utcnow().isoformat()
        self.history['count'] += 1
        self._save_json(HISTORY_FILE, self.history)

    def _format_tweet(self, item: dict) -> str:
        return f"🔥 {item['title']}\n\nSource: {item['source']}\n\n🔗 {item['url']}"

    def post(self):
        logger.info("Looking for a new trend to post...")

        for item in sorted(self.trends, key=lambda x: -x['score']):
            if not self._already_posted(item['title']):
                tweet = self._format_tweet(item)
                try:
                    self.client.create_tweet(text=tweet)
                    logger.info(f"Posted: {item['title'][:80]}...")
                    self._mark_as_posted(item['title'])
                    return
                except tweepy.TweepyException as e:
                    logger.error(f"Twitter error: {str(e)}")
                    return

        logger.info("No new trends to post.")

if __name__ == "__main__":
    bot = TweetBot()
    bot.post()
