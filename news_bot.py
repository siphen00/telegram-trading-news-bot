import feedparser
import requests
import os

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

feeds = {

"🚨 MACRO BREAKING":
[
"https://www.reuters.com/markets/rss",
"https://feeds.marketwatch.com/marketwatch/topstories/",
"https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
"https://www.ft.com/world?format=rss"
],

"📊 HIGH IMPACT ECONOMIC DATA":
[
"https://www.investing.com/rss/news_25.rss"
],

"🌍 GEOPOLITICS":
[
"https://feeds.bbci.co.uk/news/world/rss.xml"
],

"₿ CRYPTO MARKET MOVERS":
[
"https://cointelegraph.com/rss",
"https://www.coindesk.com/arc/outboundfeeds/rss/"
]

}

HIGH_IMPACT_KEYWORDS = [

"CPI",
"NFP",
"FOMC",
"interest rate",
"Federal Reserve",
"Powell",
"ECB",
"inflation",
"GDP",
"PMI",
"bond yields",
"treasury yields",
"DXY",
"dollar strength",
"war",
"missile",
"attack",
"sanctions",
"oil spike",
"Middle East",
"Russia",
"China",
"Taiwan",
"Ukraine",
"Israel",
"ETF inflows",
"Bitcoin ETF",
"liquidation",
"Nasdaq",
"gold prices",
"AI stocks"

]

sent_links = set()

for category in feeds:

    for url in feeds[category]:

        feed = feedparser.parse(url)

        for entry in feed.entries[:4]:

            title = entry.title

            if any(keyword.lower() in title.lower() for keyword in HIGH_IMPACT_KEYWORDS):

                if entry.link not in sent_links:

                    message = f"""
{category}

🚨 MARKET MOVING ALERT

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
