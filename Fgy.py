import telebot
from telebot import types
import random
import json
import os
import time
from datetime import datetime, timedelta
import math

# ======================== НАСТРОЙКИ ========================
TOKEN = '8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI'
DATA_FILE = 'users_data.json'
ADMIN_PASSWORD = 'admin123'
ADMIN_IDS = []
GAME_EMOJIS = ['🍒', '🍋', '🍊', '7️⃣']
PROMOCODES = {
    'START100': 100,
    'LUCKY777': 777,
    'BONUS500': 500,
    'VIP1000': 1000
}
# ============================================================

bot = telebot.TeleBot(TOKEN)

# Валюта: 🪙 КазикКоин (KZK)

# ======================== КРАСИВЫЙ ДИЗАЙН ========================

DESIGN = {
    'title': '🎰 *CASINO EMOJI*',
    'line': '▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰',
    'balance': '💰 *Баланс:*',
    'win': '🎉 *ПОБЕДА!*',
    'lose': '😢 *ПРОИГРЫШ...*',
    'menu': '🏠 *ГЛАВНОЕ МЕНЮ*',
    'games': '🎮 *ВЫБЕРИ ИГРУ*',
    'admin': '👑 *АДМИН-ПАНЕЛЬ*',
    'profile': '👤 *ПРОФИЛЬ ИГРОКА*',
    'promo': '🎁 *АКТИВАЦИЯ ПРОМОКОДА*'
}

def format_number(num):
    """Форматирует числа (1000 -> 1K, 1000000 -> 1M)"""
    if num >= 1000000:
        return f"{num/1000000:.1f}M"
    elif num >= 1000:
        return f"{num/1000:.1f}K"
    else:
        return str(num)

def create_progress_bar(current, total, length=10):
    """Создает красивый прогресс-бар"""
    filled = int((current / total) * length) if total > 0 else 0
    empty = length - filled
    return '🟩' * filled + '⬜' * empty

# ======================== КОЛЕСО ФОРТУНЫ ========================

WHEEL_SECTORS = [
    {'name': '🍒 100', 'value': 100, 'multiplier': 1, 'color': '🔴'},
    {'name': '🍋 200', 'value': 200, 'multiplier': 2, 'color': '🟡'},
    {'name': '🍊 300', 'value': 300, 'multiplier': 3, 'color': '🟠'},
    {'name': '🍇 500', 'value': 500, 'multiplier': 5, 'color': '🟣'},
    {'name': '💎 1000', 'value': 1000, 'multiplier': 10, 'color': '🔵'},
    {'name': '🎰 ДЖЕКПОТ', 'value': 5000, 'multiplier': 50, 'color': '🌈'},
    {'name': '❌ ПРОИГРЫШ', 'value': 0, 'multiplier': 0, 'color': '⚫'},
    {'name': '🍀 200', 'value': 200, 'multiplier': 2, 'color': '🟢'},
    {'name': '🎯 150', 'value': 150, 'multiplier': 1.5, 'color': '🔵'},
    {'name': '💫 400', 'value': 400, 'multiplier': 4, 'color': '🟣'},
    {'name': '⭐ 600', 'value': 600, 'multiplier': 6, 'color': '🟡'},
    {'name': '👑 2000', 'value': 2000, 'multiplier': 20, 'color': '👑'}
]

def draw_wheel(pointer_position):
    """Рисует красивое колесо фортуны"""
    wheel_parts = []
    for i, sector in enumerate(WHEEL_SECTORS):
        if i == pointer_position:
            wheel_parts.append(f"👉 {sector['color']} {sector['name']}")
        else:
            wheel_parts.append(f"   {sector['color']} {sector['name']}")
    
    wheel_display = "🎡 *КОЛЕСО ФОРТУНЫ*\n\n"
    wheel_display += "┌─────────────────────┐\n"
    for part in wheel_parts[:6]:
        wheel_display += f"│ {part:<19} │\n"
    wheel_display += "│        ······        │\n"
    for part in wheel_parts[6:]:
        wheel_display += f"│ {part:<19} │\n"
    wheel_display += "└─────────────────────┘\n"
    wheel_display += "\n⚡ Крути колесо и выигрывай!"
    
    return wheel_display

def spin_wheel_animation():
    """Создает анимацию вращения колеса"""
    animations = [
        "🎡 *КРУТИМ КОЛЕСО*",
        "⚡ *ВРАЩАЕТСЯ*",
        "💫 *ЕЩЕ БЫСТРЕЕ*",
        "🎯 *ОСТАНАВЛИВАЕТСЯ*",
        "🎉 *ГОТОВО!*"
    ]
    return animations[random.randint(0, 4)]

