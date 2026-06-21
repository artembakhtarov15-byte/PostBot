import requests
import time
import logging

TOKEN = "8677111342:AAGH4GV75rs6Az-1WdN41027ZTPli_RV6aQ"
CHANNEL_ID = "@Musicisthebest25"

logging.basicConfig(level=logging.INFO)

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {"timeout": 100, "offset": offset}
    try:
        response = requests.get(url, params=params)
        return response.json().get("result", [])
    except Exception as e:
        print(f"Ошибка: {e}")
        return []

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text})
    except Exception as e:
        print(f"Ошибка отправки: {e}")

print("✅ Бот работает на чистом Python!")

last_id = 0
while True:
    updates = get_updates(offset=last_id + 1)
    for update in updates:
        message = update.get("message")
        if message:
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            # Если команда /start
            if text == "/start":
                send_message(chat_id, "Привет! Я бот для твоего канала. Просто отправь мне текст, и я опубликую его в канал.")
            # Если пользователь просто написал текст
            elif text:
                try:
                    # Отправляем в канал
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                                  json={"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML"})
                    send_message(chat_id, "✅ Твой пост отправлен в канал!")
                except Exception as e:
                    send_message(chat_id, f"❌ Ошибка публикации: {e}")
        last_id = update["update_id"]
    time.sleep(1)
