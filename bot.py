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

EAT_OFFSET = timedelta(hours=3)

FEEDS = [
    ("Reuters Markets",        "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Economy",        "https://feeds.reuters.com/news/economy"),
    ("Reuters World",          "https://feeds.reuters.com/Reuters/worldNews"),
    ("MarketWatch",            "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("CNBC Markets",           "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("CNBC Politics",          "https://www.cnbc.com/id/10000115/device/rss/rss.html"),
    ("Investing.com",          "https://www.investing.com/rss/news.rss"),
    ("Yahoo Finance",          "https://finance.yahoo.com/rss/"),
    ("Forexlive",              "https://www.forexlive.com/feed/news"),
    ("Nasdaq",                 "https://www.nasdaq.com/feed/rssoutput.aspx"),
    ("CoinDesk",               "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph",          "https://cointelegraph.com/rss"),
    ("Al Jazeera",             "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Middle East Eye",        "https://www.middleeasteye.net/rss"),
]

WHITELIST = [
    "bitcoin","btc","crypto","ethereum","etf",
    "nasdaq","nq futures","s&p","spx","dow jones",
    "gold","xau","crude oil","brent","wti",
    "dollar","dxy","treasury","yield","bond",
    "fed","federal reserve","fomc","rate decision","rate hike","rate cut",
    "inflation","cpi","ppi","gdp","nonfarm","nfp","payroll","unemployment",
    "earnings","revenue","profit","guidance",
    "middle east","israel","gaza","hamas","hezbollah","west bank","lebanon",
    "iran","tehran","irgc","nuclear deal","sanctions",
    "saudi","riyadh","opec","oil supply",
    "iraq","baghdad","syria","houthi","red sea","strait of hormuz",
    "yemen","drone attack","missile","airstrike",
    "trump","white house","tariff","trade war","trade deal",
    "executive order","pentagon","us military",
    "congress","debt ceiling","federal budget",
    "china","beijing","taiwan","xi jinping",
    "russia","putin","ukraine","nato",
    "north korea","kim jong",
    "breaking","urgent","alert","flash","just in","developing",
]

BLACKLIST = [
    "horoscope","zodiac","celebrity","kardashian","oscars","grammy","nfl draft",
    "recipe","fashion","beauty","makeup","skincare","lifestyle","travel guide",
    "sports scores","game recap","nba scores","nhl scores","mlb scores",
    "movie review","tv show","streaming","netflix","disney","box office",
    "weather forecast","gardening","home decor","real estate tips",
    "social media trend","tiktok","instagram","viral","meme",
    "obituary","wedding","birth announcement",
]

RED_FOLDER_KEYWORDS = [
    "nonfarm payroll","nfp","non-farm","jobs report",
    "cpi report","inflation report","core cpi","core pce",
    "fomc","fed decision","rate decision","fed raises","fed cuts",
    "gdp report","gdp growth","gdp shrinks",
    "ppi report","retail sales","jobless claims",
    "ecb decision","boe decision","bank of england","european central bank",
    "war declared","invasion","nuclear","missile strike","major attack",
    "ceasefire","peace deal","coup","assassination",
    "market crash","circuit breaker","trading halt","flash crash",
    "trump tariff","trump sanctions","trump executive","trump fires","trump signs",
    "sec approves","sec rejects","bitcoin etf","crypto ban","exchange hack",
]

SCHEDULED_EVENTS = [
    {
        "name": "Non-Farm Payrolls (NFP)",
        "emoji": "💼",
        "keywords": ["nonfarm","nfp","non-farm","payroll","jobs report"],
        "utc_hour": 13, "utc_minute": 30,
        "description": "US Jobs Report — biggest monthly market mover",
        "impacts": "BTC  •  NQ  •  SPX  •  Gold  •  DXY",
    },
    {
        "name": "CPI — US Inflation Report",
        "emoji": "📈",
        "keywords": ["cpi","consumer price","inflation report","core cpi"],
        "utc_hour": 13, "utc_minute": 30,
        "description": "Consumer Price Index — key Fed policy driver",
        "impacts": "BTC  •  NQ  •  SPX  •  Gold  •  DXY",
    },
    {
        "name": "FOMC Rate Decision",
        "emoji": "🏦",
        "keywords": ["fomc","fed decision","rate decision","federal reserve decision"],
        "utc_hour": 19, "utc_minute": 0,
        "description": "Federal Reserve interest rate announcement",
        "impacts": "BTC  •  NQ  •  SPX  •  Gold  •  DXY",
    },
    {
        "name": "PPI — Producer Price Index",
        "emoji": "🏭",
        "keywords": ["ppi","producer price"],
        "utc_hour": 13, "utc_minute": 30,
        "description": "Producer Price Index — upstream inflation gauge",
        "impacts": "NQ  •  SPX  •  DXY",
    },
    {
        "name": "GDP Report",
        "emoji": "🌐",
        "keywords": ["gdp report","gdp growth","gdp shrinks","gross domestic product"],
        "utc_hour": 13, "utc_minute": 30,
        "description": "US GDP growth rate — economic health snapshot",
        "impacts": "NQ  •  SPX  •  Gold  •  DXY",
    },
    {
        "name": "Jobless Claims",
        "emoji": "📋",
        "keywords": ["jobless claims","initial claims","unemployment claims"],
        "utc_hour": 13, "utc_minute": 30,
        "description": "Weekly unemployment claims — labor market pulse",
        "impacts": "NQ  •  SPX  •  DXY",
    },
    {
        "name": "Retail Sales",
        "emoji": "🛒",
        "keywords": ["retail sales"],
        "utc_hour": 13, "utc_minute": 30,
        "description": "US Retail Sales — consumer spending barometer",
        "impacts": "NQ  •  SPX",
    },
    {
        "name": "ECB Rate Decision",
        "emoji": "🇪🇺",
        "keywords": ["ecb decision","european central bank","ecb rate"],
        "utc_hour": 13, "utc_minute": 15,
        "description": "European Central Bank rate announcement",
        "impacts": "Gold  •  DXY  •  SPX",
    },
]

# ── Tag each article with which markets it affects ───────────────────────────
def get_market_tags(title, summary=""):
    text = (title + " " + summary).lower()
    tags = []
    if any(w in text for w in ["bitcoin","btc","crypto","ethereum","coinbase","binance"]):
        tags.append("BTC")
    if any(w in text for w in ["nasdaq","nq","tech","nvidia","apple","microsoft","google","meta","amazon"]):
        tags.append("NQ")
    if any(w in text for w in ["s&p","spx","dow","stocks","equity","earnings","market"]):
        tags.append("SPX")
    if any(w in text for w in ["gold","xau","silver","safe haven","commodity"]):
        tags.append("GOLD")
    if any(w in text for w in ["oil","crude","brent","wti","opec","energy"]):
        tags.append("OIL")
    if any(w in text for w in ["dollar","dxy","fed","fomc","rate","inflation","cpi","ppi","gdp","treasury","yield","bond"]):
        tags.append("DXY")
    if any(w in text for w in ["middle east","israel","gaza","iran","saudi","houthi","ukraine","russia","china","taiwan"]):
        tags.append("GEO")
    return tags

def tag_bar(tags):
    if not tags:
        return ""
    icons = {
        "BTC":  "₿",
        "NQ":   "📊",
        "SPX":  "🗽",
        "GOLD": "🥇",
        "OIL":  "🛢",
        "DXY":  "💵",
        "GEO":  "🌍",
    }
    return "  ".join(f"{icons.get(t,'•')} #{t}" for t in tags)

# ── Message formatters ────────────────────────────────────────────────────────

def format_normal(source, title, link, pub_eat):
    tags = get_market_tags(title)
    tbar = tag_bar(tags)
    return (
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"📰  <b>{title}</b>\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"🏢  <i>{source}</i>   🕐 {pub_eat}\n"
        f"{tbar}\n"
        f"🔗  <a href='{link}'>Read full article →</a>"
    )

def format_breaking(source, title, link, pub_eat):
    tags = get_market_tags(title)
    tbar = tag_bar(tags)
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡  <b>BREAKING</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{title}</b>\n\n"
        f"🏢  <i>{source}</i>   🕐 {pub_eat}\n"
        f"{tbar}\n"
        f"🔗  <a href='{link}'>Read full article →</a>"
    )