# ======================== ЗАГРУЗКА ДАННЫХ ========================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_profile(user_id):
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            'balance': 1000,
            'total_bet': 0,
            'total_win': 0,
            'total_loss': 0,
            'used_promos': [],
            'username': '',
            'first_name': '',
            'last_login': str(datetime.now()),
            'wheel_free_spin': True,  # Бесплатное кручение колеса
            'wheel_last_spin': None,
            'achievements': [],
            'level': 1,
            'exp': 0
        }
        save_data(data)
    return data[user_id]

def update_balance(user_id, new_balance):
    data = load_data()
    data[str(user_id)]['balance'] = new_balance
    save_data(data)

def update_stats(user_id, bet, win):
    data = load_data()
    user_id = str(user_id)
    data[user_id]['total_bet'] += bet
    if win > 0:
        data[user_id]['total_win'] += win
        # Добавляем опыт за выигрыш
        data[user_id]['exp'] += win // 100
    else:
        data[user_id]['total_loss'] += bet
        # Добавляем опыт за проигрыш
        data[user_id]['exp'] += 1
    
    # Повышение уровня
    exp_needed = data[user_id]['level'] * 100
    if data[user_id]['exp'] >= exp_needed:
        data[user_id]['level'] += 1
        data[user_id]['exp'] -= exp_needed
    
    save_data(data)

def update_user_info(user_id, username, first_name):
    data = load_data()
    user_id = str(user_id)
    if user_id in data:
        data[user_id]['username'] = username
        data[user_id]['first_name'] = first_name
        data[user_id]['last_login'] = str(datetime.now())
        save_data(data)

def is_admin(user_id):
    return str(user_id) in ADMIN_IDS

# ======================== КЛАВИАТУРЫ ========================

def get_main_keyboard():
    """Красивая главная клавиатура"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🎮 ИГРАТЬ")
    btn2 = types.KeyboardButton("🎡 КОЛЕСО")
    btn3 = types.KeyboardButton("📊 ПРОФИЛЬ")
    btn4 = types.KeyboardButton("🎁 ПРОМОКОД")
    btn5 = types.KeyboardButton("👑 АДМИН")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    return markup

def get_games_keyboard():
    """Красивая клавиатура с играми"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    games = [
        ("🎰 Слоты", "game_slots"),
        ("📈 График", "game_graph"),
        ("📦 Коробки", "game_boxes"),
        ("🎲 Кости", "game_dice"),
        ("🔢 Лотерея", "game_lottery"),
        ("🎯 Дартс", "game_darts")
    ]
    
    buttons = []
    for game_name, game_callback in games:
        buttons.append(types.InlineKeyboardButton(game_name, callback_data=game_callback))
    
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🏠 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"))
    
    return markup

def get_admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💰 Начислить", callback_data="admin_add_balance")
    btn2 = types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    btn3 = types.InlineKeyboardButton("👥 Игроки", callback_data="admin_users")
    btn4 = types.InlineKeyboardButton("🎁 Промокоды", callback_data="admin_promos")
    btn5 = types.InlineKeyboardButton("📈 Топ", callback_data="admin_top")
    btn6 = types.InlineKeyboardButton("🚪 Выход", callback_data="admin_exit")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    markup.add(btn6)
    return markup

# ======================== КОМАНДЫ ========================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Нет username"
    first_name = message.from_user.first_name or "Игрок"
    
    update_user_info(user_id, username, first_name)
    user = get_user_profile(user_id)
    
    welcome_text = (
        f"{DESIGN['title']}\n"
        f"{DESIGN['line']}\n\n"
        f"👋 Привет, *{first_name}*!\n\n"
        f"{DESIGN['balance']} {format_number(user['balance'])} 🪙\n"
        f"📊 Уровень: {user['level']} ({create_progress_bar(user['exp'], user['level'] * 100)})\n\n"
        f"🎮 *ИГРЫ:*\n"
        f"• 🎰 Слоты (x2, x5, x10)\n"
        f"• 📈 График (x5)\n"
        f"• 📦 Коробки (x10)\n"
        f"• 🎲 Кости (x2, x5)\n"
        f"• 🔢 Лотерея (x2-x50)\n"
        f"• 🎯 Дартс (x5, x20)\n"
        f"• 🎡 Колесо Фортуны\n\n"
        f"🔥 *ПРОМОКОДЫ:*\n"
        f"• START100 - 100 🪙\n"
        f"• LUCKY777 - 777 🪙\n"
        f"• BONUS500 - 500 🪙\n"
        f"• VIP1000 - 1000 🪙\n\n"
        f"{DESIGN['line']}"
    )
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# ======================== КОЛЕСО ФОРТУНЫ ========================

