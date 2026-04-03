import feedparser
import requests
import os

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

feeds = {

"🚨 MACRO":
[
"https://www.reuters.com/markets/rss",
"https://www.ft.com/world?format=rss"
],

"📊 CRYPTO":
[
"https://cointelegraph.com/rss",
"https://www.coindesk.com/arc/outboundfeeds/rss/"
],

"🏦 CENTRAL BANK / ECONOMY":
[
"https://www.investing.com/rss/news_25.rss"
]

}

sent_links = set()

for category in feeds:

    for url in feeds[category]:

        feed = feedparser.parse(url)

        for entry in feed.entries[:2]:

            if entry.link not in sent_links:

                message = f"""
{category}

{entry.title}

{entry.link}
"""

                requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                    data={
                        "chat_id": CHANNEL_ID,
                        "text": message
                    }
                )

                sent_links.add(entry.link)
