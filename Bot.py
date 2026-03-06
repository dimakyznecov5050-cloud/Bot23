import telebot
from telebot import types
import sqlite3
from datetime import datetime, timedelta
import time
import traceback

# ---------- ТОКЕН ----------
TOKEN = '8783525882:AAE0QrrgJUy_BBFZLAMZFAoIuZir0hHAj-8'
bot = telebot.TeleBot(TOKEN)

# ---------- НАСТРОЙКИ ----------
ADMIN_ID = 8052884471
SUPPORT_USERNAME = 'Kurator111'
REVIEWS_CHANNEL = '+DpdNmcj9gAY2MThi'

CARDS = [
    {'bank': 'СБЕР', 'card': '2202 2084 1737 7224', 'recipient': 'Дмитрий'},
    {'bank': 'ВТБ', 'card': '2200 2479 5387 8262', 'recipient': 'Дмитрий'}
]

UC_PRICES = {
    60: 80, 120: 160, 180: 240, 325: 400, 385: 480,
    660: 800, 720: 910, 985: 1250, 1320: 1700,
    1800: 1950, 2460: 2800, 3850: 4000, 8100: 8200
}

# ---------- БАЗА ДАННЫХ ----------
def init_db():
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  join_date TEXT,
                  total_uc INTEGER DEFAULT 0,
                  total_orders INTEGER DEFAULT 0,
                  last_activity TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  order_number INTEGER UNIQUE,
                  user_id INTEGER,
                  username TEXT,
                  player_id TEXT,
                  uc_amount INTEGER,
                  price INTEGER,
                  discount INTEGER DEFAULT 0,
                  promocode TEXT,
                  status TEXT,
                  created_at TEXT,
                  completed_at TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS promocodes
                 (code TEXT PRIMARY KEY,
                  discount INTEGER,
                  max_uses INTEGER DEFAULT 0,
                  used_count INTEGER DEFAULT 0,
                  expires_at TEXT,
                  active INTEGER DEFAULT 1,
                  created_at TEXT)''')

    c.execute('''CREATE TABLE IF NOT EXISTS user_promos
                 (user_id INTEGER,
                  promo_code TEXT,
                  discount INTEGER,
                  activated_at TEXT,
                  PRIMARY KEY (user_id, promo_code))''')

    conn.commit()
    conn.close()
    print("✅ База данных проверена")

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
    buttons = [
        "🛒 КУПИТЬ UC", "👤 МОЙ ПРОФИЛЬ",
        "🏆 ЛИДЕРЫ", "⭐️ ОТЗЫВЫ",
        "📞 ПОДДЕРЖКА", "🎟 ПРОМОКОД"
    ]
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    return markup

# ---------- START ----------
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
    
    c.execute("""UPDATE users SET 
                 username = ?, first_name = ?, last_activity = ?
                 WHERE user_id = ?""",
              (username, first_name, str(datetime.now()), user_id))
    
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        "👋 <b>ДОБРО ПОЖАЛОВАТЬ В APEX UC SHOP!</b>\n\n🔥 Лучший магазин UC для PUBG Mobile\n\n👇 Нажми КУПИТЬ UC чтобы начать",
        parse_mode='HTML',
        reply_markup=main_keyboard()
    )

# ---------- ADMIN ----------
@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора!")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        types.InlineKeyboardButton("🎟 Промокоды", callback_data="admin_promos"),
        types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_mailing")
    )

    bot.send_message(
        message.chat.id,
        "👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=markup,
    )

# ---------- ОБРАБОТЧИК КНОПОК ----------
@bot.callback_query_handler(func=lambda call: call.data in {"admin_stats", "admin_promos", "admin_mailing", "admin_back", "promo_create", "promo_list", "promo_delete"} or call.data.startswith("delete_promo_"))
def callback_handler(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    data = call.data
    
    if data == "admin_stats":
        show_admin_stats(call)
    
    elif data == "admin_promos":
        promos_menu(call)
    
    elif data == "admin_mailing":
        start_mailing(call)
    
    elif data == "admin_back":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
            types.InlineKeyboardButton("🎟 Промокоды", callback_data="admin_promos"),
            types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_mailing")
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    elif data == "promo_create":
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎟 <b>Создание промокода</b>\n\nВведите код промокода:",
            parse_mode='HTML'
        )
        bot.register_next_step_handler(call.message, process_promo_code)
    
    elif data == "promo_list":
        promo_list(call)
    
    elif data == "promo_delete":
        promo_delete_menu(call)

    elif data.startswith("delete_promo_"):
        delete_promo(call)

# ---------- СТАТИСТИКА ----------
def show_admin_stats(call):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders")
    total_orders = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    completed_orders = c.fetchone()[0]

    c.execute("SELECT SUM(price) FROM orders WHERE status = 'completed'")
    total_earned = c.fetchone()[0] or 0

    c.execute("SELECT COUNT(*) FROM promocodes")
    total_promos = c.fetchone()[0]

    conn.close()

    text = f"""
📊 <b>СТАТИСТИКА</b>

👥 Пользователей: {total_users}
📦 Заказов: {total_orders}
✅ Выполнено: {completed_orders}
💰 Заработано: {total_earned:,} ₽
🎟 Промокодов: {total_promos}
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=markup
    )

# ---------- МЕНЮ ПРОМОКОДОВ ----------
def promos_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Создать", callback_data="promo_create"),
        types.InlineKeyboardButton("📋 Список", callback_data="promo_list")
    )
    markup.add(
        types.InlineKeyboardButton("🗑 Удалить", callback_data="promo_delete"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back")
    )
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🎟 <b>Управление промокодами</b>",
        parse_mode='HTML',
        reply_markup=markup
    )

# ---------- СОЗДАНИЕ ПРОМОКОДА ----------
def process_promo_code(message):
    if not is_admin(message.from_user.id):
        return
    
    code = message.text.upper().strip()
    if not code:
        bot.send_message(message.chat.id, "❌ Код не может быть пустым.")
        return

    bot.send_message(message.chat.id, f"Код: {code}\nВведите размер скидки (1-100):")
    bot.register_next_step_handler(message, lambda m: process_promo_discount(m, code))

def process_promo_discount(message, code):
    if not is_admin(message.from_user.id):
        return
    
    try:
        discount = int(message.text)
        if discount < 1 or discount > 100:
            raise ValueError
    except:
        bot.send_message(message.chat.id, "❌ Введите число от 1 до 100.")
        return

    bot.send_message(message.chat.id, "Введите лимит использований (0 - безлимит):")
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

    bot.send_message(message.chat.id, "Введите срок в днях (0 - бессрочно):")
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

    # Сохраняем промокод
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO promocodes (code, discount, max_uses, expires_at, created_at) VALUES (?,?,?,?,?)",
            (code, discount, max_uses, expires_at, str(datetime.now()))
        )
        conn.commit()
        
        expiry_text = "бессрочно" if not expires_at else f"до {expires_at[:10]}"
        uses_text = "безлимит" if max_uses == 0 else f"{max_uses} раз"
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>Промокод создан!</b>\n\n🎟 {code}\n💰 {discount}%\n📊 {uses_text}\n⏰ {expiry_text}",
            parse_mode='HTML'
        )
        
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, f"❌ Промокод {code} уже существует!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")
    finally:
        conn.close()
    
    # Возвращаемся в меню
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Создать ещё", callback_data="promo_create"),
        types.InlineKeyboardButton("📋 Список", callback_data="promo_list"),
        types.InlineKeyboardButton("◀️ Назад", callback_data="admin_back")
    )
    bot.send_message(
        message.chat.id,
        "🎟 <b>Управление промокодами</b>",
        parse_mode='HTML',
        reply_markup=markup
    )

# ---------- СПИСОК ПРОМОКОДОВ ----------
def promo_list(call):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT code, discount, max_uses, used_count, expires_at, active FROM promocodes ORDER BY created_at DESC")
    promos = c.fetchall()
    conn.close()

    if not promos:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promos"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎟 Промокодов пока нет.",
            parse_mode='HTML',
            reply_markup=markup
        )
        return

    text = "🎟 <b>Список промокодов:</b>\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for p in promos:
        code, discount, max_uses, used, expires, active = p
        status = "✅" if active else "❌"
        expiry = "бессрочно" if not expires else f"до {expires[:10]}"
        limit = "∞" if max_uses == 0 else f"{max_uses}"
        
        text += f"{status} <b>{code}</b> — {discount}% (исп. {used}/{limit}) {expiry}\n"
    
    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promos"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=text,
        parse_mode='HTML',
        reply_markup=markup
    )



# ---------- МЕНЮ УДАЛЕНИЯ ПРОМОКОДОВ ----------
def promo_delete_menu(call):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT code FROM promocodes ORDER BY created_at DESC")
    promo_codes = c.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    if not promo_codes:
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promos"))
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🗑 Промокодов для удаления нет.",
            parse_mode='HTML',
            reply_markup=markup
        )
        return

    for (code,) in promo_codes:
        markup.add(types.InlineKeyboardButton(f"❌ Удалить {code}", callback_data=f"delete_promo_{code}"))

    markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data="admin_promos"))
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🗑 <b>Выберите промокод для удаления:</b>",
        parse_mode='HTML',
        reply_markup=markup
    )

# ---------- УДАЛЕНИЕ ПРОМОКОДА ----------
def delete_promo(call):
    code = call.data.replace("delete_promo_", "")
    
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("DELETE FROM promocodes WHERE code = ?", (code,))
    c.execute("DELETE FROM user_promos WHERE promo_code = ?", (code,))
    conn.commit()
    conn.close()
    
    bot.answer_callback_query(call.id, f"✅ Промокод {code} удален!")
    promo_delete_menu(call)

# ---------- РАССЫЛКА (ИСПРАВЛЕННАЯ) ----------
def start_mailing(call):
    msg = bot.send_message(
        call.message.chat.id,
        "📢 <b>Рассылка</b>\n\nОтправьте сообщение (можно с фото):",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, process_mailing_content)

def process_mailing_content(message):
    if not is_admin(message.from_user.id):
        return
    
    if message.photo:
        # Сохраняем фото
        bot.mailing_photo = message.photo[-1].file_id
        bot.mailing_caption = message.caption or ""
        
        # Показываем предпросмотр
        preview = "📢 <b>ПРЕДПРОСМОТР</b>\n\n📸 Фото"
        if bot.mailing_caption:
            preview += f"\n\n{bot.mailing_caption}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ ОТПРАВИТЬ", callback_data="send_mailing"),
            types.InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_mailing")
        )
        
        bot.send_photo(
            message.chat.id,
            bot.mailing_photo,
            caption=preview,
            parse_mode='HTML',
            reply_markup=markup
        )
        
    elif message.text:
        # Сохраняем текст
        bot.mailing_text = message.text
        
        # Показываем предпросмотр
        preview = f"📢 <b>ПРЕДПРОСМОТР</b>\n\n{message.text}"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ ОТПРАВИТЬ", callback_data="send_mailing"),
            types.InlineKeyboardButton("❌ ОТМЕНА", callback_data="cancel_mailing")
        )
        
        bot.send_message(
            message.chat.id,
            preview,
            parse_mode='HTML',
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "❌ Отправьте текст или фото")

@bot.callback_query_handler(func=lambda call: call.data == "send_mailing")
def send_mailing(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return
    
    # Меняем текст предпросмотра
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="📢 <b>РАССЫЛКА НАЧАЛАСЬ...</b>",
                parse_mode='HTML',
                reply_markup=None
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="📢 <b>РАССЫЛКА НАЧАЛАСЬ...</b>",
                parse_mode='HTML',
                reply_markup=None
            )
    except Exception as e:
        print(f"Не удалось обновить предпросмотр рассылки: {e}")
    
    # Получаем пользователей
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    sent = 0
    errors = 0
    
    for (user_id,) in users:
        try:
            if hasattr(bot, 'mailing_photo'):
                bot.send_photo(
                    user_id,
                    bot.mailing_photo,
                    caption=bot.mailing_caption,
                    parse_mode='HTML'
                )
            else:
                bot.send_message(
                    user_id,
                    bot.mailing_text,
                    parse_mode='HTML'
                )
            sent += 1
            time.sleep(0.05)
        except Exception as e:
            errors += 1
            print(f"Ошибка {user_id}: {e}")
    
    # Отчет
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("◀️ В админку", callback_data="admin_back"))
    
    bot.send_message(
        call.message.chat.id,
        f"📢 <b>РАССЫЛКА ЗАВЕРШЕНА</b>\n\n✅ Успешно: {sent}\n❌ Ошибок: {errors}",
        parse_mode='HTML',
        reply_markup=markup
    )
    
    # Очищаем
    if hasattr(bot, 'mailing_photo'):
        del bot.mailing_photo
        del bot.mailing_caption
    if hasattr(bot, 'mailing_text'):
        del bot.mailing_text

@bot.callback_query_handler(func=lambda call: call.data == "cancel_mailing")
def cancel_mailing(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return
    
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption="❌ <b>РАССЫЛКА ОТМЕНЕНА</b>",
                parse_mode='HTML',
                reply_markup=None
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ <b>РАССЫЛКА ОТМЕНЕНА</b>",
                parse_mode='HTML',
                reply_markup=None
            )
    except Exception as e:
        print(f"Не удалось обновить сообщение отмены рассылки: {e}")
    
    # Очищаем
    if hasattr(bot, 'mailing_photo'):
        del bot.mailing_photo
        del bot.mailing_caption
    if hasattr(bot, 'mailing_text'):
        del bot.mailing_text
    
    admin_command(call.message)

# ---------- АКТИВАЦИЯ ПРОМОКОДА ПОЛЬЗОВАТЕЛЕМ ----------
@bot.message_handler(func=lambda message: message.text == "🎟 ПРОМОКОД")
def user_promo_start(message):
    msg = bot.send_message(message.chat.id, "📝 <b>ВВЕДИТЕ ПРОМОКОД:</b>", parse_mode='HTML')
    bot.register_next_step_handler(msg, user_activate_promo)

def user_activate_promo(message):
    code = message.text.upper().strip()
    user_id = message.from_user.id

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()

    c.execute("SELECT discount, max_uses, used_count, expires_at FROM promocodes WHERE code = ? AND active = 1", (code,))
    promo = c.fetchone()
    
    if not promo:
        bot.send_message(message.chat.id, "❌ <b>Промокод не найден!</b>", parse_mode='HTML')
        conn.close()
        return
    
    discount, max_uses, used_count, expires_at = promo

    # Проверка срока
    if expires_at:
        try:
            exp_date = datetime.strptime(expires_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
            if datetime.now() > exp_date:
                bot.send_message(message.chat.id, "❌ <b>Срок истек!</b>", parse_mode='HTML')
                conn.close()
                return
        except:
            pass

    # Проверка лимита
    if max_uses > 0 and used_count >= max_uses:
        bot.send_message(message.chat.id, "❌ <b>Лимит использований!</b>", parse_mode='HTML')
        conn.close()
        return

    # Проверка активации
    c.execute("SELECT * FROM user_promos WHERE user_id = ? AND promo_code = ?", (user_id, code))
    if c.fetchone():
        bot.send_message(message.chat.id, "❌ <b>Уже активирован!</b>", parse_mode='HTML')
        conn.close()
        return

    # Активация
    c.execute("UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?", (code,))
    c.execute("INSERT INTO user_promos (user_id, promo_code, discount, activated_at) VALUES (?,?,?,?)",
              (user_id, code, discount, str(datetime.now())))
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        f"✅ <b>Промокод активирован!</b>\n🎁 Скидка: {discount}%",
        parse_mode='HTML'
    )

# ---------- ПОКУПКА UC ----------
@bot.message_handler(func=lambda message: message.text == "🛒 КУПИТЬ UC")
def buy_uc(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    for uc, price in sorted(UC_PRICES.items()):
        price_str = f"{price:,}".replace(',', '.')
        markup.add(types.InlineKeyboardButton(
            f"{uc} UC — {price_str} ₽", 
            callback_data=f"buy_{uc}_{price}"
        ))
    bot.send_message(
        message.chat.id,
        "🛒 <b>ВЫБЕРИТЕ ПАКЕТ UC:</b>",
        parse_mode='HTML',
        reply_markup=markup,
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def select_package(call):
    data = call.data.split('_')
    uc_amount = int(data[1])
    price = int(data[2])
    
    # Проверяем промокод
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT discount FROM user_promos WHERE user_id = ? LIMIT 1", (call.from_user.id,))
    promo = c.fetchone()
    conn.close()
    
    final_price = price
    discount_text = ""
    if promo:
        discount = promo[0]
        final_price = int(price * (100 - discount) / 100)
        discount_text = f"\n🎟 Скидка {discount}%: {final_price:,} ₽"
    
    msg = bot.send_message(
        call.message.chat.id,
        f"📝 <b>ВВЕДИТЕ ID В PUBG:</b>\n\n🎮 {uc_amount} UC\n💰 Цена: {price:,} ₽{discount_text}\n\nID должен начинаться с <b>5</b>.\nПример: <code>5123456789</code>",
        parse_mode='HTML'
    )
    bot.register_next_step_handler(msg, process_player_id, uc_amount, final_price)

def process_player_id(message, uc_amount, price):
    player_id = message.text.strip()

    if not player_id.isdigit() or len(player_id) < 5 or not player_id.startswith('5'):
        bot.send_message(
            message.chat.id,
            "❌ <b>ОШИБКА!</b>\n\nВведите корректный ID (только цифры, минимум 5 символов), который начинается с <b>5</b>.",
            parse_mode='HTML'
        )
        return

    order_number = get_next_order_number()
    user_id = message.from_user.id

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()

    c.execute("""INSERT INTO orders 
                 (order_number, user_id, username, player_id, uc_amount, price, status, created_at)
                 VALUES (?,?,?,?,?,?,?,?)""",
              (order_number, user_id, message.from_user.username or "Нет username", 
               player_id, uc_amount, price, 'pending', str(datetime.now())))

    conn.commit()
    conn.close()

    # Показываем реквизиты
    text = f"""
✅ <b>ЗАКАЗ №{order_number}</b>

📦 {uc_amount} UC
💰 {price:,} ₽
🆔 {player_id}

💳 <b>РЕКВИЗИТЫ:</b>
"""
    for card in CARDS:
        text += f"\n🏦 {card['bank']}\n💳 <code>{card['card']}</code>\n👤 {card['recipient']}\n"

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Я ОПЛАТИЛ", callback_data=f"paid_{order_number}"),
        types.InlineKeyboardButton("❌ ОТМЕНА", callback_data=f"cancel_{order_number}")
    )
    
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)

# ---------- ПОДТВЕРЖДЕНИЕ ОПЛАТЫ ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('paid_'))
def user_paid(call):
    order_number = int(call.data.split('_')[1])

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ <b>ЗАКАЗ №{order_number}</b>\n\nОжидайте подтверждения...",
        parse_mode='HTML'
    )

    # Уведомляем админа
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT username, player_id, uc_amount, price FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    conn.close()

    if order:
        username, player_id, uc_amount, price = order
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{order_number}"),
            types.InlineKeyboardButton("❌ Отменить", callback_data=f"reject_{order_number}")
        )
        
        bot.send_message(
            ADMIN_ID,
            f"💰 <b>ЗАКАЗ №{order_number}</b>\n\n👤 @{username}\n🎮 {uc_amount} UC\n💰 {price:,} ₽\n🆔 {player_id}",
            parse_mode='HTML',
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def admin_confirm(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    order_number = int(call.data.split('_')[1])

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("UPDATE orders SET status = 'completed', completed_at = ? WHERE order_number = ?",
              (str(datetime.now()), order_number))
    c.execute("SELECT user_id, uc_amount FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    if order:
        user_id, uc_amount = order
        c.execute("UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1 WHERE user_id = ?",
                  (uc_amount, user_id))
    conn.commit()
    conn.close()

    if order:
        bot.send_message(order[0], f"✅ <b>ЗАКАЗ №{order_number} ВЫПОЛНЕН!</b>")

    bot.answer_callback_query(call.id, "✅ Подтверждено")
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"✅ <b>ЗАКАЗ №{order_number} ПОДТВЕРЖДЕН</b>",
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('reject_'))
def admin_reject(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Нет прав")
        return

    order_number = int(call.data.split('_')[1])

    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM orders WHERE order_number = ?", (order_number,))
    order = c.fetchone()
    conn.close()

    if order:
        bot.send_message(order[0], f"❌ <b>ЗАКАЗ №{order_number} ОТМЕНЕН</b>")

    bot.answer_callback_query(call.id, "❌ Отменено")
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
        text=f"❌ <b>ЗАКАЗ №{order_number} ОТМЕНЕН</b>",
        parse_mode='HTML'
    )

# ---------- ПРОФИЛЬ ----------
@bot.message_handler(func=lambda message: message.text == "👤 МОЙ ПРОФИЛЬ")
def my_profile(message):
    user_id = message.from_user.id
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT total_uc, total_orders, join_date, first_name FROM users WHERE user_id = ?", (user_id,))
    user_data = c.fetchone()
    conn.close()

    if user_data:
        total_uc, total_orders, join_date, first_name = user_data
        join_date_str = join_date[:10] if join_date else "Неизвестно"
    else:
        total_uc, total_orders, join_date_str, first_name = 0, 0, str(datetime.now())[:10], "Игрок"

    bot.send_message(
        message.chat.id,
        f"👤 <b>{first_name}</b>\n\n🆔 {user_id}\n📅 С {join_date_str}\n📦 Заказов: {total_orders}\n🎮 UC: {total_uc}",
        parse_mode='HTML'
    )

# ---------- ЛИДЕРЫ ----------
@bot.message_handler(func=lambda message: message.text == "🏆 ЛИДЕРЫ")
def leaders(message):
    conn = sqlite3.connect('uc_bot.db')
    c = conn.cursor()
    c.execute("SELECT first_name, total_uc FROM users WHERE total_uc > 0 ORDER BY total_uc DESC LIMIT 10")
    leaders_list = c.fetchall()
    conn.close()

    if not leaders_list:
        bot.send_message(message.chat.id, "🏆 <b>ЛИДЕРОВ ПОКА НЕТ</b>", parse_mode='HTML')
        return

    text = "🏆 <b>ТОП-10</b>\n\n"
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    for i, (name, uc) in enumerate(leaders_list):
        text += f"{medals[i]} {name} — {uc} UC\n"
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# ---------- ОТЗЫВЫ ----------
@bot.message_handler(func=lambda message: message.text == "⭐️ ОТЗЫВЫ")
def reviews(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📢 КАНАЛ", url=f"https://t.me/{REVIEWS_CHANNEL}"))
    bot.send_message(message.chat.id, "⭐️ <b>НАШИ ОТЗЫВЫ</b>", parse_mode='HTML', reply_markup=markup)

# ---------- ПОДДЕРЖКА ----------
@bot.message_handler(func=lambda message: message.text == "📞 ПОДДЕРЖКА")
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👨‍💼 НАПИСАТЬ", url=f"https://t.me/{SUPPORT_USERNAME}"))
    bot.send_message(message.chat.id, "📞 <b>ПОДДЕРЖКА</b>", parse_mode='HTML', reply_markup=markup)

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    print("🔄 Запуск...")
    init_db()
    print("✅ БОТ РАБОТАЕТ!")
    
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
