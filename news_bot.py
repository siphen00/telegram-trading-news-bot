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
"https://feeds.a.dj.com/rss/RSSWorldNews.xml"
],

"📊 MACRO DATA RELEASES":
[
"https://www.investing.com/rss/news_25.rss"
],

"🏦 CENTRAL BANK / FED":
[
"https://feeds.marketwatch.com/marketwatch/topstories/"
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

# TRUMP
"Trump",

# US–IRAN FOCUS
"Iran",
"Pentagon",
"airstrike",
"missile",
"Hormuz",
"Persian Gulf",
"sanctions",

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
"oil spike",
"crude surge",

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
