import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import time
import traceback

# ---------- НОВЫЙ ТОКЕН ----------
TOKEN = '8783525882:AAE0QrrgJUy_BBFZLAMZFAoIuZir0hHAj-8'
bot = telebot.TeleBot(TOKEN)

# ---------- НАСТРОЙКИ ----------
ADMIN_ID = 8052884471          # Твой ID (проверь через @userinfobot)
SUPPORT_USERNAME = 'Kurator111'
REVIEWS_CHANNEL = '+DpdNmcj9gAY2MThi'

CARDS = [
    {'bank': 'СБЕР', 'card': '2200 3394 8208 3478', 'recipient': 'Дмитрий'},
    {'bank': 'ВТБ', 'card': '2203 1647 7814 6419', 'recipient': 'Дмитрий'}
]

UC_PRICES = {
    60: 80,
    120: 160,
    180: 240,
    325: 400,
    385: 480,
    660: 800,
    720: 910,
    985: 1250,
    1320: 1700,
    1800: 1950,
    2460: 2800,
    3850: 4000,
    8100: 8200
}

# ---------- БАЗА ДАННЫХ ----------
def get_table_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [col[1] for col in cursor.fetchall()]

def add_column_if_not_exists(cursor, table, column, col_type, default=None):
    columns = get_table_columns(cursor, table)
    if column not in columns:
        try:
            if default is not None:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}")
            else:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            print(f"✅ Добавлен столбец {column} в таблицу {table}")
        except Exception as e:
            print(f"Ошибка добавления столбца {column}: {e}")

