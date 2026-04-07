import feedparser
import requests
import os
import json

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

STATE_FILE = "sent_titles.json"


feeds = {

"🌍 GEOPOLITICAL":
[
"https://feeds.bbci.co.uk/news/world/rss.xml",
"https://www.reuters.com/world/rss"
],

"📊 MACRO DATA":
[
"https://www.investing.com/rss/news_25.rss"
],

"🛢 OIL MARKET":
[
"https://www.reuters.com/markets/commodities/rss"
],

"💥 BTC LIQUIDATIONS":
[
"https://cryptopanic.com/news/rss/"
]

}


CRITICAL_KEYWORDS = [

"Iran",
"Hormuz",
"Strait of Hormuz",
"missile",
"airstrike",
"naval",
"war",

"CPI",
"NFP",
"FOMC",

"oil spike",
"crude surge",

"liquidation"
]


HIGH_KEYWORDS = [

"Trump",
"China",
"Taiwan",
"Russia",
"Ukraine",
"sanctions"
]


def normalize(title):
    return title.lower().strip()


def load_titles():

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            return set(json.load(f))

    return set()


def save_titles(titles):

    with open(STATE_FILE, "w") as f:

        json.dump(list(titles), f)


sent_titles = load_titles()


new_titles_added = False


for category in feeds:

    for url in feeds[category]:

        feed = feedparser.parse(url)

        for entry in feed.entries[:6]:

            title = entry.title

            clean_title = normalize(title)

            if clean_title in sent_titles:
                continue


            if any(word.lower() in clean_title for word in CRITICAL_KEYWORDS + HIGH_KEYWORDS):

                message = f"""
🚨 MARKET ALERT

{category}

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

                sent_titles.add(clean_title)

                new_titles_added = True


if new_titles_added:

    save_titles(sent_titles)
