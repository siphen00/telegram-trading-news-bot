import feedparser
import requests
import json
import os
import hashlib
import socket
from datetime import datetime, timezone, timedelta

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

GOV_SOURCES = [
    {
        "name": "BLS",
        "url": "https://www.bls.gov/feed/bls_latest.rss",
        "keywords": ["employment","nonfarm","cpi","ppi","unemployment","jobs","inflation","consumer price","producer price","jobless"],
    },
    {
        "name": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "keywords": ["rate","fomc","federal funds","monetary policy","balance sheet","interest","statement","minutes","beige book"],
    },
    {
        "name": "BEA",
        "url": "https://www.bea.gov/rss/latest_revision.xml",
        "keywords": ["gdp","gross domestic","personal income","pce","current account","trade","consumer spending"],
    },
    {
        "name": "US Census",
        "url": "https://www.census.gov/economic-indicators/feed.xml",
        "keywords": ["retail sales","housing","construction","durable goods","trade deficit","manufacturers"],
    },
    {
        "name": "US Treasury",
        "url": "https://home.treasury.gov/news/press-releases/rss.xml",
        "keywords": ["debt","yield","auction","bond","deficit","sanctions","tariff","currency"],
    },
    {
        "name": "White House",
        "url": "https://www.whitehouse.gov/feed/",
        "keywords": ["executive order","proclamation","tariff","trade","sanction","statement","trump"],
    },
    {
        "name": "EIA",
        "url": "https://www.eia.gov/rss/press_releases.xml",
        "keywords": ["crude oil","petroleum","natural gas","gasoline","inventory","opec","barrel","energy"],
    },
    {
        "name": "SEC",
        "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&datetype=custom&owner=include&count=10&search_text=&output=atom",
        "keywords": ["bitcoin","etf","crypto","enforcement","fraud","approval","rejection"],
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
    "middle east","israel","gaza","hamas","hezbollah","west bank",
    "iran","tehran","irgc","nuclear","sanctions","khamenei",
    "saudi arabia","riyadh","mbs","opec",
    "iraq","baghdad","syria","houthi","houthis",
    "red sea","strait of hormuz","gulf","persian gulf",
    "yemen","drone","missile","airstrike","attack","strike",
    "lebanon","beirut","egypt","qatar","uae","dubai",
    "trump","donald trump","white house",
    "tariff","tariffs","trade war","trade deal","trade policy",
    "executive order","congress","senate",
    "sanctions","pentagon","us military","nato",
    "debt ceiling","federal budget","deficit",
    "china","beijing","xi jinping","taiwan",
    "japan","bank of japan","boj","north korea",
    "russia","putin","ukraine","kyiv",
    "ecb","european central bank","bank of england","boe",
    "breaking","urgent","alert","flash","just in","developing",
    "crash","collapse","default","bankruptcy","crisis",
    "coup","explosion","ceasefire","peace deal",
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

# ── STRICT red folder — ONLY real scheduled economic releases ─────────────────
# These are the ONLY things that get the red folder treatment and get pinned
RED_FOLDER_STRICT = [
    "nonfarm payroll",
    "non-farm payroll",
    "nfp report",
    "jobs report",
    "cpi report",
    "consumer price index",
    "core cpi",
    "core pce",
    "pce deflator",
    "fomc decision",
    "fed decision",
    "federal reserve decision",
    "rate decision",
    "fed raises rates",
    "fed cuts rates",
    "fed holds rates",
    "gdp report",
    "gdp growth",
    "gdp contracts",
    "ppi report",
    "producer price index",
    "retail sales report",
    "jobless claims report",
    "initial claims",
    "ecb rate decision",
    "ecb decision",
    "bank of england rate",
    "boe rate decision",
]

def get_market_tags(title, summary=""):
    text = (title + " " + summary).lower()
    tags = []
    if any(w in text for w in ["bitcoin","btc","crypto","ethereum","eth","coinbase","binance","solana","xrp"]):
        tags.append("BTC")
    if any(w in text for w in ["nasdaq","nq","tech","nvidia","apple","microsoft","google","meta","amazon","tesla"]):
        tags.append("NQ")
    if any(w in text for w in ["s&p","spx","dow","stocks","equity","earnings","market"]):
        tags.append("SPX")
    if any(w in text for w in ["gold","xau","silver","safe haven","commodity"]):
        tags.append("GOLD")
    if any(w in text for w in ["oil","crude","brent","wti","opec","natural gas","energy"]):
        tags.append("OIL")
    if any(w in text for w in ["dollar","dxy","usd","fed","fomc","rate","inflation","cpi","ppi","gdp","treasury","yield","bond"]):
        tags.append("DXY")
    if any(w in text for w in ["middle east","israel","gaza","iran","saudi","houthi","ukraine","russia","china","taiwan","war","attack","strike"]):
        tags.append("GEO")
    return tags

def tag_line(tags):
    icons = {"BTC":"₿","NQ":"📊","SPX":"🗽","GOLD":"🥇","OIL":"🛢","DXY":"💵","GEO":"🌍"}
    return "  ".join(f"{icons.get(t,'')} #{t}" for t in tags) if tags else ""

# ── Message formats — WatcherGuru style ──────────────────────────────────────

def format_normal(source, title, link, pub_time):
    tags = tag_line(get_market_tags(title))
    msg = f"<b>JUST IN:</b> {title}\n\n<i>@{source}</i>  •  {pub_time}"
    if tags:
        msg += f"\n{tags}"
    msg += f"\n\n<a href='{link}'>Read more →</a>"
    return msg

def format_breaking(source, title, link, pub_time):
    tags = tag_line(get_market_tags(title))
    msg = f"⚡ <b>BREAKING:</b> {title}\n\n<i>@{source}</i>  •  {pub_time}"
    if tags:
        msg += f"\n{tags}"
    msg += f"\n\n<a href='{link}'>Read more →</a>"
    return msg

def format_gov(source, title, link, pub_time):
    tags = tag_line(get_market_tags(title))
    msg = f"🏛 <b>OFFICIAL DATA:</b> {title}\n\n<i>@{source}</i>  •  {pub_time}"
    if tags:
        msg += f"\n{tags}"
    msg += f"\n\n<a href='{link}'>Official release →</a>"
    return msg

def format_red_folder(source, title, link, pub_time):
    tags = tag_line(get_market_tags(title))
    msg = (
        f"🔴 <b>RED FOLDER</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"<i>@{source}</i>  •  {pub_time}"
    )
    if tags:
        msg += f"\n{tags}"
    msg += f"\n\n<a href='{link}'>Full report →</a>"
    return msg

def format_red_folder_pin(source, title, link, pub_time):
    tags = tag_line(get_market_tags(title))
    msg = (
        f"📌 🔴 <b>RED FOLDER — PINNED</b>\n\n"
        f"<b>{title}</b>\n\n"
        f"<i>@{source}</i>  •  {pub_time}"
    )
    if tags:
        msg += f"\n{tags}"
    msg += f"\n\n<a href='{link}'>Full report →</a>"
    msg += f"\n\n<i>Pinned • resets in 24 hours</i>"
    return msg

def now_utc():
    return datetime.now(timezone.utc)

def pub_time_str(pub_parsed):
    try:
        if not pub_parsed:
            return now_utc().strftime("%d %b %H:%M UTC")
        return datetime(*pub_parsed[:6], tzinfo=timezone.utc).strftime("%d %b %H:%M UTC")
    except Exception:
        return now_utc().strftime("%d %b %H:%M UTC")

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
    # STRICT — only exact economic release phrases qualify
    text = (title + " " + summary).lower()
    return any(phrase in text for phrase in RED_FOLDER_STRICT)

def is_recent(pub_parsed, minutes=30):
    try:
        if not pub_parsed:
            return True
        pub_dt = datetime(*pub_parsed[:6], tzinfo=timezone.utc)
        return now_utc() - pub_dt < timedelta(minutes=minutes)
    except Exception:
        return True

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

def fetch_gov_sources(seen):
    articles = []
    for source in GOV_SOURCES:
        try:
            print(f"Fetching gov: {source['name']}")
            resp = requests.get(source["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
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
                if not is_recent(pub, minutes=60):
                    continue
                text = (title + " " + summary).lower()
                if not any(kw in text for kw in source["keywords"]):
                    continue
                red = is_red_folder(title, summary)
                articles.append({
                    "source": source["name"],
                    "title": title,
                    "link": link,
                    "aid": aid,
                    "pub": pub,
                    "red": red,
                    "breaking": False,
                    "gov": True,
                })
                print(f"  {'🔴' if red else '🏛'} {title[:70]}")
        except Exception as e:
            print(f"Error fetching gov {source['name']}: {e}")
    return articles

def main():
    seen = load_seen()
    pinned = cleanup_old_pins()
    all_articles = []

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
                if is_relevant(title, summary) and is_recent(pub, minutes=30):
                    all_articles.append({
                        "source": source_name,
                        "title": title,
                        "link": link,
                        "aid": aid,
                        "pub": pub,
                        "red": is_red_folder(title, summary),
                        "breaking": is_breaking(title),
                        "gov": False,
                    })
                    flag = "🔴" if is_red_folder(title, summary) else ("⚡" if is_breaking(title) else "✓")
                    print(f"  {flag} {title[:70]}")
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    # ── Government sources ────────────────────────────────────────────────────
    all_articles.extend(fetch_gov_sources(seen))

    # Sort: red folder first → gov → breaking → normal
    def sort_key(a):
        if a["red"]:      return 0
        if a["gov"]:      return 1
        if a["breaking"]: return 2
        return 3

    all_articles.sort(key=sort_key)
    print(f"\nTotal new articles: {len(all_articles)}")

    sent = 0
    for a in all_articles:
        source   = a["source"]
        title    = a["title"]
        link     = a["link"]
        aid      = a["aid"]
        pub      = a["pub"]
        red      = a["red"]
        breaking = a["breaking"]
        gov      = a["gov"]
        pub_time = pub_time_str(pub)
        pin_key  = make_id(title[:60])

        if red:
            # First time seeing this red folder event → pin it
            if pin_key not in pinned:
                msg = format_red_folder_pin(source, title, link, pub_time)
                message_id = send_message(msg)
                if message_id:
                    pin_message(message_id)
                    pinned[pin_key] = {
                        "message_id": message_id,
                        "pinned_at": now_utc().isoformat(),
                        "title": title[:60],
                    }
                    save_json(PINNED_FILE, pinned)
                    print(f"  → 📌 RED FOLDER pinned: {title[:60]}")
            else:
                # Already pinned, send as regular red folder message
                message_id = send_message(format_red_folder(source, title, link, pub_time))
        elif gov:
            message_id = send_message(format_gov(source, title, link, pub_time))
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
