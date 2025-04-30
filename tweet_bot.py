import tweepy
import feedparser
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import os
import re
import time
import random

# ===== CONFIGURATION =====
TRENDING_KEYWORDS = {
    'india-pakistan': ['border', 'kashmir', 'diplomacy', 'talks', 'conflict'],
    'global-crisis': ['war', 'sanctions', 'summit', 'crisis'],
    'economic': ['inflation', 'market', 'GDP', 'trade']
}

NEWS_SOURCES = [
    {
        'name': 'Reuters',
        'rss': 'http://feeds.reuters.com/reuters/topNews',
        'weight': 1.2,
        'attribution': 'Source: Reuters'
    },
    {
        'name': 'BBC',
        'rss': 'http://feeds.bbci.co.uk/news/world/asia/india/rss.xml',
        'weight': 1.1,
        'attribution': 'Source: BBC'
    }
]

# ===== TWITTER CLIENT =====
def initialize_twitter_client():
    return tweepy.Client(
        consumer_key=os.getenv("API_KEY"),
        consumer_secret=os.getenv("API_SECRET"),
        access_token=os.getenv("ACCESS_TOKEN"),
        access_token_secret=os.getenv("ACCESS_SECRET"),
        wait_on_rate_limit=True
    )

# ===== CONTENT PROCESSING =====
class ContentProcessor:
    def __init__(self):
        self.trending_phrases = self.get_google_trends()
        
    def get_google_trends(self):
        """Fetch current trending search terms"""
        try:
            response = requests.get(
                "https://trends.google.com/trends/api/dailytrends?geo=IN",
                timeout=10
            )
            data = response.json()
            return [t['title']['query'].lower() 
                    for t in data['default']['trendingSearchesDays'][0]['trendingSearches']][:5]
        except Exception as e:
            print(f"Trend fetch error: {str(e)}")
            return []

    def calculate_virality(self, article):
        """Score article based on multiple factors"""
        score = 0
        content = f"{article['title']} {article.get('summary', '')}".lower()
        
        # Trending keywords match
        for category, keywords in TRENDING_KEYWORDS.items():
            score += sum(content.count(kw) * 10 for kw in keywords)
            
        # Google Trends match
        score += sum(content.count(trend) * 20 for trend in self.trending_phrases)
        
        # Freshness score (last 6 hours)
        if (datetime.now() - article['published']).seconds < 21600:
            score *= 1.5
            
        # Source credibility
        score *= article['source']['weight']
        
        return score

# ===== NEWS HANDLING =====
def fetch_news():
    processor = ContentProcessor()
    articles = []
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source['rss'])
            for entry in feed.entries[:15]:  # Latest 15 articles
                articles.append({
                    'title': entry.title,
                    'summary': entry.get('description', ''),
                    'link': entry.link,
                    'published': datetime(*entry.published_parsed[:6]),
                    'source': source
                })
        except Exception as e:
            print(f"Failed to process {source['name']}: {str(e)}")
    
    # Score and select top articles
    for article in articles:
        article['score'] = processor.calculate_virality(article)
        
    return sorted(articles, key=lambda x: x['score'], reverse=True)[:3]

def create_tweet_content(article):
    """Generate compliant tweet with key points"""
    try:
        # Extract main points
        key_points = extract_key_points(article['link'])
        
        # Build tweet structure
        tweet = f"🚨 {article['title']}\n\n"
        tweet += f"📌 Key Developments:\n{key_points}\n\n"
        tweet += f"{article['source']['attribution']} 🔗 {article['link']}"
        
        return tweet[:280]
    
    except Exception as e:
        print(f"Content creation error: {str(e)}")
        return f"📢 Breaking: {article['title']} 🔗 {article['link']}"

def extract_key_points(url):
    """Safe content extraction from article"""
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Focus on article body
        body = soup.find('article') or soup.find('div', class_=re.compile('content|body'))
        paragraphs = [p.get_text().strip() for p in body.find_all('p')] if body else []
        
        # Select impactful sentences
        key_points = [
            p for p in paragraphs 
            if 50 < len(p) < 200 and 
            any(kw in p.lower() for kw in ['important', 'critical', 'announced', 'confirmed'])
        ][:3]
        
        return '\n'.join(key_points)[:180] + '...'
    
    except Exception as e:
        print(f"Content extraction failed: {str(e)}")
        return "Key details currently emerging..."

# ===== MAIN EXECUTION =====
def execute_bot():
    client = initialize_twitter_client()
    
    try:
        articles = fetch_news()
        if not articles:
            raise ValueError("No trending articles found")
            
        tweet = create_tweet_content(articles[0])
        response = client.create_tweet(text=tweet)
        
        if response.errors:
            print(f"Twitter API error: {response.errors[0]['detail']}")
        else:
            print(f"✅ Successfully posted at {datetime.now()}")
            
    except Exception as e:
        print(f"❌ Critical failure: {str(e)}")
        # Emergency fallback
        client.create_tweet(
            text="⚠️ Breaking news update delayed - stay tuned for updates! #NewsAlert"
        )

if __name__ == "__main__":
    execute_bot()
    time.sleep(3600)  # 1 hour cooldown
