import requests
import time
import schedule
import csv
from datetime import datetime
import os

# ENV VARIABLES (set in Railway)
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# ---------------- TELEGRAM ---------------- #

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    requests.post(url, json=payload)

# ---------------- DATA MESSAGE BUILDERS ---------------- #

def build_m1(event, time_str):
    return f"""⏳ UPCOMING — {event}

🕒 {time_str}  
⚠️ High impact expected
"""

def build_m2(event, expected, actual, previous):
    deviation = round(actual - expected, 2)

    if deviation > 0:
        bias = "USD Positive"
        note = "upside surprise"
    else:
        bias = "USD Negative"
        note = "downside surprise"

    return f"""🚨 {event} released

Expected: {expected}% | Actual: {actual}% | Previous: {previous}%  
Deviation: {deviation} ({note})

⚠️ Priority: High  
🎯 Bias: {bias}
"""

def build_m3(pair, r1, r5):
    return f"""📈 {pair} reaction

1m: {r1} pips | 5m: {r5} pips  

🧠 Initial move observed  
⚠️ Watch continuation or reversal
"""

# ---------------- NEWS MESSAGE ---------------- #

def build_news(headline, reason, priority, bias):
    return f"""{headline}

{reason}

⚠️ Priority: {priority}  
🎯 Bias: {bias}
"""

# ---------------- PRICE FETCH ---------------- #

def get_price(symbol="EURUSD=X"):
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
    data = requests.get(url).json()
    return data["quoteResponse"]["result"][0]["regularMarketPrice"]

# ---------------- REACTION TRACKER ---------------- #

def track_reaction():
    price_before = get_price()

    time.sleep(60)
    price_1m = get_price()

    time.sleep(240)
    price_5m = get_price()

    r1 = round((price_1m - price_before) * 10000)
    r5 = round((price_5m - price_before) * 10000)

    return r1, r5

# ---------------- STORAGE ---------------- #

def save_data(event, expected, actual, r1, r5):
    with open("nike_log.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now(),
            event,
            expected,
            actual,
            r1,
            r5
        ])

# ---------------- DEMO FLOW ---------------- #

def run_demo():
    # MESSAGE 1
    send_message(build_m1("CPI (USD)", "6:00 PM IST"))

    time.sleep(5)

    # DATA RELEASE (simulate)
    expected = 3.2
    actual = 3.6
    previous = 3.1

    # MESSAGE 2
    send_message(build_m2("CPI (USD)", expected, actual, previous))

    # TRACK REACTION
    r1, r5 = track_reaction()

    # MESSAGE 3
    send_message(build_m3("EURUSD", r1, r5))

    # SAVE
    save_data("CPI", expected, actual, r1, r5)

# ---------------- SCHEDULER ---------------- #

def job():
    run_demo()

schedule.every().day.at("18:00").do(job)

# ---------------- MAIN LOOP ---------------- #

if __name__ == "__main__":
    print("NIKE BOT RUNNING...")
    while True:
        schedule.run_pending()
        time.sleep(1)
