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
    ("CNBC Economy",           "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
    ("Investing.com",          "https://www.investing.com/rss/news.rss"),
    ("Yahoo Finance",          "https://finance.yahoo.com/rss/"),
    ("Forexlive",              "https://www.forexlive.com/feed/news"),
    ("CoinDesk",               "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph",          "https://cointelegraph.com/rss"),
    ("Al Jazeera",             "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Middle East Eye",        "https://www.middleeasteye.net/rss"),
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
        "keywords": ["rate","fomc","federal funds","monetary policy","interest","statement","minutes"],
    },
    {
        "name": "BEA",
        "url": "https://www.bea.gov/rss/latest_revision.xml",
        "keywords": ["gdp","gross domestic","personal income","pce","consumer spending"],
    },
    {
        "name": "US Treasury",
        "url": "https://home.treasury.gov/news/press-releases/rss.xml",
        "keywords": ["sanctions","tariff","currency","debt","deficit"],
    },
    {
        "name": "White House",
        "url": "https://www.whitehouse.gov/feed/",
        "keywords": ["executive order","tariff","trade","sanction","trump"],
    },
    {
        "name": "EIA",
        "url": "https://www.eia.gov/rss/press_releases.xml",
        "keywords": ["crude oil","petroleum","natural gas","inventory","opec","energy"],
    },
]

# ── TIER 1: Must-send — these always get through no matter what ───────────────
TIER1_KEYWORDS = [
    # Hard economic data releases
    "nonfarm payroll","non-farm payroll","jobs report","nfp",
    "cpi report","consumer price index","core cpi","inflation report",
    "pce deflator","core pce",
    "fomc","fed decision","rate decision","fed raises","fed cuts","fed holds",
    "gdp report","gdp growth","gdp contracts","gdp shrinks",
    "ppi report","producer price index",
    "retail sales report","jobless claims",
    "ecb rate","ecb decision","bank of england rate","boe decision",
    # Geopolitical shocks
    "war declared","invasion begins","nuclear strike","missile strike",
    "ceasefire agreement","peace deal signed","coup","assassination",
    "market crash","trading halt","circuit breaker","flash crash",
    # Trump hard moves
    "trump signs","trump imposes","trump announces tariff","trump sanctions",
    "executive order signed",
    # Crypto hard events
    "bitcoin etf approved","bitcoin etf rejected","crypto ban","exchange hack",
    "sec approves","sec rejects",
    # Central bank surprises
    "emergency rate cut","emergency rate hike","surprise rate",
    "quantitative easing","quantitative tightening",
]

# ── TIER 2: Important but needs TWO keyword matches to pass ───────────────────
TIER2_KEYWORDS = [
    "bitcoin","btc","ethereum","eth","crypto","solana","xrp",
    "nasdaq","s&p 500","spx","dow jones",
    "gold","xau","crude oil","brent","wti","opec",
    "federal reserve","fed","powell","fomc",
    "inflation","cpi","ppi","gdp","unemployment","payroll",
    "tariff","trade war","trade deal","sanctions",
    "trump","white house",
    "israel","gaza","iran","hamas","hezbollah","houthi",
    "middle east","red sea","strait of hormuz",
    "ukraine","russia","putin","nato",
    "china","xi jinping","taiwan",
    "dollar","dxy","treasury yield","bond yield",
    "rate hike","rate cut","interest rate",
    "earnings","revenue miss","profit warning",
    "recession","default","bankruptcy","crisis",
    "breaking","urgent","just in",
    "opec","oil supply","oil cut","oil output",
    "saudi arabia","iran nuclear","north korea",
]

