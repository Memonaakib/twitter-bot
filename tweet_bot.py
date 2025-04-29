import tweepy
import requests
import random
import time
from datetime import datetime
import json
import os
import feedparser
from newspaper import Article
import openai
import nltk
nltk.download('punkt')
# ===== API CONFIG =====
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

read_client = tweepy.Client(bearer_token=BEARER_TOKEN)
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

RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.cnn.com/rss/edition.rss",
    "https://www.reutersagency.com/feed/?best-topics=business&post_type=best"
]

# ===== ARTICLE EXTRACTOR =====
from newspaper import Article, Config
def extract_full_text(url):
    try:
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 15
        config.keep_article_html = True
        
        article = Article(url, config=config)
        article.download()
        article.parse()
        article.nlp()  # Required for proper text extraction
        
        return article.text
    except Exception as e:
        print(f"❌ Article extraction failed: {e}")
        return None

# ===== SUMMARIZER =====
def summarize_text(text):
    try:
        prompt = f"Summarize this news article in 2-3 simple, readable sentences for a general audience:\n\n{text}"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=120
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"❌ Summarization error: {e}")
        return None

# ===== CELEB TWEETS (Fallback) =====
CELEB_CACHE = {}
CACHE_EXPIRY = 3600  # 1 hour

def get_cached_celeb_content():
    try:
        now = time.time()
        celeb = random.choice(GLOBAL_CELEBS)
        
        if celeb in CELEB_CACHE and now - CELEB_CACHE[celeb]['timestamp'] < CACHE_EXPIRY:
            tweets = CELEB_CACHE[celeb]['tweets']
        else:
            user = read_client.get_user(username=celeb)
            tracker.log_read()
            tweets = read_client.get_users_tweets(user.data.id, max_results=3)
            tracker.log_read()
            CELEB_CACHE[celeb] = {'tweets': tweets.data, 'timestamp': now}
        
        valid_tweets = [t for t in tweets.data if not t.text.startswith("RT ")]
        if not valid_tweets:
            return None
            
        best_tweet = max(valid_tweets, key=lambda x: x.public_metrics['like_count'])
        return f"{best_tweet.text}\n\n- @{celeb} #GlobalVoice"
        
    except Exception as e:
        print(f"❌ Celeb Error: {str(e)}")
        return None

# ===== GET NEWS CONTENT =====
def get_news_content():
    try:
        feed = feedparser.parse(random.choice(RSS_FEEDS))
        if not feed.entries:
            return None
        entry = random.choice(feed.entries)
        url = entry.link

        full_text = extract_full_text(url)
        if not full_text or len(full_text) < 300:
            return None

        summary = summarize_text(full_text)
        if not summary:
            return None

        return f"📰 {summary}\nRead more: {url} #News"
    except Exception as e:
        print(f"❌ News Error: {str(e)}")
        return None

# ===== MAIN POST FUNCTION =====        
def post_tweet():
    try:
        if tracker.get_usage()['writes'] >= 495:
            print("⚠️ Monthly write limit reached")
            return
        
        content = None
        attempts = 0
        
        while not content and attempts < 3:
            content = get_news_content() or get_cached_celeb_content()
            attempts += 1
            
        if not content:
            content = "🌍 Stay informed! More insights coming soon. #Knowledge"
        
        content = content[:275] + " #AI"
        
        retries = 0
        while retries < 3:
            try:
                write_client.create_tweet(text=content)
                tracker.log_write()
                print(f"✅ Posted at {datetime.now()}: {content[:50]}...")
                break
            except tweepy.TweepyException as e:
                print(f"🚨 Post Failed: {str(e)}")
                time.sleep(5 ** retries)
                retries += 1

        with open("usage.json", "w") as f:
            json.dump(tracker.get_usage(), f)

    except Exception as e:
        print(f"❗ Critical Error: {str(e)}")

if __name__ == "__main__":
    post_tweet()
