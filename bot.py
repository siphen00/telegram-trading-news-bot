import requests
import os

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"}
    resp = requests.post(url, json=payload, timeout=10)
    print(f"Send status: {resp.status_code} {resp.text}")
    return resp.json().get("result", {}).get("message_id")

def pin_message(message_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/pinChatMessage"
    payload = {"chat_id": CHANNEL_ID, "message_id": message_id, "disable_notification": False}
    resp = requests.post(url, json=payload, timeout=10)
    print(f"Pin status: {resp.status_code} {resp.text}")
    return resp.ok

msg_id = send_message("🔴 <b>RED FOLDER — TEST</b>\nNFP Jobs Report Released — 200K vs 180K expected\n\n📌 This message should be pinned")

if msg_id:
    print(f"Message sent with ID: {msg_id}")
    result = pin_message(msg_id)
    print(f"Pin result: {'✅ Pinned!' if result else '❌ Failed to pin'}")
else:
    print("❌ Message failed to send")
