import tweepy
import requests
import time
import random

# ===== TWITTER KEYS =====
API_KEY = "WS0dEJQqZ53qPhDUQttDacVjB"
API_SECRET = "rU0YC5JI6f3CalmLiY2iX9Ojz9gN8OQutWEGCLvUbI8ZO8v33M"
ACCESS_TOKEN = "1884012353815207939-qjRXrL3uSsabTUKyxDZny7mIPL7Ljk"
ACCESS_SECRET = "aPWyjzESx8ozzDGy9qMqFXveRYuDrdseq7rG78OCD6IAi"

# ===== AUTO-CONFIG =====
auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

# ===== CONTENT SOURCES =====
CELEBS = ["elonmusk", "BarackObama", "BillGates", "Oprah", "taylorswift13"]

def get_celeb_tweet():
    try:
        # Get latest tweets from random celeb
        celeb = random.choice(CELEBS)
        tweets = api.user_timeline(screen_name=celeb, count=5, tweet_mode='extended')
        # Pick most-liked tweet
        best_tweet = max(tweets, key=lambda x: x.favorite_count)
        return f"{best_tweet.full_text}\n\n- {celeb} #Trending"
    except:
        return None
    
def post_tweet():
    content = get_celeb_tweet() or "🌟 Inspiration coming soon! #AI"
    api.update_status(content)
    
    if content:
        api.update_status(content)
        print(f"Posted: {content}")
    else:
        print("what is current news to cover")

# ===== RUN =====
if __name__ == "__main__":
    post_tweet()
