import telebot
from telebot import types
import random
import json
import os
import time
from datetime import datetime

# ======================== НАСТРОЙКИ ========================
TOKEN = '8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI'
DATA_FILE = 'users_data.json'
ADMIN_PASSWORD = 'admin123'  # Пароль для входа в админ-панель
ADMIN_IDS = []  # Сюда автоматически добавятся админы после входа
GAME_EMOJIS = ['🍒', '🍋', '🍊', '7️⃣']  # Для игрового автомата
PROMOCODES = {
    'START100': 100,
    'LUCKY777': 777,
    'BONUS500': 500,
    'VIP1000': 1000  # Бесконечный промокод
}
# ============================================================

bot = telebot.TeleBot(TOKEN)

# Валюта: 🪙 КазикКоин (KZK)

def load_data():
    """Загружает данные пользователей из JSON файла"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    """Сохраняет данные пользователей в JSON файл"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_profile(user_id):
    """Возвращает профиль пользователя, создает если нет"""
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            'balance': 1000,  # Стартовый баланс
            'total_bet': 0,
            'total_win': 0,
            'total_loss': 0,
            'used_promos': [],
            'username': '',
            'first_name': '',
            'last_login': str(datetime.now())
        }
        save_data(data)
    return data[user_id]

def update_balance(user_id, new_balance):
    """Обновляет баланс пользователя"""
    data = load_data()
    data[str(user_id)]['balance'] = new_balance
    save_data(data)

def update_stats(user_id, bet, win):
    """Обновляет статистику игрока"""
    data = load_data()
    user_id = str(user_id)
    data[user_id]['total_bet'] += bet
    if win > 0:
        data[user_id]['total_win'] += win
    else:
        data[user_id]['total_loss'] += bet
    save_data(data)

def add_used_promo(user_id, promo_code):
    """Добавляет промокод в список использованных"""
    data = load_data()
    user_id = str(user_id)
    if 'used_promos' not in data[user_id]:
        data[user_id]['used_promos'] = []
    data[user_id]['used_promos'].append(promo_code)
    save_data(data)

def has_used_promo(user_id, promo_code):
    """Проверяет, использовал ли пользователь промокод"""
    data = load_data()
    user_id = str(user_id)
    if 'used_promos' not in data[user_id]:
        return False
    return promo_code in data[user_id]['used_promos']

def update_user_info(user_id, username, first_name):
    """Обновляет информацию о пользователе"""
    data = load_data()
    user_id = str(user_id)
    if user_id in data:
        data[user_id]['username'] = username
        data[user_id]['first_name'] = first_name
        data[user_id]['last_login'] = str(datetime.now())
        save_data(data)

def is_admin(user_id):
    """Проверяет, является ли пользователь админом"""
    return str(user_id) in ADMIN_IDS

