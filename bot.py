import json
import logging
import os
from datetime import datetime
from html import escape
from urllib import request as urlrequest

from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://akmaljonyuldashev.github.io/wondershop")
GOOGLE_SHEETS_WEBHOOK_URL = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", "")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN не найден. Добавьте BOT_TOKEN в Railway Variables.")
if not ADMIN_ID:
    raise RuntimeError("ADMIN_ID не найден. Добавьте ADMIN_ID в Railway Variables.")


def format_price(value):
    try:
        return f"{int(float(value)):,}".replace(",", " ") + " сум"
    except (TypeError, ValueError):
        return str(value or "—")


def safe(value, default="—"):
    if value is None or value == "":
        return default
    return value


def post_to_google_sheets(payload: dict):
    if not GOOGLE_SHEETS_WEBHOOK_URL:
        return

    try:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urlrequest.Request(
            GOOGLE_SHEETS_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urlrequest.urlopen(req, timeout=8).read()
    except Exception as exc:
        logging.warning("Google Sheets webhook failed: %s", exc)


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
        "Нажмите кнопку ниже, чтобы открыть каталог, собрать корзину и оформить заказ.",
        reply_markup=keyboard,
    )


async def manager_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 Напишите нам или оформите заказ через каталог.\n\n"
        "Менеджер свяжется с вами для уточнения доставки и оплаты."
    )


def build_status_keyboard(order_id: str, customer_id: int):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Принят", callback_data=f"status|accepted|{customer_id}|{order_id}"),
                InlineKeyboardButton("🚚 В доставке", callback_data=f"status|delivery|{customer_id}|{order_id}"),
            ],
            [
                InlineKeyboardButton("✔️ Выполнен", callback_data=f"status|done|{customer_id}|{order_id}"),
                InlineKeyboardButton("❌ Отменён", callback_data=f"status|cancelled|{customer_id}|{order_id}"),
            ],
        ]
    )


def status_text(status: str):
    return {
        "accepted": "✅ Ваш заказ принят в работу.",
        "delivery": "🚚 Ваш заказ передан в доставку.",
        "done": "✔️ Ваш заказ выполнен. Спасибо за покупку!",
        "cancelled": "❌ Ваш заказ отменён. Если это ошибка, свяжитесь с менеджером.",
    }.get(status, "Статус заказа обновлён.")


async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.web_app_data.data
    user = update.effective_user

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await update.message.reply_text("Ошибка данных. Попробуйте ещё раз.")
        return

    payload_type = data.get("type", "single_product")

    if payload_type == "custom_print":
        await handle_custom_print(update, context, data, user)
        return

    if payload_type == "order":
        await handle_order(update, context, data, user)
        return

    await handle_legacy_single_product(update, context, data, user)


