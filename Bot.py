import logging
import requests

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =====================
# НАСТРОЙКИ
# =====================
TOKEN = "8631003293:AAFOuLwKIq6b18_8RkK3gJILb_ES2G0mc1E"

SUPPORTED_CURRENCIES = ["USD", "RUB", "EUR", "KZT", "UAH"]

# =====================
# ЛОГИ
# =====================
logging.basicConfig(level=logging.INFO)

# =====================
# КНОПКИ
# =====================
main_keyboard = ReplyKeyboardMarkup(
    [
        ["💱 Конвертер", "⚙️ Коэффициент"],
        ["ℹ️ Помощь"],
    ],
    resize_keyboard=True,
)

currency_keyboard = ReplyKeyboardMarkup(
    [[c for c in SUPPORTED_CURRENCIES]],
    resize_keyboard=True,
)

# =====================
# API КУРСА
# =====================
def get_rate(base, target):
    url = f"https://api.frankfurter.dev/v1/latest?base={base}&symbols={target}"
    r = requests.get(url).json()
    return r["rates"][target]

# =====================
# СТАРТ
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["coef"] = 1
    await update.message.reply_text(
        "👋 Добро пожаловать!\n\nВыбери действие:",
        reply_markup=main_keyboard,
    )

# =====================
# ОБРАБОТКА КНОПОК
# =====================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "💱 Конвертер":
        context.user_data["state"] = "choose_from"
        await update.message.reply_text("Выбери валюту ИЗ:", reply_markup=currency_keyboard)

    elif text == "⚙️ Коэффициент":
        context.user_data["state"] = "set_coef"
        await update.message.reply_text("Введи коэффициент (например 0.8):")

    elif text == "ℹ️ Помощь":
        await update.message.reply_text(
            "📌 Как пользоваться:\n\n"
            "1. Выбери Конвертер\n"
            "2. Выбери валюты\n"
            "3. Напиши сумму\n\n"
            "Можно задать коэффициент (например 0.8)"
        )

# =====================
# ЛОГИКА
# =====================
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    state = context.user_data.get("state")

    # ===== выбор валюты FROM =====
    if state == "choose_from":
        context.user_data["from"] = text
        context.user_data["state"] = "choose_to"
        await update.message.reply_text("Теперь выбери валюту В:")
        return

    # ===== выбор валюты TO =====
    if state == "choose_to":
        context.user_data["to"] = text
        context.user_data["state"] = "convert"
        await update.message.reply_text(
            f"Введи сумму для перевода {context.user_data['from']} → {context.user_data['to']}"
        )
        return

    # ===== ввод коэффициента =====
    if state == "set_coef":
        try:
            coef = float(text)
            context.user_data["coef"] = coef
            await update.message.reply_text(f"✅ Коэффициент установлен: {coef}")
        except:
            await update.message.reply_text("❌ Введи число (пример: 0.8)")
        return

    # ===== конвертация =====
    if state == "convert":
        try:
            amount = float(text)

            base = context.user_data["from"]
            target = context.user_data["to"]

            rate = get_rate(base, target)
            coef = context.user_data.get("coef", 1)

            result = amount * rate * coef

            await update.message.reply_text(
                f"💱 {amount} {base} = {round(result,2)} {target}\n"
                f"Курс: 1 {base} = {round(rate,2)} {target}\n"
                f"Коэффициент: {coef}"
            )

        except Exception as e:
            await update.message.reply_text("❌ Ошибка. Введи число.")
        return

# =====================
# ЗАПУСК
# =====================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    print("Бот запущен 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()
