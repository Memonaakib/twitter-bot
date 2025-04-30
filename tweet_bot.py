import tweepy
import requests
import random
import time
from datetime import datetime
import os
import feedparser
import nltk
import ssl
import re
from bs4 import BeautifulSoup
from nltk.data import find

# ===== INITIAL SETUP =====
# Unset proxy variables
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(proxy_var, None)

# NLTK setup
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
stop_words = set(nltk.corpus.stopwords.words('english'))

def ensure_punkt():
    try:
        find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True, download_dir=os.path.expanduser('~/.nltk_data'))

nltk.data.path.append(os.path.expanduser('~/.nltk_data'))
ensure_punkt()

# ===== API CONFIGURATION =====
# Initialize Twitter client with enhanced rate limiting
write_client = tweepy.Client(
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_SECRET"),
    wait_on_rate_limit=True
)

# ===== CONTENT SOURCES =====
TRENDING_KEYWORDS = ["India", "Pakistan", "conflict", "border", "Kashmir", "diplomatic"]
RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
    "https://www.reutersagency.com/feed/?best-region=asia",
    "https://www.aljazeera.com/xml/rss/all.xml"
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
]

# ===== CONTENT PROCESSING =====
def extract_full_text(url):
    """Enhanced article extraction with SSL handling"""
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # Try newspaper3k first
        article = Article(url, language='en', fetch_images=False)
        article.download()
        article.parse()
        if len(article.text) > 300:
            return article.text

        # Fallback to BeautifulSoup
        response = requests.get(url, headers={'User-Agent': random.choice(USER_AGENTS)}, 
                              verify=False, timeout=15)
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Remove unwanted elements
        for tag in ['script', 'style', 'nav', 'footer', 'aside', 'header']:
            for element in soup(tag):
                element.decompose()
                
        main_content = soup.find('article') or soup.find('main') or soup
        return ' '.join(main_content.stripped_strings)[:3000]
        
    except Exception as e:
        print(f"❌ Extraction error: {str(e)}")
        return None

def summarize_content(text):
    """Advanced summarization using key phrase extraction"""
    try:
        # Clean and preprocess text
        text = re.sub(r'\s+', ' ', text)
        sentences = nltk.sent_tokenize(text)
        
        # Calculate word frequencies
        word_freq = {}
        for word in nltk.word_tokenize(text.lower()):
            if word.isalnum() and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
                
        # Score sentences
        sentence_scores = {}
        for idx, sentence in enumerate(sentences):
            for word in nltk.word_tokenize(sentence.lower()):
                if word in word_freq:
                    sentence_scores[idx] = sentence_scores.get(idx, 0) + word_freq[word]
        
        # Select top 2-3 sentences
        top_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:3]
        summary = ' '.join([sentences[i] for i in sorted(top_sentences)])
        
        # Ensure complete sentences
        if not summary.endswith(('.', '!', '?')):
            summary = summary.rsplit('.', 1)[0] + '...'
            
        return summary[:200]
        
    except Exception as e:
        print(f"❌ Summarization error: {str(e)}")
        return text[:200] + ('...' if len(text) > 200 else '')

# ===== CONTENT GENERATION =====
def get_trending_content():
    """Prioritize trending geopolitical news"""
    try:
        feed = feedparser.parse(random.choice(RSS_FEEDS))
        
        # Find trending articles first
        trending_entries = [
            e for e in feed.entries[:20]
            if any(kw.lower() in (e.title + e.description).lower() 
                 for kw in TRENDING_KEYWORDS)
        ]
        
        entry = random.choice(trending_entries) if trending_entries else random.choice(feed.entries[:10])
        article_text = extract_full_text(entry.link) or f"{entry.title}. {entry.description}"
        
        summary = summarize_content(article_text)
        return format_tweet(entry, summary)
        
    except Exception as e:
        print(f"❌ Content error: {str(e)}")
        return "🚨 Major geopolitical developments unfolding. Stay tuned for updates. #BreakingNews"

def format_tweet(entry, summary):
    """Create structured tweet with trending hashtags"""
    hashtags = "#BreakingNews #WorldAffairs"
    if any(kw.lower() in entry.title.lower() for kw in ["India", "Pakistan"]):
        hashtags += " #IndiaPakistan"
    
    tweet = f"🚨 {entry.title}\n\n{summary}\n\n🔗 {entry.link} {hashtags}"
    return tweet[:280]

# ===== POSTING ENGINE =====        
def post_tweet():
    """Enhanced posting with rate limit buffers"""
    try:
        content = get_trending_content()
        
        # Post with exponential backoff
        for attempt in range(3):
            try:
                response = write_client.create_tweet(text=content)
                if response.errors:
                    raise tweepy.TweepyException(response.errors[0]['detail'])
                print(f"✅ Posted at {datetime.now()}: {content[:60]}...")
                time.sleep(60)  # Buffer between posts
                return
                
            except tweepy.TooManyRequests as e:
                reset_time = int(e.response.headers.get('x-rate-limit-reset', 900))
                wait_time = max(reset_time - time.time() + 60, 300)  # Minimum 5 min
                print(f"⏳ Rate limited. Waiting {wait_time//60} minutes...")
                time.sleep(wait_time)
                
            except tweepy.TweepyException as e:
                print(f"🚨 Post failed: {str(e)}")
                time.sleep(10 * (2 ** attempt))

        print("⚠️ Failed after 3 attempts")
        
    except Exception as e:
        print(f"❗ Critical error: {str(e)}")
        # Fallback tweet
        write_client.create_tweet(
            text="⚠️ Breaking news update delayed. Stay tuned for important developments. #NewsAlert"
        )

if __name__ == "__main__":
    post_tweet()
    time.sleep(3600)  # 1 hour between runs (max 24/day)
