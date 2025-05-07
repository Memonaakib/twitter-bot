
import requests 
import json from bs4 
import BeautifulSoup from datetime 
import datetime

TRENDING_URLS = [ "https://www.livemint.com/", "https://www.reuters.com/world/" ]

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def fetch_headlines(): headlines = [] for url in TRENDING_URLS: res = requests.get(url, headers=HEADERS) soup = BeautifulSoup(res.content, 'html.parser') if "livemint" in url: titles = soup.select('h2') elif "reuters" in url: titles = soup.select('h3')

for t in titles:
        title = t.get_text(strip=True)
        if len(title) > 30:
            headlines.append(title)
return list(set(headlines))

def save_trends(headlines): timestamp = datetime.utcnow().isoformat() trending_data = [{"title": h, "timestamp": timestamp} for h in headlines] with open("trending.json", "w") as f: json.dump(trending_data, f, indent=2)

if name == "main": headlines = fetch_headlines() save_trends(headlines) print(f"Saved {len(headlines)} headlines to trending.json")