async def handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict, user):
    order_id = safe(data.get("order_id"), f"WS-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    customer = data.get("customer", {})
    items = data.get("items", [])
    total = data.get("total", 0)

    items_text_lines = []
    for i, item in enumerate(items, 1):
        items_text_lines.append(
            f"{i}. {escape(str(safe(item.get('name'))))}\n"
            f"   Категория: {escape(str(safe(item.get('category'))))}\n"
            f"   Артикул: {escape(str(safe(item.get('article'))))}\n"
            f"   Размер: {escape(str(safe(item.get('size'))))}\n"
            f"   Цвет: {escape(str(safe(item.get('color'))))}\n"
            f"   Кол-во: {escape(str(safe(item.get('quantity'), 1)))}\n"
            f"   Цена: {escape(format_price(item.get('price')))}\n"
            f"   Сумма: {escape(format_price(item.get('total', 0)))}\n"
            f"   Ссылка: {escape(str(safe(item.get('url'))))}"
        )

    admin_text = (
        f"🆕 Новый заказ Wondershop\n\n"
        f"Номер: {escape(str(order_id))}\n"
        f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        f"👤 Клиент: {escape(str(safe(customer.get('name'))))}\n"
        f"Телефон: {escape(str(safe(customer.get('phone'))))}\n"
        f"Город: {escape(str(safe(customer.get('city'))))}\n"
        f"Адрес: {escape(str(safe(customer.get('address'))))}\n"
        f"Оплата: {escape(str(safe(customer.get('payment'))))}\n"
        f"Комментарий: {escape(str(safe(customer.get('comment'))))}\n\n"
        f"Telegram: @{escape(user.username) if user.username else 'нет'}\n"
        f"Telegram ID: {user.id}\n\n"
        f"🛒 Товары:\n" + "\n\n".join(items_text_lines) +
        f"\n\n💰 Итого: {escape(format_price(total))}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        reply_markup=build_status_keyboard(str(order_id), int(user.id)),
    )

    post_to_google_sheets(
        {
            "type": "order",
            "order_id": str(order_id),
            "date": datetime.now().isoformat(),
            "telegram_id": user.id,
            "telegram_username": user.username,
            "customer": customer,
            "items": items,
            "total": total,
            "status": "new",
        }
    )

    await update.message.reply_text(
        f"🎉 Спасибо! Ваш заказ принят.\n\n"
        f"Номер заказа: {escape(str(order_id))}\n"
        f"Итого: {escape(format_price(total))}\n\n"
        "Менеджер Wondershop скоро свяжется с вами.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def handle_custom_print(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict, user):
    request_id = safe(data.get("request_id"), f"CP-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    customer = data.get("customer", {})

    admin_text = (
        "🎨 Новая заявка на свой принт\n\n"
        f"Номер: {escape(str(request_id))}\n"
        f"Товар: {escape(str(safe(data.get('product'))))}\n"
        f"Размер: {escape(str(safe(data.get('size'))))}\n"
        f"Цвет: {escape(str(safe(data.get('color'))))}\n"
        f"Количество: {escape(str(safe(data.get('quantity'), 1)))}\n"
        f"Идея: {escape(str(safe(data.get('idea'))))}\n\n"
        f"👤 Клиент: {escape(str(safe(customer.get('name'))))}\n"
        f"Телефон: {escape(str(safe(customer.get('phone'))))}\n"
        f"Telegram: @{escape(user.username) if user.username else 'нет'}\n"
        f"Telegram ID: {user.id}"
    )

    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_text)

    post_to_google_sheets(
        {
            "type": "custom_print",
            "request_id": str(request_id),
            "date": datetime.now().isoformat(),
            "telegram_id": user.id,
            "telegram_username": user.username,
            "data": data,
            "status": "new",
        }
    )

    await update.message.reply_text(
        f"✅ Заявка на свой принт принята.\n\n"
        f"Номер заявки: {escape(str(request_id))}\n\n"
        "Теперь можете отправить менеджеру изображение/макет в этот чат или дождаться связи.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def handle_legacy_single_product(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict, user):
    product_name = safe(data.get("print_name"))
    total = data.get("total", data.get("price", 0))

    await update.message.reply_text(
        f"✅ Товар выбран!\n\n"
        f"🛍 {escape(str(product_name))}\n"
        f"📦 Размер: {escape(str(safe(data.get('size'))))}\n"
        f"🎨 Цвет: {escape(str(safe(data.get('color'))))}\n"
        f"🔢 Количество: {escape(str(safe(data.get('quantity'), 1)))}\n"
        f"💰 Итого: {escape(format_price(total))}\n\n"
        "Менеджер Wondershop скоро свяжется с вами.",
        reply_markup=ReplyKeyboardRemove(),
    )


async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, status, customer_id, order_id = query.data.split("|", 3)
        customer_id = int(customer_id)
    except Exception:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    message = f"{status_text(status)}\n\nНомер заказа: {escape(order_id)}"

    try:
        await context.bot.send_message(chat_id=customer_id, text=message)
        await query.answer("Клиенту отправлено уведомление.")
    except Exception:
        await query.answer("Не удалось отправить клиенту уведомление.", show_alert=True)

    post_to_google_sheets(
        {
            "type": "status_update",
            "order_id": order_id,
            "status": status,
            "date": datetime.now().isoformat(),
            "customer_id": customer_id,
        }
    )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📞 Связаться с менеджером$"), manager_contact))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
    app.add_handler(CallbackQueryHandler(status_callback, pattern=r"^status\|"))
    app.run_polling()


if __name__ == "__main__":
    main()
