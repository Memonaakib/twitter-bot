# tweet_bot.py
import tweepy
import requests
import random
import time
from datetime import datetime
import json
import os

# ===== TWITTER V2 API CONFIG =====
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

# Initialize v2 Client with OAuth 1.0a
# For user data (READ operations)
read_client = tweepy.Client(bearer_token=BEARER_TOKEN)

# For posting (WRITE operations)
write_client = tweepy.Client(
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_SECRET
)
# ===== USAGE TRACKER =====
class UsageTracker:
    def __init__(self):
        self.reads = 0
        self.writes = 0
        
    def log_read(self, count=1):
        self.reads += count
        
    def log_write(self):
        self.writes += 1
        
    def get_usage(self):
        return {"reads": self.reads, "writes": self.writes}

tracker = UsageTracker()

# ===== CONTENT SOURCES ===== 
GLOBAL_CELEBS = [
    "narendramodi", "BarackObama", "elonmusk", "taylorswift13", "PMOIndia",
    "RahulGandhi", "SrBachchan", "XHNews", "AbeShinzo", "GretaThunberg",
    "Malala", "UN", "WHO", "BillGates", "nytimes", "BBCWorld", "Reuters"
]

NEWS_API = os.getenv("NEWS_API")
RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml,
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.npr.org/1001/rss.xml"
]

# ===== CONTENT GENERATORS =====
CELEB_CACHE = {}
CACHE_EXPIRY = 3600  # 1 hour

def get_cached_celeb_content():
    try:
        now = time.time()
        celeb = random.choice(GLOBAL_CELEBS)
        
        # Use cached data if available
        if celeb in CELEB_CACHE and now - CELEB_CACHE[celeb]['timestamp'] < CACHE_EXPIRY:
            tweets = CELEB_CACHE[celeb]['tweets']
            tracker.log_read(count=0)  # No API call used
        else:
            user = read_client.get_user(username=celeb)
            tracker.log_read()
            
            tweets = read_client.get_users_tweets(user.data.id, max_results=3)  # Reduced from 5
            tracker.log_read()
            
            CELEB_CACHE[celeb] = {
                'tweets': tweets.data,
                'timestamp': now
            }
        
        valid_tweets = [t for t in tweets.data if not t.text.startswith("RT ")]
        if not valid_tweets:
            return None
            
        best_tweet = max(valid_tweets, key=lambda x: x.public_metrics['like_count'])
        return f"{best_tweet.text}\n\n- @{celeb} #GlobalVoice"
        
    except Exception as e:
        print(f"Celeb Error: {str(e)}")
        return None
         if not user.data:
            print(f"❌ User {celeb} not found")
                return None
def get_news_content():
    try:
        # Try NewsAPI first
        if random.random() < 0.7 and tracker.get_usage()['reads'] < 90:
            response = requests.get(
                f"https://newsapi.org/v2/top-headlines?category=general&apiKey={NEWS_API}",
                timeout=10
            )
    
            news = response.json()
            
            if news.get('status') == 'ok' and news.get('articles'):
                article = random.choice(news['articles'])
                tracker.log_read()
                return f"📰 {article['title']}\n{article.get('url', '')} #News"
              
        # Fallback to RSS
        import feedparser
        feed = feedparser.parse(random.choice(RSS_FEEDS))
        entry = random.choice(feed.entries)
        return f"🌐 {entry.title}\n{entry.link} #Headlines"
        
    except Exception as e:
        print(f"News Error: {str(e)}")
        return None
            if not feed.entries:
                print("📭 Empty news feed")
                return None  
# ===== CORE FUNCTIONALITY =====        
def post_tweet():
    try:
        if tracker.get_usage()['writes'] >= 495:
            print("⚠️ Monthly write limit reached")
            return
            
        content = None
        attempts = 0
        
        while not content and attempts < 3:
            content = get_cached_celeb_content() or get_news_content()
            attempts += 1
            
        if not content:
            content = "🌍 Stay informed! More insights coming soon. #Knowledge"
            
        # Ensure compliance
        content = F"{content[:275]} + " #AI"  # Add required hashtag
        
       # Post with retries
        retries = 0
        while retries < 3:
            try:
                response = write_client.create_tweet(text=content)
                tracker.log_write()
                print(f"✅ Posted at {datetime.now()}: {content[:50]}...")
                break
            except tweepy.TweepyException as e:
                print(f"🚨 Post Failed: {str(e)}")
                time.sleep(5 ** retries)
                retries += 1
        
        # Log usage
        with open("usage.json", "w") as f:
            json.dump(tracker.get_usage(), f)
            
    except Exception as e:
        print(f"Critical Error: {str(e)}")

if __name__ == "__main__":
    post_tweet()
