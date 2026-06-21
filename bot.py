import asyncio
import logging
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

TOKEN = "8677111342:AAGH4GV75rs6Az-1WdN41027ZTPli_RV6aQ"
CHANNEL_ID = "@Musicisthebest25"
CHANNEL_NAME = "𝕷𝖚𝖈𝖍𝖘𝖍𝖊𝖊 𝖙𝖗𝖊𝖐𝖎🎧"
ADMIN_ID = 8630009939

session = AiohttpSession(timeout=60)
bot = Bot(token=TOKEN, session=session, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
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

class PostStates(StatesGroup):
    waiting_for_content = State()
    waiting_for_media = State()
    waiting_for_buttons = State()
    waiting_for_schedule_date = State()
    waiting_for_schedule_time = State()

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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}.\n"
        "Здесь ты можешь создать пост и управлять уже отложенными.",
        reply_markup=main_menu()
    )

@dp.message(F.text == "📝 Создать пост")
async def create_post(message: types.Message, state: FSMContext):
    await message.answer(
        f"Ты выбрал канал\n{CHANNEL_NAME}\n\n"
        "Отправь боту то, что собираешься опубликовать.",
        reply_markup=post_buttons()
    )
    await state.set_state(PostStates.waiting_for_content)
    await state.update_data(content=None, media=None, buttons=None, reactions=None)

@dp.message(PostStates.waiting_for_content, F.text | F.photo | F.video | F.audio)
async def get_content(message: types.Message, state: FSMContext):
    if message.text:
        await state.update_data(content=message.html_text, content_type="text")
    elif message.photo:
        await state.update_data(content=message.photo[-1].file_id, content_type="photo", caption=message.caption)
    elif message.video:
        await state.update_data(content=message.video.file_id, content_type="video", caption=message.caption)
    elif message.audio:
        await state.update_data(content=message.audio.file_id, content_type="audio", caption=message.caption)
    await message.answer("✅ Контент сохранён. Теперь можешь прикрепить медиа, настроить кнопки или перейти к публикации.",
                         reply_markup=media_buttons())
    await state.set_state(PostStates.waiting_for_media)

@dp.message(F.text == "📎 Прикрепить медиа", PostStates.waiting_for_media)
async def attach_media(message: types.Message, state: FSMContext):
    await message.answer("Пришли мне медиа файл до 100MB.", reply_markup=media_buttons())

@dp.message(PostStates.waiting_for_media, F.photo | F.video | F.audio | F.document)
async def save_media(message: types.Message, state: FSMContext):
    if message.photo:
        await state.update_data(media=message.photo[-1].file_id, media_type="photo")
    elif message.video:
        await state.update_data(media=message.video.file_id, media_type="video")
    elif message.audio:
        await state.update_data(media=message.audio.file_id, media_type="audio")
    elif message.document:
        await state.update_data(media=message.document.file_id, media_type="document")
    await message.answer("✅ Медиа прикреплено.", reply_markup=media_buttons())

@dp.message(F.text == "🔗 URL-кнопки/реакции", PostStates.waiting_for_media)
async def configure_buttons(message: types.Message, state: FSMContext):
    await message.answer(
        "Отправь мне список URL-кнопок и/или реакций одним сообщением.\n\n"
        "**Кнопки:**\n"
        "Кнопка 1 - http://t.me/durov\n"
        "Кнопка 2 - http://vk.com/id1\n\n"
        "Используй разделитель | для до трёх кнопок в ряд:\n"
        "Кнопка 1 - http://t.me/durov | Кнопка 2 - http://t.me/telepost_blog\n\n"
        "**Реакции:**\n"
        "👍 / 👎\n\n"
        "Реакции не могут идти с кнопками.",
        reply_markup=media_buttons()
    )
    await state.set_state(PostStates.waiting_for_buttons)