# ── BLACKLIST: never send these ───────────────────────────────────────────────
BLACKLIST = [
    "horoscope","zodiac","celebrity","kardashian","oscars","grammy",
    "recipe","fashion","beauty","makeup","skincare","lifestyle",
    "travel guide","sports scores","game recap",
    "nba scores","nhl scores","mlb scores","nfl scores",
    "movie review","tv show","streaming","netflix","disney","box office",
    "weather forecast","gardening","home decor",
    "social media trend","tiktok","instagram","viral","meme",
    "obituary","wedding","birth announcement","real estate tips",
    "quiz","how to","best ways","top 10","listicle",
    "review","preview","explainer","what is","guide to",
]

# ── STRICT red folder phrases — ONLY these get pinned ────────────────────────
RED_FOLDER_STRICT = [
    "nonfarm payroll",
    "non-farm payroll",
    "jobs report",
    "nfp report",
    "consumer price index",
    "cpi report",
    "core cpi",
    "core pce",
    "pce deflator",
    "fomc decision",
    "fed decision",
    "rate decision",
    "fed raises rates",
    "fed cuts rates",
    "fed holds rates",
    "emergency rate cut",
    "emergency rate hike",
    "surprise rate cut",
    "surprise rate hike",
    "gdp report",
    "gdp growth",
    "gdp contracts",
    "producer price index",
    "ppi report",
    "retail sales report",
    "jobless claims report",
    "ecb rate decision",
    "ecb decision",
    "bank of england rate",
    "boe rate decision",
    "war declared",
    "invasion begins",
    "market crash",
    "trading halt",
    "circuit breaker",
    "bitcoin etf approved",
    "bitcoin etf rejected",
]

def get_market_tags(title, summary=""):
    text = (title + " " + summary).lower()
    tags = []
    if any(w in text for w in ["bitcoin","btc","crypto","ethereum","eth","coinbase","binance","solana","xrp"]):
        tags.append("BTC")
    if any(w in text for w in ["nasdaq","nq","nvidia","apple","microsoft","google","meta","amazon","tesla","tech stock"]):
        tags.append("NQ")
    if any(w in text for w in ["s&p","spx","dow","stocks","equity","earnings","market rally","market sell"]):
        tags.append("SPX")
    if any(w in text for w in ["gold","xau","silver","safe haven"]):
        tags.append("GOLD")
    if any(w in text for w in ["oil","crude","brent","wti","opec","natural gas","energy"]):
        tags.append("OIL")
    if any(w in text for w in ["dollar","dxy","usd","fed","fomc","rate","inflation","cpi","ppi","gdp","treasury","yield","bond"]):
        tags.append("DXY")
    if any(w in text for w in ["middle east","israel","gaza","iran","saudi","houthi","ukraine","russia","china","taiwan","war","attack","strike","missile","drone"]):
        tags.append("GEO")
    return tags

def tag_line(tags):
    icons = {"BTC":"₿","NQ":"📊","SPX":"🗽","GOLD":"🥇","OIL":"🛢","DXY":"💵","GEO":"🌍"}
    return "  ".join(f"{icons[t]} #{t}" for t in tags) if tags else ""

def is_tier1(title, summary=""):
    text = (title + " " + summary).lower()
    return any(phrase in text for phrase in TIER1_KEYWORDS)

def is_tier2(title, summary=""):
    text = (title + " " + summary).lower()
    matches = sum(1 for kw in TIER2_KEYWORDS if kw in text)
    return matches >= 2

def is_important(title, summary=""):
    text = (title + " " + summary).lower()
    if any(b in text for b in BLACKLIST):
        return False
    return is_tier1(title, summary) or is_tier2(title, summary)

def is_red_folder(title, summary=""):
    text = (title + " " + summary).lower()
    return any(phrase in text for phrase in RED_FOLDER_STRICT)

def is_breaking(title):
    return any(w in title.lower() for w in ["breaking","urgent","alert","flash","just in","developing"])

