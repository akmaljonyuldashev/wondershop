import json
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TOKEN = "8667832956:AAF2n-WoNcLUQsTGQIiAn3yJMQUVrQ7TfYs"
ADMIN_ID = 124657505
WEBAPP_URL = "https://akmaljonyuldashev.github.io/wondershop"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("🛍 Открыть каталог", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        "Привет! Нажми кнопку ниже, чтобы выбрать принт 👇",
        reply_markup=keyboard
    )

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.web_app_data.data
    user = update.effective_user
    
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка данных.")
        return

    # Ответ пользователю
    await update.message.reply_text(
        f"✅ Принт выбран!\n\n"
        f"🎨 *{data['print_name']}*\n"
        f"📂 Категория: {data['category']}\n"
        f"💰 Цена: {data['price']:,} сум\n\n"
        f"Менеджер свяжется с вами для оформления заказа.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )

    # Уведомление админу
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"🛒 Новый заказ!\n\n"
            f"👤 {user.full_name} (@{user.username or 'нет'}) [ID: {user.id}]\n"
            f"🎨 Принт: {data['print_name']} (ID: {data['print_id']})\n"
            f"📂 Категория: {data['category']}\n"
            f"💰 Цена: {data['price']:,} сум\n"
            f"🖼 Фото: {data['img']}"
        )
    )

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
app.run_polling()
