import feedparser
import requests
import os

# Telegram setup from GitHub Secrets
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# RSS / API sources (same as your current bot)
FEEDS = [
    "https://financialjuice.com/rss",
    "https://www.forexlive.com/rss",
    "https://www.investing.com/rss/news.rss",
    "https://www.reuters.com/rssFeed/marketsNews",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cryptopanic.com/api/v1/posts/?auth_token=" + os.getenv("CRYPTOPANIC_TOKEN"),
    "https://www.aljazeera.com/xml/rss/all.xml"
]

# Updated keywords filter
KEYWORDS = [
    "Fed","CPI","inflation","interest rate","NFP","ECB","BoJ","recession","liquidity",
    "bitcoin","BTC","ETH","crypto","ETF",
    "gold","XAU","oil","WTI","Nasdaq","NQ",
    "China","Russia","Ukraine","Middle East","war","sanctions","missile",
    # NEW additions
    "Trump","breaking news","election","politics","US","White House"
]

# Track sent headlines to avoid duplicates
SENT_FILE = "sent_headlines.txt"
try:
    with open(SENT_FILE, "r") as f:
        sent_headlines = set(f.read().splitlines())
except FileNotFoundError:
    sent_headlines = set()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"})

def fetch_feed(url):
    if "cryptopanic.com" in url:
        data = requests.get(url).json()
        for post in data.get("results", []):
            title = post.get("title")
            if title and any(k.lower() in title.lower() for k in KEYWORDS):
                if title not in sent_headlines:
                    send_telegram(f"📢 {title}\n{post.get('url')}")
                    sent_headlines.add(title)
    else:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title")
            link = entry.get("link")
            if title and any(k.lower() in title.lower() for k in KEYWORDS):
                if title not in sent_headlines:
                    send_telegram(f"📢 {title}\n{link}")
                    sent_headlines.add(title)

for feed_url in FEEDS:
    fetch_feed(feed_url)

with open(SENT_FILE, "w") as f:
    f.write("\n".join(sent_headlines))