def is_recent(pub_parsed, minutes=30):
    try:
        if not pub_parsed:
            return True
        pub_dt = datetime(*pub_parsed[:6], tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - pub_dt < timedelta(minutes=minutes)
    except Exception:
        return True

def now_utc():
    return datetime.now(timezone.utc)

def pub_time_str(pub_parsed):
    try:
        if not pub_parsed:
            return now_utc().strftime("%d %b %H:%M UTC")
        return datetime(*pub_parsed[:6], tzinfo=timezone.utc).strftime("%d %b %H:%M UTC")
    except Exception:
        return now_utc().strftime("%d %b %H:%M UTC")

def article_id(entry):
    return hashlib.md5(
        (entry.get("id") or entry.get("link","") or entry.get("title","")).encode()
    ).hexdigest()

def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()

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
        return resp.json().get("result",{}).get("message_id")
    except Exception as e:
        print(f"Send failed: {e}")
        return None

def pin_message(message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/pinChatMessage"
    try:
        resp = requests.post(url, json={"chat_id": CHANNEL_ID, "message_id": message_id, "disable_notification": False}, timeout=10)
        if not resp.ok:
            print(f"Pin error: {resp.status_code} {resp.text}")
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

# ── Message formats — headline only, no links ─────────────────────────────────

def format_normal(source, title, pub_time, tags):
    msg = f"<b>{title}</b>\n\n"
    msg += f"<i>{source}</i>  •  {pub_time}"
    if tags:
        msg += f"\n{tag_line(tags)}"
    return msg

def format_breaking(source, title, pub_time, tags):
    msg = f"⚡ <b>BREAKING</b>\n\n"
    msg += f"<b>{title}</b>\n\n"
    msg += f"<i>{source}</i>  •  {pub_time}"
    if tags:
        msg += f"\n{tag_line(tags)}"
    return msg

def format_gov(source, title, pub_time, tags):
    msg = f"🏛 <b>OFFICIAL DATA</b>\n\n"
    msg += f"<b>{title}</b>\n\n"
    msg += f"<i>{source}</i>  •  {pub_time}"
    if tags:
        msg += f"\n{tag_line(tags)}"
    return msg

def format_red_folder(source, title, pub_time, tags):
    msg = f"🔴 <b>RED FOLDER</b>\n\n"
    msg += f"<b>{title}</b>\n\n"
    msg += f"<i>{source}</i>  •  {pub_time}"
    if tags:
        msg += f"\n{tag_line(tags)}"
    return msg

def format_red_folder_pin(source, title, pub_time, tags):
    msg = f"📌 🔴 <b>RED FOLDER — PINNED</b>\n\n"
    msg += f"<b>{title}</b>\n\n"
    msg += f"<i>{source}</i>  •  {pub_time}"
    if tags:
        msg += f"\n{tag_line(tags)}"
    msg += f"\n\n<i>📌 Pinned  •  resets in 24 hours</i>"
    return msg

def cleanup_old_pins():
    pinned = load_json(PINNED_FILE, {})
    now = now_utc()
    changed = False
    for key in list(pinned.keys()):
        pinned_at = pinned[key].get("pinned_at")
        if pinned_at:
            try:
                pinned_dt = datetime.fromisoformat(pinned_at)
                if (now - pinned_dt).total_seconds() > 86400:
                    msg_id = pinned[key].get("message_id")
                    if msg_id:
                        unpin_message(msg_id)
                        print(f"24hr reset — unpinned: {pinned[key].get('title','')[:40]}")
                    del pinned[key]
                    changed = True
            except Exception:
                del pinned[key]
                changed = True
    if changed:
        save_json(PINNED_FILE, pinned)
    return pinned

def fetch_gov(seen):
    articles = []
    for source in GOV_SOURCES:
        try:
            print(f"Gov: {source['name']}")
            resp = requests.get(source["url"], headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if not resp.ok:
                continue
            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:10]:
                aid = article_id(entry)
                if aid in seen:
                    continue
                title = entry.get("title","").strip()
                summary = entry.get("summary","")
                link = entry.get("link","")
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if not title or not is_recent(pub, minutes=60):
                    continue
                text = (title+" "+summary).lower()
                if not any(kw in text for kw in source["keywords"]):
                    continue
                articles.append({
                    "source": source["name"],
                    "title": title,
                    "aid": aid,
                    "pub": pub,
                    "red": is_red_folder(title, summary),
                    "breaking": False,
                    "gov": True,
                })
                print(f"  {'🔴' if is_red_folder(title,summary) else '🏛'} {title[:70]}")
        except Exception as e:
            print(f"Gov error {source['name']}: {e}")
    return articles

def main():
    seen = load_seen()
    pinned = cleanup_old_pins()
    all_articles = []

    # ── RSS feeds ─────────────────────────────────────────────────────────────
    for source_name, url in FEEDS:
        try:
            print(f"Fetching: {source_name}")
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            print(f"  → {len(feed.entries)} entries")
            for entry in feed.entries[:20]:
                aid = article_id(entry)
                if aid in seen:
                    continue
                title = entry.get("title","")
                summary = entry.get("summary","")
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if is_important(title, summary) and is_recent(pub, minutes=30):
                    all_articles.append({
                        "source": source_name,
                        "title": title,
                        "aid": aid,
                        "pub": pub,
                        "red": is_red_folder(title, summary),
                        "breaking": is_breaking(title),
                        "gov": False,
                    })
                    flag = "🔴" if is_red_folder(title,summary) else ("⚡" if is_breaking(title) else "✓")
                    print(f"  {flag} {title[:70]}")
        except Exception as e:
            print(f"Error {source_name}: {e}")

    # ── Government sources ────────────────────────────────────────────────────
    all_articles.extend(fetch_gov(seen))

    # Sort: red > gov > breaking > normal
    def sort_key(a):
        if a["red"]:      return 0
        if a["gov"]:      return 1
        if a["breaking"]: return 2
        return 3

    all_articles.sort(key=sort_key)
    print(f"\nTotal: {len(all_articles)} articles")

    sent = 0
    for a in all_articles:
        source   = a["source"]
        title    = a["title"]
        aid      = a["aid"]
        pub      = a["pub"]
        red      = a["red"]
        breaking = a["breaking"]
        gov      = a["gov"]
        pub_time = pub_time_str(pub)
        tags     = get_market_tags(title)
        pin_key  = make_id(title[:60])

        if red:
            if pin_key not in pinned:
                # Send pinned red folder
                msg = format_red_folder_pin(source, title, pub_time, tags)
                message_id = send_message(msg)
                if message_id:
                    success = pin_message(message_id)
                    print(f"  → Pin attempt: {'✅' if success else '❌'} message_id={message_id}")
                    if success:
                        pinned[pin_key] = {
                            "message_id": message_id,
                            "pinned_at": now_utc().isoformat(),
                            "title": title[:60],
                        }
                        save_json(PINNED_FILE, pinned)
                    seen.add(aid)
                    sent += 1
            else:
                # Duplicate red folder event — send without pinning
                msg = format_red_folder(source, title, pub_time, tags)
                message_id = send_message(msg)
                if message_id:
                    seen.add(aid)
                    sent += 1

        elif gov:
            msg = format_gov(source, title, pub_time, tags)
            message_id = send_message(msg)
            if message_id:
                seen.add(aid)
                sent += 1

        elif breaking:
            msg = format_breaking(source, title, pub_time, tags)
            message_id = send_message(msg)
            if message_id:
                seen.add(aid)
                sent += 1

        else:
            msg = format_normal(source, title, pub_time, tags)
            message_id = send_message(msg)
            if message_id:
                seen.add(aid)
                sent += 1

        if sent > 0:
            print(f"Sent: {title[:60]}")

    save_seen(seen)
    print(f"\nDone. Sent {sent} articles.")

if __name__ == "__main__":
    main()
