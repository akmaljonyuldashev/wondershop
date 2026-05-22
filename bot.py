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


def format_price(value):
    try:
        return f"{int(value):,}".replace(",", " ") + " сум"
    except (TypeError, ValueError):
        return str(value or "—")


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
        "Нажмите кнопку ниже, чтобы открыть каталог и выбрать товар.",
        reply_markup=keyboard,
    )


async def manager_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 Напишите нам или оставьте заявку через каталог.\n\n"
        "Менеджер свяжется с вами для уточнения доставки и оплаты."
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

    product_id = safe_get(data, "print_id")
    product_name = safe_get(data, "print_name")
    category = safe_get(data, "category")
    article = safe_get(data, "article")
    price = safe_get(data, "price", 0)
    size = safe_get(data, "size")
    color = safe_get(data, "color")
    color_hex = safe_get(data, "color_hex")
    quantity = safe_get(data, "quantity", 1)
    total = safe_get(data, "total", price)
    img = safe_get(data, "img")
    url = safe_get(data, "url")

    client_text = (
        "✅ Товар выбран!\n\n"
        f"🛍 {escape(str(product_name))}\n"
        f"🏷 Категория: {escape(str(category))}\n"
        f"📦 Размер: {escape(str(size))}\n"
        f"🎨 Цвет: {escape(str(color))}\n"
        f"🔢 Количество: {escape(str(quantity))}\n"
        f"💰 Итого: {escape(format_price(total))}\n\n"
        "Менеджер Wondershop скоро свяжется с вами для подтверждения заказа."
    )

    await update.message.reply_text(client_text, reply_markup=ReplyKeyboardRemove())

    admin_text = (
        "🆕 Новый заказ Wondershop\n\n"
        f"👤 Клиент: {escape(user.full_name)}\n"
        f"🔗 Username: @{escape(user.username) if user.username else 'нет'}\n"
        f"🆔 Telegram ID: {user.id}\n\n"
        f"🛍 Товар: {escape(str(product_name))}\n"
        f"ID товара: {escape(str(product_id))}\n"
        f"Категория: {escape(str(category))}\n"
        f"Артикул: {escape(str(article))}\n\n"
        f"📦 Размер: {escape(str(size))}\n"
        f"🎨 Цвет: {escape(str(color))}\n"
        f"HEX: {escape(str(color_hex))}\n"
        f"🔢 Количество: {escape(str(quantity))}\n\n"
        f"Цена за 1 шт.: {escape(format_price(price))}\n"
        f"Итого: {escape(format_price(total))}\n\n"
        f"Фото: {escape(str(img))}\n"
        f"Ссылка: {escape(str(url))}"
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
