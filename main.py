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
# 📁 FILES
# =========================
NEWS_LOG_FILE = "sent_news.json"
NEWS_DATA_FILE = "news_data.json"
REACTION_FILE = "reaction.json"
MACRO_FILE = "macro_flag.json"

def load_data(file, default):
    try:
        with open(file, "r") as f:
            return json.load(f)
    except:
        return default

def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

sent_news = load_data(NEWS_LOG_FILE, [])
macro_flag = load_data(MACRO_FILE, {})

# =========================
# 📩 TELEGRAM
# =========================
def send(text):
    try:
        bot.send_message(chat_id=CHAT_ID, text=text)
        print("✅", text)
    except Exception as e:
        print("❌", e)

# =========================
# 📰 FETCH NEWS
# =========================
def fetch_news():
    try:
        url = "https://feeds.reuters.com/reuters/businessNews"
        feed = feedparser.parse(url)
        return [entry.title for entry in feed.entries[:10]]
    except:
        return []

# =========================
# 🧠 SENTIMENT
# =========================
def get_sentiment(text):
    t = text.lower()

    bullish = ["rise", "growth", "strong", "gain", "surge"]
    bearish = ["fall", "drop", "decline", "weak", "crash"]

    if any(w in t for w in bullish):
        return "BULLISH"
    elif any(w in t for w in bearish):
        return "BEARISH"
    return "NEUTRAL"

# =========================
# 🎯 IMPACT
# =========================
def get_impact(text):
    t = text.lower()

    high = ["cpi", "inflation", "fed", "rate", "war"]
    medium = ["oil", "bank", "earnings", "pmi"]

    if any(w in t for w in high):
        return "HIGH"
    elif any(w in t for w in medium):
        return "MEDIUM"
    return "LOW"

# =========================
# 🧠 FORMAT NEWS
# =========================
def format_news(headline):
    sentiment = get_sentiment(headline)
    impact = get_impact(headline)

    if impact == "LOW":
        return None

    emoji = "📈" if sentiment == "BULLISH" else "📉" if sentiment == "BEARISH" else "📰"

    if impact == "HIGH":
        msg = f"""🚨 {headline}

🧠 Sentiment: {sentiment}
🎯 Impact: {impact}
🏆 Source: Reuters"""
    else:
        msg = f"""{emoji} {headline}
→ {sentiment.title()} tone"""

    return msg, sentiment, impact

# =========================
# 💾 STORE NEWS
# =========================
def store_news(headline, sentiment, impact):
    data = load_data(NEWS_DATA_FILE, [])

    data.append({
        "headline": headline,
        "sentiment": sentiment,
        "impact": impact,
        "time": str(datetime.now())
    })

    save_data(NEWS_DATA_FILE, data)

# =========================
# 📈 PRICE SAFE
# =========================
def get_price(symbol):
    try:
        data = yf.download(symbol, period="1d", interval="1m")
        return data["Close"].iloc[-1]
    except:
        return None

# =========================
# 📈 REACTION ENGINE
# =========================
def track_reaction(event):
    entry = get_price("EURUSD=X")
    if entry is None:
        return

    time.sleep(60)
    p1 = get_price("EURUSD=X")

    time.sleep(240)
    p5 = get_price("EURUSD=X")

    if p1 is None or p5 is None:
        return

    reaction = {
        "event": event,
        "1m": round((p1 - entry)*10000, 1),
        "5m": round((p5 - entry)*10000, 1),
        "time": str(datetime.now())
    }

    data = load_data(REACTION_FILE, [])
    data.append(reaction)
    save_data(REACTION_FILE, data)

# =========================
# 🧠 MACRO EVENTS
# =========================
EVENTS = [
    {"name": "CPI", "time": "18:00", "currency": "USD", "expected": 3.2, "actual": 3.6, "previous": 3.1}
]

def get_bias(expected, actual):
    d = actual - expected

    if d > 0.3:
        return "STRONG BULLISH"
    elif d > 0:
        return "BULLISH"
    elif d < -0.3:
        return "STRONG BEARISH"
    elif d < 0:
        return "BEARISH"
    return "NEUTRAL"

# =========================
# 🧠 MACRO ENGINE
# =========================
def macro_engine():
    global macro_flag
    now = datetime.now().strftime("%H:%M")

    for e in EVENTS:
        up = f"{e['name']}_up"
        rel = f"{e['name']}_rel"

        if now == "17:55" and not macro_flag.get(up):

            exp = "Higher" if e["expected"] > e["previous"] else "Cooling"
            bias = "USD → Bullish Bias" if exp == "Higher" else "USD → Bearish Bias"

            send(f"""⏳ UPCOMING — {e['name']} ({e['currency']})

🕒 Time: {e['time']} IST  
⚠️ High Impact Expected  

🧠 Expectation: {exp}  
🎯 {bias}""")

            macro_flag[up] = True
            save_data(MACRO_FILE, macro_flag)

        if now == e["time"] and not macro_flag.get(rel):

            deviation = round(e["actual"] - e["expected"], 2)
            bias = get_bias(e["expected"], e["actual"])

            send(f"""🚨 {e['name']} RELEASED ({e['currency']})

📊 Expected: {e['expected']}  
📊 Actual: {e['actual']}  
📊 Previous: {e['previous']}  

⚡ Deviation: {deviation:+}

🎯 {e['currency']} → {bias}""")

            threading.Thread(target=track_reaction, args=(e["name"],)).start()

            macro_flag[rel] = True
            save_data(MACRO_FILE, macro_flag)

# =========================
# 🧠 NEWS ENGINE
# =========================
def nike_news_engine():
    global sent_news

    news_list = fetch_news()

    for news in news_list:

        if news in sent_news:
            continue

        result = format_news(news)
        if not result:
            continue

        msg, sentiment, impact = result

        send(msg)
        store_news(news, sentiment, impact)

        sent_news.append(news)
        save_data(NEWS_LOG_FILE, sent_news)

# =========================
# 🚀 START
# =========================
if not sent_news:
    send("🚀 NIKE LIVE\nScanning markets...")

# =========================
# 🔁 LOOP
# =========================
while True:
    nike_news_engine()
    macro_engine()
    time.sleep(60)
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
