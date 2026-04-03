import os
import time
import requests
from telegram import Bot

# Config from Environment Variables
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHANNEL = os.getenv("CHANNEL_ID")
API_KEY = os.getenv("ALPHA_KEY")
bot = Bot(token=TOKEN)

# Assets: BTC, QQQ (Nasdaq), and GOLD
TICKERS = "CRYPTO:BTC,QQQ,GOLD"

def fetch_and_post():
    # Topics include Economy/Macro and Financial Markets
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={TICKERS}&topics=economy_macro,financial_markets&sort=LATEST&apikey={API_KEY}"
    
    try:
        data = requests.get(url).json()
        feed = data.get("feed", [])
        
        for item in feed[:3]:  # Top 3 latest high-impact news
            # High Trust Filter: Check for keywords like 'War', 'Fed', 'CPI', 'Conflict'
            important_keywords = ['war', 'conflict', 'fed', 'cpi', 'rates', 'geopolitical']
            text_to_check = (item['title'] + item['summary']).lower()
            
            is_priority = any(word in text_to_check for word in important_keywords)
            prefix = "🔥 *URGENT MACRO*" if is_priority else "📈 *MARKET UPDATE*"

            message = (
                f"{prefix}\n\n"
                f"📌 *{item['title']}*\n\n"
                f"📊 *Sentiment:* {item['overall_sentiment_label']}\n"
                f"🔗 [Read Source]({item['url']})"
            )
            
            bot.send_message(chat_id=CHANNEL, text=message, parse_mode='Markdown')
            time.sleep(5) # Prevent spamming
            
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    while True:
        fetch_and_post()
        time.sleep(600) # Check every 10 minutes (to respect free API limits)
