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
"https://feeds.a.dj.com/rss/RSSWorldNews.xml",
"https://www.reuters.com/world/rss"
],

"📊 MACRO DATA RELEASES":
[
"https://www.investing.com/rss/news_25.rss"
],

"🛢 OIL MARKET SHOCK ALERTS":
[
"https://feeds.marketwatch.com/marketwatch/topstories/",
"https://www.reuters.com/markets/commodities/rss"
],

"💥 BTC LIQUIDATIONS":
[
"https://cryptopanic.com/news/rss/"
]

}


HIGH_IMPACT_KEYWORDS = [

# RED FOLDER DATA
"CPI",
"NFP",
"FOMC",
"PCE",
"GDP",
"PMI",
"Retail Sales",
"jobless claims",
"inflation",
"interest rate",
"Federal Reserve",

# TRUMP SIGNALS
"Trump",

# US–IRAN SIGNALS
"Iran",
"Pentagon",
"airstrike",
"missile",
"naval",
"Persian Gulf",
"Hormuz",
"sanctions",
"IRGC",

# STRAIT OF HORMUZ ALERTS
"Strait of Hormuz",
"oil tanker",
"shipping disruption",
"naval deployment",

# OIL SHOCK DETECTION
"oil spike",
"crude surge",
"Brent jumps",
"energy disruption",
"supply disruption",
"pipeline attack",

# GLOBAL WAR SIGNALS
"Israel",
"Hamas",
"Russia",
"Ukraine",
"China",
"Taiwan",
"military",
"conflict",
"attack",
"war",

# MARKET SHOCK SIGNALS
"bond yields",
"DXY",
"crude jumps",

# CRYPTO VOLATILITY
"liquidation",
"long squeeze",
"short squeeze"

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

        for entry in feed.entries[:6]:

            title = entry.title

            if any(keyword.lower() in title.lower() for keyword in HIGH_IMPACT_KEYWORDS):

                if entry.link not in sent_links:

                    message = f"""
{category}

🚨 HIGH-IMPACT BREAKING NEWS

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
