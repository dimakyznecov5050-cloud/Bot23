import telebot
from telebot import types
import random
import json
import os
import time

# ======================== НАСТРОЙКИ ========================
TOKEN = '8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI'
DATA_FILE = 'users_data.json'
GAME_EMOJIS = ['🍒', '🍋', '🍊', '7️⃣']  # Четвертый эмодзи - это 7 для джекпота
PROMOCODES = {
    'START100': 100,
    'LUCKY777': 777,
    'BONUS500': 500,
    'VIP1000': 1000  # Бесконечный промокод (не удаляется из словаря)
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
            'used_promos': []  # Список использованных промокодов
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
    """Проверял, использовал ли пользователь промокод"""
    data = load_data()
    user_id = str(user_id)
    if 'used_promos' not in data[user_id]:
        return False
    return promo_code in data[user_id]['used_promos']

# ======================== КОМАНДЫ ========================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = get_user_profile(message.from_user.id)
    welcome_text = (
        f"🎰 Добро пожаловать в Казино Эмодзи!\n\n"
        f"Твой баланс: {user['balance']} 🪙 KZK\n\n"
        f"Правила:\n"
        f"• Введи сумму ставки, чтобы крутить барабаны\n"
        f"• 🍒🍒 или 🍋🍋 — выигрыш x2\n"
        f"• 🍒🍒🍒 или 🍋🍋🍋 — выигрыш x5\n"
        f"• 7️⃣7️⃣7️⃣ — ДЖЕКПОТ x10\n"
        f"• Используй /profile для статистики\n"
        f"• Используй /promo [код] для активации бонуса\n\n"
        f"🔥 Доступные промокоды:\n"
        f"• START100 - 100 🪙\n"
        f"• LUCKY777 - 777 🪙\n"
        f"• BONUS500 - 500 🪙\n"
        f"• VIP1000 - 1000 🪙 (Бесконечный!)"
    )
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🎰 Крутить")
    btn2 = types.KeyboardButton("📊 Профиль")
    btn3 = types.KeyboardButton("🎁 Промокод")
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['profile'])
def cmd_profile(message):
    show_profile(message)

@bot.message_handler(commands=['promo'])
def cmd_promo(message):
    msg = bot.send_message(message.chat.id, "Введи промокод:")
    bot.register_next_step_handler(msg, process_promo)

def process_promo(message):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if code in PROMOCODES:
        # Проверяем, не использовал ли пользователь этот промокод
        if has_used_promo(user_id, code):
            bot.send_message(message.chat.id, "❌ Ты уже активировал этот промокод!")
            return
        
        bonus = PROMOCODES[code]
        user['balance'] += bonus
        update_balance(user_id, user['balance'])
        
        # Добавляем промокод в список использованных
        add_used_promo(user_id, code)
        
        # Не удаляем VIP1000 из словаря, чтобы он был бесконечным
        if code != 'VIP1000':
            del PROMOCODES[code]
        
        bot.send_message(message.chat.id, f"✅ Промокод активирован! +{bonus} 🪙 KZK")
    else:
        bot.send_message(message.chat.id, "❌ Недействительный промокод.")

@bot.message_handler(func=lambda msg: msg.text == "📊 Профиль")
def profile_button(message):
    show_profile(message)

@bot.message_handler(func=lambda msg: msg.text == "🎁 Промокод")
def promo_button(message):
    msg = bot.send_message(message.chat.id, "🔑 Введи промокод:")
    bot.register_next_step_handler(msg, process_promo)

def show_profile(message):
    user = get_user_profile(message.from_user.id)
    profile_text = (
        f"👤 *Профиль игрока*\n\n"
        f"💰 Баланс: {user['balance']} 🪙 KZK\n"
        f"📈 Всего поставлено: {user['total_bet']} 🪙\n"
        f"🏆 Всего выиграно: {user['total_win']} 🪙\n"
        f"💔 Всего проиграно: {user['total_loss']} 🪙\n"
        f"📊 Профит: {user['total_win'] - user['total_loss']} 🪙"
    )
    bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')

# ======================== ИГРОВАЯ ЛОГИКА ========================

@bot.message_handler(func=lambda msg: msg.text == "🎰 Крутить")
def ask_bet(message):
    msg = bot.send_message(message.chat.id, "💰 Сколько ставишь? (введи число)")
    bot.register_next_step_handler(msg, process_bet)

@bot.message_handler(func=lambda msg: msg.text.isdigit())
def process_bet(message):
    bet = int(message.text)
    user_id = message.from_user.id
    user = get_user_profile(user_id)
    
    if bet <= 0:
        bot.send_message(message.chat.id, "❌ Ставка должна быть больше нуля.")
        return
    
    if user['balance'] < bet:
        bot.send_message(message.chat.id, "❌ Недостаточно средств на балансе!")
        return
    
    # Списываем ставку
    user['balance'] -= bet
    update_balance(user_id, user['balance'])
    
    # Крутим барабаны
    spin_result = [random.choice(GAME_EMOJIS) for _ in range(3)]
    spin_display = ' | '.join(spin_result)
    
    # Определяем выигрыш
    win_multiplier = 0
    if spin_result[0] == spin_result[1] == spin_result[2]:
        if spin_result[0] == '7️⃣':
            win_multiplier = 10  # Джекпот
        else:
            win_multiplier = 5   # Три одинаковых (кроме семерок)
    elif spin_result[0] == spin_result[1] or spin_result[1] == spin_result[2] or spin_result[0] == spin_result[2]:
        win_multiplier = 2       # Два одинаковых
    
    win_amount = bet * win_multiplier if win_multiplier > 0 else 0
    
    # Обновляем баланс и статистику
    if win_amount > 0:
        user['balance'] += win_amount
        update_balance(user_id, user['balance'])
        result_text = f"🎉 ПОБЕДА! +{win_amount} 🪙 (x{win_multiplier})"
    else:
        result_text = f"😢 Проигрыш... Повезет в следующий раз!"
    
    update_stats(user_id, bet, win_amount)
    
    # Формируем ответ
    response = (
        f"🎰 *Результат спина:*\n"
        f"`{spin_display}`\n\n"
        f"💵 Ставка: {bet} 🪙\n"
        f"{result_text}\n"
        f"💰 Новый баланс: {user['balance']} 🪙 KZK"
    )
    
    # Добавляем кнопку для быстрого повтора
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("🎰 Крутить")
    btn2 = types.KeyboardButton("📊 Профиль")
    btn3 = types.KeyboardButton("🎁 Промокод")
    markup.add(btn1, btn2, btn3)
    
    bot.send_message(message.chat.id, response, parse_mode='Markdown', reply_markup=markup)

# ======================== ЗАПУСК ========================

if __name__ == '__main__':
    print("🎰 Казино бот запущен!")
    print("Токен установлен, промокоды активны!")
    print("VIP1000 - бесконечный промокод на 1000 🪙")
    # Для хостинга BotHost обычно используется polling
    bot.infinity_polling()
