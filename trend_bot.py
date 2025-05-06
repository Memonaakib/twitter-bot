#!/usr/bin/env python3 import os import time import json import hashlib import logging from datetime import datetime

import tweepy

─── Configuration ──────────────────────────────────────────────

TREND_FILE = "trending.json" HISTORY_FILE = "usage.json"

─── Logging Setup ──────────────────────────────────────────────

logging.basicConfig( format="%(asctime)s - AI X BOT - %(levelname)s - %(message)s", level=logging.INFO, datefmt="%Y-%m-%d %H:%M:%S" ) logger = logging.getLogger("AI_X_Bot")

class AIXBot: def init(self): self.client = tweepy.Client( bearer_token=os.getenv("BEARER_TOKEN"), consumer_key=os.getenv("API_KEY"), consumer_secret=os.getenv("API_SECRET"), access_token=os.getenv("ACCESS_TOKEN"), access_token_secret=os.getenv("ACCESS_SECRET"), wait_on_rate_limit=True ) self.history = self._load_history()

def _load_history(self):
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'posts': {}, 'count': 0}

def _save_history(self):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(self.history, f, indent=2)

def _already_posted(self, title):
    content_hash = hashlib.md5(title.encode()).hexdigest()
    return content_hash in self.history['posts']

def _mark_posted(self, title):
    content_hash = hashlib.md5(title.encode()).hexdigest()
    self.history['posts'][content_hash] = datetime.now().isoformat()
    self.history['count'] += 1
    self._save_history()

def _create_tweet(self, article):
    return f"🔥 {article['title']}\n🔗 {article['link']}"

def post_trending_article(self):
    try:
        with open(TREND_FILE) as f:
            trending = json.load(f)

        for article in trending:
            if not self._already_posted(article['title']):
                tweet = self._create_tweet(article)
                self.client.create_tweet(text=tweet)
                self._mark_posted(article['title'])
                logger.info(f"Posted: {article['title'][:80]}...")
                return True

        logger.info("No new articles to post.")
        return False

    except Exception as e:
        logger.error(f"Error posting tweet: {str(e)}")
        return False

if name == "main": bot = AIXBot() bot.post_trending_article()

