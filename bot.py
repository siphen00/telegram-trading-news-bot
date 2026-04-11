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
    ("MarketWatch Top Stories","https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("CNBC Markets",           "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("Investing.com News",     "https://www.investing.com/rss/news.rss"),
    ("Yahoo Finance",          "https://finance.yahoo.com/rss/"),
    ("Forexlive",              "https://www.forexlive.com/feed/news"),
    ("Nasdaq News",            "https://www.nasdaq.com/feed/rssoutput.aspx"),
    ("CoinDesk",               "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph",          "https://cointelegraph.com/rss"),
]

KEYWORDS = [
    "bitcoin","btc","crypto","cryptocurrency","coinbase","binance","etf",
    "nasdaq","nq","tech","nvidia","apple","microsoft","google","meta","amazon",
    "fed","federal reserve","fomc","rate","inflation","cpi","ppi","gdp",
    "s&p","spx","dow","market","stocks","equity","recession","earnings",
    "gold","xau","silver","oil","commodity","commodities","safe haven",
    "dollar","dxy","yield","treasury","bond","jobs","nonfarm","unemployment",
    "geopolit","war","china","ukraine","middle east","opec",
]

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen)[-2000:], f)

def is_relevant(title, summary=""):
    text = (title + " " + summary).lower()
    return any(kw in text for kw in KEYWORDS)

def send_to_telegram(text):
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
        return resp.ok
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False

def article_id(entry):
    return hashlib.md5((entry.get("id") or entry.get("link","") or entry.get("title","")).encode()).hexdigest()

def main():
    # ── STRESS TEST: delete seen_ids so everything is treated as new ──
    if os.path.exists(SEEN_FILE):
        os.remove(SEEN_FILE)
    seen = set()

    print(f"BOT_TOKEN set: {bool(BOT_TOKEN)}")
    print(f"CHANNEL_ID: {CHANNEL_ID}")

    # ── Step 1: test Telegram connection first ──
    test = send_to_telegram("🧪 <b>Stress test started</b> — fetching all feeds now...")
    if not test:
        print("FATAL: Cannot reach Telegram. Check BOT_TOKEN and CHANNEL_ID.")
        return
    print("Telegram connection OK")

    new_articles = []

    for source_name, url in FEEDS:
        try:
            print(f"Fetching: {source_name}")
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            count = len(feed.entries)
            print(f"  → got {count} entries")
            for entry in feed.entries[:10]:
                aid = article_id(entry)
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                # STRESS TEST: no recency filter, no dedup
                if is_relevant(title, summary):
                    new_articles.append((source_name, title, link, aid))
                    print(f"  ✓ relevant: {title[:60]}")
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    print(f"\nTotal relevant articles found: {len(new_articles)}")

    # Send max 10 to avoid spam
    sent = 0
    for source, title, link, aid in new_articles[:10]:
        msg = f"📰 <b>{source}</b>\n{title}\n\n🔗 <a href='{link}'>Read more</a>"
        if send_to_telegram(msg):
            seen.add(aid)
            sent += 1
            print(f"Sent: {title[:60]}")

    summary_msg = f"✅ <b>Stress test done</b>\nFound: {len(new_articles)} relevant articles\nSent: {sent}/10"
    send_to_telegram(summary_msg)
    print(f"\nDone. Sent {sent} articles.")

if __name__ == "__main__":
    main()