@dp.message(PostStates.waiting_for_buttons, F.text)
async def save_buttons(message: types.Message, state: FSMContext):
    text = message.text
    if "/" in text and not (" - " in text and "http" in text):
        reactions = text.strip().split("/")
        await state.update_data(reactions=reactions)
        await message.answer(f"✅ Реакции сохранены: {' / '.join(reactions)}", reply_markup=media_buttons())
    else:
        lines = text.strip().split("\n")
        buttons = []
        for line in lines:
            if " - " in line and "http" in line:
                if " | " in line:
                    parts = line.split(" | ")
                    row = []
                    for part in parts:
                        if " - " in part:
                            name, url = part.split(" - ", 1)
                            row.append((name.strip(), url.strip()))
                    buttons.append(row)
                else:
                    name, url = line.split(" - ", 1)
                    buttons.append([(name.strip(), url.strip())])
        await state.update_data(buttons=buttons)
        await message.answer(f"✅ Кнопки сохранены ({len(buttons)} рядов).", reply_markup=media_buttons())
    await state.set_state(PostStates.waiting_for_media)

@dp.message(F.text == "🔊 Звук: ON/OFF", PostStates.waiting_for_media)
async def toggle_sound_quick(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current = get_user_setting(user_id, "sound")
    new_value = "OFF" if current == "ON" else "ON"
    update_user_setting(user_id, "sound", new_value)
    await message.answer(f"🔊 Звуковые уведомления: {new_value}", reply_markup=media_buttons())

@dp.message(F.text == "🔗 Предпросмотр: ON/OFF", PostStates.waiting_for_media)
async def toggle_preview_quick(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current = get_user_setting(user_id, "preview")
    new_value = "OFF" if current == "ON" else "ON"
    update_user_setting(user_id, "preview", new_value)
    await message.answer(f"🔗 Предпросмотр ссылок: {new_value}", reply_markup=media_buttons())

@dp.message(F.text == "✅ Готово", PostStates.waiting_for_media)
async def ready_to_publish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("content"):
        await message.answer("Нет контента. Сначала отправь текст или медиа.", reply_markup=media_buttons())
        return
    await message.answer(
        "Хочешь опубликовать пост прямо сейчас или отложить?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Опубликовать сейчас", callback_data="publish_now")],
            [InlineKeyboardButton(text="⏰ Отложить", callback_data="schedule")],
            [InlineKeyboardButton(text="💾 Сохранить черновик", callback_data="save_draft")]
        ])
    )
    await state.set_state(PostStates.waiting_for_publish_choice)

