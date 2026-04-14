import feedparser
import requests
import json
import os
import hashlib
import socket
from datetime import datetime, timezone, timedelta
from xml.etree import ElementTree as ET

socket.setdefaulttimeout(8)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
SEEN_FILE = "seen_ids.json"
PINNED_FILE = "pinned_events.json"

FEEDS = [
    ("Reuters Markets",        "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Economy",        "https://feeds.reuters.com/news/economy"),
    ("Reuters World",          "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters Politics",       "https://feeds.reuters.com/Reuters/politicsNews"),
    ("MarketWatch",            "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("CNBC Markets",           "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("CNBC Politics",          "https://www.cnbc.com/id/10000115/device/rss/rss.html"),
    ("CNBC Economy",           "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
    ("Investing.com",          "https://www.investing.com/rss/news.rss"),
    ("Investing.com Analysis", "https://www.investing.com/rss/news_25.rss"),
    ("Yahoo Finance",          "https://finance.yahoo.com/rss/"),
    ("Forexlive",              "https://www.forexlive.com/feed/news"),
    ("Forexlive Analysis",     "https://www.forexlive.com/feed/analysis"),
    ("Nasdaq",                 "https://www.nasdaq.com/feed/rssoutput.aspx"),
    ("CoinDesk",               "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph",          "https://cointelegraph.com/rss"),
    ("Al Jazeera",             "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Middle East Eye",        "https://www.middleeasteye.net/rss"),
    ("Axios Markets",          "https://api.axios.com/feed/markets"),
    ("Politico Economy",       "https://www.politico.com/rss/economy.xml"),
]

# ── Direct government data sources ───────────────────────────────────────────
# These post raw data the moment it drops — same time as Bloomberg Terminal
GOV_SOURCES = [
    {
        "name": "BLS — Bureau of Labor Statistics",
        "url": "https://www.bls.gov/feed/bls_latest.rss",
        "type": "gov",
        "keywords": ["employment","nonfarm","cpi","ppi","unemployment","jobs","inflation","consumer price","producer price","jobless"],
    },
    {
        "name": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "type": "gov",
        "keywords": ["rate","fomc","federal funds","monetary policy","balance sheet","reserve","interest","statement","minutes","beige book"],
    },
    {
        "name": "BEA — Bureau of Economic Analysis",
        "url": "https://www.bea.gov/rss/latest_revision.xml",
        "type": "gov",
        "keywords": ["gdp","gross domestic","personal income","pce","current account","trade","consumer spending"],
    },
    {
        "name": "US Census Bureau",
        "url": "https://www.census.gov/economic-indicators/feed.xml",
        "type": "gov",
        "keywords": ["retail sales","housing","construction","durable goods","trade deficit","manufacturers","shipments"],
    },
    {
        "name": "US Treasury",
        "url": "https://home.treasury.gov/news/press-releases/rss.xml",
        "type": "gov",
        "keywords": ["debt","yield","auction","bond","note","bill","deficit","sanctions","tariff","currency"],
    },
    {
        "name": "White House",
        "url": "https://www.whitehouse.gov/feed/",
        "type": "gov",
        "keywords": ["executive order","proclamation","tariff","trade","sanction","statement","briefing","trump"],
    },
    {
        "name": "EIA — Energy Information",
        "url": "https://www.eia.gov/rss/press_releases.xml",
        "type": "gov",
        "keywords": ["crude oil","petroleum","natural gas","gasoline","inventory","opec","barrel","energy"],
    },
    {
        "name": "CFTC",
        "url": "https://www.cftc.gov/rss/pressreleases.xml",
        "type": "gov",
        "keywords": ["commitment","futures","options","position","contract","enforcement","crypto","bitcoin"],
    },
    {
        "name": "SEC",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&datetype=custom&owner=include&count=10&search_text=&output=atom",
        "type": "gov",
        "keywords": ["bitcoin","etf","crypto","enforcement","fraud","filing","approval","rejection","order"],
    },
]

WHITELIST = [
    "bitcoin","btc","crypto","ethereum","eth","coinbase","binance","defi",
    "stablecoin","blockchain","web3","altcoin","solana","ripple","xrp","etf",
    "nasdaq","nq","s&p","spx","dow jones","dow","russell","stock","stocks",
    "equity","equities","earnings","revenue","profit","loss","guidance",
    "ipo","merger","acquisition","buyback","dividend",
    "nvidia","apple","microsoft","google","alphabet","meta","amazon","tesla",
    "jpmorgan","goldman","morgan stanley","blackrock","berkshire",
    "gold","xau","silver","platinum","copper",
    "crude oil","brent","wti","natural gas","energy","opec",
    "commodity","commodities","safe haven",
    "dollar","usd","dxy","euro","eur","yen","jpy","pound","gbp",
    "treasury","yield","bond","10-year","2-year","spread",
    "fed","federal reserve","fomc","powell","rate decision","rate hike","rate cut",
    "inflation","deflation","cpi","ppi","pce","gdp","nonfarm","nfp",
    "payroll","unemployment","jobless","jobs report","retail sales",
    "trade balance","current account","fiscal","monetary policy",
    "recession","stagflation","soft landing","hard landing",
    "middle east","israel","gaza","hamas","hezbollah","west bank","ramallah",
    "iran","tehran","irgc","nuclear","sanctions","khamenei",
    "saudi arabia","riyadh","mbs","crown prince",
    "iraq","baghdad","syria","damascus","houthi","houthis",
    "red sea","strait of hormuz","gulf","persian gulf",
    "yemen","drone","missile","airstrike","attack","strike",
    "lebanon","beirut","jordan","egypt","qatar","uae","abu dhabi","dubai",
    "trump","donald trump","white house","oval office",
    "tariff","tariffs","trade war","trade deal","trade policy",
    "executive order","veto","impeach","congress","senate","house",
    "treasury secretary","sec chairman","fed chair",
    "sanctions","pentagon","us military","nato","state department",
    "debt ceiling","federal budget","deficit","spending bill",
    "china","beijing","xi jinping","pla","taiwan","strait",
    "hong kong","south china sea","trade","export","import",
    "japan","bank of japan","boj","korea","north korea","kim jong",
    "russia","putin","moscow","ukraine","kyiv","war",
    "ecb","european central bank","lagarde","bank of england","boe",
    "germany","france","uk","britain","eurozone","eu",
    "breaking","urgent","alert","flash","just in","developing",
    "crash","collapse","default","bankruptcy","crisis","emergency",
    "coup","explosion","war declared","ceasefire","peace deal",
]

BLACKLIST = [
    "horoscope","zodiac","celebrity","kardashian","oscars","grammy",
    "recipe","fashion","beauty","makeup","skincare","lifestyle",
    "travel guide","sports scores","game recap",
    "nba scores","nhl scores","mlb scores","nfl scores",
    "movie review","tv show","streaming","netflix","disney","box office",
    "weather forecast","gardening","home decor",
    "social media trend","tiktok","instagram","viral","meme",
    "obituary","wedding","birth announcement","real estate tips",
]

RED_FOLDER_KEYWORDS = [
    "nonfarm payroll","nfp","non-farm","jobs report",
    "cpi report","inflation report","core cpi","core pce",
    "fomc","fed decision","rate decision","fed raises","fed cuts",
    "gdp report","gdp growth","gdp shrinks",
    "ppi report","retail sales","jobless claims",
    "ecb decision","boe decision","bank of england","european central bank",
    "war declared","invasion","nuclear strike","missile strike","major attack",
    "ceasefire","peace deal","coup","assassination",
    "market crash","circuit breaker","trading halt","flash crash",
    "trump tariff","trump sanctions","trump executive","trump fires","trump signs",
    "sec approves","sec rejects","bitcoin etf","crypto ban","exchange hack",
]

def get_market_tags(title, summary=""):
    text = (title + " " + summary).lower()
    tags = []
    if any(w in text for w in ["bitcoin","btc","crypto","ethereum","eth","coinbase","binance","solana","xrp"]):
        tags.append("BTC")
    if any(w in text for w in ["nasdaq","nq","tech","nvidia","apple","microsoft","google","meta","amazon","tesla"]):
        tags.append("NQ")
    if any(w in text for w in ["s&p","spx","dow","stocks","equity","earnings","ipo","market"]):
        tags.append("SPX")
    if any(w in text for w in ["gold","xau","silver","platinum","safe haven","commodity"]):
        tags.append("GOLD")
    if any(w in text for w in ["oil","crude","brent","wti","opec","natural gas","energy"]):
        tags.append("OIL")
    if any(w in text for w in ["dollar","dxy","usd","fed","fomc","rate","inflation","cpi","ppi","gdp","treasury","yield","bond"]):
        tags.append("DXY")
    if any(w in text for w in ["middle east","israel","gaza","iran","saudi","houthi","ukraine","russia","china","taiwan","war","attack","strike"]):
        tags.append("GEO")
    return tags

def tag_bar(tags):
    icons = {"BTC":"₿","NQ":"📊","SPX":"🗽","GOLD":"🥇","OIL":"🛢","DXY":"💵","GEO":"🌍"}
    return "  ".join(f"{icons.get(t,'•')} #{t}" for t in tags) if tags else ""

def format_normal(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"📰  <b>{title}</b>\n\n"
        f"🏢 <i>{source}</i>   🕐 {pub_time}\n"
        f"{tags}\n\n"
        f"🔗 <a href='{link}'>Read full article →</a>"
    )

def format_breaking(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"⚡ <b>BREAKING</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"🏢 <i>{source}</i>   🕐 {pub_time}\n"
        f"{tags}\n\n"
        f"🔗 <a href='{link}'>Read full article →</a>"
    )

def format_red(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"🔴 <b>RED FOLDER</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"🏢 <i>{source}</i>   🕐 {pub_time}\n"
        f"{tags}\n\n"
        f"🔗 <a href='{link}'>Read full article →</a>"
    )

def format_red_pin(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"📌 🔴 <b>RED FOLDER — PINNED</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"🏢 <i>{source}</i>   🕐 {pub_time}\n"
        f"{tags}\n\n"
        f"🔗 <a href='{link}'>Full report →</a>\n\n"
        f"<i>📌 Pinned — resets in 24 hours</i>"
    )

def format_gov(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"🏛 <b>OFFICIAL DATA — {source}</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"🕐 {pub_time}\n"
        f"{tags}\n\n"
        f"🔗 <a href='{link}'>Official release →</a>"
    )

def format_gov_pin(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"📌 🏛 <b>OFFICIAL DATA — PINNED</b>\n\n"
        f"<b>{source}</b>\n"
        f"<b>{title}</b>\n\n"
        f"🕐 {pub_time}\n"
        f"{tags}\n\n"
        f"🔗 <a href='{link}'>Official release →</a>\n\n"
        f"<i>📌 Pinned — resets in 24 hours</i>"
    )

def now_utc():
    return datetime.now(timezone.utc)

def pub_time_str(entry):
    try:
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if not pub:
            return now_utc().strftime("%d %b %H:%M UTC")
        return datetime(*pub[:6], tzinfo=timezone.utc).strftime("%d %b %H:%M UTC")
    except Exception:
        return now_utc().strftime("%d %b %H:%M UTC")

def pub_time_str_raw(pub_parsed):
    try:
        if not pub_parsed:
            return now_utc().strftime("%d %b %H:%M UTC")
        return datetime(*pub_parsed[:6], tzinfo=timezone.utc).strftime("%d %b %H:%M UTC")
    except Exception:
        return now_utc().strftime("%d %b %H:%M UTC")

def is_recent_dt(pub_parsed, minutes=30):
    try:
        if not pub_parsed:
            return True
        pub_dt = datetime(*pub_parsed[:6], tzinfo=timezone.utc)
        return now_utc() - pub_dt < timedelta(minutes=minutes)
    except Exception:
        return True

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            try:
                return json.load(f)
            except Exception:
                return default
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_seen():
    return set(load_json(SEEN_FILE, []))

def save_seen(seen):
    save_json(SEEN_FILE, list(seen)[-3000:])

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if not resp.ok:
            print(f"Telegram error: {resp.status_code} {resp.text}")
            return None
        return resp.json().get("result", {}).get("message_id")
    except Exception as e:
        print(f"Send failed: {e}")
        return None

def pin_message(message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/pinChatMessage"
    try:
        resp = requests.post(url, json={"chat_id": CHANNEL_ID, "message_id": message_id}, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"Pin failed: {e}")
        return False

def unpin_message(message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/unpinChatMessage"
    try:
        resp = requests.post(url, json={"chat_id": CHANNEL_ID, "message_id": message_id}, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"Unpin failed: {e}")
        return False

def article_id(entry):
    return hashlib.md5(
        (entry.get("id") or entry.get("link", "") or entry.get("title", "")).encode()
    ).hexdigest()

def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()

def is_relevant(title, summary=""):
    text = (title + " " + summary).lower()
    if any(b in text for b in BLACKLIST):
        return False
    return any(w in text for w in WHITELIST)

def is_breaking(title):
    return any(w in title.lower() for w in ["breaking","urgent","alert","flash","just in","developing"])

def is_red_folder(title, summary=""):
    return any(r in (title + " " + summary).lower() for r in RED_FOLDER_KEYWORDS)

def cleanup_old_pins():
    pinned = load_json(PINNED_FILE, {})
    now = now_utc()
    changed = False
    for key in list(pinned.keys()):
        pinned_at = pinned[key].get("pinned_at")
        if pinned_at:
            pinned_dt = datetime.fromisoformat(pinned_at)
            if (now - pinned_dt).total_seconds() > 86400:
                msg_id = pinned[key].get("message_id")
                if msg_id:
                    unpin_message(msg_id)
                    print(f"24hr reset — unpinned: {key[:40]}")
                del pinned[key]
                changed = True
    if changed:
        save_json(PINNED_FILE, pinned)
    return pinned

# ── Fetch government sources ──────────────────────────────────────────────────
def fetch_gov_sources(seen, pinned):
    gov_articles = []

    for source in GOV_SOURCES:
        try:
            print(f"Fetching gov: {source['name']}")
            resp = requests.get(
                source["url"],
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=8
            )
            if not resp.ok:
                print(f"  → HTTP {resp.status_code}")
                continue

            feed = feedparser.parse(resp.content)
            print(f"  → {len(feed.entries)} entries")

            for entry in feed.entries[:10]:
                aid = article_id(entry)
                if aid in seen:
                    continue

                title = entry.get("title", "").strip()
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                pub = entry.get("published_parsed") or entry.get("updated_parsed")

                if not title:
                    continue

                # Gov sources: allow up to 60 min old since they post infrequently
                if not is_recent_dt(pub, minutes=60):
                    continue

                text = (title + " " + summary).lower()
                matched = any(kw in text for kw in source["keywords"])
                if not matched:
                    continue

                pub_time = pub_time_str_raw(pub)
                red = is_red_folder(title, summary)
                gov_articles.append((source["name"], title, link, aid, red, pub_time))
                flag = "🔴" if red else "🏛"
                print(f"  {flag} {title[:70]}")

        except Exception as e:
            print(f"Error fetching {source['name']}: {e}")

    return gov_articles

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    seen = load_seen()
    pinned = cleanup_old_pins()
    new_articles = []

    # ── Regular RSS feeds ─────────────────────────────────────────────────────
    for source_name, url in FEEDS:
        try:
            print(f"Fetching: {source_name}")
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            print(f"  → {len(feed.entries)} entries")
            for entry in feed.entries[:20]:
                aid = article_id(entry)
                if aid in seen:
                    continue
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if is_relevant(title, summary) and is_recent_dt(pub, minutes=30):
                    red = is_red_folder(title, summary)
                    breaking = is_breaking(title)
                    pub_time = pub_time_str_raw(pub)
                    new_articles.append({
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "aid": aid,
                        "breaking": breaking,
                        "red": red,
                        "pub_time": pub_time,
                        "gov": False,
                    })
                    flag = "🔴" if red else ("⚡" if breaking else "✓")
                    print(f"  {flag} {title[:70]}")
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    # ── Government sources ────────────────────────────────────────────────────
    gov_articles = fetch_gov_sources(seen, pinned)
    for source, title, link, aid, red, pub_time in gov_articles:
        new_articles.append({
            "source": source,
            "title": title,
            "link": link,
            "aid": aid,
            "breaking": False,
            "red": red,
            "pub_time": pub_time,
            "gov": True,
        })

    # Sort: gov red > red > gov normal > breaking > normal
    def sort_key(a):
        if a["gov"] and a["red"]:   return 0
        if a["red"]:                return 1
        if a["gov"]:                return 2
        if a["breaking"]:           return 3
        return 4

    new_articles.sort(key=sort_key)
    print(f"\nTotal new relevant articles: {len(new_articles)}")

    sent = 0
    for a in new_articles:
        source   = a["source"]
        title    = a["title"]
        link     = a["link"]
        aid      = a["aid"]
        breaking = a["breaking"]
        red      = a["red"]
        pub_time = a["pub_time"]
        gov      = a["gov"]

        pin_key = make_id(title[:60])

        if gov and red:
            if pin_key not in pinned:
                msg = format_gov_pin(source, title, link, pub_time)
                message_id = send_message(msg)
                if message_id:
                    pin_message(message_id)
                    pinned[pin_key] = {"message_id": message_id, "pinned_at": now_utc().isoformat(), "title": title[:60]}
                    save_json(PINNED_FILE, pinned)
                    print(f"  → 📌 Gov pinned: {title[:60]}")
            else:
                message_id = send_message(format_gov(source, title, link, pub_time))

        elif gov:
            message_id = send_message(format_gov(source, title, link, pub_time))

        elif red:
            if pin_key not in pinned:
                msg = format_red_pin(source, title, link, pub_time)
                message_id = send_message(msg)
                if message_id:
                    pin_message(message_id)
                    pinned[pin_key] = {"message_id": message_id, "pinned_at": now_utc().isoformat(), "title": title[:60]}
                    save_json(PINNED_FILE, pinned)
                    print(f"  → 📌 Pinned: {title[:60]}")
            else:
                message_id = send_message(format_red(source, title, link, pub_time))

        elif breaking:
            message_id = send_message(format_breaking(source, title, link, pub_time))

        else:
            message_id = send_message(format_normal(source, title, link, pub_time))

        if message_id:
            seen.add(aid)
            sent += 1
            print(f"Sent: {title[:60]}")

    save_seen(seen)
    print(f"\nDone. Sent {sent} new articles.")

if __name__ == "__main__":
    main()
