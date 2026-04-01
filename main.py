import os
import time
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)

def send_message(text):
    bot.send_message(chat_id=CHAT_ID, text=text)

# Start message
send_message("🚀 NIKE BOT LIVE")

# Loop
while True:
    time.sleep(300)
    send_message("📰 Test news running...")
