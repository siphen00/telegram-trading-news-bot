import requests
import os

print("STARTING BOT")

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

print("TOKEN FOUND:", TOKEN is not None)
print("CHANNEL FOUND:", CHANNEL_ID is not None)

if TOKEN is None or CHANNEL_ID is None:
    raise Exception("Secrets missing")

response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={
        "chat_id": CHANNEL_ID,
        "text": "✅ BOT CONNECTION SUCCESSFUL"
    }
)

print(response.text)
