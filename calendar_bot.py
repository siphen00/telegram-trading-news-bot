import requests
import os
from datetime import datetime, timedelta

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]


USD_EVENTS = [

("ISM Services PMI", "17:00"),
("ISM Manufacturing PMI", "17:00"),
("CPI", "15:30"),
("Core CPI", "15:30"),
("NFP", "15:30"),
("Unemployment Rate", "15:30"),
("Retail Sales", "15:30"),
("GDP", "15:30"),
("FOMC", "21:00"),
("Powell Speech", "20:00")

]


def send_message(text):

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHANNEL_ID,
            "text": text
        }
    )


def pin_message(message_id):

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/pinChatMessage",
        data={
            "chat_id": CHANNEL_ID,
            "message_id": message_id
        }
    )


today = datetime.utcnow().strftime("%Y-%m-%d")

message = "📌 TODAY'S USD RED FOLDER EVENTS\n\n"

for event, time in USD_EVENTS:

    message += f"{time} — {event}\n"


response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={
        "chat_id": CHANNEL_ID,
        "text": message
    }
)


msg_id = response.json()["result"]["message_id"]

requests.post(
    f"https://api.telegram.org/bot{TOKEN}/pinChatMessage",
    data={
        "chat_id": CHANNEL_ID,
        "message_id": msg_id
    }
)
