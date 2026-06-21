import logging
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

TOKEN = "8677111342:AAGH4GV75rs6Az-1WdN41027ZTPli_RV6aQ"
CHANNEL_ID = "@Musicisthebest25"
CHANNEL_NAME = "𝕷𝖚𝖈𝖍𝖘𝖍𝖊𝖊 𝖙𝖗𝖊𝖐𝖎🎧"
ADMIN_ID = 8630009939

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("posts.db")
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT, content_type TEXT, caption TEXT, created_at TIMESTAMP
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS scheduled (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT, content_type TEXT, caption TEXT,
    scheduled_time TIMESTAMP, status TEXT DEFAULT 'pending'
)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER PRIMARY KEY,
    format TEXT DEFAULT 'HTML',
    sound TEXT DEFAULT 'ON',
    preview TEXT DEFAULT 'OFF',
    reactions TEXT DEFAULT 'ON'
)""")
conn.commit()

def get_user_setting(user_id, setting_name):
    cursor.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO user_settings (user_id) VALUES (?)", (user_id,))
        conn.commit()
        cursor.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
    settings = {"format": row[1], "sound": row[2], "preview": row[3], "reactions": row[4]}
    return settings.get(setting_name, "ON")

def update_user_setting(user_id, setting, value):
    cursor.execute(f"UPDATE user_settings SET {setting}=? WHERE user_id=?", (value, user_id))
    conn.commit()

def main_menu():
    kb = [
        [KeyboardButton(text="📝 Создать пост")],
        [KeyboardButton(text="📋 Отложенные"), KeyboardButton(text="✏️ Редактировать")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="⚙️ Настройки")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def post_buttons():
    kb = [
        [KeyboardButton(text="🧹 Очистить"), KeyboardButton(text="👁 Предпросмотр")],
        [KeyboardButton(text="❌ Отмена"), KeyboardButton(text="➡️ Дальше")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def media_buttons():
    kb = [
        [KeyboardButton(text="📎 Прикрепить медиа"), KeyboardButton(text="🔗 URL-кнопки/реакции")],
        [KeyboardButton(text="🔊 Звук: ON/OFF"), KeyboardButton(text="🔗 Предпросмотр: ON/OFF")],
        [KeyboardButton(text="❌ Отмена"), KeyboardButton(text="✅ Готово")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def settings_keyboard(user_id):
    fmt = get_user_setting(user_id, "format")
    sound = get_user_setting(user_id, "sound")
    preview = get_user_setting(user_id, "preview")
    reactions = get_user_setting(user_id, "reactions")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📝 Форматирование: {fmt}", callback_data="toggle_format")],
        [InlineKeyboardButton(text=f"🔊 Звуковые уведомления: {sound}", callback_data="toggle_sound")],
        [InlineKeyboardButton(text=f"🔗 Предпросмотр ссылок: {preview}", callback_data="toggle_preview")],
        [InlineKeyboardButton(text=f"❤️ Реакции: {reactions}", callback_data="toggle_reactions")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
    ])

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Привет, {update.effective_user.first_name}.\n"
        "Здесь ты можешь создать пост и управлять уже отложенными.",
        reply_markup=main_menu()
    )

async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Ты выбрал канал\n{CHANNEL_NAME}\n\n"
        "Отправь боту то, что собираешься опубликовать.",
        reply_markup=post_buttons()
    )
    context.user_data['content'] = None
    context.user_data['media'] = None
    context.user_data['buttons'] = None
    context.user_data['reactions'] = None
    context.user_data['step'] = 'waiting_for_content'

async def handle_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') != 'waiting_for_content':
        return
    if update.message.text:
        context.user_data['content'] = update.message.text_html
        context.user_data['content_type'] = "text"
    elif update.message.photo:
        context.user_data['content'] = update.message.photo[-1].file_id
        context.user_data['content_type'] = "photo"
        context.user_data['caption'] = update.message.caption
    elif update.message.video:
        context.user_data['content'] = update.message.video.file_id
        context.user_data['content_type'] = "video"
        context.user_data['caption'] = update.message.caption
    elif update.message.audio:
        context.user_data['content'] = update.message.audio.file_id
        context.user_data['content_type'] = "audio"
        context.user_data['caption'] = update.message.caption
    await update.message.reply_text("✅ Контент сохранён. Теперь можешь прикрепить медиа, настроить кнопки или перейти к публикации.", reply_markup=media_buttons())
    context.user_data['step'] = 'waiting_for_media'

async def attach_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') == 'waiting_for_media':
        await update.message.reply_text("Пришли мне медиа файл до 100MB.", reply_markup=media_buttons())

async def save_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('step') != 'waiting_for_media':
        return
    if update.message.photo:
        context.user_data['media'] = update.message.photo[-1].file_id
        context.user_data['media_type'] = "photo"
    elif update.message.video:
        context.user_data['media'] = update.message.video.file_id
        context.user_data['media_type'] = "video"
    elif update.message.audio:
        context.user_data['media'] = update.message.audio.file_id
        context.user_data['media_type'] = "audio"
    elif update.message.document:
        context.user_data['media'] = update.message.document.file_id
        context.user_data['media_type'] = "document"
    await update.message.reply_text("✅ Медиа прикреплено.", reply_markup=media_buttons())

async def toggle_sound_quick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = get_user_setting(user_id, "sound")
    new_value = "OFF" if current == "ON" else "ON"
    update_user_setting(user_id, "sound", new_value)
    await update.message.reply_text(f"🔊 Звуковые уведомления: {new_value}", reply_markup=media_buttons())

async def toggle_preview_quick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    current = get_user_setting(user_id, "preview")
    new_value = "OFF" if current == "ON" else "ON"
    update_user_setting(user_id, "preview", new_value)
    await update.message.reply_text(f"🔗 Предпросмотр ссылок: {new_value}", reply_markup=media_buttons())

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "Здесь ты можешь указать настройки по умолчанию.\n\n"
        f"Форматирование: {get_user_setting(user_id, 'format')}\n"
        f"Звук: {get_user_setting(user_id, 'sound')}\n"
        f"Предпросмотр: {get_user_setting(user_id, 'preview')}\n"
        f"Реакции: {get_user_setting(user_id, 'reactions')}",
        reply_markup=settings_keyboard(user_id)
    )

async def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(MessageHandler(filters.Regex("^📝 Создать пост$"), create_post))
    application.add_handler(MessageHandler(filters.Regex("^⚙️ Настройки$"), settings))
    application.add_handler(MessageHandler(filters.Regex("^🔊 Звук: ON/OFF$"), toggle_sound_quick))
    application.add_handler(MessageHandler(filters.Regex("^🔗 Предпросмотр: ON/OFF$"), toggle_preview_quick))
    application.add_handler(MessageHandler(filters.Regex("^📎 Прикрепить медиа$"), attach_media))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL, save_media))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_content))
    print("✅ Бот успешно запущен и готов к работе!")
    application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
