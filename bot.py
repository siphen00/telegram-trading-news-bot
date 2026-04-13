import feedparser
import requests
import json
import os
import hashlib
import socket
from datetime import datetime, timezone, timedelta

socket.setdefaulttimeout(8)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
SEEN_FILE = "seen_ids.json"

FEEDS = [
    ("Reuters Markets",        "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Economy",        "https://feeds.reuters.com/news/economy"),
    ("Reuters World",          "https://feeds.reuters.com/Reuters/worldNews"),
    ("MarketWatch Top Stories","https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("CNBC Markets",           "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("CNBC World Politics",    "https://www.cnbc.com/id/10000115/device/rss/rss.html"),
    ("Investing.com News",     "https://www.investing.com/rss/news.rss"),
    ("Yahoo Finance",          "https://finance.yahoo.com/rss/"),
    ("Forexlive",              "https://www.forexlive.com/feed/news"),
    ("Nasdaq News",            "https://www.nasdaq.com/feed/rssoutput.aspx"),
    ("CoinDesk",               "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph",          "https://cointelegraph.com/rss"),
    ("Al Jazeera",             "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Middle East Eye",        "https://www.middleeasteye.net/rss"),
]

# ── MUST contain at least one of these to pass ────────────────────────────────
WHITELIST = [
    # Markets & instruments
    "bitcoin","btc","crypto","ethereum","etf",
    "nasdaq","nq futures","s&p","spx","dow jones",
    "gold","xau","crude oil","brent","wti",
    "dollar","dxy","treasury","yield","bond",
    "fed","federal reserve","fomc","rate decision","rate hike","rate cut",
    "inflation","cpi","ppi","gdp","nonfarm","nfp","payroll","unemployment",
    "earnings","revenue","profit","guidance",
    # Geopolitical — Middle East
    "middle east","israel","gaza","hamas","hezbollah","west bank","lebanon",
    "iran","tehran","irgc","nuclear deal","sanctions",
    "saudi","riyadh","opec","oil supply",
    "iraq","baghdad","syria","houthi","red sea","strait of hormuz",
    "yemen","drone attack","missile","airstrike",
    # Trump / US politics market-moving
    "trump","white house","tariff","trade war","trade deal",
    "executive order","sanctions","pentagon","us military",
    "congress","debt ceiling","federal budget",
    # Other macro geopolitical
    "china","beijing","taiwan","xi jinping",
    "russia","putin","ukraine","nato",
    "north korea","kim jong",
    # Breaking / urgent
    "breaking","urgent","alert","flash","just in","developing",
]

# ── If title contains ANY of these → trash it, skip ──────────────────────────
BLACKLIST = [
    "horoscope","zodiac","celebrity","kardashian","oscars","grammy","nfl draft",
    "recipe","fashion","beauty","makeup","skincare","lifestyle","travel guide",
    "sports scores","game recap","nba scores","nhl scores","mlb scores",
    "movie review","tv show","streaming","netflix","disney","box office",
    "weather forecast","gardening","home decor","real estate tips",
    "social media trend","tiktok","instagram","viral","meme",
    "obituary","wedding","birth announcement",
]

# ── RED FOLDER: high-impact events that get pinned ───────────────────────────
RED_FOLDER_KEYWORDS = [
    # Economic data releases
    "nonfarm payroll","nfp","non-farm","jobs report",
    "cpi report","inflation report","core cpi","core pce",
    "fomc","fed decision","rate decision","fed raises","fed cuts",
    "gdp report","gdp growth","gdp shrinks",
    "ppi report","retail sales","jobless claims",
    "ecb decision","boe decision","bank of england","european central bank",
    # Geopolitical shocks
    "war declared","invasion","nuclear","missile strike","major attack",
    "ceasefire","peace deal","coup","assassination",
    "market crash","circuit breaker","trading halt","black monday","flash crash",
    # Trump high-impact
    "trump tariff","trump sanctions","trump executive","trump fires","trump signs",
    # Crypto shocks
    "sec approves","sec rejects","bitcoin etf","crypto ban","exchange hack",
]

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            try:
                return set(json.load(f))
            except Exception:
                return set()
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen)[-2000:], f)

def is_relevant(title, summary=""):
    text = (title + " " + summary).lower()
    # Fail blacklist first
    if any(b in text for b in BLACKLIST):
        return False
    # Must match whitelist
    return any(w in text for w in WHITELIST)

def is_breaking(title):
    t = title.lower()
    return any(w in t for w in ["breaking","urgent","alert","flash","just in","developing"])

def is_red_folder(title, summary=""):
    text = (title + " " + summary).lower()
    return any(r in text for r in RED_FOLDER_KEYWORDS)

def is_recent(entry):
    try:
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if not pub:
            return True
        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - pub_dt < timedelta(minutes=5)
    except Exception:
        return True

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            print(f"Telegram error: {resp.status_code} {resp.text}")
            return None
        return resp.json().get("result", {}).get("message_id")
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return None

def pin_message(message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/pinChatMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "message_id": message_id,
        "disable_notification": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"Pin failed: {e}")
        return False

def article_id(entry):
    return hashlib.md5(
        (entry.get("id") or entry.get("link", "") or entry.get("title", "")).encode()
    ).hexdigest()

def format_message(source, title, link, breaking=False, red=False):
    if red:
        header = f"🔴 <b>RED FOLDER — {source}</b>"
    elif breaking:
        header = f"⚡ <b>BREAKING — {source}</b>"
    else:
        header = f"📰 <b>{source}</b>"
    return f"{header}\n{title}\n\n🔗 <a href='{link}'>Read more</a>"

def main():
    seen = load_seen()
    new_articles = []

    for source_name, url in FEEDS:
        try:
            print(f"Fetching: {source_name}")
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            print(f"  → {len(feed.entries)} entries")
            for entry in feed.entries[:15]:
                aid = article_id(entry)
                if aid in seen:
                    continue
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                if is_relevant(title, summary) and is_recent(entry):
                    red = is_red_folder(title, summary)
                    breaking = is_breaking(title)
                    new_articles.append((source_name, title, link, aid, breaking, red))
                    flag = "🔴" if red else ("⚡" if breaking else "✓")
                    print(f"  {flag} {title[:70]}")
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    # Sort: red folder first, then breaking, then normal
    new_articles.sort(key=lambda x: (not x[5], not x[4]))

    print(f"\nTotal new relevant articles: {len(new_articles)}")

    sent = 0
    for source, title, link, aid, breaking, red in new_articles:
        msg = format_message(source, title, link, breaking, red)
        message_id = send_message(msg)
        if message_id:
            seen.add(aid)
            sent += 1
            print(f"Sent ({'RED' if red else 'BREAKING' if breaking else 'normal'}): {title[:60]}")
            # Pin red folder messages
            if red:
                pinned = pin_message(message_id)
                print(f"  → Pin: {'✅' if pinned else '❌ failed'}")

    save_seen(seen)
    print(f"Done. Sent {sent} new articles.")

if __name__ == "__main__":
    main()
