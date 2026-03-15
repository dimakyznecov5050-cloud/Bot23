# -*- coding: utf-8 -*-
# APEX UC BOT - one file version for Pydroid 3
# Install first:
# pip install pyTelegramBotAPI

import telebot
from telebot import types
import sqlite3
from datetime import datetime

# =========================
# CONFIG
# =========================
TOKEN = "8783525882:AAE0QrrgJUy_BBFZLAMZFAoIuZir0hHAj-8"
ADMIN_ID = 8052884471  # <-- сюда вставь свой Telegram ID

BOT_NAME = "APEX UC BOT"
SUPPORT = "@your_support"

# Пакеты UC и цены
UC_PACKS = [
    ("60 UC", 60, 99),
    ("325 UC", 325, 449),
    ("660 UC", 660, 899),
    ("1800 UC", 1800, 2399),
    ("3850 UC", 3850, 4999),
    ("8100 UC", 8100, 9999),
]

# Реквизиты для оплаты
PAYMENT_TEXT = """
💳 Оплата заказа

Переведите сумму по реквизитам:

Карта: 0000 0000 0000 0000
Банк: T-Bank / Sber
Получатель: APEX STORE

После оплаты нажмите кнопку:
✅ Я оплатил

Затем отправьте чек или скрин оплаты.
"""

# =========================
# INIT
# =========================
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
user_data = {}

