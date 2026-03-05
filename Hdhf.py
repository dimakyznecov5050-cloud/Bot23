import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import random
import json
import os
from datetime import datetime

# Токен бота (вставьте свой)
TOKEN = '8531867613:AAHxjS7JtTjoB0mgO_ntFTjakNFbVn2stuI'
bot = telebot.TeleBot(TOKEN)

# Название валюты
CURRENCY = "🌟 Кристаллы"

# Файл для хранения данных пользователей
DATA_FILE = 'users_data.json'

# Эмодзи для слотов
SLOT_EMOJIS = {
    'lemon': '🍋',
    'seven': '7️⃣',
    'cherry': '🍒',
    'bell': '🔔',
    'grape': '🍇'
}

# Загрузка данных пользователей
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Сохранение данных пользователей
def save_users(users):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# Получение данных пользователя
def get_user(user_id):
    users = load_users()
    user_id = str(user_id)
    if user_id not in users:
        users[user_id] = {
            'balance': 1000,
            'total_won': 0,
            'total_lost': 0,
            'games_played': 0
        }
        save_users(users)
    return users[user_id]

# Обновление баланса
def update_balance(user_id, amount):
    users = load_users()
    user_id = str(user_id)
    if user_id in users:
        users[user_id]['balance'] += amount
        if amount > 0:
            users[user_id]['total_won'] += amount
        else:
            users[user_id]['total_lost'] += abs(amount)
        users[user_id]['games_played'] += 1
        save_users(users)
        return users[user_id]['balance']
    return None

# Генерация случайных слотов
def spin_slots():
    symbols = ['lemon', 'seven', 'cherry', 'bell', 'grape']
    return [random.choice(symbols) for _ in range(3)]

# Расчет выигрыша
def calculate_win(slots, bet):
    s1, s2, s3 = slots
    
    # Проверка на три семерки (особый приз)
    if s1 == 'seven' and s2 == 'seven' and s3 == 'seven':
        return bet * 10, "ДЖЕКПОТ! 🎰 ТРИ СЕМЕРКИ! x10"
    
    # Проверка на три одинаковых (кроме семерок)
    if s1 == s2 == s3:
        return bet * 5, "ТРИ ОДИНАКОВЫХ! 🎰 x5"
    
    # Проверка на два одинаковых
    if s1 == s2 or s1 == s3 or s2 == s3:
        return bet * 2, "ДВА ОДИНАКОВЫХ! 🎰 x2"
    
    return 0, "Повезет в следующий раз 🍀"

# Создание клавиатуры для выбора количества спинов
def get_spin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=5)
    buttons = [
        InlineKeyboardButton("1️⃣", callback_data="spin_1"),
        InlineKeyboardButton("2️⃣", callback_data="spin_2"),
        InlineKeyboardButton("3️⃣", callback_data="spin_3"),
        InlineKeyboardButton("5️⃣", callback_data="spin_5"),
        InlineKeyboardButton("🔟", callback_data="spin_10"),
        InlineKeyboardButton("2️⃣5️⃣", callback_data="spin_25"),
        InlineKeyboardButton("5️⃣0️⃣", callback_data="spin_50"),
        InlineKeyboardButton("💯", callback_data="spin_100")
    ]
    keyboard.add(*buttons)
    keyboard.add(InlineKeyboardButton("💰 Профиль", callback_data="profile"))
    return keyboard

# Команда старт
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    welcome_text = (
        f"🎰 Добро пожаловать в Casino Slots!\n\n"
        f"Твой баланс: {user['balance']} {CURRENCY}\n"
        f"Нажимай кнопки ниже чтобы крутить слоты!\n\n"
        f"🎰 Правила:\n"
        f"• Два одинаковых — x2 к ставке\n"
        f"• Три одинаковых — x5 к ставке\n"
        f"• ТРИ СЕМЕРКИ (7️⃣7️⃣7️⃣) — x10 ДЖЕКПОТ!\n"
        f"• Каждый спин стоит 10 {CURRENCY}"
    )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_spin_keyboard())

# Команда профиль
@bot.message_handler(commands=['profile'])
def profile(message):
    show_profile(message.chat.id, message.from_user.id)

def show_profile(chat_id, user_id):
    user = get_user(user_id)
    profile_text = (
        f"👤 Твой профиль\n\n"
        f"💰 Баланс: {user['balance']} {CURRENCY}\n"
        f"🏆 Всего выиграно: {user['total_won']} {CURRENCY}\n"
        f"📉 Всего проиграно: {user['total_lost']} {CURRENCY}\n"
        f"🎮 Сыграно игр: {user['games_played']}\n"
        f"📊 Чистый доход: {user['total_won'] - user['total_lost']} {CURRENCY}"
    )
    bot.send_message(chat_id, profile_text, reply_markup=get_spin_keyboard())

# Обработка нажатий кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if call.data == "profile":
        show_profile(chat_id, user_id)
        return
    
    if call.data.startswith("spin_"):
        spins = int(call.data.split("_")[1])
        process_spins(chat_id, user_id, spins)

def process_spins(chat_id, user_id, num_spins):
    user = get_user(user_id)
    bet_per_spin = 10
    total_cost = bet_per_spin * num_spins
    
    # Проверка баланса
    if user['balance'] < total_cost:
        bot.send_message(chat_id, 
                        f"❌ Недостаточно средств!\n"
                        f"Нужно: {total_cost} {CURRENCY}\n"
                        f"У тебя: {user['balance']} {CURRENCY}",
                        reply_markup=get_spin_keyboard())
        return
    
    # Списываем ставку
    update_balance(user_id, -total_cost)
    
    results = []
    total_win = 0
    message_text = f"🎰 Крутим {num_spins} раз!\n\n"
    
    for i in range(num_spins):
        slots = spin_slots()
        win_amount, win_text = calculate_win(slots, bet_per_spin)
        total_win += win_amount
        
        # Форматируем результат
        slots_emoji = " ".join([SLOT_EMOJIS[s] for s in slots])
        result_line = f"{i+1}. {slots_emoji} | {win_text}"
        if win_amount > 0:
            result_line += f" (+{win_amount} {CURRENCY})"
        results.append(result_line)
    
    # Добавляем выигрыш
    if total_win > 0:
        update_balance(user_id, total_win)
        message_text += "\n".join(results)
        message_text += f"\n\n✨ Итого выигрыш: +{total_win} {CURRENCY}"
    else:
        message_text += "\n".join(results)
        message_text += f"\n\n😢 В этот раз без выигрыша..."
    
    # Показываем новый баланс
    new_balance = get_user(user_id)['balance']
    message_text += f"\n💰 Новый баланс: {new_balance} {CURRENCY}"
    
    # Отправляем результат
    bot.send_message(chat_id, message_text, reply_markup=get_spin_keyboard())

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
