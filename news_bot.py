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
"https://feeds.a.dj.com/rss/RSSWorldNews.xml",
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
"Pentagon",
"war",

"CPI",
"NFP",
"FOMC",
"interest rate",

"oil spike",
"crude surge",
"supply disruption",

"liquidation",
"long squeeze",
"short squeeze"

]


HIGH_KEYWORDS = [

"Trump",
"sanctions",
"China",
"Taiwan",
"Russia",
"Ukraine",

"bond yields",
"DXY"

]


MEDIUM_KEYWORDS = [

"GDP",
"PMI",
"Retail Sales",
"jobless claims",
"inflation expectations"

]


def normalize(title):

    return title.lower().strip()


def classify_priority(title):

    title_lower = title.lower()

    if any(word.lower() in title_lower for word in CRITICAL_KEYWORDS):

        return "🔴 CRITICAL"

    if any(word.lower() in title_lower for word in HIGH_KEYWORDS):

        return "🟠 HIGH"

    if any(word.lower() in title_lower for word in MEDIUM_KEYWORDS):

        return "🟡 MEDIUM"

    return None


def load_titles():

    if os.path.exists(STATE_FILE):

        with open(STATE_FILE, "r") as f:

            return set(json.load(f))

    return set()


def save_titles(titles):

    with open(STATE_FILE, "w") as f:

        json.dump(list(titles), f)


sent_titles = load_titles()


for category in feeds:

    for url in feeds[category]:

        feed = feedparser.parse(url)

        for entry in feed.entries[:6]:

            title = entry.title

            clean_title = normalize(title)

            if clean_title in sent_titles:

                continue


            priority = classify_priority(title)


            if priority:

                message = f"""
{priority}

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


save_titles(sent_titles)
