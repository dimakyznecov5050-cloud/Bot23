import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Optional

import telebot
from telebot import types

# =====================
# CONFIG (Bothost-ready)
# =====================
TOKEN = os.getenv("BOT_TOKEN", "8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8052884471"))
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "your_support_username")
REVIEWS_CHANNEL = os.getenv("REVIEWS_CHANNEL", "https://t.me/your_reviews_channel")
DB_PATH = os.getenv("DB_PATH", "bot.db")

CARDS = [
    {"bank": "Сбер", "number": "2202 1234 5678 9012", "holder": "IVAN IVANOV"},
    {"bank": "Т-Банк", "number": "2200 9876 5432 1098", "holder": "IVAN IVANOV"},
]

UC_PRICES = {
    60: 99,
    325: 449,
    660: 899,
    1800: 2299,
    3850: 4499,
}

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# in-memory step states
user_buy_state = {}
admin_state = {}


# =====================
# DB
# =====================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, col: str, definition: str):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                reg_date TEXT,
                total_uc INTEGER DEFAULT 0,
                total_orders INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number INTEGER UNIQUE,
                user_id INTEGER,
                username TEXT,
                player_id TEXT,
                uc_amount INTEGER,
                price INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                completed_at TEXT,
                promo_code TEXT,
                discount_percent INTEGER DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                discount INTEGER,
                usage_limit INTEGER DEFAULT 0,
                used_count INTEGER DEFAULT 0,
                expires_at TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_promos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                promo_code TEXT,
                activated_at TEXT,
                UNIQUE(user_id, promo_code)
            )
            """
        )

        # Migrations / missing columns
        _ensure_column(conn, "users", "username", "TEXT")
        _ensure_column(conn, "users", "reg_date", "TEXT")
        _ensure_column(conn, "users", "total_uc", "INTEGER DEFAULT 0")
        _ensure_column(conn, "users", "total_orders", "INTEGER DEFAULT 0")

        _ensure_column(conn, "orders", "order_number", "INTEGER")
        _ensure_column(conn, "orders", "promo_code", "TEXT")
        _ensure_column(conn, "orders", "discount_percent", "INTEGER DEFAULT 0")
        _ensure_column(conn, "orders", "completed_at", "TEXT")

        _ensure_column(conn, "promocodes", "usage_limit", "INTEGER DEFAULT 0")
        _ensure_column(conn, "promocodes", "used_count", "INTEGER DEFAULT 0")
        _ensure_column(conn, "promocodes", "expires_at", "TEXT")
        _ensure_column(conn, "promocodes", "is_active", "INTEGER DEFAULT 1")
        _ensure_column(conn, "promocodes", "created_at", "TEXT")

        conn.commit()


def _parse_expires_at(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def get_next_order_number() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(order_number) AS mx FROM orders").fetchone()
        return (row["mx"] or 0) + 1


def register_user(user):
    with get_conn() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,)).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO users(user_id, username, reg_date, total_uc, total_orders) VALUES(?,?,?,?,0)",
                (
                    user.id,
                    user.username or user.first_name or "unknown",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    0,
                ),
            )
        else:
            conn.execute(
                "UPDATE users SET username=? WHERE user_id=?",
                (user.username or user.first_name or "unknown", user.id),
            )
        conn.commit()


def get_active_user_promo(user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT p.*
            FROM user_promos up
            JOIN promocodes p ON p.code = up.promo_code
            WHERE up.user_id = ?
            ORDER BY up.activated_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if not row:
            return None
        if row["is_active"] != 1:
            return None
        expires_at = _parse_expires_at(row["expires_at"])
        if expires_at and datetime.now() > expires_at:
            return None
        return row


# =====================
# UI
# =====================
def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🛒 КУПИТЬ UC", "👤 МОЙ ПРОФИЛЬ")
    kb.row("🏆 ЛИДЕРЫ", "⭐️ ОТЗЫВЫ")
    kb.row("📞 ПОДДЕРЖКА", "🎟 ПРОМОКОД")
    return kb


@bot.message_handler(commands=["start"])
def cmd_start(message):
    register_user(message.from_user)
    bot.send_message(
        message.chat.id,
        "Добро пожаловать! Выберите действие в меню ниже 👇",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if not is_admin(message.from_user.id):
        return bot.reply_to(message, "⛔ У вас нет доступа.")
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    kb.add(types.InlineKeyboardButton("🎟 Промокоды", callback_data="admin_promos"))
    kb.add(types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"))
    bot.send_message(message.chat.id, "Админ-панель:", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "🛒 КУПИТЬ UC")
def buy_uc(message):
    kb = types.InlineKeyboardMarkup()
    for uc, price in UC_PRICES.items():
        kb.add(types.InlineKeyboardButton(f"{uc} UC — {price}₽", callback_data=f"buy_{uc}"))
    bot.send_message(message.chat.id, "Выберите пакет UC:", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "👤 МОЙ ПРОФИЛЬ")
def profile(message):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()
    if not row:
        return bot.reply_to(message, "Профиль не найден. Нажмите /start")
    text = (
        "<b>Ваш профиль</b>\n"
        f"ID: <code>{row['user_id']}</code>\n"
        f"Регистрация: {row['reg_date']}\n"
        f"Заказов: {row['total_orders']}\n"
        f"Всего куплено UC: {row['total_uc']}"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "🏆 ЛИДЕРЫ")
def leaders(message):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT username, total_uc FROM users ORDER BY total_uc DESC LIMIT 10"
        ).fetchall()
    if not rows:
        return bot.send_message(message.chat.id, "Пока нет данных.")
    text = "<b>Топ-10 лидеров по UC:</b>\n"
    for i, r in enumerate(rows, start=1):
        text += f"{i}. @{r['username']} — {r['total_uc']} UC\n"
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "⭐️ ОТЗЫВЫ")
def reviews(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Перейти в канал отзывов", url=REVIEWS_CHANNEL))
    bot.send_message(message.chat.id, "Наши отзывы:", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "📞 ПОДДЕРЖКА")
def support(message):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Связаться с поддержкой", url=f"https://t.me/{SUPPORT_USERNAME}"))
    bot.send_message(message.chat.id, "Поддержка:", reply_markup=kb)


@bot.message_handler(func=lambda m: m.text == "🎟 ПРОМОКОД")
def promo_start(message):
    bot.send_message(message.chat.id, "Введите промокод текстом:")
    bot.register_next_step_handler(message, promo_apply)


def promo_apply(message):
    code = (message.text or "").strip().upper()
    user_id = message.from_user.id
    if not code:
        return bot.send_message(message.chat.id, "Промокод пустой.")

    with get_conn() as conn:
        promo = conn.execute("SELECT * FROM promocodes WHERE code=?", (code,)).fetchone()
        if not promo:
            return bot.send_message(message.chat.id, "❌ Промокод не найден.")
        if promo["is_active"] != 1:
            return bot.send_message(message.chat.id, "❌ Промокод неактивен.")
        exp = _parse_expires_at(promo["expires_at"])
        if exp and datetime.now() > exp:
            return bot.send_message(message.chat.id, "❌ Срок действия промокода истек.")
        if promo["usage_limit"] > 0 and promo["used_count"] >= promo["usage_limit"]:
            return bot.send_message(message.chat.id, "❌ Лимит использований промокода исчерпан.")

        already = conn.execute(
            "SELECT 1 FROM user_promos WHERE user_id=? AND promo_code=?",
            (user_id, code),
        ).fetchone()
        if already:
            return bot.send_message(message.chat.id, "❌ Вы уже активировали этот промокод.")

        conn.execute(
            "INSERT INTO user_promos(user_id, promo_code, activated_at) VALUES(?,?,?)",
            (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code=?", (code,))
        conn.commit()

    bot.send_message(
        message.chat.id,
        f"✅ Промокод <b>{code}</b> активирован. Скидка: <b>{promo['discount']}%</b>",
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
def process_buy_choose(call):
    uc = int(call.data.split("_")[1])
    price = UC_PRICES[uc]
    promo = get_active_user_promo(call.from_user.id)
    discount = promo["discount"] if promo else 0
    final_price = int(price * (100 - discount) / 100)

    user_buy_state[call.from_user.id] = {
        "uc": uc,
        "base_price": price,
        "final_price": final_price,
        "promo_code": promo["code"] if promo else None,
        "discount": discount,
    }

    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"Вы выбрали <b>{uc} UC</b>.\n"
        f"Цена: <s>{price}₽</s> <b>{final_price}₽</b>\n"
        "Отправьте ваш игровой ID:",
    )
    bot.register_next_step_handler(call.message, process_player_id)


def process_player_id(message):
    st = user_buy_state.get(message.from_user.id)
    if not st:
        return bot.send_message(message.chat.id, "Сессия покупки не найдена. Нажмите «КУПИТЬ UC».")

    player_id = (message.text or "").strip()
    if len(player_id) < 4:
        bot.send_message(message.chat.id, "Игровой ID выглядит слишком коротким, попробуйте еще раз:")
        return bot.register_next_step_handler(message, process_player_id)

    order_number = get_next_order_number()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO orders(order_number, user_id, username, player_id, uc_amount, price, status, created_at, promo_code, discount_percent)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                order_number,
                message.from_user.id,
                message.from_user.username or message.from_user.first_name or "unknown",
                player_id,
                st["uc"],
                st["final_price"],
                "pending",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                st["promo_code"],
                st["discount"],
            ),
        )
        conn.commit()

    cards_text = "\n".join([f"• {c['bank']}: <code>{c['number']}</code> ({c['holder']})" for c in CARDS])
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_number}"))
    kb.add(types.InlineKeyboardButton("❌ ОТМЕНА", callback_data=f"cancel_{order_number}"))

    bot.send_message(
        message.chat.id,
        "<b>Заказ создан</b>\n"
        f"Номер: <code>{order_number}</code>\n"
        f"Игровой ID: <code>{player_id}</code>\n"
        f"UC: {st['uc']}\n"
        f"К оплате: <b>{st['final_price']}₽</b>\n\n"
        "Реквизиты для оплаты:\n"
        f"{cards_text}\n\n"
        "После оплаты нажмите кнопку ниже:",
        reply_markup=kb,
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("cancel_"))
def process_cancel_order(call):
    order_number = int(call.data.split("_")[1])
    with get_conn() as conn:
        conn.execute(
            "UPDATE orders SET status='canceled' WHERE order_number=? AND user_id=?",
            (order_number, call.from_user.id),
        )
        conn.commit()
    bot.answer_callback_query(call.id, "Заказ отменен")
    bot.send_message(call.message.chat.id, "❌ Заказ отменен. Вы можете создать новый.")


@bot.callback_query_handler(func=lambda c: c.data.startswith("paid_"))
def process_paid_order(call):
    order_number = int(call.data.split("_")[1])
    with get_conn() as conn:
        order = conn.execute(
            "SELECT * FROM orders WHERE order_number=? AND user_id=?",
            (order_number, call.from_user.id),
        ).fetchone()
        if not order:
            return bot.answer_callback_query(call.id, "Заказ не найден", show_alert=True)
        conn.execute(
            "UPDATE orders SET status='processing' WHERE order_number=?",
            (order_number,),
        )
        conn.commit()

    bot.answer_callback_query(call.id, "Заявка отправлена")
    bot.send_message(call.message.chat.id, "✅ Заявка принята, ожидайте подтверждения администратора.")

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"adm_ok_{order_number}"))
    kb.add(types.InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data=f"adm_cancel_{order_number}"))

    text = (
        "<b>Новая заявка на пополнение</b>\n"
        f"Заказ: <code>{order['order_number']}</code>\n"
        f"User ID: <code>{order['user_id']}</code>\n"
        f"Username: @{order['username']}\n"
        f"Player ID: <code>{order['player_id']}</code>\n"
        f"UC: {order['uc_amount']}\n"
        f"Сумма: {order['price']}₽\n"
        f"Промо: {order['promo_code'] or '—'} ({order['discount_percent']}%)"
    )
    bot.send_message(ADMIN_ID, text, reply_markup=kb)


@bot.callback_query_handler(func=lambda c: c.data in {"admin_stats", "admin_promos", "admin_broadcast"})
def admin_menu_router(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)

    if call.data == "admin_stats":
        with get_conn() as conn:
            users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            orders_all = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
            completed = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE status='completed'").fetchone()["c"]
            processing = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE status='processing'").fetchone()["c"]
            revenue = conn.execute("SELECT COALESCE(SUM(price),0) AS s FROM orders WHERE status='completed'").fetchone()["s"]
            sold_uc = conn.execute("SELECT COALESCE(SUM(uc_amount),0) AS s FROM orders WHERE status='completed'").fetchone()["s"]
            promos = conn.execute("SELECT COUNT(*) AS c FROM promocodes").fetchone()["c"]

        text = (
            "<b>Статистика</b>\n"
            f"Пользователей: {users}\n"
            f"Заказов всего: {orders_all}\n"
            f"Выполнено: {completed}\n"
            f"В обработке: {processing}\n"
            f"Заработано: {revenue}₽\n"
            f"Продано UC: {sold_uc}\n"
            f"Промокодов: {promos}"
        )
        bot.answer_callback_query(call.id)
        return bot.send_message(call.message.chat.id, text)

    if call.data == "admin_promos":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Создать", callback_data="promo_create"))
        kb.add(types.InlineKeyboardButton("Список", callback_data="promo_list"))
        bot.answer_callback_query(call.id)
        return bot.send_message(call.message.chat.id, "Управление промокодами:", reply_markup=kb)

    if call.data == "admin_broadcast":
        admin_state[call.from_user.id] = {"mode": "broadcast_wait"}
        bot.answer_callback_query(call.id)
        return bot.send_message(call.message.chat.id, "Введите текст рассылки одним сообщением:")


@bot.callback_query_handler(func=lambda c: c.data in {"promo_create", "promo_list"})
def admin_promos_router(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)

    if call.data == "promo_list":
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM promocodes ORDER BY id DESC"
            ).fetchall()
        if not rows:
            return bot.send_message(call.message.chat.id, "Список промокодов пуст.")
        text = "<b>Промокоды:</b>\n"
        for r in rows:
            status = "активен" if r["is_active"] == 1 else "неактивен"
            limit = "безлимит" if r["usage_limit"] == 0 else f"{r['used_count']}/{r['usage_limit']}"
            exp = r["expires_at"] or "бессрочно"
            text += f"\n• <code>{r['code']}</code> — {r['discount']}% | {limit} | до {exp} | {status}"
        return bot.send_message(call.message.chat.id, text)

    admin_state[call.from_user.id] = {"mode": "promo_create_code"}
    bot.send_message(call.message.chat.id, "Введите текст промокода:")


@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.from_user.id in admin_state)
def admin_step_handler(message):
    st = admin_state.get(message.from_user.id, {})
    mode = st.get("mode")

    if mode == "broadcast_wait":
        text = message.text or ""
        sent = 0
        failed = 0
        with get_conn() as conn:
            users = conn.execute("SELECT user_id FROM users").fetchall()
        for u in users:
            try:
                bot.send_message(u["user_id"], text)
                sent += 1
            except Exception:
                failed += 1
        admin_state.pop(message.from_user.id, None)
        return bot.send_message(message.chat.id, f"Рассылка завершена. Отправлено: {sent}, ошибок: {failed}")

    if mode == "promo_create_code":
        st["code"] = (message.text or "").strip().upper()
        st["mode"] = "promo_create_discount"
        admin_state[message.from_user.id] = st
        return bot.send_message(message.chat.id, "Введите скидку в % (например, 10):")

    if mode == "promo_create_discount":
        try:
            discount = int((message.text or "0").strip())
            if discount <= 0 or discount >= 100:
                raise ValueError
        except ValueError:
            return bot.send_message(message.chat.id, "Введите число 1..99")
        st["discount"] = discount
        st["mode"] = "promo_create_limit"
        admin_state[message.from_user.id] = st
        return bot.send_message(message.chat.id, "Введите лимит использований (0 = безлимит):")

    if mode == "promo_create_limit":
        try:
            limit = int((message.text or "0").strip())
            if limit < 0:
                raise ValueError
        except ValueError:
            return bot.send_message(message.chat.id, "Введите корректное число (0 или больше)")
        st["usage_limit"] = limit
        st["mode"] = "promo_create_days"
        admin_state[message.from_user.id] = st
        return bot.send_message(message.chat.id, "Введите срок действия в днях (0 = бессрочно):")

    if mode == "promo_create_days":
        try:
            days = int((message.text or "0").strip())
            if days < 0:
                raise ValueError
        except ValueError:
            return bot.send_message(message.chat.id, "Введите корректное число (0 или больше)")

        expires_at = None
        if days > 0:
            expires_at = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

        with get_conn() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO promocodes(code, discount, usage_limit, used_count, expires_at, is_active, created_at)
                    VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        st["code"],
                        st["discount"],
                        st["usage_limit"],
                        0,
                        expires_at,
                        1,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                admin_state.pop(message.from_user.id, None)
                return bot.send_message(message.chat.id, "Промокод с таким кодом уже существует.")

        admin_state.pop(message.from_user.id, None)
        return bot.send_message(
            message.chat.id,
            f"✅ Промокод создан: {st['code']} ({st['discount']}%)",
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ok_") or c.data.startswith("adm_cancel_"))
def admin_order_actions(call):
    if not is_admin(call.from_user.id):
        return bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)

    is_ok = call.data.startswith("adm_ok_")
    order_number = int(call.data.split("_")[-1])

    with get_conn() as conn:
        order = conn.execute("SELECT * FROM orders WHERE order_number=?", (order_number,)).fetchone()
        if not order:
            return bot.answer_callback_query(call.id, "Заказ не найден", show_alert=True)

        if is_ok:
            conn.execute(
                "UPDATE orders SET status='completed', completed_at=? WHERE order_number=?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_number),
            )
            conn.execute(
                "UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1 WHERE user_id=?",
                (order["uc_amount"], order["user_id"]),
            )
            conn.commit()

            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Оставить отзыв", url=REVIEWS_CHANNEL))
            bot.send_message(
                order["user_id"],
                f"✅ Ваш заказ #{order_number} выполнен!\nНачислено: {order['uc_amount']} UC",
                reply_markup=kb,
            )
            bot.answer_callback_query(call.id, "Подтверждено")
            bot.send_message(call.message.chat.id, f"Заказ #{order_number} подтвержден и выдан.")
        else:
            conn.execute(
                "UPDATE orders SET status='canceled' WHERE order_number=?",
                (order_number,),
            )
            conn.commit()

            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("Связаться с поддержкой", url=f"https://t.me/{SUPPORT_USERNAME}"))
            bot.send_message(
                order["user_id"],
                f"❌ Ваш заказ #{order_number} отменен. Если нужна помощь — напишите в поддержку.",
                reply_markup=kb,
            )
            bot.answer_callback_query(call.id, "Отменено")
            bot.send_message(call.message.chat.id, f"Заказ #{order_number} отменен.")


@bot.message_handler(func=lambda _: True)
def fallback(message):
    bot.send_message(message.chat.id, "Используйте меню кнопок ниже 👇", reply_markup=main_keyboard())


if __name__ == "__main__":
    init_db()
    print("Bot started")
    while True:
        try:
            bot.polling(non_stop=True, timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)