def get_main_keyboard():
    """Создает главную клавиатуру с одной кнопкой ИГРАТЬ"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🎮 ИГРАТЬ")
    btn2 = types.KeyboardButton("📊 ПРОФИЛЬ")
    btn3 = types.KeyboardButton("🎁 ПРОМОКОД")
    btn4 = types.KeyboardButton("👑 АДМИН")  # Кнопка для входа в админку
    markup.add(btn1)
    markup.add(btn2, btn3, btn4)
    return markup

def get_games_keyboard():
    """Создает клавиатуру с выбором игр"""
    markup = types.InlineKeyboardMarkup(row_width=3)
    
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
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    return markup

def get_admin_keyboard():
    """Создает клавиатуру для админ-панели"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("💰 Начислить валюту", callback_data="admin_add_balance")
    btn2 = types.InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
    btn3 = types.InlineKeyboardButton("👥 Список игроков", callback_data="admin_users")
    btn4 = types.InlineKeyboardButton("🎁 Управление промокодами", callback_data="admin_promos")
    btn5 = types.InlineKeyboardButton("📈 Топ игроков", callback_data="admin_top")
    btn6 = types.InlineKeyboardButton("🚪 Выйти из админки", callback_data="admin_exit")
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
    
    # Обновляем информацию о пользователе
    update_user_info(user_id, username, first_name)
    user = get_user_profile(user_id)
    
    welcome_text = (
        f"🎰 *CASINO EMOJI*\n\n"
        f"👋 Привет, {first_name}!\n"
        f"💰 Твой баланс: {user['balance']} 🪙 KZK\n\n"
        f"🎮 *ИГРЫ:*\n"
        f"• 🎰 Слоты (x2, x5, x10)\n"
        f"• 📈 График (x5)\n"
        f"• 📦 Коробки (x10)\n"
        f"• 🎲 Кости (x2, x5)\n"
        f"• 🔢 Лотерея (x2-x50)\n"
        f"• 🎯 Дартс (x5, x20)\n\n"
        f"🔥 *ПРОМОКОДЫ:*\n"
        f"• START100 - 100 🪙\n"
        f"• LUCKY777 - 777 🪙\n"
        f"• BONUS500 - 500 🪙\n"
        f"• VIP1000 - 1000 🪙 (∞)"
    )
    bot.send_message(
        message.chat.id, 
        welcome_text, 
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# ======================== АДМИН-ПАНЕЛЬ ========================

@bot.message_handler(func=lambda msg: msg.text == "👑 АДМИН")
def admin_login(message):
    msg = bot.send_message(
        message.chat.id,
        "🔐 *ВХОД В АДМИН-ПАНЕЛЬ*\n\nВведи пароль:",
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
            "✅ *ДОБРО ПОЖАЛОВАТЬ В АДМИН-ПАНЕЛЬ!*\n\nВыбери действие:",
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback(call):
    user_id = str(call.from_user.id)
    
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ У тебя нет прав администратора!")
        return
    
    bot.answer_callback_query(call.id)
    
    if call.data == "admin_add_balance":
        msg = bot.send_message(
            call.message.chat.id,
            "💰 *НАЧИСЛЕНИЕ ВАЛЮТЫ*\n\nВведи ID пользователя и сумму через пробел\nПример: `123456789 1000`",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(msg, process_admin_add_balance)
    
    elif call.data == "admin_stats":
        show_admin_stats(call.message)
    
    elif call.data == "admin_users":
        show_admin_users(call.message)
    
    elif call.data == "admin_promos":
        show_admin_promos(call.message)
    
    elif call.data == "admin_top":
        show_admin_top(call.message)
    
    elif call.data == "admin_exit":
        if user_id in ADMIN_IDS:
            ADMIN_IDS.remove(user_id)
        bot.edit_message_text(
            "👋 *ВЫХОД ИЗ АДМИН-ПАНЕЛИ*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        bot.send_message(
            call.message.chat.id,
            "Главное меню:",
            reply_markup=get_main_keyboard()
        )

def process_admin_add_balance(message):
    if not is_admin(str(message.from_user.id)):
        bot.send_message(message.chat.id, "❌ Нет доступа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            raise ValueError
        
        target_id = parts[0].strip()
        amount = int(parts[1])
        
        data = load_data()
        
        if target_id not in data:
            # Создаем пользователя если не существует
            data[target_id] = {
                'balance': 1000,
                'total_bet': 0,
                'total_win': 0,
                'total_loss': 0,
                'used_promos': [],
                'username': 'Неизвестно',
                'first_name': 'Пользователь',
                'last_login': str(datetime.now())
            }
        
        # Начисляем валюту
        data[target_id]['balance'] += amount
        save_data(data)
        
        # Пытаемся уведомить пользователя
        try:
            bot.send_message(
                int(target_id),
                f"👑 *АДМИН НАЧИСЛИЛ БОНУС!*\n\n+{amount} 🪙 KZK",
                parse_mode='Markdown'
            )
        except:
            pass  # Пользователь не начал чат с ботом
        
        user_info = data[target_id]
        name = user_info.get('first_name', 'Пользователь')
        
        bot.send_message(
            message.chat.id,
            f"✅ *УСПЕШНО!*\n\nНачислено {amount} 🪙 пользователю {name} (ID: {target_id})\nНовый баланс: {data[target_id]['balance']} 🪙",
            parse_mode='Markdown',
            reply_markup=get_admin_keyboard()
        )
        
    except Exception as e:
        bot.send_message(
            message.chat.id,
            "❌ *ОШИБКА!*\n\nНеправильный формат. Используй: `ID сумма`",
            parse_mode='Markdown',
            reply_markup=get_admin_keyboard()
        )

def show_admin_stats(message):
    data = load_data()
    
    total_users = len(data)
    total_balance = sum(user['balance'] for user in data.values())
    total_bets = sum(user['total_bet'] for user in data.values())
    total_wins = sum(user['total_win'] for user in data.values())
    total_losses = sum(user['total_loss'] for user in data.values())
    avg_balance = total_balance // total_users if total_users > 0 else 0
    
    stats_text = (
        f"📊 *ОБЩАЯ СТАТИСТИКА*\n\n"
        f"👥 Всего игроков: {total_users}\n"
        f"💰 Общий баланс: {total_balance} 🪙\n"
        f"📊 Средний баланс: {avg_balance} 🪙\n"
        f"📈 Всего ставок: {total_bets} 🪙\n"
        f"🏆 Всего выигрышей: {total_wins} 🪙\n"
        f"💔 Всего проигрышей: {total_losses} 🪙\n"
        f"📊 Профит казино: {total_bets - total_wins} 🪙"
    )
    
    bot.send_message(
        message.chat.id,
        stats_text,
        parse_mode='Markdown',
        reply_markup=get_admin_keyboard()
    )

def show_admin_users(message):
    data = load_data()
    
    # Сортируем пользователей по балансу
    sorted_users = sorted(data.items(), key=lambda x: x[1]['balance'], reverse=True)
    
    users_text = "👥 *СПИСОК ИГРОКОВ*\n\n"
    
    for i, (user_id, user_data) in enumerate(sorted_users[:10], 1):
        name = user_data.get('first_name', 'Неизвестно')
        username = user_data.get('username', '')
        balance = user_data['total_win'] - user_data['total_loss']
        
        users_text += f"{i}. *{name}*\n"
        users_text += f"   🆔 `{user_id}`\n"
        users_text += f"   💰 Баланс: {user_data['balance']} 🪙\n"
        users_text += f"   📊 Профит: {balance} 🪙\n\n"
    
    users_text += f"📊 Всего игроков: {len(data)}"
    
    bot.send_message(
        message.chat.id,
        users_text,
        parse_mode='Markdown',
        reply_markup=get_admin_keyboard()
    )

def show_admin_promos(message):
    promos_text = "🎁 *УПРАВЛЕНИЕ ПРОМОКОДАМИ*\n\n"
    
    for code, value in PROMOCODES.items():
        promos_text += f"• `{code}` - {value} 🪙\n"
    
    promos_text += "\nЧтобы добавить промокод, введи:\n`/addpromo КОД СУММА`\n\nЧтобы удалить промокод:\n`/delpromo КОД`"
    
    bot.send_message(
        message.chat.id,
        promos_text,
        parse_mode='Markdown',
        reply_markup=get_admin_keyboard()
    )

def show_admin_top(message):
    data = load_data()
    
    # Топ по балансу
    top_balance = sorted(data.items(), key=lambda x: x[1]['balance'], reverse=True)[:5]
    
    # Топ по выигрышам
    top_wins = sorted(data.items(), key=lambda x: x[1]['total_win'], reverse=True)[:5]
    
    # Топ по активности (сумма ставок)
    top_active = sorted(data.items(), key=lambda x: x[1]['total_bet'], reverse=True)[:5]
    
    top_text = "🏆 *ТОП ИГРОКОВ*\n\n"
    
    top_text += "💰 *По балансу:*\n"
    for i, (user_id, user_data) in enumerate(top_balance, 1):
        name = user_data.get('first_name', 'Игрок')
        top_text += f"{i}. {name} - {user_data['balance']} 🪙\n"
    
    top_text += "\n🏆 *По выигрышам:*\n"
    for i, (user_id, user_data) in enumerate(top_wins, 1):
        name = user_data.get('first_name', 'Игрок')
        top_text += f"{i}. {name} - {user_data['total_win']} 🪙\n"
    
    top_text += "\n🎯 *По активности:*\n"
    for i, (user_id, user_data) in enumerate(top_active, 1):
        name = user_data.get('first_name', 'Игрок')
        top_text += f"{i}. {name} - {user_data['total_bet']} 🪙\n"
    
    bot.send_message(
        message.chat.id,
        top_text,
        parse_mode='Markdown',
        reply_markup=get_admin_keyboard()
    )

# Команды для управления промокодами (только для админов)
@bot.message_handler(commands=['addpromo'])
def add_promo(message):
    if not is_admin(str(message.from_user.id)):
        bot.send_message(message.chat.id, "❌ Нет доступа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ Формат: /addpromo КОД СУММА")
            return
        
        code = parts[1].upper()
        value = int(parts[2])
        
        PROMOCODES[code] = value
        
        bot.send_message(
            message.chat.id,
            f"✅ Промокод `{code}` добавлен! Сумма: {value} 🪙",
            parse_mode='Markdown'
        )
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Проверь формат.")

@bot.message_handler(commands=['delpromo'])
def del_promo(message):
    if not is_admin(str(message.from_user.id)):
        bot.send_message(message.chat.id, "❌ Нет доступа!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ Формат: /delpromo КОД")
            return
        
        code = parts[1].upper()
        
        if code in PROMOCODES:
            del PROMOCODES[code]
            bot.send_message(message.chat.id, f"✅ Промокод `{code}` удален!", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "❌ Промокод не найден!")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка!")

@bot.message_handler(func=lambda msg: msg.text == "🎮 ИГРАТЬ")
def play_button(message):
    user = get_user_profile(message.from_user.id)
    games_text = (
        f"🎮 *ВЫБЕРИ ИГРУ*\n\n"
        f"💰 Твой баланс: {user['balance']} 🪙 KZK\n\n"
        f"🎰 *Слоты* - классический автомат (x2, x5, x10)\n"
        f"📈 *График* - угадай вверх/вниз (x5)\n"
        f"📦 *Коробки* - найди шарик (x10)\n"
        f"🎲 *Кости* - ставки на сумму кубиков (x2, x5)\n"
        f"🔢 *Лотерея* - угадай числа (x2-x50)\n"
        f"🎯 *Дартс* - попади в цель (x5, x20)"
    )
    bot.send_message(
        message.chat.id,
        games_text,
        parse_mode='Markdown',
        reply_markup=get_games_keyboard()
    )

@bot.message_handler(func=lambda msg: msg.text == "📊 ПРОФИЛЬ")
def profile_button(message):
    show_profile(message)

@bot.message_handler(func=lambda msg: msg.text == "🎁 ПРОМОКОД")
def promo_button(message):
    msg = bot.send_message(
        message.chat.id, 
        "🔑 *ВВЕДИ ПРОМОКОД*\n\nНапример: VIP1000, START100",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_promo)

def process_promo(message):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if code in PROMOCODES:
        if has_used_promo(user_id, code):
            bot.send_message(
                message.chat.id, 
                "❌ *ОШИБКА*\n\nТы уже активировал этот промокод!",
                parse_mode='Markdown',
                reply_markup=get_main_keyboard()
            )
            return
        
        bonus = PROMOCODES[code]
        user['balance'] += bonus
        update_balance(user_id, user['balance'])
        add_used_promo(user_id, code)
        
        if code != 'VIP1000':
            del PROMOCODES[code]
        
        bot.send_message(
            message.chat.id, 
            f"✅ *ПРОМОКОД АКТИВИРОВАН!*\n\n+{bonus} 🪙 KZK\n💰 Новый баланс: {user['balance']} 🪙",
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

def show_profile(message):
    user = get_user_profile(message.from_user.id)
    win_rate = (user['total_win'] / user['total_bet'] * 100) if user['total_bet'] > 0 else 0
    profit = user['total_win'] - user['total_loss']
    
    profile_text = (
        f"👤 *ПРОФИЛЬ ИГРОКА*\n\n"
        f"💰 Баланс: {user['balance']} 🪙 KZK\n"
        f"📈 Всего ставок: {user['total_bet']} 🪙\n"
        f"🏆 Выиграно: {user['total_win']} 🪙\n"
        f"💔 Проиграно: {user['total_loss']} 🪙\n"
        f"📊 Профит: {profit} 🪙\n"
        f"🎯 Винрейт: {win_rate:.1f}%"
    )
    bot.send_message(
        message.chat.id, 
        profile_text, 
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# ======================== ИГРЫ ========================

@bot.callback_query_handler(func=lambda call: call.data == "game_slots")
def slots_game(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🎰 *СЛОТЫ*\n\n💰 Введи сумму ставки:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_slots_bet)

def process_slots_bet(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введи число!")
        return
    
    bet = int(message.text)
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if bet <= 0:
        bot.send_message(message.chat.id, "❌ Ставка должна быть больше нуля.")
        return
    
    if user['balance'] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно средств на балансе!")
        return
    
    user['balance'] -= bet
    update_balance(user_id, user['balance'])
    
    spin_result = [random.choice(GAME_EMOJIS) for _ in range(3)]
    spin_display = ' | '.join(spin_result)
    
    win_multiplier = 0
    if spin_result[0] == spin_result[1] == spin_result[2]:
        if spin_result[0] == '7️⃣':
            win_multiplier = 10
        else:
            win_multiplier = 5
    elif spin_result[0] == spin_result[1] or spin_result[1] == spin_result[2] or spin_result[0] == spin_result[2]:
        win_multiplier = 2
    
    win_amount = bet * win_multiplier if win_multiplier > 0 else 0
    
    if win_amount > 0:
        user['balance'] += win_amount
        update_balance(user_id, user['balance'])
        result_text = f"🎉 *ПОБЕДА!* +{win_amount} 🪙 (x{win_multiplier})"
    else:
        result_text = f"😢 *ПРОИГРЫШ...*"
    
    update_stats(user_id, bet, win_amount)
    
    response = (
        f"🎰 *СЛОТЫ - РЕЗУЛЬТАТ*\n\n"
        f"`{spin_display}`\n\n"
        f"💰 Ставка: {bet} 🪙\n"
        f"{result_text}\n"
        f"💎 Новый баланс: {user['balance']} 🪙 KZK"
    )
    
    bot.send_message(
        message.chat.id, 
        response, 
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "game_graph")
def graph_game(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📈 *ГРАФИК*\n\n💰 Введи сумму ставки:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_graph_bet)

def process_graph_bet(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введи число!")
        return
    
    bet = int(message.text)
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if bet <= 0:
        bot.send_message(message.chat.id, "❌ Ставка должна быть больше нуля.")
        return
    
    if user['balance'] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно средств на балансе!")
        return
    
    user['balance'] -= bet
    update_balance(user_id, user['balance'])
    
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📈 ВВЕРХ (x5)", callback_data=f"graph_up_{bet}")
    btn2 = types.InlineKeyboardButton("📉 ВНИЗ (x5)", callback_data=f"graph_down_{bet}")
    markup.add(btn1, btn2)
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.send_message(
        message.chat.id,
        f"💰 Ставка {bet} 🪙 принята!\n\n📊 Куда пойдет график?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('graph_') and not call.data == "game_graph")
def graph_callback(call):
    data = call.data.split('_')
    direction = data[1]
    bet = int(data[2])
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    result = random.choice(['up', 'down'])
    win_multiplier = 5 if direction == result else 0
    win_amount = bet * win_multiplier if win_multiplier > 0 else 0
    
    user = get_user_profile(user_id)
    
    if win_amount > 0:
        user['balance'] += win_amount
        update_balance(user_id, user['balance'])
        result_text = f"🎉 *ПОБЕДА!* +{win_amount} 🪙 (x5)"
    else:
        result_text = f"😢 *ПРОИГРЫШ...*"
    
    update_stats(user_id, bet, win_amount)
    
    response = (
        f"📈 *ГРАФИК - РЕЗУЛЬТАТ*\n\n"
        f"📊 График пошел: {'📈 ВВЕРХ' if result == 'up' else '📉 ВНИЗ'}\n"
        f"🎯 Ты выбрал: {'📈 ВВЕРХ' if direction == 'up' else '📉 ВНИЗ'}\n"
        f"💰 Ставка: {bet} 🪙\n"
        f"{result_text}\n"
        f"💎 Новый баланс: {user['balance']} 🪙 KZK"
    )
    
    bot.edit_message_text(
        response,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    bot.send_message(
        call.message.chat.id,
        "🎮 Выбери действие:",
        reply_markup=get_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "game_boxes")
def boxes_game(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📦 *КОРОБКИ*\n\n💰 Введи сумму ставки:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_boxes_bet)

def process_boxes_bet(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введи число!")
        return
    
    bet = int(message.text)
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if bet <= 0:
        bot.send_message(message.chat.id, "❌ Ставка должна быть больше нуля.")
        return
    
    if user['balance'] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно средств на балансе!")
        return
    
    user['balance'] -= bet
    update_balance(user_id, user['balance'])
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton("📦 1 (x10)", callback_data=f"box_1_{bet}")
    btn2 = types.InlineKeyboardButton("📦 2 (x10)", callback_data=f"box_2_{bet}")
    btn3 = types.InlineKeyboardButton("📦 3 (x10)", callback_data=f"box_3_{bet}")
    markup.add(btn1, btn2, btn3)
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.send_message(
        message.chat.id,
        f"💰 Ставка {bet} 🪙 принята!\n\n🎯 В какой коробке шарик?",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('box_') and not call.data == "game_boxes")
def box_callback(call):
    data = call.data.split('_')
    box = data[1]
    bet = int(data[2])
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    ball_position = str(random.randint(1, 3))
    win_multiplier = 10 if box == ball_position else 0
    win_amount = bet * win_multiplier if win_multiplier > 0 else 0
    
    user = get_user_profile(user_id)
    
    if win_amount > 0:
        user['balance'] += win_amount
        update_balance(user_id, user['balance'])
        result_text = f"🎉 *ПОБЕДА!* +{win_amount} 🪙 (x10)"
    else:
        result_text = f"😢 *ПРОИГРЫШ...*"
    
    update_stats(user_id, bet, win_amount)
    
    boxes_display = ""
    for i in range(1, 4):
        if str(i) == ball_position:
            boxes_display += "📦🎯 "
        else:
            boxes_display += "📦⬜ "
    
    response = (
        f"📦 *КОРОБКИ - РЕЗУЛЬТАТ*\n\n"
        f"{boxes_display}\n\n"
        f"🎯 Ты выбрал: Коробку {box}\n"
        f"📍 Шарик был в: Коробке {ball_position}\n"
        f"💰 Ставка: {bet} 🪙\n"
        f"{result_text}\n"
        f"💎 Новый баланс: {user['balance']} 🪙 KZK"
    )
    
    bot.edit_message_text(
        response,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    bot.send_message(
        call.message.chat.id,
        "🎮 Выбери действие:",
        reply_markup=get_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "game_dice")
def dice_game(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🎲 *КОСТИ*\n\n💰 Введи сумму ставки:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_dice_bet)

def process_dice_bet(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введи число!")
        return
    
    bet = int(message.text)
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if bet <= 0:
        bot.send_message(message.chat.id, "❌ Ставка должна быть больше нуля.")
        return
    
    if user['balance'] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно средств на балансе!")
        return
    
    user['balance'] -= bet
    update_balance(user_id, user['balance'])
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🎲 Чет (x2)", callback_data=f"dice_even_{bet}")
    btn2 = types.InlineKeyboardButton("🎲 Нечет (x2)", callback_data=f"dice_odd_{bet}")
    btn3 = types.InlineKeyboardButton("🎲 >7 (x2)", callback_data=f"dice_over7_{bet}")
    btn4 = types.InlineKeyboardButton("🎲 <7 (x2)", callback_data=f"dice_under7_{bet}")
    btn5 = types.InlineKeyboardButton("🎲 =7 (x5)", callback_data=f"dice_equal7_{bet}")
    btn6 = types.InlineKeyboardButton("🎲 Дубль (x5)", callback_data=f"dice_double_{bet}")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.send_message(
        message.chat.id,
        f"💰 Ставка {bet} 🪙 принята!\n\n🎲 Выбери тип ставки:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('dice_') and not call.data == "game_dice")
def dice_callback(call):
    data = call.data.split('_')
    bet_type = data[1]
    bet = int(data[2])
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    
    dice1 = random.randint(1, 6)
    dice2 = random.randint(1, 6)
    total = dice1 + dice2
    is_even = total % 2 == 0
    is_double = dice1 == dice2
    
    win = False
    multiplier = 0
    
    if bet_type == 'even' and is_even:
        win, multiplier = True, 2
    elif bet_type == 'odd' and not is_even:
        win, multiplier = True, 2
    elif bet_type == 'over7' and total > 7:
        win, multiplier = True, 2
    elif bet_type == 'under7' and total < 7:
        win, multiplier = True, 2
    elif bet_type == 'equal7' and total == 7:
        win, multiplier = True, 5
    elif bet_type == 'double' and is_double:
        win, multiplier = True, 5
    
    win_amount = bet * multiplier if win else 0
    user = get_user_profile(user_id)
    
    if win:
        user['balance'] += win_amount
        update_balance(user_id, user['balance'])
        result_text = f"🎉 *ПОБЕДА!* +{win_amount} 🪙 (x{multiplier})"
    else:
        result_text = f"😢 *ПРОИГРЫШ...*"
    
    update_stats(user_id, bet, win_amount)
    
    response = (
        f"🎲 *КОСТИ - РЕЗУЛЬТАТ*\n\n"
        f"🎲 {dice1} + {dice2} = {total}\n"
        f"{'🎯 ДУБЛЬ!' if is_double else ''}\n\n"
        f"💰 Ставка: {bet} 🪙\n"
        f"{result_text}\n"
        f"💎 Новый баланс: {user['balance']} 🪙 KZK"
    )
    
    bot.edit_message_text(
        response,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    bot.send_message(
        call.message.chat.id,
        "🎮 Выбери действие:",
        reply_markup=get_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data == "game_lottery")
def lottery_game(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🔢 *ЛОТЕРЕЯ*\n\n💰 Введи сумму ставки:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_lottery_bet)

def process_lottery_bet(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введи число!")
        return
    
    bet = int(message.text)
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if bet <= 0:
        bot.send_message(message.chat.id, "❌ Ставка должна быть больше нуля.")
        return
    
    if user['balance'] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно средств на балансе!")
        return
    
    user['balance'] -= bet
    update_balance(user_id, user['balance'])
    
    markup = types.InlineKeyboardMarkup(row_width=5)
    numbers = []
    for i in range(1, 11):
        numbers.append(types.InlineKeyboardButton(str(i), callback_data=f"lottery_{i}_{bet}"))
    markup.add(*numbers)
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.send_message(
        message.chat.id,
        f"💰 Ставка {bet} 🪙 принята!\n\n🔢 Выбери 3 числа от 1 до 10:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('lottery_'))
def lottery_callback(call):
    data = call.data.split('_')
    if len(data) == 3:
        # Первый выбор
        num1 = int(data[1])
        bet = int(data[2])
        user_id = call.from_user.id
        
        markup = types.InlineKeyboardMarkup(row_width=5)
        numbers = []
        for i in range(1, 11):
            if i != num1:
                numbers.append(types.InlineKeyboardButton(str(i), callback_data=f"lottery2_{num1}_{i}_{bet}"))
        markup.add(*numbers)
        markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
        
        bot.edit_message_text(
            f"🔢 Выбрано: {num1}\n\nВыбери второе число:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif len(data) == 4:
        # Второй выбор
        num1 = int(data[1])
        num2 = int(data[2])
        bet = int(data[3])
        user_id = call.from_user.id
        
        markup = types.InlineKeyboardMarkup(row_width=5)
        numbers = []
        for i in range(1, 11):
            if i != num1 and i != num2:
                numbers.append(types.InlineKeyboardButton(str(i), callback_data=f"lottery3_{num1}_{num2}_{i}_{bet}"))
        markup.add(*numbers)
        markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
        
        bot.edit_message_text(
            f"🔢 Выбрано: {num1}, {num2}\n\nВыбери третье число:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif len(data) == 5:
        # Третий выбор - результат
        num1 = int(data[1])
        num2 = int(data[2])
        num3 = int(data[3])
        bet = int(data[4])
        user_id = call.from_user.id
        
        chosen_numbers = {num1, num2, num3}
        
        # Генерируем 5 выигрышных чисел
        winning_numbers = set(random.sample(range(1, 11), 5))
        
        # Считаем совпадения
        matches = len(chosen_numbers & winning_numbers)
        
        # Определяем множитель
        multipliers = {0: 0, 1: 2, 2: 5, 3: 10}
        multiplier = multipliers.get(matches, 0)
        
        win_amount = bet * multiplier if multiplier > 0 else 0
        user = get_user_profile(user_id)
        
        if win_amount > 0:
            user['balance'] += win_amount
            update_balance(user_id, user['balance'])
            result_text = f"🎉 *ПОБЕДА!* +{win_amount} 🪙 (x{multiplier})"
        else:
            result_text = f"😢 *ПРОИГРЫШ...*"
        
        update_stats(user_id, bet, win_amount)
        
        response = (
            f"🔢 *ЛОТЕРЕЯ - РЕЗУЛЬТАТ*\n\n"
            f"🎯 Твои числа: {num1}, {num2}, {num3}\n"
            f"🏆 Выигрышные: {sorted(winning_numbers)}\n"
            f"✨ Совпадений: {matches}\n\n"
            f"💰 Ставка: {bet} 🪙\n"
            f"{result_text}\n"
            f"💎 Новый баланс: {user['balance']} 🪙 KZK"
        )
        
        bot.edit_message_text(
            response,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='Markdown'
        )
        
        bot.send_message(
            call.message.chat.id,
            "🎮 Выбери действие:",
            reply_markup=get_main_keyboard()
        )

@bot.callback_query_handler(func=lambda call: call.data == "game_darts")
def darts_game(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "🎯 *ДАРТС*\n\n💰 Введи сумму ставки:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(msg, process_darts_bet)

def process_darts_bet(message):
    if not message.text.isdigit():
        bot.send_message(message.chat.id, "❌ Введи число!")
        return
    
    bet = int(message.text)
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if bet <= 0:
        bot.send_message(message.chat.id, "❌ Ставка должна быть больше нуля.")
        return
    
    if user['balance'] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно средств на балансе!")
        return
    
    user['balance'] -= bet
    update_balance(user_id, user['balance'])
    
    markup = types.InlineKeyboardMarkup(row_width=4)
    sectors = []
    for i in [5, 10, 15, 20]:
        sectors.append(types.InlineKeyboardButton(f"🎯 {i}", callback_data=f"darts_{i}_{bet}"))
    markup.add(*sectors)
    markup.add(types.InlineKeyboardButton("🎯 БУЛЛ-АЙ (x20)", callback_data=f"darts_bull_{bet}"))
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))
    
    bot.send_message(
        message.chat.id,
        f"💰 Ставка {bet} 🪙 принята!\n\n🎯 Выбери сектор для броска:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('darts_') and not call.data == "game_darts")
def darts_callback(call):
    data = call.data.split('_')
    
    if data[1] == 'bull':
        bet = int(data[2])
        target = 'bull'
        target_name = "БУЛЛ-АЙ (центр)"
    else:
        target = int(data[1])
        bet = int(data[2])
        target_name = f"сектор {target}"
    
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    # Бросок (случайное число от 1 до 20)
    hit = random.randint(1, 20)
    
    # Определяем выигрыш
    if target == 'bull':
        win = (hit == 1)  # 5% шанс
        multiplier = 20 if win else 0
    else:
        win = (hit == target)
        multiplier = 5 if win else 0
    
    win_amount = bet * multiplier if win else 0
    user = get_user_profile(user_id)
    
    if win:
        user['balance'] += win_amount
        update_balance(user_id, user['balance'])
        result_text = f"🎉 *ПОБЕДА!* +{win_amount} 🪙 (x{multiplier})"
    else:
        result_text = f"😢 *ПРОИГРЫШ...*\nПопадание в сектор {hit}"
    
    update_stats(user_id, bet, win_amount)
    
    response = (
        f"🎯 *ДАРТС - РЕЗУЛЬТАТ*\n\n"
        f"🎯 Цель: {target_name}\n"
        f"📍 Попадание: сектор {hit}\n\n"
        f"💰 Ставка: {bet} 🪙\n"
        f"{result_text}\n"
        f"💎 Новый баланс: {user['balance']} 🪙 KZK"
    )
    
    bot.edit_message_text(
        response,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    
    bot.send_message(
        call.message.chat.id,
        "🎮 Выбери действие:",
        reply_markup=get_main_keyboard()
    )

# ======================== ГЛАВНОЕ МЕНЮ ========================

@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def back_to_main_menu(call):
    bot.answer_callback_query(call.id)
    user = get_user_profile(call.from_user.id)
    
    menu_text = (
        f"🏠 *ГЛАВНОЕ МЕНЮ*\n\n"
        f"💰 Баланс: {user['balance']} 🪙 KZK\n\n"
        f"🎮 Нажми *ИГРАТЬ* чтобы выбрать игру!"
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
    print("✅ 6 игр загружены")
    print("✅ АДМИН-ПАНЕЛЬ АКТИВНА!")
    print("=" * 40)
    print(f"🔐 Пароль для админки: {ADMIN_PASSWORD}")
    print("📝 Команды админа:")
    print("   /addpromo КОД СУММА - добавить промокод")
    print("   /delpromo КОД - удалить промокод")
    print("=" * 40)
    print("VIP1000 - бесконечный промокод на 1000 🪙")
    print("🎮 Нажми 👑 АДМИН в боте для входа!")
    
    bot.infinity_polling()