def format_red(source, title, link, pub_eat):
    tags = get_market_tags(title)
    tbar = tag_bar(tags)
    return (
        f"🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n"
        f"🔴  <b>RED FOLDER</b>\n"
        f"🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n\n"
        f"<b>{title}</b>\n\n"
        f"🏢  <i>{source}</i>   🕐 {pub_eat}\n"
        f"{tbar}\n\n"
        f"🔗  <a href='{link}'>Read full article →</a>\n"
        f"🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴"
    )

def format_upcoming_pin(event, event_eat_str):
    return (
        f"📌━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴  <b>UPCOMING HIGH-IMPACT EVENT</b>\n"
        f"📌━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{event['emoji']}  <b>{event['name']}</b>\n\n"
        f"🕐  <b>{event_eat_str}</b>\n"
        f"📊  {event['description']}\n\n"
        f"📉  Affects:  {event['impacts']}\n\n"
        f"⚠️  <i>Expect high volatility at release.\n"
        f"Results will be posted here automatically.</i>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

def format_result_pin(event, event_eat_str, result_text):
    return (
        f"✅━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴  <b>RED FOLDER — DATA RELEASED</b>\n"
        f"✅━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{event['emoji']}  <b>{event['name']}</b>\n"
        f"🕐  Released:  {event_eat_str}\n\n"
        f"📊  <b>Result:</b>\n"
        f"{result_text}\n\n"
        f"📉  Affects:  {event['impacts']}\n\n"
        f"📌  <i>This pin resets in 24 hours.</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

# ── Helpers ──────────────────────────────────────────────────────────────────

def now_utc():
    return datetime.now(timezone.utc)

def now_eat():
    return now_utc() + EAT_OFFSET

def pub_to_eat_str(entry):
    try:
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if not pub:
            return now_eat().strftime("%H:%M EAT")
        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc) + EAT_OFFSET
        return pub_dt.strftime("%H:%M EAT")
    except Exception:
        return now_eat().strftime("%H:%M EAT")

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
    save_json(SEEN_FILE, list(seen)[-2000:])

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
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

def edit_message(message_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {"chat_id": CHANNEL_ID, "message_id": message_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.ok
    except Exception as e:
        print(f"Edit failed: {e}")
        return False

def article_id(entry):
    return hashlib.md5(
        (entry.get("id") or entry.get("link", "") or entry.get("title", "")).encode()
    ).hexdigest()

def is_relevant(title, summary=""):
    text = (title + " " + summary).lower()
    if any(b in text for b in BLACKLIST):
        return False
    return any(w in text for w in WHITELIST)

def is_breaking(title):
    return any(w in title.lower() for w in ["breaking","urgent","alert","flash","just in","developing"])

def is_red_folder(title, summary=""):
    return any(r in (title + " " + summary).lower() for r in RED_FOLDER_KEYWORDS)

def is_recent(entry):
    try:
        pub = entry.get("published_parsed") or entry.get("updated_parsed")
        if not pub:
            return True
        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
        return now_utc() - pub_dt < timedelta(minutes=5)
    except Exception:
        return True

def get_next_occurrence(utc_hour, utc_minute):
    now = now_utc()
    candidate = now.replace(hour=utc_hour, minute=utc_minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate

def fetch_event_result(event):
    for source_name, url in FEEDS[:6]:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                text = (title + " " + summary).lower()
                if any(kw in text for kw in event["keywords"]):
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    if pub:
                        pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                        yesterday_slot = get_next_occurrence(event["utc_hour"], event["utc_minute"]) - timedelta(days=1)
                        if pub_dt >= yesterday_slot:
                            link = entry.get("link", "")
                            return f"<b>{title}</b>\n🔗 <a href='{link}'>Full report →</a>"
        except Exception:
            continue
    return None

# ── Scheduled event pin manager ───────────────────────────────────────────────

def check_scheduled_events():
    pinned_events = load_json(PINNED_FILE, {})
    now = now_utc()

    for event in SCHEDULED_EVENTS:
        key = event["name"]
        next_time = get_next_occurrence(event["utc_hour"], event["utc_minute"])
        hours_until = (next_time - now).total_seconds() / 3600
        event_eat_str = (next_time + EAT_OFFSET).strftime("%A  %d %b %Y  —  %H:%M EAT")

        stored = pinned_events.get(key, {})
        msg_id = stored.get("message_id")
        pinned_at = stored.get("pinned_at")
        released = stored.get("released", False)

        # 24hr reset
        if pinned_at:
            pinned_dt = datetime.fromisoformat(pinned_at)
            if (now - pinned_dt).total_seconds() > 86400:
                print(f"24hr reset: {key}")
                if msg_id:
                    unpin_message(msg_id)
                del pinned_events[key]
                save_json(PINNED_FILE, pinned_events)
                continue

        # Pin 8 hours before
        if 0 < hours_until <= 8 and not msg_id:
            text = format_upcoming_pin(event, event_eat_str)
            new_msg_id = send_message(text)
            if new_msg_id:
                pin_message(new_msg_id)
                pinned_events[key] = {
                    "message_id": new_msg_id,
                    "pinned_at": now.isoformat(),
                    "released": False,
                    "event_time_utc": next_time.isoformat(),
                }
                save_json(PINNED_FILE, pinned_events)
                print(f"📌 Pinned upcoming: {key} — {event_eat_str}")

        # Update with results after event fires
        elif msg_id and not released and now >= next_time:
            result = fetch_event_result(event)
            if result:
                updated = format_result_pin(event, event_eat_str, result)
                edit_message(msg_id, updated)
                pinned_events[key]["released"] = True
                save_json(PINNED_FILE, pinned_events)
                print(f"✅ Results posted: {key}")

    save_json(PINNED_FILE, pinned_events)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    seen = load_seen()

    print("Checking scheduled events...")
    check_scheduled_events()

    new_articles = []

    for source_name, url in FEEDS:
        try:
            print(f"Fetching: {source_name}")
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            print(f"  → {len(feed.entries)} entries")
            for entry in feed.entries[:15]:
                aid = article_id(entry)
                if aid in seen:
                    continue
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                link = entry.get("link", "")
                if is_relevant(title, summary) and is_recent(entry):
                    red = is_red_folder(title, summary)
                    breaking = is_breaking(title)
                    eat_time = pub_to_eat_str(entry)
                    new_articles.append((source_name, title, link, aid, breaking, red, eat_time))
                    flag = "🔴" if red else ("⚡" if breaking else "✓")
                    print(f"  {flag} {title[:70]}")
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    # Red first → breaking → normal
    new_articles.sort(key=lambda x: (not x[5], not x[4]))
    print(f"\nTotal new relevant articles: {len(new_articles)}")

    sent = 0
    for source, title, link, aid, breaking, red, eat_time in new_articles:
        if red:
            msg = format_red(source, title, link, eat_time)
        elif breaking:
            msg = format_breaking(source, title, link, eat_time)
        else:
            msg = format_normal(source, title, link, eat_time)

        message_id = send_message(msg)
        if message_id:
            seen.add(aid)
            sent += 1
            print(f"Sent ({'RED' if red else 'BREAKING' if breaking else 'normal'}): {title[:60]}")
            if red:
                pinned = pin_message(message_id)
                print(f"  → Pin: {'✅' if pinned else '❌'}")

    save_seen(seen)
    print(f"\nDone. Sent {sent} new articles.")

if __name__ == "__main__":
    main()
