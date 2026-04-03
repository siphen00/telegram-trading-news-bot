import feedparser
import requests
import os

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

feeds = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://www.reuters.com/markets/rss"
]

sent_links = set()

for url in feeds:
    feed = feedparser.parse(url)

    for entry in feed.entries[:3]:

        message = f"""
🚨 Trading News Alert

{entry.title}

{entry.link}
"""

        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={"chat_id": CHANNEL_ID, "text": message}
        )
