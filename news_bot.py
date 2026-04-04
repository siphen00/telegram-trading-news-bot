import feedparser
import requests
import os
import json

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

STATE_FILE = "sent_links.json"

feeds = {

"🌍 GEOPOLITICAL BREAKING":
[
"https://feeds.bbci.co.uk/news/world/rss.xml",
"https://www.reuters.com/world/rss",
"https://feeds.a.dj.com/rss/RSSWorldNews.xml"
],

"🚨 MACRO MARKET MOVERS":
[
"https://www.reuters.com/markets/rss",
"https://feeds.marketwatch.com/marketwatch/topstories/"
],

"📊 HIGH IMPACT ECONOMIC DATA":
[
"https://www.investing.com/rss/news_25.rss"
],

"💥 BTC LIQUIDATIONS":
[
"https://cryptopanic.com/news/rss/"
]

}

HIGH_IMPACT_KEYWORDS = [

# US / Iran focus
"Iran",
"United States",
"Pentagon",
"missile",
"airstrike",
"naval",
"sanctions",
"Hormuz",
"Persian Gulf",

# broader geopolitics
"Israel",
"Hamas",
"Russia",
"Ukraine",
"China",
"Taiwan",
"war",
"attack",
"military",
"conflict",

# macro volatility triggers
"CPI",
"NFP",
"FOMC",
"interest rate",
"Federal Reserve",
"Powell",
"inflation",
"bond yields",
"DXY",

# crypto liquidation signals
"liquidation",
"liquidations",
"short squeeze",
"long squeeze"

]


def load_sent_links():

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            return set(json.load(f))

    return set()


def save_sent_links(links):

    with open(STATE_FILE, "w") as f:

        json.dump(list(links), f)


sent_links = load_sent_links()


for category in feeds:

    for url in feeds[category]:

        feed = feedparser.parse(url)

        for entry in feed.entries[:5]:

            title = entry.title

            if any(keyword.lower() in title.lower() for keyword in HIGH_IMPACT_KEYWORDS):

                if entry.link not in sent_links:

                    message = f"""
{category}

🚨 HIGH-IMPACT ALERT

{title}

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


save_sent_links(sent_links)
