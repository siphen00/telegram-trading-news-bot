import feedparser
import requests
import os
import json

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

STATE_FILE = "sent_titles.json"


feeds = [

"https://feeds.bbci.co.uk/news/world/rss.xml",
"https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
"https://apnews.com/rss/apf-topnews",

"https://www.reutersagency.com/feed/?best-topics=energy&post_type=best",
"https://oilprice.com/rss/main",

"https://www.investing.com/rss/news_25.rss",

"https://cryptopanic.com/news/rss/"
]


KEYWORDS = [

"iran",
"hormuz",
"war",
"attack",
"military",
"missile",

"trump",

"china",
"taiwan",
"russia",
"ukraine",

"cpi",
"nfp",
"fomc",
"inflation",
"interest rate",

"oil",
"crude",
"energy",

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

sent_this_run = False


print("Loaded previous titles:", len(sent_titles))


for url in feeds:

    print("Checking feed:", url)

    feed = feedparser.parse(url)


    for entry in feed.entries[:10]:

        title = entry.title

        clean_title = normalize(title)


        if clean_title in sent_titles:

            continue


        if any(word in clean_title for word in KEYWORDS):

            message = f"""

🚨 MARKET ALERT

{title}

{entry.link}

"""

            response = requests.post(

                f"https://api.telegram.org/bot{TOKEN}/sendMessage",

                data={

                    "chat_id": CHANNEL_ID,

                    "text": message

                }

            )


            print("Sent:", title)

            print(response.text)


            sent_titles.add(clean_title)

            sent_this_run = True


if sent_this_run:

    save_titles(sent_titles)

else:

    print("No keyword matches found — sending heartbeat message")


    requests.post(

        f"https://api.telegram.org/bot{TOKEN}/sendMessage",

        data={

            "chat_id": CHANNEL_ID,

            "text": "✅ Bot running — no macro/geopolitical alerts this cycle"

        }

    )
