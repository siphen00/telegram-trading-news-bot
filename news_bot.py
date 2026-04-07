import feedparser
import requests
import os
import json

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

STATE_FILE = "sent_titles.json"


feeds = {

"🌍 WORLD":
[
"https://feeds.bbci.co.uk/news/world/rss.xml",
"https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
"https://apnews.com/rss/apf-topnews"
],

"🛢 ENERGY":
[
"https://oilprice.com/rss/main",
"https://www.reutersagency.com/feed/?best-topics=energy&post_type=best"
],

"📊 MACRO":
[
"https://www.investing.com/rss/news_25.rss"
],

"₿ CRYPTO":
[
"https://cryptopanic.com/news/rss/"
]

}


KEYWORDS = [

"iran",
"hormuz",
"war",
"attack",
"military",
"missile",

"cpi",
"nfp",
"fomc",
"inflation",
"interest rate",

"oil",
"crude",
"energy",

"trump",
"china",
"taiwan",
"russia",
"ukraine",

"liquidation",
"squeeze"
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

        for entry in feed.entries[:8]:

            title = entry.title

            clean_title = normalize(title)

            if clean_title in sent_titles:
                continue


            if any(word in clean_title for word in KEYWORDS):

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


# TEST MESSAGE IF NOTHING SENT

if not new_titles_added:

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHANNEL_ID,
            "text": "✅ Bot is running but no high-impact news detected in this cycle."
        }
    )