@dp.callback_query(F.data == "publish_now")
async def publish_now(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    content = data.get("content")
    content_type = data.get("content_type", "text")
    caption = data.get("caption", "")
    media = data.get("media")
    media_type = data.get("media_type")
    buttons = data.get("buttons", [])
    
    signature = f"\n\n<a href=\"https://t.me/Musicisthebest25\">{CHANNEL_NAME}</a>"
    final_caption = (caption or "") + signature
    
    user_id = callback.from_user.id
    parse_mode = get_user_setting(user_id, "format")
    if parse_mode == "HTML":
        parse_mode = "HTML"
    elif parse_mode == "Markdown":
        parse_mode = "Markdown"
    else:
        parse_mode = None
    
    try:
        if media:
            if media_type == "photo":
                await bot.send_photo(CHANNEL_ID, photo=media, caption=final_caption, parse_mode=parse_mode)
            elif media_type == "video":
                await bot.send_video(CHANNEL_ID, video=media, caption=final_caption, parse_mode=parse_mode)
            elif media_type == "audio":
                await bot.send_audio(CHANNEL_ID, audio=media, caption=final_caption, parse_mode=parse_mode)
            elif media_type == "document":
                await bot.send_document(CHANNEL_ID, document=media, caption=final_caption, parse_mode=parse_mode)
        else:
            await bot.send_message(CHANNEL_ID, content + signature, parse_mode=parse_mode)
        
        if buttons:
            kb = InlineKeyboardBuilder()
            for row in buttons:
                for name, url in row:
                    kb.button(text=name, url=url)
                kb.adjust(len(row))
            await bot.send_message(CHANNEL_ID, "Кнопки:", reply_markup=kb.as_markup())
        
        await callback.message.edit_text("✅ Пост опубликован в канале!")
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка при публикации: {e}")
    
    await state.clear()
    await callback.message.answer("Вернуться в главное меню:", reply_markup=main_menu())

@dp.callback_query(F.data == "schedule")
async def schedule_post(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("⏰ Введи дату в формате ДД.ММ (например, 01.04)")
    await state.set_state(PostStates.waiting_for_schedule_date)

@dp.message(PostStates.waiting_for_schedule_date)
async def get_schedule_date(message: types.Message, state: FSMContext):
    try:
        date_str = message.text.strip()
        day, month = map(int, date_str.split('.'))
        if day < 1 or day > 31 or month < 1 or month > 12:
            raise ValueError
        await state.update_data(schedule_date=f"{day:02d}.{month:02d}")
        await message.answer("Теперь введи время в формате ЧЧ:ММ (например, 15:30)")
        await state.set_state(PostStates.waiting_for_schedule_time)
    except:
        await message.answer("❌ Неверный формат. Введи дату как ДД.ММ")

@dp.message(PostStates.waiting_for_schedule_time)
async def get_schedule_time(message: types.Message, state: FSMContext):
    try:
        time_str = message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError
        data = await state.get_data()
        date_str = data.get("schedule_date")
        scheduled_time = datetime.strptime(f"{date_str} {hour:02d}:{minute:02d}", "%d.%m %H:%M")
        if scheduled_time < datetime.now():
            await message.answer("❌ Нельзя отложить в прошлое. Введи будущую дату.")
            return
        cursor.execute("""
            INSERT INTO scheduled (content, content_type, caption, scheduled_time, status)
            VALUES (?, ?, ?, ?, ?)
        """, (data.get("content"), data.get("content_type"), data.get("caption"), scheduled_time, "pending"))
        conn.commit()
        await message.answer(f"✅ Пост запланирован на {scheduled_time.strftime('%d.%m.%Y %H:%M')}")
        await state.clear()
        await message.answer("Вернуться в главное меню:", reply_markup=main_menu())
    except:
        await message.answer("❌ Неверный формат. Введи время как ЧЧ:ММ")

@dp.callback_query(F.data == "save_draft")
async def save_draft(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cursor.execute("INSERT INTO drafts (content, content_type, caption, created_at) VALUES (?, ?, ?, ?)",
                   (data.get("content"), data.get("content_type"), data.get("caption"), datetime.now()))
    conn.commit()
    await callback.message.edit_text("💾 Пост сохранён в черновиках.")
    await state.clear()
    await callback.message.answer("Вернуться в главное меню:", reply_markup=main_menu())

@dp.message(F.text == "📋 Отложенные")
async def scheduled_posts(message: types.Message):
    cursor.execute("SELECT id, scheduled_time FROM scheduled WHERE status='pending' ORDER BY scheduled_time")
    posts = cursor.fetchall()
    if not posts:
        await message.answer(f"📋 В канале {CHANNEL_NAME} нет запланированных постов.")
        return
    text = "📅 **Запланированные посты:**\n\n"
    for post_id, sched_time in posts:
        text += f"• ID {post_id} — {sched_time}\n"
    text += "\nЧтобы отменить, используй /cancel_scheduled <id>"
    await message.answer(text)

@dp.message(Command("cancel_scheduled"))
async def cancel_scheduled(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        post_id = int(message.text.split()[1])
        cursor.execute("DELETE FROM scheduled WHERE id=?", (post_id,))
        conn.commit()
        await message.answer(f"✅ Пост ID {post_id} удалён из отложенных.")
    except:
        await message.answer("❌ Используй: /cancel_scheduled <id>")

@dp.message(F.text == "✏️ Редактировать")
async def edit_posts(message: types.Message):
    await message.answer(
        "Здесь ты можешь указать настройки по умолчанию.\n\n"
        f"Форматирование: {get_user_setting(message.from_user.id, 'format')}\n"
        f"Звук: {get_user_setting(message.from_user.id, 'sound')}\n"
        f"Предпросмотр: {get_user_setting(message.from_user.id, 'preview')}\n"
        f"Реакции: {get_user_setting(message.from_user.id, 'reactions')}"
    )

@dp.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    cursor.execute("SELECT COUNT(*) FROM drafts")
    drafts_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM scheduled WHERE status='pending'")
    scheduled_count = cursor.fetchone()[0]
    await message.answer(
        f"📊 **Статистика канала {CHANNEL_NAME}**\n\n"
        f"📝 Черновиков: {drafts_count}\n"
        f"⏰ Отложенных: {scheduled_count}\n"
        f"🎵 Всего постов: (вручную)\n\n"
        f"📈 Рекламный охват: ~40–60 уникальных просмотров"
    )

@dp.message(F.text == "⚙️ Настройки")
async def settings(message: types.Message):
    await message.answer(
        "Здесь ты можешь указать настройки по умолчанию.\n\n"
        f"Форматирование: {get_user_setting(message.from_user.id, 'format')}\n"
        f"Звук: {get_user_setting(message.from_user.id, 'sound')}\n"
        f"Предпросмотр: {get_user_setting(message.from_user.id, 'preview')}\n"
        f"Реакции: {get_user_setting(message.from_user.id, 'reactions')}",
        reply_markup=settings_keyboard(message.from_user.id)
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        f"Привет, {callback.from_user.first_name}.\n"
        "Здесь ты можешь создать пост и управлять уже отложенными.",
        reply_markup=main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "toggle_format")
async def toggle_format(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current = get_user_setting(user_id, "format")
    options = ["HTML", "Markdown", "Native"]
    next_index = (options.index(current) + 1) % len(options) if current in options else 0
    new_value = options[next_index]
    update_user_setting(user_id, "format", new_value)
    await callback.message.edit_text(
        "Настройки по умолчанию.\n\n"
        f"Форматирование: {new_value}\n"
        f"Звук: {get_user_setting(user_id, 'sound')}\n"
        f"Предпросмотр: {get_user_setting(user_id, 'preview')}\n"
        f"Реакции: {get_user_setting(user_id, 'reactions')}",
        reply_markup=settings_keyboard(user_id)
    )
    await callback.answer(f"✅ Форматирование: {new_value}")

@dp.callback_query(F.data == "toggle_sound")
async def toggle_sound(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current = get_user_setting(user_id, "sound")
    new_value = "OFF" if current == "ON" else "ON"
    update_user_setting(user_id, "sound", new_value)
    await callback.message.edit_text(
        "Настройки по умолчанию.\n\n"
        f"Форматирование: {get_user_setting(user_id, 'format')}\n"
        f"Звук: {new_value}\n"
        f"Предпросмотр: {get_user_setting(user_id, 'preview')}\n"
        f"Реакции: {get_user_setting(user_id, 'reactions')}",
        reply_markup=settings_keyboard(user_id)
    )
    await callback.answer(f"✅ Звук: {new_value}")

@dp.callback_query(F.data == "toggle_preview")
async def toggle_preview(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current = get_user_setting(user_id, "preview")
    new_value = "OFF" if current == "ON" else "ON"
    update_user_setting(user_id, "preview", new_value)
    await callback.message.edit_text(
        "Настройки по умолчанию.\n\n"
        f"Форматирование: {get_user_setting(user_id, 'format')}\n"
        f"Звук: {get_user_setting(user_id, 'sound')}\n"
        f"Предпросмотр: {new_value}\n"
        f"Реакции: {get_user_setting(user_id, 'reactions')}",
        reply_markup=settings_keyboard(user_id)
    )
    await callback.answer(f"✅ Предпросмотр: {new_value}")

@dp.callback_query(F.data == "toggle_reactions")
async def toggle_reactions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    current = get_user_setting(user_id, "reactions")
    new_value = "OFF" if current == "ON" else "ON"
    update_user_setting(user_id, "reactions", new_value)
    await callback.message.edit_text(
        "Настройки по умолчанию.\n\n"
        f"Форматирование: {get_user_setting(user_id, 'format')}\n"
        f"Звук: {get_user_setting(user_id, 'sound')}\n"
        f"Предпросмотр: {get_user_setting(user_id, 'preview')}\n"
        f"Реакции: {new_value}",
        reply_markup=settings_keyboard(user_id)
    )
    await callback.answer(f"✅ Реакции: {new_value}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
