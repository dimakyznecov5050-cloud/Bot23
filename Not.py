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
ADMIN_ID = 8052884471          # Твой ID
SECOND_USER_ID = 0  # Сюда вставь ID второго аккаунта для теста
SUPPORT_USERNAME = 'Kurator111'
REVIEWS_CHANNEL = '+DpdNmcj9gAY2MThi'

CARDS = [
    {'bank': 'СБЕР', 'card': '2202 2084 1737 7224', 'recipient': 'Дмитрий'},
    {'bank': 'ВТБ', 'card': '2200 2479 5387 8262', 'recipient': 'Дмитрий'}
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
                  total_uc INTEGER DEFAULT 0,
                  last_activity TEXT)''')

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

    # Добавляем недостающие колонки
    add_column_if_not_exists(c, 'users', 'total_orders', 'INTEGER', '0')
    add_column_if_not_exists(c, 'users', 'last_activity', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'orders', 'discount', 'INTEGER', '0')
    add_column_if_not_exists(c, 'orders', 'promocode', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'promocodes', 'max_uses', 'INTEGER', '0')
    add_column_if_not_exists(c, 'promocodes', 'used_count', 'INTEGER', '0')
    add_column_if_not_exists(c, 'promocodes', 'expires_at', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'promocodes', 'active', 'INTEGER', '1')

    conn.commit()
    conn.close()
    print("✅ База данных проверена/создана, миграция выполнена.")

def update_last_activity(user_id):
    """Обновляет время последней активности пользователя"""
    try:
        conn = sqlite3.connect('uc_bot.db')
        c = conn.cursor()
        c.execute("UPDATE users SET last_activity = ? WHERE user_id = ?", 
                  (str(datetime.now()), user_id))
        conn.commit()
        conn.close()
    except:
        pass

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

# ---------- ДИАГНОСТИЧЕСКАЯ КОМАНДА ----------
@bot.message_handler(commands=['debug_users'])
def debug_users(message):
    """Проверяет всех пользователей в БД и их доступность"""
    if not is_admin(message.from_user.id):
        return
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, last_activity FROM users ORDER BY last_activity DESC")
    users = c.fetchall()
    conn.close()
    
    text = "📋 <b>Список пользователей в БД:</b>\n\n"
    
    if not users:
        text += "❌ Пользователей нет!"
    else:
        for user_id, username, first_name, last_activity in users:
            status = "🟢"  # Неизвестно
            if last_activity:
                last = datetime.strptime(last_activity.split('.')[0], '%Y-%m-%d %H:%M:%S')
                if datetime.now() - last < timedelta(days=1):
                    status = "🟢 Активен сегодня"
                elif datetime.now() - last < timedelta(days=7):
                    status = "🟡 Был(а) на неделе"
                else:
                    status = "🔴 Давно не активен"
            
            text += f"{status}\n"
            text += f"👤 ID: <code>{user_id}</code>\n"
            text += f"📝 Имя: {first_name}\n"
            text += f"🔗 Username: @{username}\n"
            text += f"⏱ Последняя активность: {last_activity or 'никогда'}\n\n"
    
    # Разбиваем на части если слишком длинное
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            bot.send_message(message.chat.id, text[x:x+4000], parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, text, parse_mode='HTML')

@bot.message_handler(commands=['test_user'])
def test_user(message):
    """Тестирует отправку конкретному пользователю"""
    if not is_admin(message.from_user.id):
        return
    
    msg = bot.send_message(message.chat.id, "Введите ID пользователя для теста:")
    bot.register_next_step_handler(msg, process_test_user)

def process_test_user(message):
    try:
        user_id = int(message.text.strip())
        
        # Пробуем отправить тестовое сообщение
        bot.send_message(user_id, "🧪 <b>ТЕСТОВОЕ СООБЩЕНИЕ</b>\n\nЕсли вы это видите - бот работает!", parse_mode='HTML')
        
        # Проверяем есть ли в БД
        conn = sqlite3.connect('uc_bot.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        
        if user:
            bot.send_message(message.chat.id, f"✅ Сообщение отправлено!\nПользователь найден в БД.")
        else:
            bot.send_message(message.chat.id, f"✅ Сообщение отправлено!\n❌ Пользователь НЕ найден в БД.")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

# ---------- ОСНОВНЫЕ КОМАНДЫ ----------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    first_name = message.from_user.first_name or "Игрок"

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO users 
                 (user_id, username, first_name, join_date, total_uc, total_orders, last_activity) 
                 VALUES (?,?,?,?,?,?,?)""",
              (user_id, username, first_name, str(datetime.now()), 0, 0, str(datetime.now())))
    
    # Обновляем существующего пользователя
    c.execute("""UPDATE users SET 
                 username = ?, 
                 first_name = ?,
                 last_activity = ?
                 WHERE user_id = ?""",
              (username, first_name, str(datetime.now()), user_id))
    
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
    btn_debug = types.InlineKeyboardButton("🔍 Диагностика", callback_data="admin_debug")
    markup.add(btn_stats, btn_promos, btn_mailing, btn_debug)

    bot.send_message(
        message.chat.id,
        "👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=markup,
    )

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
    elif action == "debug":
        debug_menu(call)

def debug_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_users = types.InlineKeyboardButton("👥 Список пользователей", callback_data="debug_users")
    btn_test = types.InlineKeyboardButton("🧪 Тест отправки", callback_data="debug_test")
    btn_back = types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back")
    markup.add(btn_users, btn_test, btn_back)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🔍 <b>ДИАГНОСТИКА</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "debug_users")
def debug_users_callback(call):
    if not is_admin(call.from_user.id):
        return
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, last_activity FROM users ORDER BY last_activity DESC LIMIT 10")
    users = c.fetchall()
    conn.close()
    
    text = "📋 <b>Последние 10 активных пользователей:</b>\n\n"
    
    for user_id, username, first_name, last_activity in users:
        text += f"• ID: <code>{user_id}</code>\n"
        text += f"  Имя: {first_name}\n"
        text += f"  Username: @{username}\n"
        text += f"  Активность: {last_activity or 'никогда'}\n\n"
    
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("◀️ Назад", callback_data="admin_debug")
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "debug_test")
def debug_test_callback(call):
    if not is_admin(call.from_user.id):
        return
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🧪 <b>ТЕСТ ОТПРАВКИ</b>\n\nВведите ID пользователя для теста:",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(call.message, process_test_user)

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
    
    # Активные пользователи за последние 24 часа
    yesterday = str(datetime.now() - timedelta(days=1))
    c.execute("SELECT COUNT(*) FROM users WHERE last_activity > ?", (yesterday,))
    active_24h = c.fetchone()[0]

    conn.close()

    text = f"""
📊 <b>СТАТИСТИКА</b>

👥 Всего пользователей: {total_users}
🟢 Активны за 24ч: {active_24h}
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
    btn_back = types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back")
    markup.add(btn_create, btn_list, btn_back)

    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="🎟 <b>Управление промокодами</b>", parse_mode='HTML', reply_markup=markup)

# ---------- ПРОМОКОДЫ ----------
@bot.callback_query_handler(func=lambda call: call.data == "promo_create")
def promo_create_step1(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🎟 <b>Создание промокода</b>\n\nВведите код промокода (например, SUMMER15):",
        parse_mode='HTML',
    )
    bot.register_next_step_handler(call.message, process_promo_code)

def process_promo_code(message):
    if not is_admin(message.from_user.id):
        return
    code = message.text.upper().strip()
    if not code:
        bot.send_message(message.chat.id, "❌ Код не может быть пустым.")
        return

    bot.send_message(
        message.chat.id,
        f"Код: {code}\nТеперь введите размер скидки (число от 1 до 100):",
    )
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
    bot.send_message(
        message.chat.id,
        (
            f"🎟 Промокод: <b>{code}</b>\n"
            f"💰 Скидка: <b>{discount}%</b>\n"
            f"📊 Лимит: {uses_text}\n"
            f"⏰ Срок: {expiry_text}\n\n"
            "Сохранить?"
        ),
        parse_mode='HTML',
        reply_markup=markup,
    )

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

# ---------- ИСПРАВЛЕННАЯ РАССЫЛКА (поддерживает фото) ----------
def start_mailing(call):
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📢 <b>Рассылка</b>\n\nОтправьте сообщение для рассылки (можно с фото и подписью):",
        parse_mode='HTML',
    )
    bot.register_next_step_handler(call.message, process_mailing_content)

def process_mailing_content(message):
    """Обрабатывает сообщение для рассылки (текст или фото с подписью)"""
    if not is_admin(message.from_user.id):
        return
    
    # Сохраняем тип контента и само содержимое
    if message.photo:
        # Если есть фото - берём фото и подпись
        photo = message.photo[-1].file_id  # Берём фото максимального размера
        caption = message.caption or ""
        content = {'type': 'photo', 'file_id': photo, 'caption': caption}
    elif message.text:
        # Если только текст
        content = {'type': 'text', 'text': message.text}
    else:
        bot.send_message(message.chat.id, "❌ Поддерживаются только текстовые сообщения и фото с подписью.")
        return

    markup = types.InlineKeyboardMarkup()
    btn_yes = types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"mailing_confirm")
    btn_no = types.InlineKeyboardButton("❌ Отмена", callback_data="mailing_cancel")
    markup.add(btn_yes, btn_no)

    # Отправляем предпросмотр
    preview_text = "📢 <b>Предпросмотр рассылки:</b>\n\n"
    
    if content['type'] == 'photo':
        preview_text += f"📸 Фото с подписью:\n{content['caption']}" if content['caption'] else "📸 Фото (без подписи)"
        bot.send_photo(
            message.chat.id,
            content['file_id'],
            caption=preview_text,
            parse_mode='HTML',
            reply_markup=markup
        )
    else:
        preview_text += content['text']
        bot.send_message(
            message.chat.id,
            preview_text,
            parse_mode='HTML',
            reply_markup=markup
        )

    # Сохраняем контент для последующей рассылки
    bot.mailing_content = content

@bot.callback_query_handler(func=lambda call: call.data == "mailing_confirm")
def mailing_confirm(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    content = getattr(bot, 'mailing_content', None)
    if not content:
        bot.answer_callback_query(call.id, "❌ Контент не найден, начните заново.")
        return

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="📢 <b>Рассылка началась. Следите за логами в консоли...</b>",
        parse_mode='HTML'
    )

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username FROM users")
    users = c.fetchall()
    conn.close()

    sent = 0
    errors = 0
    error_details = []
    
    print("\n" + "="*50)
    print("🚀 НАЧАЛО РАССЫЛКИ")
    print(f"📊 Всего пользователей в БД: {len(users)}")
    print("="*50)
    
    for user_id, username in users:
        try:
            print(f"🔄 Отправка пользователю {user_id} (@{username})...", end=" ")
            
            if content['type'] == 'photo':
                bot.send_photo(
                    user_id,
                    content['file_id'],
                    caption=content['caption'],
                    parse_mode='HTML'
                )
            else:
                bot.send_message(
                    user_id,
                    content['text'],
                    parse_mode='HTML'
                )
            sent += 1
            print("✅ УСПЕШНО")
            
            # Обновляем время активности
            update_last_activity(user_id)
            
        except Exception as e:
            errors += 1
            error_msg = str(e)
            print(f"❌ ОШИБКА: {error_msg}")
            
            # Определяем тип ошибки
            if "bot was blocked by the user" in error_msg:
                error_type = "ЗАБЛОКИРОВАЛ БОТА"
            elif "chat not found" in error_msg:
                error_type = "НЕТ ЧАТА (не запускал /start)"
            elif "user is deactivated" in error_msg:
                error_type = "АККАУНТ УДАЛЕН"
            else:
                error_type = "ДРУГАЯ ОШИБКА"
            
            error_details.append(f"{user_id}: {error_type}")
            
            time.sleep(0.05)

    # Итоговый отчет
    print("="*50)
    print("📊 ИТОГИ РАССЫЛКИ:")
    print(f"✅ Успешно: {sent}")
    print(f"❌ Ошибок: {errors}")
    print(f"👥 Всего: {len(users)}")
    
    # Подробный разбор ошибок
    if error_details:
        print("\n📋 Детали ошибок:")
        for err in error_details:
            print(f"  {err}")
    
    print("="*50 + "\n")
    
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back")
    )
    
    # Считаем статистику ошибок
    blocked = sum(1 for err in error_details if "ЗАБЛОКИРОВАЛ" in err)
    no_chat = sum(1 for err in error_details if "НЕТ ЧАТА" in err)
    deactivated = sum(1 for err in error_details if "УДАЛЕН" in err)
    other = sum(1 for err in error_details if "ДРУГАЯ" in err)
    
    report = (
        "📢 <b>Рассылка завершена!</b>\n\n"
        f"✅ Успешно: {sent}\n"
        f"❌ Ошибок всего: {errors}\n"
        f"🚫 Заблокировали бота: {blocked}\n"
        f"👤 Не запускали бота: {no_chat}\n"
        f"💀 Аккаунты удалены: {deactivated}\n"
        f"⚠️ Другие ошибки: {other}\n"
        f"👥 Всего в базе: {len(users)}\n\n"
    )
    
    if error_details and len(error_details) > 0:
        report += "📋 <b>Первые 5 ошибок:</b>\n"
        for err in error_details[:5]:
            report += f"• {err}\n"
    
    bot.send_message(
        call.message.chat.id,
        report,
        parse_mode='HTML',
        reply_markup=markup
    )
    
    bot.mailing_content = None

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
    btn_debug = types.InlineKeyboardButton("🔍 Диагностика", callback_data="admin_debug")
    markup.add(btn_stats, btn_promos, btn_mailing, btn_debug)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=markup,
    )

# ---------- ОБРАБОТЧИКИ СООБЩЕНИЙ ----------
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """Обновляет активность при любом сообщении"""
    update_last_activity(message.from_user.id)
    
    # Обработка текстовых кнопок
    text = message.text
    
    if text == "🎟 ПРОМОКОД":
        user_promo_start(message)
    elif text == "🛒 КУПИТЬ UC":
        buy_uc(message)
    elif text == "👤 МОЙ ПРОФИЛЬ":
        my_profile(message)
    elif text == "🏆 ЛИДЕРЫ":
        leaders(message)
    elif text == "⭐️ ОТЗЫВЫ":
        reviews(message)
    elif text == "📞 ПОДДЕРЖКА":
        support(message)

def user_promo_start(message):
    msg = bot.send_message(message.chat.id, "📝 <b>ВВЕДИТЕ ПРОМОКОД:</b>", parse_mode='HTML')
    bot.register_next_step_handler(msg, user_activate_promo)

def _parse_expires_at(expires_at: str) -> datetime:
    """
    Поддерживает форматы даты из БД, включая случаи с микросекундами и без минут/секунд:
      2026-02-23 05
      2026-02-23 05:10
      2026-02-23 05:10:59
      2026-02-23 05:10:59.123456
      2026-02-23
      2026-02-23T05:10:59(.123456)
    """
    if expires_at is None:
        raise ValueError("expires_at is None")

    s = str(expires_at).strip()

    # ISO с 'T' тоже принимаем
    if "T" in s and " " not in s:
        s = s.replace("T", " ")

    for fmt in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass

    raise ValueError(f"Unsupported expires_at format: {s!r}")

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
            exp_date = _parse_expires_at(expires_at)
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

        bot.send_message(
            message.chat.id,
            (
                "✅ <b>Промокод активирован!</b>\n"
                f"🎁 Ваша скидка: {discount}%\n"
                "💰 Она будет применена при следующей покупке."
            ),
            parse_mode='HTML',
        )
        print("Промокод успешно активирован")

    except Exception as e:
        print("Ошибка при активации промокода:")
        traceback.print_exc()
        bot.send_message(message.chat.id, "❌ Произошла внутренняя ошибка. Попробуйте позже или сообщите администратору.", parse_mode='HTML')
        try:
            conn.close()
        except:
            pass

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

    bot.send_message(
        message.chat.id,
        "🛒 <b>ВЫБЕРИТЕ ПАКЕТ UC:</b>\n\n👇 Нажмите на нужный пакет",
        parse_mode='HTML',
        reply_markup=markup,
    )

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

    text = (
        "📝 <b>ВВЕДИТЕ ВАШ ID В PUBG:</b>\n\n"
        f"🎮 Пакет: {uc_amount} UC\n"
        f"💰 Исходная сумма: {price:,} ₽\n"
        + (f"🎟 Скидка {discount}%: {final_price:,} ₽\n" if discount else "")
        + "\n⚠️ <b>ВНИМАНИЕ!</b>\n"
        + "Проверьте ID несколько раз перед отправкой!\n\n"
        + "Пример: 1234567890"
    )
    msg = bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    bot.register_next_step_handler(msg, process_player_id, uc_amount, final_price, price, discount, promo_code)

def process_player_id(message, uc_amount, final_price, original_price, discount, promo_code):
    player_id = message.text.strip()

    if not player_id.isdigit() or len(player_id) < 5:
        bot.send_message(
            message.chat.id,
            "❌ <b>ОШИБКА!</b>\n\n"
            "Введите корректный ID (только цифры, минимум 5 цифр).\n"
            "Попробуйте снова через 🛒 КУПИТЬ UC",
            parse_mode='HTML',
        )
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

💳 <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:</b>

"""
    for card in CARDS:
        text += f"""
🏦 {card['bank']}
💳 Карта: <code>{card['card']}</code>
👤 Получатель: {card['recipient']}
"""

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
            admin_text = (
                f"💰 <b>ПОДТВЕРЖДЕНИЕ ОПЛАТЫ №{order_number}</b> 💰\n\n"
                f"👤 Пользователь: @{username}\n"
                f"🆔 User ID: <code>{user_id}</code>\n"
                f"🎮 Пакет: {uc_amount} UC\n"
                f"💰 Сумма: {price_str} ₽\n"
                f"🆔 Player ID: {player_id}\n\n"
                "👇 <b>Выберите действие:</b>"
            )
            bot.send_message(
                ADMIN_ID,
                admin_text,
                parse_mode='HTML',
                reply_markup=markup_admin,
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
                parse_mode='HTML',
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

def leaders(message):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("""SELECT first_name, total_uc FROM users 
                 WHERE total_uc > 0 
                 ORDER BY total_uc DESC LIMIT 10""")
    leaders_list = c.fetchall()
    conn.close()

    if not leaders_list:
        bot.send_message(
            message.chat.id,
            "🏆 <b>ЛИДЕРОВ ПОКА НЕТ</b>\n\nСделайте первый заказ и попадите в топ!",
            parse_mode='HTML',
        )
        return

    text = "🏆 <b>ТОП-10 ПОКУПАТЕЛЕЙ (по количеству UC)</b>\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, leader in enumerate(leaders_list):
        first_name, total_uc = leader
        text += f"{medals[i]} {first_name} — {total_uc} UC\n"

    bot.send_message(message.chat.id, text, parse_mode='HTML')

def reviews(message):
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📢 ПЕРЕЙТИ В КАНАЛ С ОТЗЫВАМИ", url=f"https://t.me/{REVIEWS_CHANNEL}")
    markup.add(btn)

    text = """
⭐️ <b>НАШИ ОТЗЫВЫ</b> ⭐️

👇 Нажми на кнопку чтобы перейти в канал с отзывами
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

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
    print("📢 Рассылка поддерживает фото и текст")
    print("🔍 Для диагностики используй /debug_users или /test_user")

    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