conn = sqlite3.connect("apex_uc_bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    full_name TEXT,
    player_id TEXT,
    uc_amount INTEGER,
    price INTEGER,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()


# =========================
# DB FUNCTIONS
# =========================
def create_order(user_id, username, full_name, player_id, uc_amount, price):
    created_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    cur.execute("""
        INSERT INTO orders (user_id, username, full_name, player_id, uc_amount, price, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, full_name, player_id, uc_amount, price, "WAITING_PAYMENT", created_at))
    conn.commit()
    return cur.lastrowid

def get_order(order_id):
    cur.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    return cur.fetchone()

def update_order_status(order_id, status):
    cur.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
    conn.commit()

def get_user_orders(user_id):
    cur.execute("""
        SELECT id, uc_amount, price, status, created_at
        FROM orders
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10
    """, (user_id,))
    return cur.fetchall()

def status_text(status):
    statuses = {
        "WAITING_PAYMENT": "⏳ Ожидает оплату",
        "PAYMENT_SENT": "📩 Чек отправлен",
        "ON_REVIEW": "🔎 На проверке",
        "PAYMENT_CONFIRMED": "✅ Оплата подтверждена",
        "PAYMENT_REJECTED": "❌ Оплата отклонена",
        "DONE": "🎉 Выполнен",
        "CANCELED": "🚫 Отменён",
    }
    return statuses.get(status, status)


# =========================
# KEYBOARDS
# =========================
def main_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("🛒 Купить UC", callback_data="buy_uc"),
        types.InlineKeyboardButton("📦 Мои заказы", callback_data="my_orders"),
        types.InlineKeyboardButton("ℹ️ Как это работает", callback_data="help"),
    )
    return kb

def packs_menu():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for title, uc, price in UC_PACKS:
        kb.add(types.InlineKeyboardButton(f"{title} — {price}₽", callback_data=f"pack_{uc}_{price}"))
    kb.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_main"))
    return kb

def payment_menu(order_id):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{order_id}"),
        types.InlineKeyboardButton("❌ Отменить заказ", callback_data=f"cancel_{order_id}")
    )
    return kb

def admin_menu(order_id):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_ok_{order_id}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"admin_no_{order_id}")
    )
    kb.add(types.InlineKeyboardButton("🎉 Выполнено", callback_data=f"admin_done_{order_id}"))
    return kb


# =========================
# TEXTS
# =========================
def welcome_text(first_name):
    return f"""
<b>👋 Добро пожаловать в {BOT_NAME}</b>

{first_name}, здесь ты можешь оформить заказ на пополнение <b>UC для PUBG Mobile</b>.

<b>Что умеет бот:</b>
• выбор пакета UC
• оформление заказа
• отправка на проверку
• уведомление администратора
• просмотр своих заказов

Нажми кнопку ниже, чтобы начать.
"""

HELP_TEXT = f"""
<b>ℹ️ Как это работает</b>

1. Нажимаешь <b>Купить UC</b>
2. Выбираешь нужный пакет
3. Отправляешь <b>Player ID</b>
4. Получаешь реквизиты
5. Оплачиваешь заказ
6. Отправляешь чек
7. Админ подтверждает оплату
8. Заказ выполняется

<b>Важно:</b>
• Указывай правильный Player ID
• После оплаты обязательно отправь чек
• По всем вопросам: {SUPPORT}
"""


# =========================
# COMMANDS
# =========================
@bot.message_handler(commands=["start"])
def start_handler(message):
    user_data[message.chat.id] = {}
    text = welcome_text(message.from_user.first_name or "друг")
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

@bot.message_handler(commands=["admin"])
def admin_handler(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ У тебя нет доступа к админ-панели.")
        return
    bot.send_message(message.chat.id, "👑 Ты вошёл как администратор.")

@bot.message_handler(commands=["id"])
def id_handler(message):
    bot.send_message(message.chat.id, f"Твой ID: <code>{message.from_user.id}</code>")


# =========================
# CALLBACKS
# =========================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == "buy_uc":
            bot.edit_message_text(
                "🛒 <b>Выбери пакет UC:</b>",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=packs_menu()
            )

        elif call.data == "my_orders":
            orders = get_user_orders(call.from_user.id)
            if not orders:
                bot.answer_callback_query(call.id, "У тебя пока нет заказов")
                bot.send_message(call.message.chat.id, "📦 У тебя пока нет заказов.", reply_markup=main_menu())
                return

            text = "<b>📦 Твои последние заказы:</b>\n\n"
            for order in orders:
                oid, uc, price, status, created = order
                text += (
                    f"• <b>Заказ #{oid}</b>\n"
                    f"  💎 {uc} UC\n"
                    f"  💰 {price}₽\n"
                    f"  📌 {status_text(status)}\n"
                    f"  🕒 {created}\n\n"
                )
            bot.send_message(call.message.chat.id, text, reply_markup=main_menu())

        elif call.data == "help":
            bot.edit_message_text(
                HELP_TEXT,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_menu()
            )

        elif call.data == "back_main":
            bot.edit_message_text(
                welcome_text(call.from_user.first_name or "друг"),
                call.message.chat.id,
                call.message.message_id,
                reply_markup=main_menu()
            )

        elif call.data.startswith("pack_"):
            _, uc, price = call.data.split("_")
            user_data[call.from_user.id] = {
                "uc": int(uc),
                "price": int(price),
                "step": "waiting_player_id"
            }

            bot.send_message(
                call.message.chat.id,
                f"✍️ Ты выбрал: <b>{uc} UC</b> за <b>{price}₽</b>\n\n"
                f"Теперь отправь свой <b>Player ID</b> одним сообщением.\n\n"
                f"Пример: <code>5123456789</code>"
            )

        elif call.data.startswith("paid_"):
            order_id = int(call.data.split("_")[1])
            order = get_order(order_id)

            if not order:
                bot.answer_callback_query(call.id, "Заказ не найден")
                return

            if order[1] != call.from_user.id:
                bot.answer_callback_query(call.id, "Это не твой заказ")
                return

            update_order_status(order_id, "PAYMENT_SENT")
            user_data[call.from_user.id] = {
                "step": "waiting_proof",
                "order_id": order_id
            }

            bot.send_message(
                call.message.chat.id,
                f"📩 Отлично. Теперь отправь <b>чек или скрин оплаты</b>.\n\nЗаказ: <b>#{order_id}</b>"
            )

        elif call.data.startswith("cancel_"):
            order_id = int(call.data.split("_")[1])
            order = get_order(order_id)

            if not order:
                bot.answer_callback_query(call.id, "Заказ не найден")
                return

            if order[1] != call.from_user.id:
                bot.answer_callback_query(call.id, "Это не твой заказ")
                return

            update_order_status(order_id, "CANCELED")
            bot.send_message(call.message.chat.id, f"🚫 Заказ <b>#{order_id}</b> отменён.", reply_markup=main_menu())
            try:
                bot.send_message(ADMIN_ID, f"⚠️ Пользователь отменил заказ <b>#{order_id}</b>.")
            except:
                pass

        elif call.data.startswith("admin_ok_"):
            if call.from_user.id != ADMIN_ID:
                bot.answer_callback_query(call.id, "Нет доступа")
                return

            order_id = int(call.data.split("_")[2])
            order = get_order(order_id)
            if not order:
                bot.answer_callback_query(call.id, "Заказ не найден")
                return

            update_order_status(order_id, "PAYMENT_CONFIRMED")
            user_id = order[1]

            bot.send_message(user_id, f"✅ Оплата по заказу <b>#{order_id}</b> подтверждена.\nОжидай пополнение UC.")
            bot.edit_message_text(
                f"✅ Заказ <b>#{order_id}</b>\nСтатус: <b>Оплата подтверждена</b>",
                call.message.chat.id,
                call.message.message_id
            )

        elif call.data.startswith("admin_no_"):
            if call.from_user.id != ADMIN_ID:
                bot.answer_callback_query(call.id, "Нет доступа")
                return

            order_id = int(call.data.split("_")[2])
            order = get_order(order_id)
            if not order:
                bot.answer_callback_query(call.id, "Заказ не найден")
                return

            update_order_status(order_id, "PAYMENT_REJECTED")
            user_id = order[1]

            bot.send_message(user_id, f"❌ Оплата по заказу <b>#{order_id}</b> отклонена.\nНапиши в поддержку: {SUPPORT}")
            bot.edit_message_text(
                f"❌ Заказ <b>#{order_id}</b>\nСтатус: <b>Оплата отклонена</b>",
                call.message.chat.id,
                call.message.message_id
            )

        elif call.data.startswith("admin_done_"):
            if call.from_user.id != ADMIN_ID:
                bot.answer_callback_query(call.id, "Нет доступа")
                return

            order_id = int(call.data.split("_")[2])
            order = get_order(order_id)
            if not order:
                bot.answer_callback_query(call.id, "Заказ не найден")
                return

            update_order_status(order_id, "DONE")
            user_id = order[1]

            bot.send_message(user_id, f"🎉 Заказ <b>#{order_id}</b> выполнен.\nСпасибо за покупку в <b>{BOT_NAME}</b>!")
            bot.edit_message_text(
                f"🎉 Заказ <b>#{order_id}</b>\nСтатус: <b>Выполнен</b>",
                call.message.chat.id,
                call.message.message_id
            )

    except Exception as e:
        try:
            bot.send_message(call.message.chat.id, f"Ошибка: <code>{e}</code>")
        except:
            pass


# =========================
# MESSAGE HANDLERS
# =========================
@bot.message_handler(content_types=["text"])
def text_handler(message):
    uid = message.from_user.id

    if uid not in user_data:
        user_data[uid] = {}

    step = user_data[uid].get("step")

    if step == "waiting_player_id":
        player_id = message.text.strip()

        if len(player_id) < 5:
            bot.send_message(message.chat.id, "❗️Player ID выглядит слишком коротким. Попробуй ещё раз.")
            return

        uc = user_data[uid]["uc"]
        price = user_data[uid]["price"]

        order_id = create_order(
            user_id=uid,
            username=message.from_user.username or "",
            full_name=f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip(),
            player_id=player_id,
            uc_amount=uc,
            price=price
        )

        user_data[uid] = {}

        text = (
            f"✅ <b>Заказ создан успешно</b>\n\n"
            f"🆔 Номер заказа: <b>#{order_id}</b>\n"
            f"🎮 Player ID: <code>{player_id}</code>\n"
            f"💎 Пакет: <b>{uc} UC</b>\n"
            f"💰 Сумма: <b>{price}₽</b>\n\n"
            f"{PAYMENT_TEXT}"
        )

        bot.send_message(message.chat.id, text, reply_markup=payment_menu(order_id))

        try:
            admin_text = (
                f"🆕 <b>Новый заказ</b>\n\n"
                f"📦 Заказ: <b>#{order_id}</b>\n"
                f"👤 Пользователь: <b>{message.from_user.first_name}</b>\n"
                f"🆔 TG ID: <code>{uid}</code>\n"
                f"🔗 Username: @{message.from_user.username if message.from_user.username else 'нет'}\n"
                f"🎮 Player ID: <code>{player_id}</code>\n"
                f"💎 UC: <b>{uc}</b>\n"
                f"💰 Сумма: <b>{price}₽</b>\n"
                f"📌 Статус: <b>{status_text('WAITING_PAYMENT')}</b>"
            )
            bot.send_message(ADMIN_ID, admin_text, reply_markup=admin_menu(order_id))
        except:
            pass

    elif step == "waiting_proof":
        order_id = user_data[uid]["order_id"]
        update_order_status(order_id, "ON_REVIEW")
        user_data[uid] = {}

        bot.send_message(
            message.chat.id,
            f"✅ Чек по заказу <b>#{order_id}</b> отправлен на проверку.\nОжидай подтверждение.",
            reply_markup=main_menu()
        )

        try:
            bot.send_message(ADMIN_ID, f"🔎 Пользователь отправил подтверждение оплаты по заказу <b>#{order_id}</b>")
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        except:
            pass

    else:
        bot.send_message(
            message.chat.id,
            "Выбери нужный пункт меню 👇",
            reply_markup=main_menu()
        )


@bot.message_handler(content_types=["photo", "document"])
def media_handler(message):
    uid = message.from_user.id

    if uid not in user_data:
        user_data[uid] = {}

    step = user_data[uid].get("step")

    if step == "waiting_proof":
        order_id = user_data[uid]["order_id"]
        update_order_status(order_id, "ON_REVIEW")
        user_data[uid] = {}

        bot.send_message(
            message.chat.id,
            f"✅ Чек по заказу <b>#{order_id}</b> получен и отправлен на проверку.",
            reply_markup=main_menu()
        )

        try:
            bot.send_message(ADMIN_ID, f"🔎 Новый чек по заказу <b>#{order_id}</b>")
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
        except:
            pass
    else:
        bot.send_message(message.chat.id, "Сейчас бот не ожидает файл. Используй меню ниже.", reply_markup=main_menu())


# =========================
# START BOT
# =========================
print("APEX UC BOT is running...")
bot.infinity_polling(skip_pending=True)
