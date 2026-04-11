import requests
import os

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHANNEL_ID,
    "text": "✅ Bot is connected and working!",
}

resp = requests.post(url, json=payload, timeout=10)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")
