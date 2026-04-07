import os
import json
import asyncio
import feedparser
import yfinance as yf
from telegram import Bot
from datetime import datetime, timedelta
from transformers import pipeline

# =========================
# 🔐 CONFIG & NLP MODELS
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Missing BOT_TOKEN or CHAT_ID")

bot = Bot(token=BOT_TOKEN)

print("Loading NLP Models for Normal News...")
# FinBERT for financial sentiment
finbert = pipeline("text-classification", model="ProsusAI/finbert")
# Zero-shot classifier for dynamic relevance scoring
zero_shot = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

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

sent_news = load_data(NEWS_LOG_FILE,)
macro_flag = load_data(MACRO_FILE, {})

# =========================
# 📩 TELEGRAM
# =========================
async def send(text):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
        print("✅", text)
    except Exception as e:
        print("❌", e)

# =========================
# 📈 PRICE SAFE
# =========================
def get_price(symbol):
    try:
        data = yf.download(symbol, period="1d", interval="1m", progress=False)
        return data["Close"].iloc[-1].iloc
    except:
        return None

# =========================
# 📈 REACTION ENGINE (ASYNC)
# =========================
async def track_reaction(event):
    entry = get_price("EURUSD=X")
    if entry is None:
        return

    await asyncio.sleep(60)
    p1 = get_price("EURUSD=X")

    await asyncio.sleep(240)
    p5 = get_price("EURUSD=X")

    if p1 is None or p5 is None:
        return

    reaction = {
        "event": event,
        "1m": round((p1 - entry)*10000, 1),
        "5m": round((p5 - entry)*10000, 1),
        "time": str(datetime.now())
    }

    data = load_data(REACTION_FILE,)
    data.append(reaction)
    save_data(REACTION_FILE, data)

# =========================
# 🧠 MACRO EVENTS (KEPT AS IS)
# =========================
EVENTS =

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
# 🧠 IST TIME FIX
# =========================
def get_ist_time():
    utc_now = datetime.utcnow()
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    return ist_now.strftime("%H:%M")

# =========================
# 🧠 MACRO ENGINE
# =========================
async def macro_engine():
    global macro_flag
    now = get_ist_time()

    for e in EVENTS:
        up = f"{e['name']}_up"
        rel = f"{e['name']}_rel"

        if now == "17:55" and not macro_flag.get(up):
            exp = "Higher" if e["expected"] > e["previous"] else "Cooling"
            bias = "USD → Bullish Bias" if exp == "Higher" else "USD → Bearish Bias"

            await send(f"""⏳ UPCOMING — {e['name']} ({e['currency']})

🕒 Time: {e['time']} IST  
⚠️ High Impact Expected  

🧠 Expectation: {exp}  
🎯 {bias}""")

            macro_flag[up] = True
            save_data(MACRO_FILE, macro_flag)

        if now == e["time"] and not macro_flag.get(rel):
            deviation = round(e["actual"] - e["expected"], 2)
            bias = get_bias(e["expected"], e["actual"])

            await send(f"""🚨 {e['name']} RELEASED ({e['currency']})

📊 Expected: {e['expected']}  
📊 Actual: {e['actual']}  
📊 Previous: {e['previous']}  

⚡ Deviation: {deviation:+}

🎯 {e['currency']} → {bias}""")

            asyncio.create_task(track_reaction(e["name"]))

            macro_flag[rel] = True
            save_data(MACRO_FILE, macro_flag)

# =========================
# 📰 NORMAL NEWS ENGINE (UPGRADED WITH NLP)
# =========================
def fetch_news():
    try:
        url = "https://feeds.reuters.com/reuters/businessNews"
        feed = feedparser.parse(url)
        return [entry.title for entry in feed.entries[:10]]
    except:
        return

async def nike_news_engine():
    global sent_news
    news_list = fetch_news()

    for news in news_list:
        if news in sent_news:
            continue

        # 1. Zero-Shot Relevance Scoring
        labels = ["Corporate Action", "High Impact Macroeconomic", "Low Impact Noise"]
        impact_analysis = zero_shot(news, candidate_labels=labels)
        impact_category = impact_analysis['labels']
        impact_score = impact_analysis['scores']

        if impact_category == "Low Impact Noise" or impact_score < 0.60:
            sent_news.append(news)
            continue

        # 2. FinBERT Sentiment Tensor
        sentiment_analysis = finbert(news)
        sentiment = sentiment_analysis['label'].upper()
        confidence = sentiment_analysis['score']

        if confidence > 0.70:
            emoji = "📈" if sentiment == "BULLISH" else "📉" if sentiment == "BEARISH" else "📰"
            msg = f"""{emoji} *NORMAL NEWS DETECTED*

📰 Headline: {news}
🧠 Sentiment: {sentiment} ({confidence:.2f})
🎯 Impact: {impact_category}
🏆 Source: Reuters"""
            
            await send(msg)
            
            # Store data
            data = load_data(NEWS_DATA_FILE,)
            data.append({
                "headline": news,
                "sentiment": sentiment,
                "impact": impact_category,
                "time": str(datetime.now())
            })
            save_data(NEWS_DATA_FILE, data)
            
            # Track reaction for normal news
            asyncio.create_task(track_reaction(news))

        sent_news.append(news)
        save_data(NEWS_LOG_FILE, sent_news)

# =========================
# 🚀 START
# =========================
async def main():
    if not sent_news:
        await send("🚀 NIKE LIVE\nScanning markets with Macro & NLP engines...")

    # =========================
    # 🔁 LOOP
    # =========================
    while True:
        await nike_news_engine()
        await macro_engine()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
