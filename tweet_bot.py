import tweepy
import requests
import random
import time
from datetime import datetime
import os
import feedparser
import nltk
import ssl
from bs4 import BeautifulSoup
from readability import Document
from newspaper import Article
from nltk.data import find

# ===== INITIAL SETUP =====
# Unset proxy variables
for proxy_var in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']:
    os.environ.pop(proxy_var, None)

# NLTK setup
def ensure_punkt():
    try:
        find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True, download_dir=os.path.expanduser('~/.nltk_data'))

nltk.data.path.append(os.path.expanduser('~/.nltk_data'))
ensure_punkt()

# ===== API CONFIGURATION =====
# Initialize Twitter clients
write_client = tweepy.Client(
    consumer_key=os.getenv("API_KEY"),
    consumer_secret=os.getenv("API_SECRET"),
    access_token=os.getenv("ACCESS_TOKEN"),
    access_token_secret=os.getenv("ACCESS_SECRET"),
    wait_on_rate_limit=True
)

# ===== CONTENT SOURCES =====
RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.npr.org/1001/rss.xml"
]

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
]

CURIOSITY_PROMPTS = [
    "Did you know? The average cloud weighs about 1.1 million pounds! ☁️ #FunFact",
    "Question of the day: What's one skill you wish you learned earlier in life? 🤔 #DailyThought",
    "Mind-blowing fact: Bananas are berries, but strawberries aren't! 🍌 #FoodScience",
    "Conversation starter: What's your favorite 'useless' fact? 💭 #TriviaTime",
    "Nature fact: A single oak tree can produce about 10 million acorns in its lifetime! 🌳 #NatureWonders","Did you know? The average person spends 6 months of their life waiting for red lights to turn green. 🚦 #FunFact",
    "Question of the day: If you could instantly master any skill, what would it be? 🤔 #DailyThought",
    "Mind-blowing fact: Honey never spoils. Archaeologists have found edible honey in ancient Egyptian tombs! 🍯 #WowFact",
    "Conversation starter: What's one thing you believed as a child that turned out to be completely wrong? 👶 #Throwback",
    "Fascinating science: Octopuses have three hearts and blue blood! 🐙 #NatureIsAmazing",
    "Thought experiment: If you could have dinner with any historical figure, who would it be? ⏳ #TimeTravel",
    "Amazing nature fact: A single teaspoon of soil contains more microorganisms than there are people on Earth! 🌱 #Science"
]

# ===== CONTENT PROCESSING =====
def extract_full_text(url):
    """Extract article text with multiple fallback methods"""
    try:
        # Configure SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        # Try newspaper3k first
        article = Article(url, language='en')
        article.download()
        article.parse()
        if len(article.text) > 300:
            return article.text
            
        # Fallback to BeautifulSoup
        response = requests.get(
            url,
            headers={'User-Agent': random.choice(USER_AGENTS)},
            verify=False,
            timeout=15
        )
        soup = BeautifulSoup(response.text, 'lxml')
        for element in soup(['script', 'style', 'nav', 'footer']):
            element.decompose()
        text = ' '.join(soup.stripped_strings)
        if len(text) > 300:
            return text
            
        # Final fallback to readability
        doc = Document(response.text)
        return doc.summary()
        
    except Exception as e:
        print(f"❌ Extraction failed: {str(e)}")
        return None

def summarize_text(text):
    """Generate simple summary without external APIs"""
    sentences = nltk.sent_tokenize(text)
    if len(sentences) >= 2:
        return f"{sentences[0]} {sentences[1]}"
    return text[:140] + "..."

# ===== CONTENT GENERATION =====
def get_news_content():
    """Generate news content with engaging fallbacks"""
    try:
        feed = feedparser.parse(random.choice(RSS_FEEDS))
        if not feed.entries:
            return random.choice(CURIOSITY_PROMPTS)
            
        entry = random.choice(feed.entries[:5])  # Only recent articles
        article_text = extract_full_text(entry.link)
        
        if article_text and len(article_text) >= 300:
            summary = summarize_text(article_text)
            if summary:
                return f"📰 {summary}\n\n🔗 {entry.link} #News"
        
        # Fallback to engaging content
        prompt = random.choice(CURIOSITY_PROMPTS)
        if entry:
            return f"{prompt}\n\n📚 Read more: {entry.link}"
        return prompt
        
    except Exception as e:
        print(f"❌ Content Error: {str(e)}")
        return random.choice(CURIOSITY_PROMPTS)

# ===== POSTING ENGINE =====        
def post_tweet():
    """Main posting function with error handling"""
    try:
        content = get_news_content()
        
        # Ensure proper length
        content = content[:275] + ("..." if len(content) > 275 else "")
        
        # Post with rate limit handling
        for retry in range(3):
            try:
                write_client.create_tweet(text=content)
                print(f"✅ Posted at {datetime.now()}: {content[:60]}...")
                break
            except tweepy.TweepyException as e:
                wait_time = (10 * (2 ** retry))
                print(f"🚨 Post Failed: {str(e)}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

    except Exception as e:
        print(f"❗ Critical Error: {str(e)}")

if __name__ == "__main__":
    post_tweet()
    time.sleep(300)  # 5 minute delay between runs
