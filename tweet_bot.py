import tweepy
import requests
import random
import time
from datetime import datetime
import json
import os
import feedparser
import nltk
import ssl
from bs4 import BeautifulSoup
from readability import Document
from newspaper import Article
from nltk.data import find
# at the top, unset any proxy envs to avoid the proxies kwarg issue:
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
from openai import OpenAI
def ensure_punkt():
    try:
        find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True, download_dir=os.path.expanduser('~/.nltk_data'))

# Set NLTK data path so both local runs and CI use the same cache
nltk.data.path.append(os.path.expanduser('~/.nltk_data'))

# Only downloads once (or if truly missing)
ensure_punkt()

# ===== API CONFIGURATION =====
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Twitter clients
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
RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.reutersagency.com/feed/?best-topics=business&post_type=best"
]

# ===== CONTENT PROCESSING =====
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
]

def extract_full_text(url):
    """Extract article text with multiple fallback methods"""
    try:
        # Configure SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # First try: newspaper3k
        article = Article(url, language='en')
        article.download()
        article.parse()
        if len(article.text) > 300:
            return article.text
            
        # Fallback 1: BeautifulSoup
        response = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, verify=False, timeout=15)
        soup = BeautifulSoup(response.text, 'lxml')
        for element in soup(['script', 'style', 'nav', 'footer']):
            element.decompose()
        text = ' '.join(soup.stripped_strings)
        if len(text) > 300:
            return text
            
        # Fallback 2: readability
        doc = Document(response.text)
        return doc.summary()
        
    except Exception as e:
        print(f"❌ Extraction failed: {str(e)}")
        return None
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def summarize_text(text):
    """Generate AI summary using OpenAI"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Summarize this in 2 short, engaging sentences:\n\n{text[:3000]}"
            }],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ Summarization error: {str(e)}")
        return None

# ===== CONTENT GENERATION =====
def get_news_content():
    """Generate news content from RSS feeds"""
    try:
        feed = feedparser.parse(random.choice(RSS_FEEDS))
        if not feed.entries:
            return None
            
        entry = random.choice(feed.entries)
        article_text = extract_full_text(entry.link)
        
        if not article_text or len(article_text) < 300:
            return None
            
        summary = summarize_text(article_text)
        if not summary:
            return None
            
        return f"📰 {summary}\n\n🔗 {entry.link} #News #AI"
        
    except Exception as e:
        print(f"❌ News Error: {str(e)}")
        return None

# ===== POSTING ENGINE =====        
def post_tweet():
    """Main posting function with error handling"""
    try:
        if tracker.get_usage()['writes'] >= 495:
            print("⚠️ Monthly write limit reached")
            return
            
        content = None
        attempts = 0
        
        # Attempt to generate content
        while not content and attempts < 3:
            content = get_news_content()
            attempts += 1
            time.sleep(1)
            
        # Fallback content
        if not content:
            content = "🌟 Stay curious! More insights coming soon. #Knowledge #AI"
        else:
            content = content[:275] + " #Breaking"  # Ensure proper length
            
        # Attempt to post
        retries = 0
        while retries < 3:
            try:
                write_client.create_tweet(text=content)
                tracker.log_write()
                print(f"✅ Posted at {datetime.now()}: {content[:60]}...")
                break
            except tweepy.TweepyException as e:
                print(f"🚨 Post Failed: {str(e)}")
                time.sleep(5 ** retries)
                retries += 1
                
        # Update usage

        with open("usage.json", "w") as f:
            json.dump(tracker.get_usage(), f)

    except Exception as e:
        print(f"❗ Critical Error: {str(e)}")

if __name__ == "__main__":
    post_tweet()
