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
    icons = {"BTC":"₿","NQ":"📊","SPX":"🗽","GOLD":"🥇","OIL":"🛢","DXY":"💵","GEO":"🌍"}
    return "  ".join(f"{icons.get(t,'•')} #{t}" for t in tags) if tags else ""

def format_normal(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"📰  <b>{title}</b>\n"
        f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        f"🏢  <i>{source}</i>   🕐 {pub_time}\n"
        f"{tags}\n"
        f"🔗  <a href='{link}'>Read full article →</a>"
    )

def format_breaking(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡  <b>BREAKING</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{title}</b>\n\n"
        f"🏢  <i>{source}</i>   🕐 {pub_time}\n"
        f"{tags}\n"
        f"🔗  <a href='{link}'>Read full article →</a>"
    )

def format_red(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n"
        f"🔴  <b>RED FOLDER</b>\n"
        f"🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴\n\n"
        f"<b>{title}</b>\n\n"
        f"🏢  <i>{source}</i>   🕐 {pub_time}\n"
        f"{tags}\n\n"
        f"🔗  <a href='{link}'>Read full article →</a>\n"
        f"🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴"
    )

def format_red_pin(source, title, link, pub_time):
    tags = tag_bar(get_market_tags(title))
    return (
        f"📌━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔴  <b>RED FOLDER — PINNED</b>\n"
        f"📌━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"<b>{title}</b>\n\n"
        f"🏢  <i>{source}</i>   🕐 {pub_time}\n"
        f"{tags}\n\n"
        f"🔗  <a href='{link}'>Full report →</a>\n\n"
        f"📌  <i>Pinned — resets in 24 hours</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━"
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
                    print(f"24hr reset — unpinned: {key}")
                del pinned[key]
                changed = True
    if changed:
        save_json(PINNED_FILE, pinned)
    return pinned

def main():
    seen = load_seen()
    pinned = cleanup_old_pins()
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
                    pub_time = pub_time_str(entry)
                    new_articles.append((source_name, title, link, aid, breaking, red, pub_time))
                    flag = "🔴" if red else ("⚡" if breaking else "✓")
                    print(f"  {flag} {title[:70]}")
        except Exception as e:
            print(f"Error fetching {source_name}: {e}")

    new_articles.sort(key=lambda x: (not x[5], not x[4]))
    print(f"\nTotal new relevant articles: {len(new_articles)}")

    sent = 0
    for source, title, link, aid, breaking, red, pub_time in new_articles:
        if red:
            pin_key = hashlib.md5(title[:60].encode()).hexdigest()
            if pin_key not in pinned:
                msg = format_red_pin(source, title, link, pub_time)
                message_id = send_message(msg)
                if message_id:
                    pin_message(message_id)
                    pinned[pin_key] = {
                        "message_id": message_id,
                        "pinned_at": now_utc().isoformat(),
                        "title": title[:60],
                    }
                    save_json(PINNED_FILE, pinned)
                    print(f"  → 📌 Pinned: {title[:60]}")
            else:
                msg = format_red(source, title, link, pub_time)
                message_id = send_message(msg)
            seen.add(aid)
            sent += 1
        else:
            msg = format_breaking(source, title, link, pub_time) if breaking else format_normal(source, title, link, pub_time)
            message_id = send_message(msg)
            if message_id:
                seen.add(aid)
                sent += 1
                print(f"Sent ({'BREAKING' if breaking else 'normal'}): {title[:60]}")

    save_seen(seen)
    print(f"\nDone. Sent {sent} new articles.")

if __name__ == "__main__":
    main()
