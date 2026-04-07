import feedparser
import requests
import os
import json

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

STATE_FILE = "sent_titles.json"


feeds = {

"🌍 GEOPOLITICAL BREAKING":
[
"https://feeds.bbci.co.uk/news/world/rss.xml",
"https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
"https://apnews.com/rss/apf-topnews"
],

"⚔️ MILITARY ALERTS":
[
"https://warontherocks.com/feed/",
"https://www.thecipherbrief.com/feed"
],

"🛢 ENERGY SHOCK ALERTS":
[
"https://oilprice.com/rss/main",
"https://www.reutersagency.com/feed/?best-topics=energy&post_type=best"
],

"📊 MACRO DATA":
[
"https://www.investing.com/rss/news_25.rss"
],

"💥 BTC LIQUIDATIONS":
[
"https://cryptopanic.com/news/rss/"
]

}


CRITICAL_KEYWORDS = [

"iran",
"hormuz",
"missile",
"naval",
"airstrike",
"attack",
"war",

"cpi",
"nfp",
"fomc",
"interest rate",

"oil spike",
"crude surge",
"supply disruption",

"liquidation",
"squeeze"

]


HIGH_KEYWORDS = [

"trump",
"china",
"taiwan",
"russia",
"ukraine",
"sanctions",
"bond yields",
"dxy"

]


def normalize(title):
    return title.lower().strip()


def classify_priority(title):

    title_lower = title.lower()

    if any(word in title_lower for word in CRITICAL_KEYWORDS):
        return "🔴 CRITICAL"

    if any(word in title_lower for word in HIGH_KEYWORDS):
        return "🟠 HIGH"

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

new_titles_added = False


for category in feeds:

    for url in feeds[category]:

        feed = feedparser.parse(url)

        for entry in feed.entries[:10]:

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

                new_titles_added = True


if new_titles_added:
    save_titles(sent_titles)
