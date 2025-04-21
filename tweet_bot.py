# tweet_bot.py
import tweepy
import requests
import random
import time
from datetime import datetime

# ===== TWITTER AUTH ===== (OAuth 1.0a)
API_KEY = "dpv4WE2Fz6qXb3zYaLi47mnTt"
API_SECRET = "BbJKl0sAIoOo6o6gD8HekZRpfQujIPKyBEPb8b5dZSbttLtW6I"
ACCESS_TOKEN = "1884012353815207939-xIWdpeLviThza87zG03KXHqWgC0vhj"
ACCESS_SECRET = "ahSKHOVkNveMgJ1NLaqVBrrTU8ivZhxxCGp3oaD1PplfT"

auth = tweepy.OAuth1UserHandler(
    API_KEY, API_SECRET,
    ACCESS_TOKEN, ACCESS_SECRET
)
api = tweepy.API(auth, wait_on_rate_limit=True)

# ===== CONTENT SOURCES =====
NEWS_API = "ec31e15ee7b34f4d8aef23fca516f9e0"
CELEBS = [
    # India
    "narendramodi", "AmitabhBachchan", "SrBachchan", "iHrithik", "deepikapadukone",
    "PMOIndia", "RahulGandhi", "akshaykumar", "priyankachopra", "AnushkaSharma",
    
    # United States
    "BarackObama", "JoeBiden", "elonmusk", "taylorswift13", "TheRock",
    "Oprah", "BillGates", "JeffBezos", "tim_cook", "Schwarzenegger",
    
    # China
    "XHNews", "GlobalTimes", "JackMa", "Yaoming", "ZhangZiyi",
    "LiKeqiang", "WangYidi", "realKrisWu", "JayChou", "LiuYifei",
    
    # Japan
    "AbeShinzo", "HayaoMiyazaki", "YoshihideSuga", "taku2015", "hiroshima_peace",
    "ShinzoMiyazaki", "HarukiMurakami", "ShinyaYamanaka", "maki_osawa", "nagashima_ichiro",
    
    # Gaza/Palestine
    "RashidaTlaib", "MohammedAssaf", "MaiRawah", "DrEbaa", "GazaYouthBrigade",
    "Palestine_UN", "Mustafa_Barghouti", "HaninZoabi", "MunaElKurd", "Gazanews",
    
    # Global Tech
    "sundarpichai", "satyanadella", "AndrewYNg", "ylecun", "danielgross",
    "SamAltman", "BrianArmstrong", "VitalikButerin", "cdixon", "jack",
    
    # Global Activists
    "GretaThunberg", "Malala", "EmmaWatson", "LeonardoDiCaprio", "algore",
    "JaneGoodallInst", "VanessaNakate", "XiyeBastida", "chelseahandler", "simone_biles",
    
    # Business Leaders
    "WarrenBuffett", "CarlosSlim", "MasayoshiSon", "richardbranson", "MukeshAmbani",
    "RayDalio", "JamieDimon", "guyraz", "AriannaHuff", "dhh",
    
    # Media Personalities
    "iamsrk", "shakira", "BTS_twt", "jimmyfallon", "ConanOBrien",
    "BBCWorld", "CNN", "AJEnglish", "Reuters", "nytimes",
    
    # Sports Icons
    "Cristiano", "neymarjr", "KingJames", "stephencurry30", "UsainBolt",
    "serenawilliams", "naomiOsaka", "messi", "rogerfederer", "FIFAcom"
]

FALLBACK_TWEETS = [
    "🌟 Great ideas deserve to be shared! #Inspiration",
    "💡 Curiosity fuels innovation. Stay curious! #Motivation",
    "🚀 The future is built today. What's your next step? #AI"
]

def get_celeb_tweet():
    try:
        celeb = random.choice(CELEBS)
        tweets = api.user_timeline(screen_name=celeb, count=5, tweet_mode='extended')
        valid_tweets = [t for t in tweets if not t.retweeted and not hasattr(t, 'retweeted_status')]
        
        if not valid_tweets:
            return None
            
        best_tweet = max(valid_tweets, key=lambda x: x.favorite_count)
        return f"{best_tweet.full_text}\n\n- @{celeb} #Trending"
        
    except Exception as e:
        print(f"Celeb Error: {str(e)}")
        return None

def get_news():
    try:
        response = requests.get(
            f"https://newsapi.org/v2/top-headlines?category=business&apiKey=ec31e15ee7b34f4d8aef23fca516f9e0",
            timeout=15
        )
        
        if response.status_code != 200:
            print(f"NewsAPI HTTP Error: {response.status_code}")
            return None
            
        news = response.json()
        
        if news.get('status') != 'ok':
            print(f"NewsAPI Error: {news.get('message', 'Unknown')}")
            return None
            
        articles = news.get('articles', [])
        valid_articles = [
            a for a in articles 
            if a.get('title') 
            and len(a['title']) > 20 
            and not "[Removed]" in a['title']
        ]
        
        if not valid_articles:
            print("No valid articles")
            return None
            
        article = random.choice(valid_articles)
        return f"📰 {article['title'].strip()}\n\n{article.get('url', '')} #News"
        
    except Exception as e:
        print(f"News Error: {str(e)}")
        return None

def post_tweet():
    try:
        content = get_celeb_tweet() or get_news() or random.choice(FALLBACK_TWEETS)
        
        # Ensure compliance with Twitter rules
        content = content[:280]  # Character limit
        if "#AI" not in content:
            content += " #AI"  # Automation disclosure
            
        api.update_status(content)
        print(f"Posted at {datetime.now()}:\n{content}")
        
    except tweepy.TweepyException as e:
        print(f"Posting Failed: {str(e)}")

if __name__ == "__main__":
    post_tweet()
    time.sleep(5)  # Prevent rapid exit
