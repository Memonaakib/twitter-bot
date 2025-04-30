import tweepy
import feedparser
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from bs4 import BeautifulSoup
import os
import re
import time
import random

# ===== CONFIGURATION =====
TRENDING_KEYWORDS = {
    'conflict': ['border', 'clash', 'tension', 'diplomacy', 'talks'],
    'economy': ['inflation', 'market', 'GDP', 'trade', 'currency'],
    'disaster': ['earthquake', 'flood', 'cyclone', 'rescue', 'alert']
}

NEWS_SOURCES = [
    {
        'name': 'Reuters',
        'rss': 'http://feeds.reuters.com/reuters/topNews',
        'weight': 1.2,
        'attribution': 'Source: Reuters'
    },
    {
        'name': 'Livemint',
        'rss': 'https://www.livemint.com/rss/news',
        'weight': 1.0,
        'attribution': 'Source: Livemint'
    },
    {
        'name': 'BBC',
        'rss': 'http://feeds.bbci.co.uk/news/world/asia/india/rss.xml',
        'weight': 1.1,
        'attribution': 'Source: BBC'
    }
]

# ===== TWITTER CLIENT =====
def init_twitter_client():
    return tweepy.Client(
        consumer_key=os.getenv("API_KEY"),
        consumer_secret=os.getenv("API_SECRET"),
        access_token=os.getenv("ACCESS_TOKEN"),
        access_token_secret=os.getenv("ACCESS_SECRET"),
        wait_on_rate_limit=True
    )

# ===== VIRALITY ANALYSIS =====
class ViralNewsDetector:
    def __init__(self):
        self.trends = self.get_google_trends()
        
    def get_google_trends(self):
        try:
            response = requests.get(
                "https://trends.google.com/trends/api/dailytrends?geo=IN",
                timeout=10
            )
            return [t['title']['query'].lower() 
                    for t in response.json()['default']['trendingSearchesDays'][0]['trendingSearches']][:5]
        except:
            return []
    
    def calculate_score(self, article):
        score = 0
        content = f"{article['title']} {article['summary']}".lower()
        
        # Trend matching
        for trend in self.trends:
            if trend in content:
                score += 50
                
        # Keyword matching
        for category, keywords in TRENDING_KEYWORDS.items():
            score += sum(content.count(kw) * 10 for kw in keywords)
            
        # Freshness score
        if (datetime.now() - article['published']).seconds < 21600:  # 6 hours
            score *= 1.5
            
        # Source credibility
        score *= article['source']['weight']
        
        return score

# ===== NEWS PROCESSING =====
def fetch_articles():
    detector = ViralNewsDetector()
    articles = []
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source['rss'])
            for entry in feed.entries[:10]:  # Only latest 10
                articles.append({
                    'title': entry.title,
                    'summary': entry.get('description', ''),
                    'link': entry.link,
                    'published': datetime(*entry.published_parsed[:6]),
                    'source': source
                })
        except Exception as e:
            print(f"Failed to fetch {source['name']}: {str(e)}")
    
    # Score and sort articles
    for article in articles:
        article['score'] = detector.calculate_score(article)
        
    return sorted(articles, key=lambda x: x['score'], reverse=True)[:5]

def format_article(article):
    """Create compliant tweet with attribution"""
    try:
        text = f"🚨 {article['title']}\n\n"
        text += f"📌 Key points:\n{extract_key_points(article['link'])}\n\n"
        text += f"{article['source']['attribution']} 🔗 {article['link']}"
        return text[:280]
    except:
        return f"📢 Breaking news update 🔗 {article['link']}"

def extract_key_points(url):
    """Safe content extraction"""
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Focus on article body
        body = soup.find('article') or soup.find('div', class_=re.compile('body'))
        paragraphs = [p.get_text().strip() for p in body.find_all('p')] if body else []
        
        # Select key sentences
        key_points = [p for p in paragraphs if 50 < len(p) < 200][:3]
        return '\n'.join(key_points)[:180] + '...'
    except:
        return "Important developments unfolding..."

# ===== MAIN EXECUTION =====
def post_viral_update():
    client = init_twitter_client()
    
    try:
        articles = fetch_articles()
        if not articles:
            raise ValueError("No articles found")
            
        tweet = format_article(articles[0])
        response = client.create_tweet(text=tweet)
        
        if response.errors:
            print(f"Twitter error: {response.errors[0]['detail']}")
        else:
            print(f"✅ Posted viral update: {tweet[:60]}...")
            
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        # Fallback tweet
        client.create_tweet(
            text="⚠️ Breaking news update delayed. Stay tuned! #NewsAlert"
        )

if __name__ == "__main__":
    post_viral_update()
    time.sleep(3600)  # 1 hour between runs
