import telebot
from telebot import types
import random
import json
import os
import time

# ======================== НАСТРОЙКИ ========================
TOKEN = '8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI'
DATA_FILE = 'users_data.json'
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
            'used_promos': []
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

def get_main_keyboard():
    """Создает главную клавиатуру с одной кнопкой ИГРАТЬ"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🎮 ИГРАТЬ")
    btn2 = types.KeyboardButton("📊 ПРОФИЛЬ")
    btn3 = types.KeyboardButton("🎁 ПРОМОКОД")
    markup.add(btn1)
    markup.add(btn2, btn3)
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

# ======================== КОМАНДЫ ========================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = get_user_profile(message.from_user.id)
    welcome_text = (
        f"🎰 Добро пожаловать в *CASINO EMOJI*!\n\n"
        f"👤 Твой баланс: {user['balance']} 🪙 KZK\n\n"
        f"🎮 Нажми *ИГРАТЬ* чтобы выбрать игру!\n"
        f"📊 Смотри статистику в ПРОФИЛЬ\n"
        f"🎁 Активируй ПРОМОКОДЫ для бонусов\n\n"
        f"🔥 Доступные промокоды:\n"
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

@bot.message_handler(commands=['profile'])
def cmd_profile(message):
    show_profile(message)

@bot.message_handler(commands=['promo'])
def cmd_promo(message):
    msg = bot.send_message(message.chat.id, "🔑 Введи промокод:")
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
    profile_text = (
        f"👤 *ПРОФИЛЬ ИГРОКА*\n\n"
        f"💰 Баланс: {user['balance']} 🪙 KZK\n"
        f"📈 Всего поставлено: {user['total_bet']} 🪙\n"
        f"🏆 Всего выиграно: {user['total_win']} 🪙\n"
        f"💔 Всего проиграно: {user['total_loss']} 🪙\n"
        f"📊 Чистый профит: {user['total_win'] - user['total_loss']} 🪙"
    )
    bot.send_message(
        message.chat.id, 
        profile_text, 
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

# ======================== ИГРА 1: СЛОТЫ ========================

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

# ======================== ИГРА 2: ГРАФИК ========================

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

# ======================== ИГРА 3: КОРОБКИ ========================

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

# ======================== ИГРА 4: КОСТИ ========================

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

@bot.callback_query_handler(func=lambda call: call.data.startswith('dice_'))
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

# ======================== ИГРА 5: ЛОТЕРЕЯ ========================

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

# ======================== ИГРА 6: ДАРТС ========================

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

@bot.callback_query_handler(func=lambda call: call.data.startswith('darts_'))
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
    print("✅ 6 игр загружены:")
    print("   🎰 Слоты | 📈 График | 📦 Коробки")
    print("   🎲 Кости | 🔢 Лотерея | 🎯 Дартс")
    print("=" * 40)
    print("VIP1000 - бесконечный промокод на 1000 🪙")
    print("🎮 Нажми ИГРАТЬ в боте!")
    
    bot.infinity_polling()
