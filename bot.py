import json
import logging
import os
from html import escape

from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://akmaljonyuldashev.github.io/wondershop",
)

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Добавьте BOT_TOKEN в переменные окружения.")

if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID не найден. Добавьте ADMIN_ID в переменные окружения.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [
            [KeyboardButton("🛍 Открыть каталог", web_app=WebAppInfo(url=WEBAPP_URL))],
            [KeyboardButton("📞 Связаться с менеджером")],
        ],
        resize_keyboard=True,
    )

    await update.message.reply_text(
        "👋 Добро пожаловать в Wondershop!\n\n"
        "Нажмите кнопку ниже, чтобы открыть каталог и выбрать принт.",
        reply_markup=keyboard,
    )


async def manager_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 Напишите нам в Telegram или оставьте заявку через каталог.\n\n"
        "Менеджер свяжется с вами для уточнения размера, цвета, доставки и оплаты."
    )


def safe_get(data: dict, key: str, default: str = "—"):
    value = data.get(key, default)
    if value is None or value == "":
        return default
    return value


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.web_app_data.data
    user = update.effective_user

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка данных. Попробуйте выбрать товар ещё раз.")
        return

    print_id = safe_get(data, "print_id")
    print_name = safe_get(data, "print_name")
    category = safe_get(data, "category")
    price = safe_get(data, "price", 0)
    img = safe_get(data, "img")

    try:
        price_int = int(price)
        price_text = f"{price_int:,}".replace(",", " ") + " сум"
    except (TypeError, ValueError):
        price_text = str(price)

    await update.message.reply_text(
        f"✅ Принт выбран!\n\n"
        f"🖼 {escape(str(print_name))}\n"
        f"🏷 Категория: {escape(str(category))}\n"
        f"💰 Цена: {escape(price_text)}\n\n"
        f"Менеджер свяжется с вами для оформления заказа.",
        reply_markup=ReplyKeyboardRemove(),
    )

    admin_text = (
        "🆕 Новый заказ Wondershop\n\n"
        f"👤 Клиент: {escape(user.full_name)}\n"
        f"🔗 Username: @{escape(user.username) if user.username else 'нет'}\n"
        f"🆔 Telegram ID: {user.id}\n\n"
        f"🖼 Принт: {escape(str(print_name))}\n"
        f"ID: {escape(str(print_id))}\n"
        f"Категория: {escape(str(category))}\n"
        f"Цена: {escape(price_text)}\n"
        f"Фото: {escape(str(img))}"
    )

    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text)


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📞 Связаться с менеджером$"), manager_contact))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    app.run_polling()


if __name__ == "__main__":
    main()
