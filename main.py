import os
import time
import json
import threading
import feedparser
import yfinance as yf
from telegram import Bot
from datetime import datetime

# =========================
# 🔐 CONFIG
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Missing BOT_TOKEN or CHAT_ID")

bot = Bot(token=BOT_TOKEN)

# =========================
# 📁 FILE STORAGE
# =========================
NEWS_FILE = "sent_news.json"
REACTION_FILE = "reaction.json"

def load_data(file):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return []

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f)

sent_news = load_data(NEWS_FILE)

# =========================
# 📩 TELEGRAM SEND
# =========================
def send(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
        print("✅ Sent:", text)
    except Exception as e:
        print("❌ Error:", e)

# =========================
# 📰 FETCH NEWS (REUTERS)
# =========================
def fetch_news():
    url = "https://feeds.reuters.com/reuters/businessNews"
    feed = feedparser.parse(url)
    return [entry.title for entry in feed.entries[:10]]

# =========================
# 🎯 PRIORITY FILTER
# =========================
def classify_news(headline):
    h = headline.lower()

    high = ["cpi", "inflation", "fed", "interest rate", "war", "conflict"]
    medium = ["oil", "crude", "rbi", "bank", "earnings", "reliance", "adani"]

    if any(k in h for k in high):
        return "HIGH"
    elif any(k in h for k in medium):
        return "MEDIUM"
    else:
        return "LOW"

# =========================
# 🧠 FORMAT ENGINE (SMART)
# =========================
def format_news(headline, level):
    h = headline.lower()

    if "oil" in h or "crude" in h:
        emoji = "🛢️"
        bias = "Bullish for oil (short-term)"
    elif "fed" in h or "rate" in h:
        emoji = "🏦"
        bias = "USD sensitive"
    elif "inflation" in h or "cpi" in h:
        emoji = "📊"
        bias = "Volatility expected"
    elif "war" in h or "conflict" in h:
        emoji = "🌍"
        bias = "Risk sentiment shift"
    elif "reliance" in h:
        emoji = "🇮🇳"
        bias = "Stock-specific move"
    elif "adani" in h:
        emoji = "🇮🇳"
        bias = "High volatility expected"
    else:
        emoji = "📰"
        bias = None

    # STYLE VARIATION
    if level == "HIGH":
        msg = f"🚨 {headline}"
        if bias:
            msg += f"\n🎯 {bias}"
    elif level == "MEDIUM":
        msg = f"{emoji} {headline}"
        if bias:
            msg += f"\n→ {bias}"
    else:
        msg = f"{emoji} {headline}"

    return msg

# =========================
# 📈 PRICE FETCH
# =========================
def get_price(symbol):
    data = yf.download(symbol, period="1d", interval="1m")
    return data["Close"].iloc[-1]

# =========================
# 🧠 REACTION ENGINE (SILENT)
# =========================
def track_reaction_background(event, symbol):
    try:
        entry = get_price(symbol)

        time.sleep(60)
        p1 = get_price(symbol)

        time.sleep(240)
        p5 = get_price(symbol)

        reaction = {
            "event": event,
            "symbol": symbol,
            "entry": float(entry),
            "1m": float(p1 - entry),
            "5m": float(p5 - entry),
            "time": str(datetime.now())
        }

        data = load_data(REACTION_FILE)
        data.append(reaction)
        save_data(REACTION_FILE, data)

        print("📈 Stored reaction:", reaction)

    except Exception as e:
        print("❌ Reaction error:", e)

# =========================
# 🧠 MAIN ENGINE
# =========================
def nike_news_engine():
    global sent_news

    news_list = fetch_news()

    for news in news_list:

        if news in sent_news:
            continue

        level = classify_news(news)

        if level == "LOW":
            continue

        formatted = format_news(news, level)

        send(formatted)

        # 🔥 BACKGROUND REACTION TRACKING
        threading.Thread(
            target=track_reaction_background,
            args=(news, "EURUSD=X")
        ).start()

        sent_news.append(news)
        save_data(NEWS_FILE, sent_news)

# =========================
# 🚀 START
# =========================
send("🚀 NIKE LIVE\nScanning markets...")

# =========================
# 🔁 LOOP
# =========================
while True:
    nike_news_engine()
    time.sleep(600)
