import requests
import os
from datetime import datetime, timedelta

TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

API_URL = "https://api.tradingeconomics.com/calendar/country/united states?c=guest:guest&format=json"


RED_FOLDER_KEYWORDS = [

"CPI",
"Core CPI",
"NFP",
"Non Farm Payrolls",
"FOMC",
"Interest Rate Decision",
"PCE",
"Core PCE",
"GDP",
"Retail Sales",
"ISM",
"Unemployment",
"Jobless Claims",
"Powell",
"Federal Reserve"
]


def send_message(text):

    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={
            "chat_id": CHANNEL_ID,
            "text": text
        }
    )

    return response.json()


def pin_message(message_id):

    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/pinChatMessage",
        data={
            "chat_id": CHANNEL_ID,
            "message_id": message_id
        }
    )


events = requests.get(API_URL).json()

today = datetime.utcnow().date()
tomorrow = today + timedelta(days=1)

today_events = []


for event in events:

    event_datetime = datetime.fromisoformat(event["Date"].replace("Z", ""))

    event_date = event_datetime.date()

    title = event["Event"]

    if today <= event_date <= tomorrow:

        if any(keyword.lower() in title.lower() for keyword in RED_FOLDER_KEYWORDS):

            event_time = event_datetime.strftime("%H:%M")

            today_events.append(f"{event_time} — {title}")


if today_events:

    message = "📌 TODAY'S USD RED FOLDER EVENTS\n\n"

    message += "\n".join(today_events)

    response = send_message(message)

    message_id = response["result"]["message_id"]

    pin_message(message_id)