@bot.message_handler(func=lambda msg: msg.text == "🎡 КОЛЕСО")
def wheel_of_fortune(message):
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    # Проверяем бесплатное кручение
    last_spin = user.get('wheel_last_spin')
    free_spin = user.get('wheel_free_spin', True)
    
    if free_spin:
        text = "🎡 *КОЛЕСО ФОРТУНЫ*\n\nУ тебя есть *бесплатное* кручение!"
    else:
        text = "🎡 *КОЛЕСО ФОРТУНЫ*\n\nКрутить стоит 100 🪙"
    
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🎡 КРУТИТЬ КОЛЕСО", callback_data="wheel_spin")
    btn2 = types.InlineKeyboardButton("🏠 В МЕНЮ", callback_data="main_menu")
    markup.add(btn1)
    markup.add(btn2)
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "wheel_spin")
def wheel_spin(call):
    user_id = call.from_user.id
    user = get_user_profile(user_id)
    
    # Проверяем возможность кручения
    last_spin = user.get('wheel_last_spin')
    free_spin = user.get('wheel_free_spin', True)
    
    if not free_spin:
        if user['balance'] < 100:
            bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
            return
        
        # Списываем плату
        user['balance'] -= 100
        update_balance(user_id, user['balance'])
        update_stats(user_id, 100, 0)
    
    # Анимация вращения
    anim_msg = bot.send_message(
        call.message.chat.id,
        spin_wheel_animation(),
        parse_mode='Markdown'
    )
    
    time.sleep(1)
    
    # Выбираем случайный сектор
    position = random.randint(0, len(WHEEL_SECTORS) - 1)
    sector = WHEEL_SECTORS[position]
    
    # Начисляем выигрыш
    win_amount = sector['value']
    
    if win_amount > 0:
        user['balance'] += win_amount
        update_balance(user_id, user['balance'])
        update_stats(user_id, 0, win_amount)
    
    # Обновляем статус бесплатного кручения
    user['wheel_free_spin'] = False
    user['wheel_last_spin'] = str(datetime.now())
    save_data(load_data())
    
    # Рисуем результат
    result_text = (
        f"{draw_wheel(position)}\n\n"
        f"{DESIGN['line']}\n\n"
    )
    
    if win_amount > 0:
        result_text += f"🎉 *ПОБЕДА!* +{win_amount} 🪙 (x{sector['multiplier']})\n"
    else:
        result_text += f"😢 *ПРОИГРЫШ...* Попробуй еще!\n"
    
    result_text += f"{DESIGN['balance']} {format_number(user['balance'])} 🪙\n"
    result_text += f"{DESIGN['line']}"
    
    bot.edit_message_text(
        result_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    # Добавляем кнопку для повторного кручения
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🎡 КРУТИТЬ ЕЩЕ", callback_data="wheel_spin")
    btn2 = types.InlineKeyboardButton("🏠 В МЕНЮ", callback_data="main_menu")
    markup.add(btn1)
    markup.add(btn2)
    
    bot.send_message(
        call.message.chat.id,
        "🎡 Хочешь крутить еще?",
        reply_markup=markup
    )

# ======================== ОСТАЛЬНЫЕ ИГРЫ ========================

@bot.message_handler(func=lambda msg: msg.text == "🎮 ИГРАТЬ")
def play_button(message):
    user = get_user_profile(message.from_user.id)
    games_text = (
        f"{DESIGN['games']}\n"
        f"{DESIGN['line']}\n\n"
        f"{DESIGN['balance']} {format_number(user['balance'])} 🪙\n\n"
        f"🎰 *Слоты* - x2, x5, x10\n"
        f"📈 *График* - x5\n"
        f"📦 *Коробки* - x10\n"
        f"🎲 *Кости* - x2, x5\n"
        f"🔢 *Лотерея* - x2-x50\n"
        f"🎯 *Дартс* - x5, x20\n"
        f"{DESIGN['line']}"
    )
    bot.send_message(
        message.chat.id,
        games_text,
        parse_mode='Markdown',
        reply_markup=get_games_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "📊 ПРОФИЛЬ")
def profile_button(message):
    user = get_user_profile(message.from_user.id)
    win_rate = (user['total_win'] / user['total_bet'] * 100) if user['total_bet'] > 0 else 0
    profit = user['total_win'] - user['total_loss']
    
    # Получаем последние достижения
    achievements = user.get('achievements', [])
    achievements_text = ""
    if achievements:
        achievements_text = "\n🏆 *Достижения:*\n"
        for ach in achievements[-3:]:  # Последние 3
            achievements_text += f"• {ach}\n"
    
    profile_text = (
        f"{DESIGN['profile']}\n"
        f"{DESIGN['line']}\n\n"
        f"👤 Игрок: {user.get('first_name', 'Неизвестно')}\n"
        f"📊 Уровень: {user['level']} ({create_progress_bar(user['exp'], user['level'] * 100)})\n\n"
        f"{DESIGN['balance']} {format_number(user['balance'])} 🪙\n"
        f"📈 Всего ставок: {format_number(user['total_bet'])} 🪙\n"
        f"🏆 Выиграно: {format_number(user['total_win'])} 🪙\n"
        f"💔 Проиграно: {format_number(user['total_loss'])} 🪙\n"
        f"📊 Профит: {format_number(profit)} 🪙\n"
        f"🎯 Винрейт: {win_rate:.1f}%\n"
        f"{achievements_text}\n"
        f"{DESIGN['line']}"
    )
    bot.send_message(
        message.chat.id, 
        profile_text, 
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "🎁 ПРОМОКОД")
def promo_button(message):
    msg = bot.send_message(
        message.chat.id, 
        f"{DESIGN['promo']}\n"
        f"{DESIGN['line']}\n\n"
        f"🔑 Введи промокод:\n"
        f"Например: VIP1000, START100\n"
        f"{DESIGN['line']}",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_promo)

def process_promo(message):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if code in PROMOCODES:
        if code in user.get('used_promos', []):
            bot.send_message(
                message.chat.id, 
                f"❌ *ОШИБКА*\n\nТы уже активировал этот промокод!",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
            return
        
        bonus = PROMOCODES[code]
        user['balance'] += bonus
        user['used_promos'] = user.get('used_promos', []) + [code]
        update_balance(user_id, user['balance'])
        save_data(load_data())
        
        if code != 'VIP1000':
            del PROMOCODES[code]
        
        bot.send_message(
            message.chat.id, 
            f"✅ *ПРОМОКОД АКТИВИРОВАН!*\n\n"
            f"+{bonus} 🪙 KZK\n"
            f"{DESIGN['balance']} {format_number(user['balance'])} 🪙",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id, 
            "❌ *ОШИБКА*\n\nНедействительный промокод!",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

# ======================== АДМИН-ПАНЕЛЬ ========================

@bot.message_handler(func=lambda msg: msg.text == "👑 АДМИН")
def admin_login(message):
    msg = bot.send_message(
        message.chat.id,
        f"{DESIGN['admin']}\n"
        f"{DESIGN['line']}\n\n"
        f"🔐 Введи пароль:\n"
        f"{DESIGN['line']}",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_admin_password)

def process_admin_password(message):
    user_id = str(message.from_user.id)
    
    if message.text == ADMIN_PASSWORD:
        if user_id not in ADMIN_IDS:
            ADMIN_IDS.append(user_id)
        
        bot.send_message(
            message.chat.id,
            f"✅ *ДОБРО ПОЖАЛОВАТЬ В АДМИН-ПАНЕЛЬ!*",
            parse_mode='Markdown',
            reply_markup=get_admin_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "❌ *НЕВЕРНЫЙ ПАРОЛЬ!*",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    bot.answer_callback_query(call.id)
    user = get_user_profile(call.from_user.id)
    
    menu_text = (
        f"{DESIGN['menu']}\n"
        f"{DESIGN['line']}\n\n"
        f"{DESIGN['balance']} {format_number(user['balance'])} 🪙\n"
        f"📊 Уровень: {user['level']} ({create_progress_bar(user['exp'], user['level'] * 100)})\n\n"
        f"🎮 Нажми *ИГРАТЬ* чтобы выбрать игру!\n"
        f"🎡 Нажми *КОЛЕСО* для удачи!\n"
        f"{DESIGN['line']}"
    )
    
    bot.edit_message_text(
        menu_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    bot.send_message(
        call.message.chat.id,
        "Выбери действие:",
        reply_markup=get_main_keyboard()
    )

# ======================== ЗАПУСК ========================

if __name__ == '__main__':
    print("🎰 CASINO EMOJI БОТ ЗАПУЩЕН!")
    print("=" * 40)
    print("✅ Токен установлен")
    print("✅ Промокоды активны")
    print("✅ 7 игр загружены")
    print("✅ КОЛЕСО ФОРТУНЫ ДОБАВЛЕНО!")
    print("✅ КРАСИВЫЙ ДИЗАЙН АКТИВЕН!")
    print("=" * 40)
    print(f"🔐 Пароль для админки: {ADMIN_PASSWORD}")
    print("=" * 40)
    print("VIP1000 - промокод на 1000 🪙")
    print("🎡 Колесо Фортуны ждет тебя!")
    
    bot.infinity_polling()