def init_db():
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  join_date TEXT,
                  total_uc INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_number INTEGER UNIQUE,
                  user_id INTEGER,
                  username TEXT,
                  player_id TEXT,
                  uc_amount INTEGER,
                  price INTEGER,
                  status TEXT,
                  created_at TEXT,
                  completed_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS promocodes
                 (code TEXT PRIMARY KEY,
                  discount INTEGER,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_promos
                 (user_id INTEGER,
                  promo_code TEXT,
                  discount INTEGER,
                  activated_at TEXT,
                  PRIMARY KEY (user_id, promo_code))''')

    add_column_if_not_exists(c, 'users', 'total_orders', 'INTEGER', '0')
    add_column_if_not_exists(c, 'orders', 'discount', 'INTEGER', '0')
    add_column_if_not_exists(c, 'orders', 'promocode', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'promocodes', 'max_uses', 'INTEGER', '0')
    add_column_if_not_exists(c, 'promocodes', 'used_count', 'INTEGER', '0')
    add_column_if_not_exists(c, 'promocodes', 'expires_at', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'promocodes', 'active', 'INTEGER', '1')

    conn.commit()
    conn.close()
    print("✅ База данных проверена/создана, миграция выполнена.")

def get_next_order_number():
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT MAX(order_number) FROM orders")
    max_num = c.fetchone()[0]
    conn.close()
    return (max_num or 0) + 1

def is_admin(user_id):
    return user_id == ADMIN_ID

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🛒 КУПИТЬ UC")
    btn2 = types.KeyboardButton("👤 МОЙ ПРОФИЛЬ")
    btn3 = types.KeyboardButton("🏆 ЛИДЕРЫ")
    btn4 = types.KeyboardButton("⭐️ ОТЗЫВЫ")
    btn5 = types.KeyboardButton("📞 ПОДДЕРЖКА")
    btn6 = types.KeyboardButton("🎟 ПРОМОКОД")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    first_name = message.from_user.first_name or "Игрок"

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO users 
                 (user_id, username, first_name, join_date, total_uc, total_orders) 
                 VALUES (?,?,?,?,?,?)""",
              (user_id, username, first_name, str(datetime.now()), 0, 0))
    conn.commit()
    conn.close()

    welcome_text = """
👋 <b>ДОБРО ПОЖАЛОВАТЬ В APEX UC SHOP!</b>

🔥 Лучший магазин UC для PUBG Mobile

✅ Наши преимущества:
• Быстрая доставка 5-15 минут
• 100% гарантия пополнения
• Круглосуточная поддержка
• Низкие цены

👇 Нажми КУПИТЬ UC чтобы начать
"""
    bot.send_message(message.chat.id, welcome_text, parse_mode='HTML', reply_markup=main_keyboard())

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора!")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_stats = types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    btn_promos = types.InlineKeyboardButton("🎟 Промокоды", callback_data="admin_promos")
    btn_mailing = types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_mailing")
    markup.add(btn_stats, btn_promos, btn_mailing)

    bot.send_message(message.chat.id, "👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    action = call.data.split('_')[1]

    if action == "stats":
        show_admin_stats(call)
    elif action == "promos":
        promos_menu(call)
    elif action == "mailing":
        start_mailing(call)
    elif action == "back":
        admin_back(call)

def show_admin_stats(call):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    completed_orders = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = c.fetchone()[0]

    c.execute("SELECT SUM(price) FROM orders WHERE status = 'completed'")
    total_earned = c.fetchone()[0] or 0

    c.execute("SELECT SUM(uc_amount) FROM orders WHERE status = 'completed'")
    total_uc_sold = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM promocodes")
    total_promos = c.fetchone()[0]

    conn.close()

    text = f"""
📊 <b>СТАТИСТИКА</b>

👥 Пользователей: {total_users}
📦 Всего заказов: {total_orders}
✅ Выполнено: {completed_orders}
⏳ В обработке: {pending_orders}
💰 Заработано: {total_earned:,} ₽
🎮 Продано UC: {total_uc_sold}
🎟 Промокодов: {total_promos}
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=text, parse_mode='HTML', reply_markup=markup)

def promos_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_create = types.InlineKeyboardButton("➕ Создать", callback_data="promo_create")
    btn_list = types.InlineKeyboardButton("📋 Список", callback_data="promo_list")
    btn_delete = types.InlineKeyboardButton("🗑 Удалить", callback_data="promo_delete")
    btn_back = types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back")
    markup.add(btn_create, btn_list)
    markup.add(btn_delete)
    markup.add(btn_back)

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="🎟 <b>Управление промокодами</b>", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "promo_create")
def promo_create_step1(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="🎟 <b>Создание промокода</b>\n\nВведите код промокода (например, SUMMER15):",
                          parse_mode='HTML')
    bot.register_next_step_handler(call.message, process_promo_code)

def process_promo_code(message):
    if not is_admin(message.from_user.id):
        return
    code = message.text.upper().strip()
    if not code:
        bot.send_message(message.chat.id, "❌ Код не может быть пустым.")
        return

    bot.send_message(message.chat.id, f"Код: {code}\nТеперь введите размер скидки (число от 1 до 100):")
    bot.register_next_step_handler(message, lambda m: process_promo_discount(m, code))

def process_promo_discount(message, code):
    if not is_admin(message.from_user.id):
        return
    try:
        discount = int(message.text)
        if discount < 1 or discount > 100:
            raise ValueError
    except:
        bot.send_message(message.chat.id, "❌ Введите целое число от 1 до 100.")
        return

    bot.send_message(message.chat.id, "Введите максимальное количество использований (0 - безлимит):")
    bot.register_next_step_handler(message, lambda m: process_promo_uses(m, code, discount))

def process_promo_uses(message, code, discount):
    if not is_admin(message.from_user.id):
        return
    try:
        max_uses = int(message.text)
        if max_uses < 0:
            raise ValueError
    except:
        bot.send_message(message.chat.id, "❌ Введите целое число (0 - безлимит).")
        return

    bot.send_message(message.chat.id, "Введите срок действия в днях (0 - бессрочно):")
    bot.register_next_step_handler(message, lambda m: process_promo_expiry(m, code, discount, max_uses))

def process_promo_expiry(message, code, discount, max_uses):
    if not is_admin(message.from_user.id):
        return
    try:
        days = int(message.text)
        if days < 0:
            raise ValueError
    except:
        bot.send_message(message.chat.id, "❌ Введите целое число (0 - бессрочно).")
        return

    expires_at = None
    if days > 0:
        expires_at = str(datetime.now() + timedelta(days=days))

    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"promo_save:{code}:{discount}:{max_uses}:{expires_at or 'None'}")
    btn_no = types.InlineKeyboardButton("❌ Отмена", callback_data="promo_cancel")
    markup.add(btn_yes, btn_no)

    expiry_text = "бессрочно" if not expires_at else f"до {expires_at[:10]}"
    uses_text = "безлимит" if max_uses == 0 else f"{max_uses} раз"
    bot.send_message(message.chat.id, f"🎟 Промокод: <b>{code}</b>\n💰 Скидка: <b>{discount}%</b>\n📊 Лимит: {uses_text}\n⏰ Срок: {expiry_text}\n\nСохранить?",
                     parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('promo_save:'))
def promo_save(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    parts = call.data.split(':')
    code = parts[1]
    discount = int(parts[2])
    max_uses = int(parts[3])
    expires_at = parts[4] if parts[4] != 'None' else None

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO promocodes (code, discount, max_uses, expires_at, created_at) VALUES (?,?,?,?,?)",
                  (code, discount, max_uses, expires_at, str(datetime.now())))
        conn.commit()
        bot.answer_callback_query(call.id, "✅ Промокод создан!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"✅ Промокод <b>{code}</b> успешно создан.", parse_mode='HTML')
    except sqlite3.IntegrityError:
        bot.answer_callback_query(call.id, "❌ Такой код уже существует!")
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data == "promo_cancel")
def promo_cancel(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="❌ Создание отменено.", reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promos")))

@bot.callback_query_handler(func=lambda call: call.data == "promo_list")
def promo_list(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT code, discount, max_uses, used_count, expires_at, active FROM promocodes ORDER BY created_at DESC")
    promos = c.fetchall()
    conn.close()

    if not promos:
        text = "🎟 Промокодов пока нет."
    else:
        text = "🎟 <b>Список промокодов:</b>\n\n"
        for p in promos:
            code, discount, max_uses, used, expires, active = p
            status = "✅ Активен" if active else "❌ Неактивен"
            expiry = "бессрочно" if not expires else f"до {expires[:10]}"
            limit = "безлимит" if max_uses == 0 else f"{max_uses}"
            text += f"• <b>{code}</b> — {discount}% (исп. {used}/{limit}) {expiry} {status}\n"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promos"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=text, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "promo_delete")
def promo_delete_menu(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT code, discount FROM promocodes ORDER BY created_at DESC")
    promos = c.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)

    if not promos:
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promos"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🗑 <b>Удаление промокода</b>\n\nПромокодов пока нет.",
            parse_mode='HTML',
            reply_markup=markup
        )
        return

    for code, discount in promos:
        markup.add(types.InlineKeyboardButton(f"{code} — {discount}%", callback_data=f"promo_delete_select:{code}"))
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promos"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🗑 <b>Удаление промокода</b>\n\nНажмите на промокод, чтобы удалить его:",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("promo_delete_select:"))
def promo_delete_select(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    code = call.data.split(':', 1)[1]

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    c.execute("DELETE FROM user_promos WHERE promo_code = ?", (code,))
    conn.commit()
    deleted = c.rowcount
    conn.close()

    if deleted:
        bot.answer_callback_query(call.id, "✅ Промокод удалён!")
    else:
        bot.answer_callback_query(call.id, "❌ Промокод не найден")

    promo_delete_menu(call)

def start_mailing(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="📢 <b>Рассылка</b>\n\nОтправьте сообщение для рассылки. Можно текст или фото с подписью:",
                          parse_mode='HTML')
    bot.register_next_step_handler(call.message, process_mailing_content)

def process_mailing_content(message):
    if not is_admin(message.from_user.id):
        return

    mailing_data = {
        'type': None,
        'text': None,
        'photo': None,
        'caption': None
    }

    if message.content_type == 'text':
        text = (message.text or '').strip()
        if not text:
            bot.send_message(message.chat.id, "❌ Текст не может быть пустым.")
            return
        mailing_data['type'] = 'text'
        mailing_data['text'] = text
    elif message.content_type == 'photo':
        caption = (message.caption or '').strip()
        mailing_data['type'] = 'photo'
        mailing_data['photo'] = message.photo[-1].file_id
        mailing_data['caption'] = caption
    else:
        bot.send_message(message.chat.id, "❌ Поддерживается только текст или фото с подписью.")
        return

    bot.mailing_data = mailing_data

    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Подтвердить", callback_data="mailing_confirm")
    btn_no = types.InlineKeyboardButton("❌ Отмена", callback_data="mailing_cancel")
    markup.add(btn_yes, btn_no)

    if mailing_data['type'] == 'photo':
        preview_caption = mailing_data['caption'] or "‎"
        bot.send_photo(
            message.chat.id,
            mailing_data['photo'],
            caption=f"📢 <b>Предпросмотр рассылки:</b>\n\n{preview_caption}",
            parse_mode='HTML',
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, f"📢 <b>Предпросмотр рассылки:</b>\n\n{mailing_data['text']}\n\nОтправить это сообщение всем пользователям?",
                         parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'mailing_confirm')
def mailing_confirm(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    mailing_data = getattr(bot, 'mailing_data', None)
    if not mailing_data:
        bot.answer_callback_query(call.id, "❌ Данные рассылки не найдены, начните заново.")
        return

    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                     caption="📢 <b>Рассылка начата...</b>", parse_mode='HTML')
        else:
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📢 <b>Рассылка начата...</b>", parse_mode='HTML')
    except:
        bot.send_message(call.message.chat.id, "📢 <b>Рассылка начата...</b>", parse_mode='HTML')

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()

    sent = 0
    errors = 0
    for (user_id,) in users:
        try:
            if mailing_data['type'] == 'photo':
                bot.send_photo(
                    user_id,
                    mailing_data['photo'],
                    caption=mailing_data['caption'] or None,
                    parse_mode='HTML'
                )
            else:
                bot.send_message(user_id, mailing_data['text'], parse_mode='HTML')
            sent += 1
            time.sleep(0.05)
        except:
            errors += 1

    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back"))
    bot.send_message(call.message.chat.id, f"📢 <b>Рассылка завершена!</b>\n\n✅ Успешно: {sent}\n❌ Ошибок: {errors}\n👥 Всего пользователей: {len(users)}",
                     parse_mode='HTML', reply_markup=markup)

    bot.mailing_data = None

@bot.callback_query_handler(func=lambda call: call.data == "mailing_cancel")
def mailing_cancel(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="❌ Рассылка отменена.", reply_markup=types.InlineKeyboardMarkup().add(
                              types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back")))

@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def admin_back(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_stats = types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    btn_promos = types.InlineKeyboardButton("🎟 Промокоды", callback_data="admin_promos")
    btn_mailing = types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_mailing")
    markup.add(btn_stats, btn_promos, btn_mailing)

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:", parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🎟 ПРОМОКОД")
def user_promo_start(message):
    msg = bot.send_message(message.chat.id, "📝 <b>ВВЕДИТЕ ПРОМОКОД:</b>", parse_mode='HTML')
    bot.register_next_step_handler(msg, user_activate_promo)

def user_activate_promo(message):
    code = message.text.upper().strip()
    user_id = message.from_user.id
    print(f"Попытка активации промокода '{code}' от пользователя {user_id}")

    try:
        conn = sqlite3.connect('uc_bot.db')
        c = conn.cursor()

        c.execute("SELECT discount, max_uses, used_count, expires_at FROM promocodes WHERE code = ? AND active = 1", (code,))
        promo = c.fetchone()
        if not promo:
            bot.send_message(message.chat.id, "❌ <b>Промокод не найден или неактивен!</b>", parse_mode='HTML')
            conn.close()
            print("Промокод не найден")
            return
        discount, max_uses, used_count, expires_at = promo
        print(f"Найден промокод: скидка={discount}, max_uses={max_uses}, used={used_count}, expires={expires_at}")

        if expires_at:
            exp_date = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
            if datetime.now() > exp_date:
                bot.send_message(message.chat.id, "❌ <b>Срок действия промокода истек!</b>", parse_mode='HTML')
                conn.close()
                print("Срок истек")
                return

        if max_uses > 0 and used_count >= max_uses:
            bot.send_message(message.chat.id, "❌ <b>Промокод больше не действует (достигнут лимит использований)!</b>", parse_mode='HTML')
            conn.close()
            print("Лимит исчерпан")
            return

        c.execute("SELECT * FROM user_promos WHERE user_id = ? AND promo_code = ?", (user_id, code))
        if c.fetchone():
            bot.send_message(message.chat.id, "❌ <b>Вы уже активировали этот промокод!</b>", parse_mode='HTML')
            conn.close()
            print("Уже активирован")
            return

        c.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (code,))
        c.execute("INSERT INTO user_promos (user_id, promo_code, discount, activated_at) VALUES (?,?,?,?)",
                  (user_id, code, discount, str(datetime.now())))
        conn.commit()
        conn.close()

        bot.send_message(message.chat.id, f"✅ <b>Промокод активирован!</b>\n🎁 Ваша скидка: {discount}%\n💰 Она будет применена при следующей покупке.", parse_mode='HTML')
        print("Промокод успешно активирован")

    except Exception as e:
        print("Ошибка при активации промокода:")
        traceback.print_exc()
        bot.send_message(message.chat.id, "❌ Произошла внутренняя ошибка. Попробуйте позже или сообщите администратору.", parse_mode='HTML')
        try:
            conn.close()
        except:
            pass

@bot.message_handler(func=lambda message: message.text == "🛒 КУПИТЬ UC")
def buy_uc(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for uc, price in sorted(UC_PRICES.items()):
        price_str = f"{price:,}".replace(',', '.')
        buttons.append(types.InlineKeyboardButton(
            f"{uc} UC — {price_str} ₽", 
            callback_data=f"uc_{uc}_{price}"
        ))
    markup.add(*buttons)

    bot.send_message(message.chat.id, "🛒 <b>ВЫБЕРИТЕ ПАКЕТ UC:</b>\n\n👇 Нажмите на нужный пакет", parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('uc_'))
def select_package(call):
    data = call.data.split('_')
    uc_amount = int(data[1])
    price = int(data[2])
    user_id = call.from_user.id

    final_price = price
    promo_code = None
    discount = 0

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT promo_code, discount FROM user_promos WHERE user_id = ? LIMIT 1", (user_id,))
    promo = c.fetchone()
    if promo:
        promo_code, discount = promo
        final_price = int(price * (100 - discount) / 100)
    conn.close()

    msg = bot.send_message(
        call.message.chat.id,
        f"📝 <b>ВВЕДИТЕ ВАШ ID В PUBG:</b>\n\n"
        f"🎮 Пакет: {uc_amount} UC\n"
        f"💰 Исходная сумма: {price:,} ₽\n"
        + (f"🎟 Скидка {discount}%: {final_price:,} ₽\n" if discount else "")
        + f"\n⚠️ <b>ВНИМАНИЕ!</b>\n"
        f"Проверьте ID несколько раз перед отправкой!\n"
        f"ID должен начинаться с цифры 5.\n\n"
        f"Пример: 5123456789",
        parse_mode='HTML'
    )

    bot.register_next_step_handler(msg, process_player_id, uc_amount, final_price, price, discount, promo_code)

def process_player_id(message, uc_amount, final_price, original_price, discount, promo_code):
    player_id = message.text.strip()

    if not player_id.isdigit() or len(player_id) < 5 or not player_id.startswith('5'):
        bot.send_message(message.chat.id, "❌ <b>ОШИБКА!</b>\n\nВведите корректный ID: только цифры, минимум 5 цифр и ID должен начинаться с 5.\nПопробуйте снова через 🛒 КУПИТЬ UC", parse_mode='HTML')
        return

    order_number = get_next_order_number()
    user_id = message.from_user.id

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()

    c.execute("""INSERT INTO orders 
                 (order_number, user_id, username, player_id, uc_amount, price, discount, promocode, status, created_at)
                 VALUES (?,?,?,?,?,?,?,?,?,?)""",
              (order_number, user_id, message.from_user.username or "Нет username", 
               player_id, uc_amount, final_price, discount, promo_code, 'pending', str(datetime.now())))

    if promo_code:
        c.execute("DELETE FROM user_promos WHERE user_id = ? AND promo_code = ?", (user_id, promo_code))

    conn.commit()
    conn.close()

    show_payment(message, order_number, player_id, uc_amount, final_price)

def show_payment(message, order_number, player_id, uc_amount, price):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_number}")
    btn2 = types.InlineKeyboardButton("❌ ОТМЕНА", callback_data=f"cancel_{order_number}")
    markup.add(btn1, btn2)

    price_str = f"{price:,}".replace(',', '.')
    text = f"""
✅ <b>ЗАКАЗ №{order_number} СОЗДАН!</b>

📦 <b>Детали заказа:</b>
• Пакет: {uc_amount} UC
• Сумма: {price_str} ₽
• ID: {player_id}

💳 <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:</b>\n
"""
    for card in CARDS:
        text += f"""
🏦 {card['bank']}
💳 Карта: <code>{card['card']}</code>
👤 Получатель: {card['recipient']}\n"""

    text += f"""
💰 <b>Сумма: {price_str} ₽ (на любую карту)</b>

⚠️ <b>ВАЖНО:</b>
1. Переведи точную сумму
2. Можешь выбрать любой удобный банк
3. После оплаты нажми кнопку '✅ Я ОПЛАТИЛ'
4. Ожидай пополнения 5-15 минут
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def user_paid(call):
    order_number = int(call.data.split('_')[1])

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"""
✅ <b>ЗАЯВКА ПРИНЯТА!</b>

📋 <b>ЗАКАЗ №{order_number}</b>

✅ Ваша оплата проверяется!
⏱ Ожидайте, оператор проверит платеж

⏳ СРЕДНЕЕ ВРЕМЯ: 5-15 минут
""",
        parse_mode='HTML'
    )

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, player_id, uc_amount, price FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    conn.close()

    if order:
        user_id, username, player_id, uc_amount, price = order
        price_str = f"{price:,}".replace(',', '.')

        markup_admin = types.InlineKeyboardMarkup(row_width=2)
        btn_confirm = types.InlineKeyboardButton("✅ ПОДТВЕРДИТЬ", callback_data=f"confirm_{order_number}")
        btn_cancel = types.InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data=f"admin_cancel_{order_number}")
        markup_admin.add(btn_confirm, btn_cancel)

        try:
            bot.send_message(
                ADMIN_ID,
                f"💰 <b>ПОДТВЕРЖДЕНИЕ ОПЛАТЫ №{order_number}</b> 💰\n\n"
                f"👤 Пользователь: @{username}\n"
                f"🆔 User ID: <code>{user_id}</code>\n"
                f"🎮 Пакет: {uc_amount} UC\n"
                f"💰 Сумма: {price_str} ₽\n"
                f"🆔 Player ID: {player_id}\n\n"
                f"👇 <b>Выберите действие:</b>",
                parse_mode='HTML',
                reply_markup=markup_admin
            )
        except:
            print("Не удалось отправить уведомление админу")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def admin_confirm(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return

    order_number = int(call.data.split('_')[1])

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""UPDATE orders SET status = 'completed', completed_at = ? 
                 WHERE order_number = ?""", (str(datetime.now()), order_number))

    c.execute("SELECT user_id, uc_amount, player_id FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    if order:
        user_id, uc_amount, player_id = order
        c.execute("""UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1
                     WHERE user_id = ?""", (uc_amount, user_id))

    conn.commit()
    conn.close()

    if order:
        user_id, uc_amount, player_id = order

        markup = types.InlineKeyboardMarkup()
        btn_review = types.InlineKeyboardButton("⭐ Оставить отзыв", url=f"https://t.me/{REVIEWS_CHANNEL}")
        markup.add(btn_review)

        try:
            bot.send_message(
                user_id,
                f"""
✅ <b>ЗАКАЗ №{order_number} ВЫПОЛНЕН!</b>

💰 <b>{uc_amount} UC</b> успешно зачислены на твой аккаунт!
Спасибо за покупку! ❤️

⭐ Будем благодарны за отзыв о нашей работе!
                """,
                parse_mode='HTML',
                reply_markup=markup
            )

            bot.answer_callback_query(call.id, "✅ UC выданы!")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ <b>ЗАКАЗ №{order_number} ПОДТВЕРЖДЕН!</b>\n\nUC успешно выданы.",
                parse_mode='HTML'
            )

        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_cancel_'))
def admin_cancel(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет прав!")
        return

    order_number = int(call.data.split('_')[2])

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    conn.close()

    if order:
        user_id = order[0]

        markup = types.InlineKeyboardMarkup()
        btn_support = types.InlineKeyboardButton("📞 НАПИСАТЬ В ПОДДЕРЖКУ", url=f"https://t.me/{SUPPORT_USERNAME}")
        markup.add(btn_support)

        try:
            bot.send_message(
                user_id,
                f"""
❌ <b>ЗАКАЗ №{order_number} ОТМЕНЕН</b>

Ваш заказ был отменен администратором.

📞 Пожалуйста, уточните детали в поддержке
                """,
                parse_mode='HTML',
                reply_markup=markup
            )
        except:
            pass

    bot.answer_callback_query(call.id, "✅ Заказ отменен")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"❌ <b>ЗАКАЗ №{order_number} ОТМЕНЕН</b>",
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_'))
def cancel_order(call):
    order_number = int(call.data.split('_')[1])

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"""
❌ <b>ЗАКАЗ ОТМЕНЕН</b>

📋 <b>ЗАКАЗ №{order_number}</b>

Вы можете создать новый заказ в любое время!

👇 Нажмите 🛒 КУПИТЬ UC
""",
        parse_mode='HTML'
    )

@bot.message_handler(func=lambda message: message.text == "👤 МОЙ ПРОФИЛЬ")
def my_profile(message):
    user_id = message.from_user.id

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT total_uc, total_orders, join_date, first_name FROM users WHERE user_id = ?", (user_id,))
    user_data = c.fetchone()

    if user_data:
        total_uc, total_orders, join_date, first_name = user_data
        join_date_str = join_date[:10] if join_date else "Неизвестно"
    else:
        total_uc, total_orders, join_date_str, first_name = 0, 0, str(datetime.now())[:10], "Игрок"

    text = f"""
👤 <b>МОЙ ПРОФИЛЬ</b>
Привет, {first_name}!

📊 <b>СТАТИСТИКА:</b>
🆔 User ID: <code>{user_id}</code>
📅 На сайте с: {join_date_str}

💰 <b>ПОКУПКИ:</b>
📦 Всего заказов: {total_orders}
🎮 Всего UC: {total_uc}
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "🏆 ЛИДЕРЫ")
def leaders(message):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""SELECT first_name, total_uc FROM users 
                 WHERE total_uc > 0 
                 ORDER BY total_uc DESC LIMIT 10""")
    leaders_list = c.fetchall()
    conn.close()

    if not leaders_list:
        bot.send_message(message.chat.id, "🏆 <b>ЛИДЕРОВ ПОКА НЕТ</b>\n\nСделайте первый заказ и попадите в топ!", parse_mode='HTML')
        return

    text = "🏆 <b>ТОП-10 ПОКУПАТЕЛЕЙ (по количеству UC)</b>\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, leader in enumerate(leaders_list):
        first_name, total_uc = leader
        text += f"{medals[i]} {first_name} — {total_uc} UC\n"

    bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.text == "⭐️ ОТЗЫВЫ")
def reviews(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📢 ПЕРЕЙТИ В КАНАЛ С ОТЗЫВАМИ", url=f"https://t.me/{REVIEWS_CHANNEL}")
    markup.add(btn)

    text = """
⭐️ <b>НАШИ ОТЗЫВЫ</b> ⭐️

👇 Нажми на кнопку чтобы перейти в канал с отзывами
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📞 ПОДДЕРЖКА")
def support(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("👨‍💼 НАПИСАТЬ В ПОДДЕРЖКУ", url=f"https://t.me/{SUPPORT_USERNAME}")
    markup.add(btn)

    text = """
📞 <b>СЛУЖБА ПОДДЕРЖКИ</b>

🕐 Работаем 24/7 без выходных
⏱ Среднее время ответа: 5-10 минут

👇 Нажми кнопку ниже
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

if __name__ == '__main__':
    print("🔄 Проверяю базу данных...")
    init_db()
    print("✅ БОТ ЗАПУЩЕН!")
    print(f"👤 ADMIN ID: {ADMIN_ID}")
    print("⚡️ БОТ РАБОТАЕТ - ОТПРАВЬ /start")

    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
