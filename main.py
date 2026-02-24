diff --git a/main.py b/main.py
index e18a903af15965c34a4bb6860547c5782ed2fb9d..fd2eebd8fdeb44a4963a96578ea44a35a515ad04 100644
--- a/main.py
+++ b/main.py
@@ -1,999 +1,494 @@
-diff --git a/main.py b/main.py
-index 5f2a7fe1c349e94113cb9f5396f338333fe43c26..bf1b4e59b614c637d71bea24a5496baf798d6c4e 100644
---- a/main.py
-+++ b/main.py
-@@ -1,59 +1,65 @@
- import os
- import sqlite3
- import time
- from datetime import datetime, timedelta
- from typing import Optional
- 
- import telebot
- from telebot import types
- 
- # =====================
- # CONFIG (Bothost-ready)
- # =====================
--TOKEN = os.getenv("BOT_TOKEN", "8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI")
-+TOKEN = os.getenv("BOT_TOKEN", "")
- ADMIN_ID = int(os.getenv("ADMIN_ID", "8052884471"))
- SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "your_support_username")
- REVIEWS_CHANNEL = os.getenv("REVIEWS_CHANNEL", "https://t.me/your_reviews_channel")
- DB_PATH = os.getenv("DB_PATH", "bot.db")
- 
- CARDS = [
-     {"bank": "Сбер", "number": "2202 1234 5678 9012", "holder": "IVAN IVANOV"},
-     {"bank": "Т-Банк", "number": "2200 9876 5432 1098", "holder": "IVAN IVANOV"},
- ]
- 
--UC_PRICES = {
-+DEFAULT_UC_PACKS = {
-     60: 99,
-     325: 449,
-     660: 899,
-     1800: 2299,
-     3850: 4499,
- }
- 
-+DEFAULT_POPULARITY_PACKS = [
-+    ("100 подписчиков", 100, 199),
-+    ("500 подписчиков", 500, 899),
-+    ("1000 подписчиков", 1000, 1599),
-+    ("5000 просмотров", 5000, 499),
-+]
-+
- bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
- 
--# in-memory step states
- user_buy_state = {}
- admin_state = {}
- 
- 
- # =====================
- # DB
- # =====================
- def get_conn():
-     conn = sqlite3.connect(DB_PATH, check_same_thread=False)
-     conn.row_factory = sqlite3.Row
-     return conn
- 
- 
- def _ensure_column(conn: sqlite3.Connection, table: str, col: str, definition: str):
-     cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
-     if col not in cols:
-         conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
- 
- 
- def init_db():
-     with get_conn() as conn:
-         conn.execute(
-             """
-             CREATE TABLE IF NOT EXISTS users (
-                 user_id INTEGER PRIMARY KEY,
-@@ -85,475 +91,711 @@ def init_db():
-         conn.execute(
-             """
-             CREATE TABLE IF NOT EXISTS promocodes (
-                 id INTEGER PRIMARY KEY AUTOINCREMENT,
-                 code TEXT UNIQUE,
-                 discount INTEGER,
-                 usage_limit INTEGER DEFAULT 0,
-                 used_count INTEGER DEFAULT 0,
-                 expires_at TEXT,
-                 is_active INTEGER DEFAULT 1,
-                 created_at TEXT
-             )
-             """
-         )
-         conn.execute(
-             """
-             CREATE TABLE IF NOT EXISTS user_promos (
-                 id INTEGER PRIMARY KEY AUTOINCREMENT,
-                 user_id INTEGER,
-                 promo_code TEXT,
-                 activated_at TEXT,
-                 UNIQUE(user_id, promo_code)
-             )
-             """
-         )
-+        conn.execute(
-+            """
-+            CREATE TABLE IF NOT EXISTS uc_packs (
-+                uc_amount INTEGER PRIMARY KEY,
-+                price INTEGER NOT NULL,
-+                is_active INTEGER DEFAULT 1
-+            )
-+            """
-+        )
-+        conn.execute(
-+            """
-+            CREATE TABLE IF NOT EXISTS popularity_packs (
-+                id INTEGER PRIMARY KEY AUTOINCREMENT,
-+                title TEXT NOT NULL,
-+                amount INTEGER DEFAULT 0,
-+                price INTEGER NOT NULL,
-+                is_active INTEGER DEFAULT 1,
-+                created_at TEXT
-+            )
-+            """
-+        )
-+        conn.execute(
-+            """
-+            CREATE TABLE IF NOT EXISTS popularity_orders (
-+                id INTEGER PRIMARY KEY AUTOINCREMENT,
-+                order_number INTEGER UNIQUE,
-+                user_id INTEGER,
-+                username TEXT,
-+                pack_id INTEGER,
-+                pack_title TEXT,
-+                amount INTEGER,
-+                target_link TEXT,
-+                price INTEGER,
-+                status TEXT DEFAULT 'pending',
-+                created_at TEXT,
-+                completed_at TEXT
-+            )
-+            """
-+        )
- 
--        # Migrations / missing columns
--        _ensure_column(conn, "users", "username", "TEXT")
--        _ensure_column(conn, "users", "reg_date", "TEXT")
--        _ensure_column(conn, "users", "total_uc", "INTEGER DEFAULT 0")
--        _ensure_column(conn, "users", "total_orders", "INTEGER DEFAULT 0")
--
--        _ensure_column(conn, "orders", "order_number", "INTEGER")
--        _ensure_column(conn, "orders", "promo_code", "TEXT")
--        _ensure_column(conn, "orders", "discount_percent", "INTEGER DEFAULT 0")
--        _ensure_column(conn, "orders", "completed_at", "TEXT")
-+        for uc, price in DEFAULT_UC_PACKS.items():
-+            conn.execute(
-+                "INSERT OR IGNORE INTO uc_packs(uc_amount, price, is_active) VALUES(?,?,1)",
-+                (uc, price),
-+            )
- 
--        _ensure_column(conn, "promocodes", "usage_limit", "INTEGER DEFAULT 0")
--        _ensure_column(conn, "promocodes", "used_count", "INTEGER DEFAULT 0")
--        _ensure_column(conn, "promocodes", "expires_at", "TEXT")
--        _ensure_column(conn, "promocodes", "is_active", "INTEGER DEFAULT 1")
--        _ensure_column(conn, "promocodes", "created_at", "TEXT")
-+        if conn.execute("SELECT COUNT(*) AS c FROM popularity_packs").fetchone()["c"] == 0:
-+            for title, amount, price in DEFAULT_POPULARITY_PACKS:
-+                conn.execute(
-+                    """
-+                    INSERT INTO popularity_packs(title, amount, price, is_active, created_at)
-+                    VALUES(?,?,?,?,?)
-+                    """,
-+                    (title, amount, price, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
-+                )
- 
-         conn.commit()
- 
- 
- def _parse_expires_at(value: Optional[str]) -> Optional[datetime]:
-     if not value:
-         return None
-     for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y"):
-         try:
-             return datetime.strptime(value, fmt)
-         except ValueError:
-             continue
-     return None
- 
- 
- def is_admin(user_id: int) -> bool:
-     return user_id == ADMIN_ID
- 
- 
- def get_next_order_number() -> int:
-     with get_conn() as conn:
--        row = conn.execute("SELECT MAX(order_number) AS mx FROM orders").fetchone()
--        return (row["mx"] or 0) + 1
-+        mx_uc = conn.execute("SELECT MAX(order_number) AS mx FROM orders").fetchone()["mx"] or 0
-+        mx_pop = conn.execute("SELECT MAX(order_number) AS mx FROM popularity_orders").fetchone()["mx"] or 0
-+    return max(mx_uc, mx_pop) + 1
-+
-+
-+def get_uc_packs():
-+    with get_conn() as conn:
-+        rows = conn.execute(
-+            "SELECT uc_amount, price FROM uc_packs WHERE is_active=1 ORDER BY uc_amount"
-+        ).fetchall()
-+    return rows
-+
-+
-+def get_popularity_packs():
-+    with get_conn() as conn:
-+        rows = conn.execute(
-+            "SELECT id, title, amount, price FROM popularity_packs WHERE is_active=1 ORDER BY id"
-+        ).fetchall()
-+    return rows
- 
- 
- def register_user(user):
-     with get_conn() as conn:
-         row = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,)).fetchone()
-         if not row:
-             conn.execute(
-                 "INSERT INTO users(user_id, username, reg_date, total_uc, total_orders) VALUES(?,?,?,?,0)",
-                 (
-                     user.id,
-                     user.username or user.first_name or "unknown",
-                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
-                     0,
-                 ),
-             )
-         else:
-             conn.execute(
-                 "UPDATE users SET username=? WHERE user_id=?",
-                 (user.username or user.first_name or "unknown", user.id),
-             )
-         conn.commit()
- 
- 
- def get_active_user_promo(user_id: int):
-     with get_conn() as conn:
-         row = conn.execute(
-             """
-             SELECT p.*
-             FROM user_promos up
-             JOIN promocodes p ON p.code = up.promo_code
-             WHERE up.user_id = ?
-             ORDER BY up.activated_at DESC
-             LIMIT 1
-             """,
-             (user_id,),
-         ).fetchone()
--        if not row:
--            return None
--        if row["is_active"] != 1:
-+        if not row or row["is_active"] != 1:
-             return None
-         expires_at = _parse_expires_at(row["expires_at"])
-         if expires_at and datetime.now() > expires_at:
-             return None
-         return row
- 
- 
- # =====================
- # UI
- # =====================
- def main_keyboard():
-     kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
--    kb.row("🛒 КУПИТЬ UC", "👤 МОЙ ПРОФИЛЬ")
--    kb.row("🏆 ЛИДЕРЫ", "⭐️ ОТЗЫВЫ")
--    kb.row("📞 ПОДДЕРЖКА", "🎟 ПРОМОКОД")
-+    kb.row("🛒 КУПИТЬ UC", "🔥 ПАКИ ПОПУЛЯРНОСТИ")
-+    kb.row("👤 МОЙ ПРОФИЛЬ", "🏆 ЛИДЕРЫ")
-+    kb.row("⭐️ ОТЗЫВЫ", "📞 ПОДДЕРЖКА")
-+    kb.row("🎟 ПРОМОКОД")
-     return kb
- 
- 
- @bot.message_handler(commands=["start"])
- def cmd_start(message):
-     register_user(message.from_user)
--    bot.send_message(
--        message.chat.id,
--        "Добро пожаловать! Выберите действие в меню ниже 👇",
--        reply_markup=main_keyboard(),
--    )
-+    bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие 👇", reply_markup=main_keyboard())
- 
- 
- @bot.message_handler(commands=["admin"])
- def cmd_admin(message):
-     if not is_admin(message.from_user.id):
-         return bot.reply_to(message, "⛔ У вас нет доступа.")
-     kb = types.InlineKeyboardMarkup()
-     kb.add(types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
-+    kb.add(types.InlineKeyboardButton("💸 Цены UC", callback_data="admin_uc_prices"))
-     kb.add(types.InlineKeyboardButton("🎟 Промокоды", callback_data="admin_promos"))
-+    kb.add(types.InlineKeyboardButton("🔥 Паки популярности", callback_data="admin_pop_packs"))
-     kb.add(types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"))
-     bot.send_message(message.chat.id, "Админ-панель:", reply_markup=kb)
- 
- 
- @bot.message_handler(func=lambda m: m.text == "🛒 КУПИТЬ UC")
- def buy_uc(message):
-     kb = types.InlineKeyboardMarkup()
--    for uc, price in UC_PRICES.items():
--        kb.add(types.InlineKeyboardButton(f"{uc} UC — {price}₽", callback_data=f"buy_{uc}"))
-+    packs = get_uc_packs()
-+    if not packs:
-+        return bot.send_message(message.chat.id, "Пакеты UC временно недоступны.")
-+    for row in packs:
-+        kb.add(types.InlineKeyboardButton(f"{row['uc_amount']} UC — {row['price']}₽", callback_data=f"buy_{row['uc_amount']}"))
-     bot.send_message(message.chat.id, "Выберите пакет UC:", reply_markup=kb)
- 
- 
-+@bot.message_handler(func=lambda m: m.text == "🔥 ПАКИ ПОПУЛЯРНОСТИ")
-+def buy_popularity(message):
-+    kb = types.InlineKeyboardMarkup()
-+    packs = get_popularity_packs()
-+    if not packs:
-+        return bot.send_message(message.chat.id, "Паки популярности временно недоступны.")
-+    for p in packs:
-+        kb.add(types.InlineKeyboardButton(f"{p['title']} — {p['price']}₽", callback_data=f"pop_buy_{p['id']}"))
-+    bot.send_message(message.chat.id, "Выберите пак популярности:", reply_markup=kb)
-+
-+
- @bot.message_handler(func=lambda m: m.text == "👤 МОЙ ПРОФИЛЬ")
- def profile(message):
-     with get_conn() as conn:
-         row = conn.execute("SELECT * FROM users WHERE user_id=?", (message.from_user.id,)).fetchone()
-     if not row:
-         return bot.reply_to(message, "Профиль не найден. Нажмите /start")
-     text = (
-         "<b>Ваш профиль</b>\n"
-         f"ID: <code>{row['user_id']}</code>\n"
-         f"Регистрация: {row['reg_date']}\n"
-         f"Заказов: {row['total_orders']}\n"
-         f"Всего куплено UC: {row['total_uc']}"
-     )
-     bot.send_message(message.chat.id, text)
- 
- 
- @bot.message_handler(func=lambda m: m.text == "🏆 ЛИДЕРЫ")
- def leaders(message):
-     with get_conn() as conn:
--        rows = conn.execute(
--            "SELECT username, total_uc FROM users ORDER BY total_uc DESC LIMIT 10"
--        ).fetchall()
-+        rows = conn.execute("SELECT username, total_uc FROM users ORDER BY total_uc DESC LIMIT 10").fetchall()
-     if not rows:
-         return bot.send_message(message.chat.id, "Пока нет данных.")
--    text = "<b>Топ-10 лидеров по UC:</b>\n"
-+    text = "<b>Топ-10 лидеров по купленным UC:</b>\n"
-     for i, r in enumerate(rows, start=1):
-         text += f"{i}. @{r['username']} — {r['total_uc']} UC\n"
-     bot.send_message(message.chat.id, text)
- 
- 
- @bot.message_handler(func=lambda m: m.text == "⭐️ ОТЗЫВЫ")
- def reviews(message):
-     kb = types.InlineKeyboardMarkup()
-     kb.add(types.InlineKeyboardButton("Перейти в канал отзывов", url=REVIEWS_CHANNEL))
-     bot.send_message(message.chat.id, "Наши отзывы:", reply_markup=kb)
- 
- 
- @bot.message_handler(func=lambda m: m.text == "📞 ПОДДЕРЖКА")
- def support(message):
-     kb = types.InlineKeyboardMarkup()
-     kb.add(types.InlineKeyboardButton("Связаться с поддержкой", url=f"https://t.me/{SUPPORT_USERNAME}"))
-     bot.send_message(message.chat.id, "Поддержка:", reply_markup=kb)
- 
- 
- @bot.message_handler(func=lambda m: m.text == "🎟 ПРОМОКОД")
- def promo_start(message):
-     bot.send_message(message.chat.id, "Введите промокод текстом:")
-     bot.register_next_step_handler(message, promo_apply)
- 
- 
- def promo_apply(message):
-     code = (message.text or "").strip().upper()
-     user_id = message.from_user.id
-     if not code:
-         return bot.send_message(message.chat.id, "Промокод пустой.")
- 
-     with get_conn() as conn:
-         promo = conn.execute("SELECT * FROM promocodes WHERE code=?", (code,)).fetchone()
-         if not promo:
-             return bot.send_message(message.chat.id, "❌ Промокод не найден.")
-         if promo["is_active"] != 1:
-             return bot.send_message(message.chat.id, "❌ Промокод неактивен.")
-         exp = _parse_expires_at(promo["expires_at"])
-         if exp and datetime.now() > exp:
-             return bot.send_message(message.chat.id, "❌ Срок действия промокода истек.")
-         if promo["usage_limit"] > 0 and promo["used_count"] >= promo["usage_limit"]:
-             return bot.send_message(message.chat.id, "❌ Лимит использований промокода исчерпан.")
- 
--        already = conn.execute(
--            "SELECT 1 FROM user_promos WHERE user_id=? AND promo_code=?",
--            (user_id, code),
--        ).fetchone()
-+        already = conn.execute("SELECT 1 FROM user_promos WHERE user_id=? AND promo_code=?", (user_id, code)).fetchone()
-         if already:
-             return bot.send_message(message.chat.id, "❌ Вы уже активировали этот промокод.")
- 
-         conn.execute(
-             "INSERT INTO user_promos(user_id, promo_code, activated_at) VALUES(?,?,?)",
-             (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
-         )
-         conn.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code=?", (code,))
-         conn.commit()
- 
--    bot.send_message(
--        message.chat.id,
--        f"✅ Промокод <b>{code}</b> активирован. Скидка: <b>{promo['discount']}%</b>",
--    )
-+    bot.send_message(message.chat.id, f"✅ Промокод <b>{code}</b> активирован. Скидка: <b>{promo['discount']}%</b>")
- 
- 
- @bot.callback_query_handler(func=lambda c: c.data.startswith("buy_"))
- def process_buy_choose(call):
-     uc = int(call.data.split("_")[1])
--    price = UC_PRICES[uc]
-+    with get_conn() as conn:
-+        row = conn.execute("SELECT price FROM uc_packs WHERE uc_amount=? AND is_active=1", (uc,)).fetchone()
-+    if not row:
-+        return bot.answer_callback_query(call.id, "Пакет не найден", show_alert=True)
-+
-+    price = row["price"]
-     promo = get_active_user_promo(call.from_user.id)
-     discount = promo["discount"] if promo else 0
-     final_price = int(price * (100 - discount) / 100)
--
-     user_buy_state[call.from_user.id] = {
-+        "flow": "uc",
-         "uc": uc,
--        "base_price": price,
-         "final_price": final_price,
-         "promo_code": promo["code"] if promo else None,
-         "discount": discount,
-     }
- 
-     bot.answer_callback_query(call.id)
-     bot.send_message(
-         call.message.chat.id,
--        f"Вы выбрали <b>{uc} UC</b>.\n"
--        f"Цена: <s>{price}₽</s> <b>{final_price}₽</b>\n"
--        "Отправьте ваш игровой ID:",
-+        f"Вы выбрали <b>{uc} UC</b>.\nЦена: <b>{final_price}₽</b>\nОтправьте ваш игровой ID:",
-     )
-     bot.register_next_step_handler(call.message, process_player_id)
- 
- 
-+@bot.callback_query_handler(func=lambda c: c.data.startswith("pop_buy_"))
-+def process_pop_buy_choose(call):
-+    pack_id = int(call.data.split("_")[-1])
-+    with get_conn() as conn:
-+        pack = conn.execute(
-+            "SELECT id, title, amount, price FROM popularity_packs WHERE id=? AND is_active=1",
-+            (pack_id,),
-+        ).fetchone()
-+    if not pack:
-+        return bot.answer_callback_query(call.id, "Пак не найден", show_alert=True)
-+
-+    user_buy_state[call.from_user.id] = {
-+        "flow": "pop",
-+        "pack_id": pack["id"],
-+        "pack_title": pack["title"],
-+        "amount": pack["amount"],
-+        "final_price": pack["price"],
-+    }
-+    bot.answer_callback_query(call.id)
-+    bot.send_message(
-+        call.message.chat.id,
-+        f"Вы выбрали <b>{pack['title']}</b>.\nЦена: <b>{pack['price']}₽</b>\n"
-+        "Отправьте ссылку (канал/пост/профиль), куда нужно выполнить заказ:",
-+    )
-+    bot.register_next_step_handler(call.message, process_pop_target)
-+
-+
-+def process_pop_target(message):
-+    st = user_buy_state.get(message.from_user.id)
-+    if not st or st.get("flow") != "pop":
-+        return bot.send_message(message.chat.id, "Сессия не найдена. Выберите пак заново.")
-+    target = (message.text or "").strip()
-+    if len(target) < 5:
-+        bot.send_message(message.chat.id, "Ссылка слишком короткая, попробуйте снова:")
-+        return bot.register_next_step_handler(message, process_pop_target)
-+
-+    order_number = get_next_order_number()
-+    with get_conn() as conn:
-+        conn.execute(
-+            """
-+            INSERT INTO popularity_orders(order_number, user_id, username, pack_id, pack_title, amount, target_link, price, status, created_at)
-+            VALUES(?,?,?,?,?,?,?,?,?,?)
-+            """,
-+            (
-+                order_number,
-+                message.from_user.id,
-+                message.from_user.username or message.from_user.first_name or "unknown",
-+                st["pack_id"],
-+                st["pack_title"],
-+                st["amount"],
-+                target,
-+                st["final_price"],
-+                "pending",
-+                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
-+            ),
-+        )
-+        conn.commit()
-+
-+    cards_text = "\n".join([f"• {c['bank']}: <code>{c['number']}</code> ({c['holder']})" for c in CARDS])
-+    kb = types.InlineKeyboardMarkup()
-+    kb.add(types.InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"pop_paid_{order_number}"))
-+    kb.add(types.InlineKeyboardButton("❌ ОТМЕНА", callback_data=f"pop_cancel_{order_number}"))
-+    bot.send_message(
-+        message.chat.id,
-+        "<b>Заказ на популярность создан</b>\n"
-+        f"Номер: <code>{order_number}</code>\n"
-+        f"Пак: {st['pack_title']}\n"
-+        f"Ссылка: <code>{target}</code>\n"
-+        f"К оплате: <b>{st['final_price']}₽</b>\n\n"
-+        "Реквизиты для оплаты:\n"
-+        f"{cards_text}",
-+        reply_markup=kb,
-+    )
-+
-+
- def process_player_id(message):
-     st = user_buy_state.get(message.from_user.id)
--    if not st:
-+    if not st or st.get("flow") != "uc":
-         return bot.send_message(message.chat.id, "Сессия покупки не найдена. Нажмите «КУПИТЬ UC».")
- 
-     player_id = (message.text or "").strip()
-     if len(player_id) < 4:
-         bot.send_message(message.chat.id, "Игровой ID выглядит слишком коротким, попробуйте еще раз:")
-         return bot.register_next_step_handler(message, process_player_id)
- 
-     order_number = get_next_order_number()
-     with get_conn() as conn:
-         conn.execute(
-             """
-             INSERT INTO orders(order_number, user_id, username, player_id, uc_amount, price, status, created_at, promo_code, discount_percent)
-             VALUES(?,?,?,?,?,?,?,?,?,?)
-             """,
-             (
-                 order_number,
-                 message.from_user.id,
-                 message.from_user.username or message.from_user.first_name or "unknown",
-                 player_id,
-                 st["uc"],
-                 st["final_price"],
-                 "pending",
-                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
-                 st["promo_code"],
-                 st["discount"],
-             ),
-         )
-         conn.commit()
- 
-     cards_text = "\n".join([f"• {c['bank']}: <code>{c['number']}</code> ({c['holder']})" for c in CARDS])
-     kb = types.InlineKeyboardMarkup()
-     kb.add(types.InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_number}"))
-     kb.add(types.InlineKeyboardButton("❌ ОТМЕНА", callback_data=f"cancel_{order_number}"))
- 
-     bot.send_message(
-         message.chat.id,
-         "<b>Заказ создан</b>\n"
-         f"Номер: <code>{order_number}</code>\n"
-         f"Игровой ID: <code>{player_id}</code>\n"
-         f"UC: {st['uc']}\n"
-         f"К оплате: <b>{st['final_price']}₽</b>\n\n"
-         "Реквизиты для оплаты:\n"
--        f"{cards_text}\n\n"
--        "После оплаты нажмите кнопку ниже:",
-+        f"{cards_text}",
-         reply_markup=kb,
-     )
- 
- 
- @bot.callback_query_handler(func=lambda c: c.data.startswith("cancel_"))
- def process_cancel_order(call):
-     order_number = int(call.data.split("_")[1])
-+    with get_conn() as conn:
-+        conn.execute("UPDATE orders SET status='canceled' WHERE order_number=? AND user_id=?", (order_number, call.from_user.id))
-+        conn.commit()
-+    bot.answer_callback_query(call.id, "Заказ отменен")
-+    bot.send_message(call.message.chat.id, "❌ Заказ отменен.")
-+
-+
-+@bot.callback_query_handler(func=lambda c: c.data.startswith("pop_cancel_"))
-+def process_pop_cancel_order(call):
-+    order_number = int(call.data.split("_")[-1])
-     with get_conn() as conn:
-         conn.execute(
--            "UPDATE orders SET status='canceled' WHERE order_number=? AND user_id=?",
-+            "UPDATE popularity_orders SET status='canceled' WHERE order_number=? AND user_id=?",
-             (order_number, call.from_user.id),
-         )
-         conn.commit()
-     bot.answer_callback_query(call.id, "Заказ отменен")
--    bot.send_message(call.message.chat.id, "❌ Заказ отменен. Вы можете создать новый.")
-+    bot.send_message(call.message.chat.id, "❌ Заказ на популярность отменен.")
- 
- 
- @bot.callback_query_handler(func=lambda c: c.data.startswith("paid_"))
- def process_paid_order(call):
-     order_number = int(call.data.split("_")[1])
-     with get_conn() as conn:
--        order = conn.execute(
--            "SELECT * FROM orders WHERE order_number=? AND user_id=?",
--            (order_number, call.from_user.id),
--        ).fetchone()
-+        order = conn.execute("SELECT * FROM orders WHERE order_number=? AND user_id=?", (order_number, call.from_user.id)).fetchone()
-         if not order:
-             return bot.answer_callback_query(call.id, "Заказ не найден", show_alert=True)
--        conn.execute(
--            "UPDATE orders SET status='processing' WHERE order_number=?",
--            (order_number,),
--        )
-+        conn.execute("UPDATE orders SET status='processing' WHERE order_number=?", (order_number,))
-         conn.commit()
- 
-     bot.answer_callback_query(call.id, "Заявка отправлена")
--    bot.send_message(call.message.chat.id, "✅ Заявка принята, ожидайте подтверждения администратора.")
--
-     kb = types.InlineKeyboardMarkup()
-     kb.add(types.InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"adm_ok_{order_number}"))
-     kb.add(types.InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data=f"adm_cancel_{order_number}"))
--
--    text = (
--        "<b>Новая заявка на пополнение</b>\n"
-+    bot.send_message(
-+        ADMIN_ID,
-+        "<b>Новая заявка на пополнение UC</b>\n"
-         f"Заказ: <code>{order['order_number']}</code>\n"
-         f"User ID: <code>{order['user_id']}</code>\n"
--        f"Username: @{order['username']}\n"
-         f"Player ID: <code>{order['player_id']}</code>\n"
-         f"UC: {order['uc_amount']}\n"
--        f"Сумма: {order['price']}₽\n"
--        f"Промо: {order['promo_code'] or '—'} ({order['discount_percent']}%)"
-+        f"Сумма: {order['price']}₽",
-+        reply_markup=kb,
-+    )
-+
-+
-+@bot.callback_query_handler(func=lambda c: c.data.startswith("pop_paid_"))
-+def process_pop_paid_order(call):
-+    order_number = int(call.data.split("_")[-1])
-+    with get_conn() as conn:
-+        order = conn.execute(
-+            "SELECT * FROM popularity_orders WHERE order_number=? AND user_id=?",
-+            (order_number, call.from_user.id),
-+        ).fetchone()
-+        if not order:
-+            return bot.answer_callback_query(call.id, "Заказ не найден", show_alert=True)
-+        conn.execute("UPDATE popularity_orders SET status='processing' WHERE order_number=?", (order_number,))
-+        conn.commit()
-+
-+    bot.answer_callback_query(call.id, "Заявка отправлена")
-+    kb = types.InlineKeyboardMarkup()
-+    kb.add(types.InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"adm_pop_ok_{order_number}"))
-+    kb.add(types.InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data=f"adm_pop_cancel_{order_number}"))
-+    bot.send_message(
-+        ADMIN_ID,
-+        "<b>Новая заявка на популярность</b>\n"
-+        f"Заказ: <code>{order['order_number']}</code>\n"
-+        f"User ID: <code>{order['user_id']}</code>\n"
-+        f"Пак: {order['pack_title']}\n"
-+        f"Ссылка: <code>{order['target_link']}</code>\n"
-+        f"Сумма: {order['price']}₽",
-+        reply_markup=kb,
-     )
--    bot.send_message(ADMIN_ID, text, reply_markup=kb)
- 
- 
--@bot.callback_query_handler(func=lambda c: c.data in {"admin_stats", "admin_promos", "admin_broadcast"})
-+@bot.callback_query_handler(func=lambda c: c.data in {"admin_stats", "admin_promos", "admin_broadcast", "admin_uc_prices", "admin_pop_packs"})
- def admin_menu_router(call):
-     if not is_admin(call.from_user.id):
-         return bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
- 
-     if call.data == "admin_stats":
-         with get_conn() as conn:
-             users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
--            orders_all = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
--            completed = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE status='completed'").fetchone()["c"]
--            processing = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE status='processing'").fetchone()["c"]
--            revenue = conn.execute("SELECT COALESCE(SUM(price),0) AS s FROM orders WHERE status='completed'").fetchone()["s"]
-+            uc_completed = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE status='completed'").fetchone()["c"]
-+            pop_completed = conn.execute("SELECT COUNT(*) AS c FROM popularity_orders WHERE status='completed'").fetchone()["c"]
-+            uc_revenue = conn.execute("SELECT COALESCE(SUM(price),0) AS s FROM orders WHERE status='completed'").fetchone()["s"]
-+            pop_revenue = conn.execute("SELECT COALESCE(SUM(price),0) AS s FROM popularity_orders WHERE status='completed'").fetchone()["s"]
-             sold_uc = conn.execute("SELECT COALESCE(SUM(uc_amount),0) AS s FROM orders WHERE status='completed'").fetchone()["s"]
--            promos = conn.execute("SELECT COUNT(*) AS c FROM promocodes").fetchone()["c"]
- 
--        text = (
-+        bot.answer_callback_query(call.id)
-+        return bot.send_message(
-+            call.message.chat.id,
-             "<b>Статистика</b>\n"
-             f"Пользователей: {users}\n"
--            f"Заказов всего: {orders_all}\n"
--            f"Выполнено: {completed}\n"
--            f"В обработке: {processing}\n"
--            f"Заработано: {revenue}₽\n"
-+            f"Заказов UC выполнено: {uc_completed}\n"
-+            f"Заказов популярности выполнено: {pop_completed}\n"
-             f"Продано UC: {sold_uc}\n"
--            f"Промокодов: {promos}"
-+            f"Заработано на UC: {uc_revenue}₽\n"
-+            f"Заработано на популярности: {pop_revenue}₽\n"
-+            f"Итого заработано: {uc_revenue + pop_revenue}₽",
-         )
-+
-+    if call.data == "admin_uc_prices":
-+        with get_conn() as conn:
-+            rows = conn.execute("SELECT uc_amount, price FROM uc_packs ORDER BY uc_amount").fetchall()
-+        txt = "<b>Текущие цены UC</b>\n"
-+        for r in rows:
-+            txt += f"• {r['uc_amount']} UC — {r['price']}₽\n"
-+        txt += "\nОтправьте в формате: <code>UC ЦЕНА</code>\nПример: <code>660 950</code>"
-+        admin_state[call.from_user.id] = {"mode": "uc_price_wait"}
-         bot.answer_callback_query(call.id)
--        return bot.send_message(call.message.chat.id, text)
-+        return bot.send_message(call.message.chat.id, txt)
- 
-     if call.data == "admin_promos":
-         kb = types.InlineKeyboardMarkup()
-         kb.add(types.InlineKeyboardButton("Создать", callback_data="promo_create"))
-         kb.add(types.InlineKeyboardButton("Список", callback_data="promo_list"))
-         bot.answer_callback_query(call.id)
-         return bot.send_message(call.message.chat.id, "Управление промокодами:", reply_markup=kb)
- 
-+    if call.data == "admin_pop_packs":
-+        admin_state[call.from_user.id] = {"mode": "pop_pack_create_title"}
-+        bot.answer_callback_query(call.id)
-+        return bot.send_message(
-+            call.message.chat.id,
-+            "Создание пака популярности.\nВведите название (пример: 2000 подписчиков):",
-+        )
-+
-     if call.data == "admin_broadcast":
-         admin_state[call.from_user.id] = {"mode": "broadcast_wait"}
-         bot.answer_callback_query(call.id)
-         return bot.send_message(call.message.chat.id, "Введите текст рассылки одним сообщением:")
- 
- 
- @bot.callback_query_handler(func=lambda c: c.data in {"promo_create", "promo_list"})
- def admin_promos_router(call):
-     if not is_admin(call.from_user.id):
-         return bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
- 
-     if call.data == "promo_list":
-         with get_conn() as conn:
--            rows = conn.execute(
--                "SELECT * FROM promocodes ORDER BY id DESC"
--            ).fetchall()
-+            rows = conn.execute("SELECT * FROM promocodes ORDER BY id DESC").fetchall()
-         if not rows:
-             return bot.send_message(call.message.chat.id, "Список промокодов пуст.")
-         text = "<b>Промокоды:</b>\n"
-         for r in rows:
-             status = "активен" if r["is_active"] == 1 else "неактивен"
-             limit = "безлимит" if r["usage_limit"] == 0 else f"{r['used_count']}/{r['usage_limit']}"
-             exp = r["expires_at"] or "бессрочно"
-             text += f"\n• <code>{r['code']}</code> — {r['discount']}% | {limit} | до {exp} | {status}"
-         return bot.send_message(call.message.chat.id, text)
- 
-     admin_state[call.from_user.id] = {"mode": "promo_create_code"}
-     bot.send_message(call.message.chat.id, "Введите текст промокода:")
- 
- 
- @bot.message_handler(func=lambda m: is_admin(m.from_user.id) and m.from_user.id in admin_state)
- def admin_step_handler(message):
-     st = admin_state.get(message.from_user.id, {})
-     mode = st.get("mode")
- 
-     if mode == "broadcast_wait":
-         text = message.text or ""
-         sent = 0
-         failed = 0
-         with get_conn() as conn:
-             users = conn.execute("SELECT user_id FROM users").fetchall()
-         for u in users:
-             try:
-                 bot.send_message(u["user_id"], text)
-                 sent += 1
-             except Exception:
-                 failed += 1
-         admin_state.pop(message.from_user.id, None)
-         return bot.send_message(message.chat.id, f"Рассылка завершена. Отправлено: {sent}, ошибок: {failed}")
- 
-+    if mode == "uc_price_wait":
-+        parts = (message.text or "").strip().split()
-+        if len(parts) != 2:
-+            return bot.send_message(message.chat.id, "Формат: UC ЦЕНА")
-+        try:
-+            uc_amount = int(parts[0])
-+            price = int(parts[1])
-+            if uc_amount <= 0 or price <= 0:
-+                raise ValueError
-+        except ValueError:
-+            return bot.send_message(message.chat.id, "Оба значения должны быть положительными числами.")
-+
-+        with get_conn() as conn:
-+            conn.execute(
-+                "INSERT INTO uc_packs(uc_amount, price, is_active) VALUES(?,?,1) "
-+                "ON CONFLICT(uc_amount) DO UPDATE SET price=excluded.price, is_active=1",
-+                (uc_amount, price),
-+            )
-+            conn.commit()
-+        admin_state.pop(message.from_user.id, None)
-+        return bot.send_message(message.chat.id, f"✅ Цена обновлена: {uc_amount} UC = {price}₽")
-+
-+    if mode == "pop_pack_create_title":
-+        st["title"] = (message.text or "").strip()
-+        st["mode"] = "pop_pack_create_amount"
-+        admin_state[message.from_user.id] = st
-+        return bot.send_message(message.chat.id, "Введите количество (число):")
-+
-+    if mode == "pop_pack_create_amount":
-+        try:
-+            amount = int((message.text or "").strip())
-+            if amount <= 0:
-+                raise ValueError
-+        except ValueError:
-+            return bot.send_message(message.chat.id, "Введите корректное число больше 0")
-+        st["amount"] = amount
-+        st["mode"] = "pop_pack_create_price"
-+        admin_state[message.from_user.id] = st
-+        return bot.send_message(message.chat.id, "Введите цену в рублях:")
-+
-+    if mode == "pop_pack_create_price":
-+        try:
-+            price = int((message.text or "").strip())
-+            if price <= 0:
-+                raise ValueError
-+        except ValueError:
-+            return bot.send_message(message.chat.id, "Введите корректную цену.")
-+
-+        with get_conn() as conn:
-+            conn.execute(
-+                "INSERT INTO popularity_packs(title, amount, price, is_active, created_at) VALUES(?,?,?,?,?)",
-+                (st["title"], st["amount"], price, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
-+            )
-+            conn.commit()
-+        admin_state.pop(message.from_user.id, None)
-+        return bot.send_message(message.chat.id, f"✅ Пак популярности добавлен: {st['title']} — {price}₽")
-+
-     if mode == "promo_create_code":
-         st["code"] = (message.text or "").strip().upper()
-         st["mode"] = "promo_create_discount"
-         admin_state[message.from_user.id] = st
-         return bot.send_message(message.chat.id, "Введите скидку в % (например, 10):")
- 
-     if mode == "promo_create_discount":
-         try:
-             discount = int((message.text or "0").strip())
-             if discount <= 0 or discount >= 100:
-                 raise ValueError
-         except ValueError:
-             return bot.send_message(message.chat.id, "Введите число 1..99")
-         st["discount"] = discount
-         st["mode"] = "promo_create_limit"
-         admin_state[message.from_user.id] = st
-         return bot.send_message(message.chat.id, "Введите лимит использований (0 = безлимит):")
- 
-     if mode == "promo_create_limit":
-         try:
-             limit = int((message.text or "0").strip())
-             if limit < 0:
-                 raise ValueError
-         except ValueError:
-             return bot.send_message(message.chat.id, "Введите корректное число (0 или больше)")
-@@ -575,96 +817,96 @@ def admin_step_handler(message):
-             expires_at = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
- 
-         with get_conn() as conn:
-             try:
-                 conn.execute(
-                     """
-                     INSERT INTO promocodes(code, discount, usage_limit, used_count, expires_at, is_active, created_at)
-                     VALUES(?,?,?,?,?,?,?)
-                     """,
-                     (
-                         st["code"],
-                         st["discount"],
-                         st["usage_limit"],
-                         0,
-                         expires_at,
-                         1,
-                         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
-                     ),
-                 )
-                 conn.commit()
-             except sqlite3.IntegrityError:
-                 admin_state.pop(message.from_user.id, None)
-                 return bot.send_message(message.chat.id, "Промокод с таким кодом уже существует.")
- 
-         admin_state.pop(message.from_user.id, None)
--        return bot.send_message(
--            message.chat.id,
--            f"✅ Промокод создан: {st['code']} ({st['discount']}%)",
--        )
-+        return bot.send_message(message.chat.id, f"✅ Промокод создан: {st['code']} ({st['discount']}%)")
- 
- 
- @bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ok_") or c.data.startswith("adm_cancel_"))
- def admin_order_actions(call):
-     if not is_admin(call.from_user.id):
-         return bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
- 
-     is_ok = call.data.startswith("adm_ok_")
-     order_number = int(call.data.split("_")[-1])
- 
-     with get_conn() as conn:
-         order = conn.execute("SELECT * FROM orders WHERE order_number=?", (order_number,)).fetchone()
-         if not order:
-             return bot.answer_callback_query(call.id, "Заказ не найден", show_alert=True)
- 
-+        if is_ok:
-+            conn.execute("UPDATE orders SET status='completed', completed_at=? WHERE order_number=?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_number))
-+            conn.execute("UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1 WHERE user_id=?", (order["uc_amount"], order["user_id"]))
-+            conn.commit()
-+            bot.send_message(order["user_id"], f"✅ Заказ #{order_number} выполнен! Начислено: {order['uc_amount']} UC")
-+            bot.answer_callback_query(call.id, "Подтверждено")
-+        else:
-+            conn.execute("UPDATE orders SET status='canceled' WHERE order_number=?", (order_number,))
-+            conn.commit()
-+            bot.send_message(order["user_id"], f"❌ Заказ #{order_number} отменен. Напишите в поддержку: @{SUPPORT_USERNAME}")
-+            bot.answer_callback_query(call.id, "Отменено")
-+
-+
-+@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_pop_ok_") or c.data.startswith("adm_pop_cancel_"))
-+def admin_pop_order_actions(call):
-+    if not is_admin(call.from_user.id):
-+        return bot.answer_callback_query(call.id, "Нет доступа", show_alert=True)
-+
-+    is_ok = call.data.startswith("adm_pop_ok_")
-+    order_number = int(call.data.split("_")[-1])
-+
-+    with get_conn() as conn:
-+        order = conn.execute("SELECT * FROM popularity_orders WHERE order_number=?", (order_number,)).fetchone()
-+        if not order:
-+            return bot.answer_callback_query(call.id, "Заказ не найден", show_alert=True)
-+
-         if is_ok:
-             conn.execute(
--                "UPDATE orders SET status='completed', completed_at=? WHERE order_number=?",
-+                "UPDATE popularity_orders SET status='completed', completed_at=? WHERE order_number=?",
-                 (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_number),
-             )
--            conn.execute(
--                "UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1 WHERE user_id=?",
--                (order["uc_amount"], order["user_id"]),
--            )
-             conn.commit()
--
--            kb = types.InlineKeyboardMarkup()
--            kb.add(types.InlineKeyboardButton("Оставить отзыв", url=REVIEWS_CHANNEL))
--            bot.send_message(
--                order["user_id"],
--                f"✅ Ваш заказ #{order_number} выполнен!\nНачислено: {order['uc_amount']} UC",
--                reply_markup=kb,
--            )
-+            bot.send_message(order["user_id"], f"✅ Заказ на популярность #{order_number} выполнен!")
-             bot.answer_callback_query(call.id, "Подтверждено")
--            bot.send_message(call.message.chat.id, f"Заказ #{order_number} подтвержден и выдан.")
-         else:
--            conn.execute(
--                "UPDATE orders SET status='canceled' WHERE order_number=?",
--                (order_number,),
--            )
-+            conn.execute("UPDATE popularity_orders SET status='canceled' WHERE order_number=?", (order_number,))
-             conn.commit()
--
--            kb = types.InlineKeyboardMarkup()
--            kb.add(types.InlineKeyboardButton("Связаться с поддержкой", url=f"https://t.me/{SUPPORT_USERNAME}"))
--            bot.send_message(
--                order["user_id"],
--                f"❌ Ваш заказ #{order_number} отменен. Если нужна помощь — напишите в поддержку.",
--                reply_markup=kb,
--            )
-+            bot.send_message(order["user_id"], f"❌ Заказ #{order_number} отменен. Напишите в поддержку: @{SUPPORT_USERNAME}")
-             bot.answer_callback_query(call.id, "Отменено")
--            bot.send_message(call.message.chat.id, f"Заказ #{order_number} отменен.")
- 
- 
- @bot.message_handler(func=lambda _: True)
- def fallback(message):
-     bot.send_message(message.chat.id, "Используйте меню кнопок ниже 👇", reply_markup=main_keyboard())
- 
- 
- if __name__ == "__main__":
-     init_db()
-     print("Bot started")
-     while True:
-         try:
-             bot.polling(non_stop=True, timeout=60, long_polling_timeout=30)
-         except Exception as e:
-             print(f"Polling error: {e}")
-             time.sleep(5)
+import os
+import sqlite3
+from datetime import datetime
+from typing import Dict, Optional
+
+import telebot
+from telebot import types
+
+# =====================
+# CONFIG (Bothost-ready)
+# =====================
+TOKEN = os.getenv("BOT_TOKEN", "")
+ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
+SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "support")
+REVIEWS_CHANNEL = os.getenv("REVIEWS_CHANNEL", "https://t.me/example")
+DB_PATH = os.getenv("DB_PATH", "bot.db")
+
+CARDS = [
+    {"bank": "Сбер", "number": "2202 1234 5678 9012", "holder": "IVAN IVANOV"},
+    {"bank": "Т-Банк", "number": "2200 9876 5432 1098", "holder": "IVAN IVANOV"},
+]
+
+DEFAULT_UC_PACKS = {
+    60: 99,
+    325: 449,
+    660: 899,
+    1800: 2299,
+    3850: 4499,
+}
+
+bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
+user_state: Dict[int, dict] = {}
+
+
+def get_conn():
+    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
+    conn.row_factory = sqlite3.Row
+    return conn
+
+
+def init_db():
+    with get_conn() as conn:
+        conn.execute(
+            """
+            CREATE TABLE IF NOT EXISTS users (
+                user_id INTEGER PRIMARY KEY,
+                username TEXT,
+                reg_date TEXT,
+                total_orders INTEGER DEFAULT 0,
+                total_spent INTEGER DEFAULT 0
+            )
+            """
+        )
+        conn.execute(
+            """
+            CREATE TABLE IF NOT EXISTS uc_packs (
+                uc_amount INTEGER PRIMARY KEY,
+                price INTEGER NOT NULL,
+                is_active INTEGER DEFAULT 1
+            )
+            """
+        )
+        conn.execute(
+            """
+            CREATE TABLE IF NOT EXISTS orders (
+                id INTEGER PRIMARY KEY AUTOINCREMENT,
+                order_number INTEGER UNIQUE,
+                user_id INTEGER,
+                username TEXT,
+                player_id TEXT,
+                uc_amount INTEGER,
+                price INTEGER,
+                payment_method TEXT,
+                receipt_file_id TEXT,
+                status TEXT DEFAULT 'pending',
+                created_at TEXT,
+                completed_at TEXT
+            )
+            """
+        )
+
+        for uc, price in DEFAULT_UC_PACKS.items():
+            conn.execute(
+                "INSERT OR IGNORE INTO uc_packs(uc_amount, price, is_active) VALUES(?,?,1)",
+                (uc, price),
+            )
+        conn.commit()
+
+
+def ensure_user(message: types.Message):
+    with get_conn() as conn:
+        conn.execute(
+            """
+            INSERT OR IGNORE INTO users(user_id, username, reg_date)
+            VALUES(?,?,?)
+            """,
+            (
+                message.from_user.id,
+                message.from_user.username or "",
+                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
+            ),
+        )
+        conn.commit()
+
+
+def is_admin(user_id: int) -> bool:
+    return ADMIN_ID and user_id == ADMIN_ID
+
+
+def get_next_order_number() -> int:
+    with get_conn() as conn:
+        row = conn.execute("SELECT MAX(order_number) AS mx FROM orders").fetchone()
+    return (row["mx"] or 0) + 1
+
+
+def main_kb(user_id: int):
+    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
+    kb.row("🛒 Купить UC", "📦 Мои заказы")
+    kb.row("💬 Поддержка", "⭐ Отзывы")
+    if is_admin(user_id):
+        kb.row("🧰 Админ-панель")
+    return kb
+
+
+def admin_kb():
+    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
+    kb.row("📊 Статистика", "⏳ Ожидают оплаты")
+    kb.row("✅ Завершить заказ", "❌ Отклонить заказ")
+    kb.row("💲 Добавить пакет UC", "🧾 Список пакетов")
+    kb.row("🔙 В меню")
+    return kb
+
+
+def build_uc_inline_kb():
+    kb = types.InlineKeyboardMarkup()
+    with get_conn() as conn:
+        rows = conn.execute(
+            "SELECT uc_amount, price FROM uc_packs WHERE is_active=1 ORDER BY uc_amount"
+        ).fetchall()
+    for r in rows:
+        kb.add(
+            types.InlineKeyboardButton(
+                text=f"{r['uc_amount']} UC — {r['price']} ₽",
+                callback_data=f"pick_uc:{r['uc_amount']}",
+            )
+        )
+    return kb
+
+
+@bot.message_handler(commands=["start"])
+def cmd_start(message: types.Message):
+    ensure_user(message)
+    text = (
+        "👋 <b>Добро пожаловать в PUBG UC BOT</b>\n\n"
+        "Здесь можно оформить пополнение UC быстро и безопасно.\n"
+        "Для старта нажмите <b>🛒 Купить UC</b>."
+    )
+    bot.send_message(message.chat.id, text, reply_markup=main_kb(message.from_user.id))
+
+
+@bot.message_handler(func=lambda m: m.text == "🔙 В меню")
+def back_menu(message: types.Message):
+    bot.send_message(message.chat.id, "Вы вернулись в меню.", reply_markup=main_kb(message.from_user.id))
+
+
+@bot.message_handler(func=lambda m: m.text == "🛒 Купить UC")
+def buy_uc(message: types.Message):
+    ensure_user(message)
+    bot.send_message(
+        message.chat.id,
+        "Выберите пакет UC:",
+        reply_markup=build_uc_inline_kb(),
+    )
+
+
+@bot.callback_query_handler(func=lambda c: c.data.startswith("pick_uc:"))
+def pick_uc(call: types.CallbackQuery):
+    uc_amount = int(call.data.split(":")[1])
+    with get_conn() as conn:
+        row = conn.execute(
+            "SELECT uc_amount, price FROM uc_packs WHERE uc_amount=? AND is_active=1",
+            (uc_amount,),
+        ).fetchone()
+    if not row:
+        bot.answer_callback_query(call.id, "Пакет недоступен", show_alert=True)
+        return
+
+    user_state[call.from_user.id] = {
+        "step": "wait_player_id",
+        "uc_amount": row["uc_amount"],
+        "price": row["price"],
+    }
+    bot.answer_callback_query(call.id)
+    bot.send_message(
+        call.message.chat.id,
+        (
+            f"Вы выбрали <b>{row['uc_amount']} UC</b> за <b>{row['price']} ₽</b>.\n"
+            "Отправьте ваш <b>Player ID</b> PUBG (только цифры)."
+        ),
+    )
+
+
+@bot.message_handler(func=lambda m: m.text == "📦 Мои заказы")
+def my_orders(message: types.Message):
+    with get_conn() as conn:
+        rows = conn.execute(
+            """
+            SELECT order_number, uc_amount, price, status, created_at
+            FROM orders
+            WHERE user_id=?
+            ORDER BY id DESC
+            LIMIT 10
+            """,
+            (message.from_user.id,),
+        ).fetchall()
+    if not rows:
+        bot.send_message(message.chat.id, "У вас пока нет заказов.")
+        return
+
+    status_map = {
+        "pending": "⏳ Ожидает оплаты",
+        "paid": "💸 Оплачен, в обработке",
+        "completed": "✅ Выполнен",
+        "rejected": "❌ Отклонён",
+    }
+    lines = ["<b>Ваши последние заказы:</b>"]
+    for r in rows:
+        lines.append(
+            f"№{r['order_number']} | {r['uc_amount']} UC | {r['price']} ₽ | {status_map.get(r['status'], r['status'])}"
+        )
+    bot.send_message(message.chat.id, "\n".join(lines))
+
+
+@bot.message_handler(func=lambda m: m.text == "💬 Поддержка")
+def support(message: types.Message):
+    bot.send_message(message.chat.id, f"Напишите в поддержку: @{SUPPORT_USERNAME}")
+
+
+@bot.message_handler(func=lambda m: m.text == "⭐ Отзывы")
+def reviews(message: types.Message):
+    bot.send_message(message.chat.id, f"Отзывы клиентов: {REVIEWS_CHANNEL}")
+
+
+@bot.message_handler(func=lambda m: m.text == "🧰 Админ-панель")
+def admin_panel(message: types.Message):
+    if not is_admin(message.from_user.id):
+        return
+    bot.send_message(message.chat.id, "Админ-панель открыта", reply_markup=admin_kb())
+
+
+@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
+def admin_stats(message: types.Message):
+    if not is_admin(message.from_user.id):
+        return
+    with get_conn() as conn:
+        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
+        orders = conn.execute("SELECT COUNT(*) AS c FROM orders").fetchone()["c"]
+        pending = conn.execute("SELECT COUNT(*) AS c FROM orders WHERE status='pending'").fetchone()["c"]
+        revenue = conn.execute("SELECT COALESCE(SUM(price),0) AS s FROM orders WHERE status='completed'").fetchone()["s"]
+    bot.send_message(
+        message.chat.id,
+        (
+            "<b>Статистика бота</b>\n"
+            f"Пользователей: <b>{users}</b>\n"
+            f"Заказов: <b>{orders}</b>\n"
+            f"Ожидают оплаты: <b>{pending}</b>\n"
+            f"Подтверждённая выручка: <b>{revenue} ₽</b>"
+        ),
+    )
+
+
+@bot.message_handler(func=lambda m: m.text == "⏳ Ожидают оплаты")
+def admin_pending(message: types.Message):
+    if not is_admin(message.from_user.id):
+        return
+    with get_conn() as conn:
+        rows = conn.execute(
+            """
+            SELECT order_number, username, uc_amount, price, status
+            FROM orders
+            WHERE status IN ('pending', 'paid')
+            ORDER BY id DESC
+            LIMIT 20
+            """
+        ).fetchall()
+    if not rows:
+        bot.send_message(message.chat.id, "Нет заказов в ожидании.")
+        return
+    text = ["<b>Ожидающие заказы:</b>"]
+    for r in rows:
+        uname = f"@{r['username']}" if r["username"] else "без username"
+        text.append(f"№{r['order_number']} | {uname} | {r['uc_amount']} UC | {r['price']} ₽ | {r['status']}")
+    bot.send_message(message.chat.id, "\n".join(text))
+
+
+@bot.message_handler(func=lambda m: m.text in ["✅ Завершить заказ", "❌ Отклонить заказ"])
+def admin_order_action(message: types.Message):
+    if not is_admin(message.from_user.id):
+        return
+    mode = "complete" if message.text.startswith("✅") else "reject"
+    user_state[message.from_user.id] = {"step": "admin_wait_order", "mode": mode}
+    bot.send_message(message.chat.id, "Введите номер заказа (только число):")
+
+
+@bot.message_handler(func=lambda m: m.text == "💲 Добавить пакет UC")
+def admin_add_pack(message: types.Message):
+    if not is_admin(message.from_user.id):
+        return
+    user_state[message.from_user.id] = {"step": "admin_add_pack"}
+    bot.send_message(message.chat.id, "Введите пакет в формате: UC ЦЕНА\nПример: 810 1099")
+
+
+@bot.message_handler(func=lambda m: m.text == "🧾 Список пакетов")
+def admin_list_packs(message: types.Message):
+    if not is_admin(message.from_user.id):
+        return
+    with get_conn() as conn:
+        rows = conn.execute(
+            "SELECT uc_amount, price, is_active FROM uc_packs ORDER BY uc_amount"
+        ).fetchall()
+    lines = ["<b>Пакеты UC:</b>"]
+    for r in rows:
+        flag = "✅" if r["is_active"] else "🚫"
+        lines.append(f"{flag} {r['uc_amount']} UC — {r['price']} ₽")
+    bot.send_message(message.chat.id, "\n".join(lines))
+
+
+@bot.message_handler(content_types=["photo"])
+def handle_photo(message: types.Message):
+    state = user_state.get(message.from_user.id)
+    if not state or state.get("step") != "wait_receipt":
+        return
+
+    receipt_file_id = message.photo[-1].file_id
+    order_number = get_next_order_number()
+
+    with get_conn() as conn:
+        conn.execute(
+            """
+            INSERT INTO orders(
+                order_number, user_id, username, player_id, uc_amount, price,
+                payment_method, receipt_file_id, status, created_at
+            ) VALUES(?,?,?,?,?,?,?,?,?,?)
+            """,
+            (
+                order_number,
+                message.from_user.id,
+                message.from_user.username or "",
+                state["player_id"],
+                state["uc_amount"],
+                state["price"],
+                state["payment_method"],
+                receipt_file_id,
+                "paid",
+                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
+            ),
+        )
+        conn.execute(
+            "UPDATE users SET total_orders=total_orders+1 WHERE user_id=?",
+            (message.from_user.id,),
+        )
+        conn.commit()
+
+    admin_msg = (
+        "💸 <b>Новая оплата</b>\n"
+        f"Заказ №{order_number}\n"
+        f"Пользователь: @{message.from_user.username or 'без username'} ({message.from_user.id})\n"
+        f"Player ID: <code>{state['player_id']}</code>\n"
+        f"Пакет: {state['uc_amount']} UC\n"
+        f"Сумма: {state['price']} ₽"
+    )
+
+    if ADMIN_ID:
+        bot.send_photo(ADMIN_ID, receipt_file_id, caption=admin_msg)
+
+    bot.send_message(
+        message.chat.id,
+        f"✅ Чек получен! Заказ №{order_number} передан на обработку.",
+        reply_markup=main_kb(message.from_user.id),
+    )
+    user_state.pop(message.from_user.id, None)
+
+
+@bot.message_handler(func=lambda m: True)
+def text_router(message: types.Message):
+    state = user_state.get(message.from_user.id)
+    if not state:
+        return
+
+    if state.get("step") == "wait_player_id":
+        player_id = "".join(ch for ch in message.text if ch.isdigit())
+        if len(player_id) < 6:
+            bot.send_message(message.chat.id, "Player ID выглядит некорректно. Введите ещё раз.")
+            return
+        state["player_id"] = player_id
+        state["step"] = "wait_payment_method"
+
+        kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
+        for c in CARDS:
+            kb.add(f"{c['bank']} • {c['number']}")
+        kb.add("🔙 В меню")
+
+        cards_text = "\n".join(
+            [f"• <b>{c['bank']}</b>: <code>{c['number']}</code> ({c['holder']})" for c in CARDS]
+        )
+        bot.send_message(
+            message.chat.id,
+            (
+                f"К оплате: <b>{state['price']} ₽</b> за <b>{state['uc_amount']} UC</b>.\n"
+                "Выберите карту для оплаты или скопируйте реквизиты ниже:\n\n"
+                f"{cards_text}\n\n"
+                "После оплаты отправьте <b>фото чека</b>."
+            ),
+            reply_markup=kb,
+        )
+        return
+
+    if state.get("step") == "wait_payment_method":
+        if message.text == "🔙 В меню":
+            user_state.pop(message.from_user.id, None)
+            bot.send_message(message.chat.id, "Оформление отменено.", reply_markup=main_kb(message.from_user.id))
+            return
+
+        state["payment_method"] = message.text
+        state["step"] = "wait_receipt"
+        bot.send_message(
+            message.chat.id,
+            "Отлично. Теперь отправьте <b>фото чека</b> одним сообщением.",
+        )
+        return
+
+    if state.get("step") == "admin_wait_order" and is_admin(message.from_user.id):
+        if not message.text.isdigit():
+            bot.send_message(message.chat.id, "Нужно ввести только номер заказа цифрами.")
+            return
+        number = int(message.text)
+        new_status = "completed" if state["mode"] == "complete" else "rejected"
+
+        with get_conn() as conn:
+            row = conn.execute(
+                "SELECT id, user_id FROM orders WHERE order_number=?",
+                (number,),
+            ).fetchone()
+            if not row:
+                bot.send_message(message.chat.id, "Заказ не найден.")
+                return
+
+            conn.execute(
+                "UPDATE orders SET status=?, completed_at=? WHERE order_number=?",
+                (new_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), number),
+            )
+            if new_status == "completed":
+                price = conn.execute(
+                    "SELECT price FROM orders WHERE order_number=?", (number,)
+                ).fetchone()["price"]
+                conn.execute(
+                    "UPDATE users SET total_spent=total_spent+? WHERE user_id=?",
+                    (price, row["user_id"]),
+                )
+            conn.commit()
+
+        status_msg = "✅ выполнен" if new_status == "completed" else "❌ отклонён"
+        bot.send_message(message.chat.id, f"Заказ №{number} помечен как {status_msg}.")
+        try:
+            bot.send_message(row["user_id"], f"Ваш заказ №{number} {status_msg}.")
+        except Exception:
+            pass
+
+        user_state.pop(message.from_user.id, None)
+        return
+
+    if state.get("step") == "admin_add_pack" and is_admin(message.from_user.id):
+        parts = message.text.split()
+        if len(parts) != 2 or not all(p.isdigit() for p in parts):
+            bot.send_message(message.chat.id, "Неверный формат. Пример: 810 1099")
+            return
+        uc, price = map(int, parts)
+        with get_conn() as conn:
+            conn.execute(
+                "INSERT INTO uc_packs(uc_amount, price, is_active) VALUES(?,?,1) "
+                "ON CONFLICT(uc_amount) DO UPDATE SET price=excluded.price, is_active=1",
+                (uc, price),
+            )
+            conn.commit()
+        bot.send_message(message.chat.id, f"Пакет {uc} UC за {price} ₽ сохранён.")
+        user_state.pop(message.from_user.id, None)
+
+
+if __name__ == "__main__":
+    if not TOKEN:
+        raise RuntimeError("Укажите BOT_TOKEN в переменных окружения (Bothost -> Variables).")
+    init_db()
+    print("Bot started...")
+    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
