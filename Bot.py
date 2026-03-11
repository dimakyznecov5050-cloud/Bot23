import sqlite3
import threading
import time
import traceback
from datetime import datetime, timedelta

import telebot
from telebot import types

# ---------- ТОКЕН ----------
TOKEN = '8783525882:AAE0QrrgJUy_BBFZLAMZFAoIuZir0hHAj-8'
bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# ---------- НАСТРОЙКИ ----------
ADMIN_ID = 8052884471
SUPPORT_USERNAME = 'Kurator111'
REVIEWS_CHANNEL = '+DpdNmcj9gAY2MThi'
DB_PATH = 'uc_bot.db'
WELCOME_IMAGE_PATH = 'IMG_2822.jpeg'

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

POPULARITY_ITEMS = {
    'pop_regular': {
        'title': '✨Популярность✨',
        'description': (
            '✨<b>Популярность</b>✨\n\n'
            '➤Купить Популярность Вы можете круглосуточно (24/7)\n\n'
            '❕Не оформляйте заказ если до конца раунда осталось менее 15 минут\n\n'
            '🕒Среднее время доставки 1-15 минут'
        ),
        'product_label': 'Популярность',
        'prices': [
            ('10 000 ПП', 150), ('20 000 ПП', 300), ('40 000 ПП', 600), ('60 000 ПП', 900),
            ('100 000 ПП', 1500), ('200 000 ПП', 3000), ('500 000 ПП', 7500),
        ]
    },
    'pop_home': {
        'title': '✨Популярность для дома✨',
        'description': (
            '✨<b>Популярность для дома</b>✨\n\n'
            '➤Купить Популярность для дома Вы можете круглосуточно (24/7)\n\n'
            '❕Не оформляйте заказ если до конца раунда осталось менее 15 минут\n\n'
            '🕒Среднее время доставки 1-15 минут'
        ),
        'product_label': 'Популярность для дома',
        'prices': [
            ('20 000 ПП для дома', 250), ('40 000 ПП для дома', 500), ('60 000 ПП для дома', 750),
            ('100 000 ПП для дома', 1250), ('200 000 ПП для дома', 2500), ('500 000 ПП для дома', 6250),
        ]
    },
    'pop_last': {
        'title': '✨Популярность для последних минут раунда✨',
        'description': (
            '✨<b>Популярность для последних минут раунда</b>✨\n\n'
            '➤Оформляйте заказ заранее и популярность поступит в последние 1-2 минуты раунда\n\n'
            '❕Оформляйте заказ не позже 30 минут до конца раунда'
        ),
        'product_label': 'Популярность на последней минуте',
        'prices': [
            ('50 000 ПП', 1300), ('100 000 ПП', 2600), ('150 000 ПП', 3900), ('200 000 ПП', 5200), ('500 000 ПП', 13000),
        ]
    }
}

SUBSCRIPTION_ITEMS = [
    ('Prime (1 месяц)', 120), ('Prime (3 месяца)', 320), ('Prime (6 месяцев)', 557),
    ('Prime (12 месяцев)', 1007), ('Prime Plus (1 месяц)', 850), ('Prime Plus (3 месяца)', 2550),
    ('Prime Plus (6 месяцев)', 5100), ('Prime Plus (12 месяцев)', 6960), ('Миф.Кристал', 330),
]

SUBSCRIPTION_INFO_TEXT = (
    '⭐️<b>Prime</b> (1 месяц) - 60 UC\n'
    '⭐️<b>Prime</b> (3 месяца) - 180 UC\n'
    '⭐️<b>Prime</b> (6 месяцев) - 360 UC\n'
    '⭐️<b>Prime</b> (12 месяцев) - 720 UC\n'
    '❗️А также - 3 UC, 5 RP очков каждый день\n\n'
    '👑 <b>PRIME PLUS</b> (1/3/6/12 месяцев)\n'
    'Включает UC сразу + UC в течение периода и бонусы.\n\n'
    '🔺Миф Кристал: покупается 1 раз в неделю'
)

state_lock = threading.Lock()
user_states = {}


def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout = 30000')
    return conn


def is_admin(user_id):
    return user_id == ADMIN_ID


def fmt_price(value):
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, float):
        text = f'{value:,.1f}'
    else:
        text = f'{value:,}'
    return text.replace(',', ' ')


def escape_html(text):
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, join_date TEXT,
        total_uc INTEGER DEFAULT 0, total_orders INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT, order_number INTEGER UNIQUE, user_id INTEGER,
        username TEXT, player_id TEXT, uc_amount INTEGER, price REAL, status TEXT,
        created_at TEXT, completed_at TEXT, discount INTEGER DEFAULT 0, promocode TEXT DEFAULT NULL,
        product_type TEXT DEFAULT 'uc', product_name TEXT DEFAULT 'UC', quantity_text TEXT DEFAULT NULL,
        target_value TEXT DEFAULT NULL, target_type TEXT DEFAULT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS promocodes (
        code TEXT PRIMARY KEY, discount INTEGER, created_at TEXT, max_uses INTEGER DEFAULT 0,
        used_count INTEGER DEFAULT 0, expires_at TEXT DEFAULT NULL, active INTEGER DEFAULT 1
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_promos (
        user_id INTEGER, promo_code TEXT, discount INTEGER, activated_at TEXT,
        PRIMARY KEY (user_id, promo_code)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS price_settings (
        key TEXT PRIMARY KEY, value REAL
    )''')

    defaults = []
    for uc, price in UC_PRICES.items():
        defaults.append((f'uc:{uc}', price))
    for k, cfg in POPULARITY_ITEMS.items():
        for i, (_, price) in enumerate(cfg['prices']):
            defaults.append((f'pop:{k}:{i}', price))
    for i, (_, price) in enumerate(SUBSCRIPTION_ITEMS):
        defaults.append((f'sub:{i}', price))
    defaults.append(('tgstars:unit', 1.5))

    for key, val in defaults:
        c.execute('INSERT OR IGNORE INTO price_settings (key, value) VALUES (?,?)', (key, val))

    conn.commit()
    conn.close()


def get_price(key, fallback):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT value FROM price_settings WHERE key = ?', (key,))
    row = c.fetchone()
    conn.close()
    return row['value'] if row else fallback


def set_price(key, value):
    conn = get_conn()
    c = conn.cursor()
    c.execute('INSERT INTO price_settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value = excluded.value', (key, value))
    conn.commit()
    conn.close()


def ensure_user(message):
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO users (user_id, username, first_name, join_date, total_uc, total_orders)
                 VALUES (?,?,?,?,?,?)''',
              (message.from_user.id, message.from_user.username or 'Нет username',
               message.from_user.first_name or 'Игрок', str(datetime.now()), 0, 0))
    c.execute('UPDATE users SET username=?, first_name=? WHERE user_id=?',
              (message.from_user.username or 'Нет username', message.from_user.first_name or 'Игрок', message.from_user.id))
    conn.commit()
    conn.close()


def get_next_order_number():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT MAX(order_number) FROM orders')
    n = c.fetchone()[0]
    conn.close()
    return (n or 0) + 1


def set_state(user_id, **kwargs):
    with state_lock:
        current = user_states.get(user_id, {})
        current.update(kwargs)
        user_states[user_id] = current


def get_state(user_id):
    with state_lock:
        return dict(user_states.get(user_id, {}))


def clear_state(user_id, keep_menu=True):
    with state_lock:
        cur = user_states.get(user_id, {})
        cid = cur.get('menu_chat_id') if keep_menu else None
        mid = cur.get('menu_message_id') if keep_menu else None
        user_states[user_id] = {}
        if cid and mid:
            user_states[user_id]['menu_chat_id'] = cid
            user_states[user_id]['menu_message_id'] = mid


def safe_delete_message(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def delete_user_message(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass


def mask_name(name):
    text = (name or 'Игрок').strip()
    if len(text) <= 2:
        return text[0] + '**' if text else 'Игрок'
    keep = max(2, len(text) // 2)
    return text[:keep] + '**'


def menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton('🛒 Купить UC', callback_data='menu_uc'))
    markup.add(
        types.InlineKeyboardButton('🔥 Популярность', callback_data='menu_popularity'),
        types.InlineKeyboardButton('👑 Подписки', callback_data='menu_subs')
    )
    markup.add(types.InlineKeyboardButton('⭐️ Пополнить Telegram Stars', callback_data='menu_tgstars'))
    markup.add(
        types.InlineKeyboardButton('🎟 Промокод', callback_data='menu_promo'),
        types.InlineKeyboardButton('ℹ️ Информация', callback_data='menu_support')
    )
    markup.add(
        types.InlineKeyboardButton('👤 Профиль', callback_data='menu_profile'),
        types.InlineKeyboardButton('🏆 Лидеры', callback_data='menu_leaders')
    )
    markup.add(types.InlineKeyboardButton('⭐️ Отзывы', callback_data='menu_reviews'))
    return markup


def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('📊 Статистика', callback_data='admin_stats'),
        types.InlineKeyboardButton('🎟 Промокоды', callback_data='admin_promos')
    )
    markup.add(
        types.InlineKeyboardButton('💸 Изменить цены', callback_data='admin_prices'),
        types.InlineKeyboardButton('📢 Рассылка', callback_data='admin_mailing')
    )
    markup.add(types.InlineKeyboardButton('🚪 Выйти', callback_data='admin_exit'))
    return markup


def back_to_menu_markup():
    return types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ Назад', callback_data='back_main'))


def back_to_admin_markup(back='admin_back'):
    return types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ Назад', callback_data=back))


def render_main_menu_text():
    return (
        '👋 ДОБРО ПОЖАЛОВАТЬ В APEX UC SHOP!\n\n'
        '🔥 Лучший магазин UC для PUBG Mobile\n\n'
        '✅ Наши преимущества:\n'
        '• Быстрая доставка 5-15 минут\n'
        '• 100% гарантия пополнения\n'
        '• Круглосуточная поддержка\n'
        '• Низкие цены\n\n'
        '👇 Нажми КУПИТЬ UC чтобы начать'
    )


def send_or_update_main_menu(chat_id, user_id):
    text = render_main_menu_text()
    markup = menu_keyboard()
    state = get_state(user_id)
    mid = state.get('menu_message_id')
    mchat = state.get('menu_chat_id', chat_id)

    if mid and mchat == chat_id:
        safe_delete_message(chat_id, mid)

    with open(WELCOME_IMAGE_PATH, 'rb') as img:
        sent = bot.send_photo(chat_id, img, caption=text, reply_markup=markup)
    clear_state(user_id, keep_menu=False)
    set_state(user_id, menu_chat_id=chat_id, menu_message_id=sent.message_id)


def edit_menu(user_id, text, reply_markup):
    st = get_state(user_id)
    cid = st.get('menu_chat_id')
    mid = st.get('menu_message_id')
    if not cid or not mid:
        return False
    try:
        bot.edit_message_text(text, cid, mid, reply_markup=reply_markup)
        return True
    except Exception:
        try:
            sent = bot.send_message(cid, text, reply_markup=reply_markup)
            safe_delete_message(cid, mid)
            set_state(user_id, menu_chat_id=cid, menu_message_id=sent.message_id)
            return True
        except Exception:
            return False


def build_payment_text(order_number, product_name, quantity_text, price, target_value, target_type):
    t = [
        f'✅ <b>ЗАКАЗ №{order_number} СОЗДАН!</b>', '', f'• Товар: {escape_html(product_name)}',
        f'• Выбрано: {escape_html(quantity_text)}',
        f'• {"PUBG ID" if target_type=="player_id" else "Получатель"}: <code>{escape_html(target_value)}</code>',
        f'• Сумма: {fmt_price(price)} ₽', '', '💳 <b>РЕКВИЗИТЫ:</b>'
    ]
    for card in CARDS:
        t.extend([f'{card["bank"]}: <code>{card["card"]}</code> ({card["recipient"]})'])
    return '\n'.join(t)


def create_order(user, product_type, product_name, quantity_text, price, target_value, target_type, uc_amount=0):
    num = get_next_order_number()
    conn = get_conn()
    c = conn.cursor()
    c.execute('''INSERT INTO orders (order_number, user_id, username, player_id, uc_amount, price, status, created_at,
                 completed_at, product_type, product_name, quantity_text, target_value, target_type)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (num, user.id, user.username or 'Нет username', target_value if target_type == 'player_id' else None,
               uc_amount, price, 'pending', str(datetime.now()), None, product_type, product_name, quantity_text,
               target_value, target_type))
    conn.commit()
    conn.close()
    return num


def payment_markup(order_number):
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('✅ Я оплатил', callback_data=f'paid_{order_number}'),
          types.InlineKeyboardButton('❌ Отмена', callback_data=f'user_cancel_{order_number}'))
    return m


def notify_admin_about_paid_order(order_number):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
    order = c.fetchone()
    conn.close()
    if not order:
        return
    txt = (
        f'💰 <b>ПОДТВЕРЖДЕНИЕ ОПЛАТЫ №{order_number}</b>\n\n'
        f'👤 @{escape_html(order["username"] or "-")}\n'
        f'🛒 {escape_html(order["product_name"])} ({escape_html(order["quantity_text"] or "-")})\n'
        f'💰 {fmt_price(order["price"])} ₽\n'
        f'🎯 <code>{escape_html(order["target_value"] or "-")}</code>'
    )
    mk = types.InlineKeyboardMarkup(row_width=2)
    mk.add(types.InlineKeyboardButton('✅ Подтвердить', callback_data=f'admin_done_{order_number}'),
           types.InlineKeyboardButton('❌ Отказать', callback_data=f'admin_deny_{order_number}'))
    mk.add(types.InlineKeyboardButton('⬅️ В админ-панель', callback_data='admin_back'))
    bot.send_message(ADMIN_ID, txt, reply_markup=mk)


def finalize_order_success(order_number):
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT user_id, product_type, quantity_text, uc_amount FROM orders WHERE order_number = ?', (order_number,))
    o = c.fetchone()
    if not o:
        conn.close()
        return None
    c.execute("UPDATE orders SET status='completed', completed_at=? WHERE order_number=?", (str(datetime.now()), order_number))
    if o['product_type'] == 'uc':
        c.execute('UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1 WHERE user_id = ?', (o['uc_amount'], o['user_id']))
    else:
        c.execute('UPDATE users SET total_orders = total_orders + 1 WHERE user_id = ?', (o['user_id'],))
    conn.commit()
    conn.close()
    return o


def finalize_order_denied(order_number):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE orders SET status='cancelled', completed_at=? WHERE order_number=?", (str(datetime.now()), order_number))
    c.execute('SELECT user_id FROM orders WHERE order_number=?', (order_number,))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row['user_id'] if row else None


@bot.message_handler(commands=['start'])
def start(message):
    ensure_user(message)
    send_or_update_main_menu(message.chat.id, message.from_user.id)


@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, '❌ У вас нет прав администратора!')
        return
    bot.send_message(message.chat.id, '👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:', reply_markup=admin_keyboard())


@bot.callback_query_handler(func=lambda c: c.data.startswith('admin_') and not c.data.startswith('admin_done_') and not c.data.startswith('admin_deny_'))
def admin_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, '❌ Нет прав')
        return

    if call.data == 'admin_back':
        bot.edit_message_text('👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:', call.message.chat.id, call.message.message_id, reply_markup=admin_keyboard())
    elif call.data == 'admin_exit':
        bot.delete_message(call.message.chat.id, call.message.message_id)
    elif call.data == 'admin_stats':
        conn = get_conn(); c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users'); users = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM orders'); orders = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'"); pending = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(price),0) FROM orders WHERE status='completed'"); earned = c.fetchone()[0]
        conn.close()
        bot.edit_message_text(
            f'📊 <b>СТАТИСТИКА</b>\n\n👥 Пользователей: {users}\n📦 Заказов: {orders}\n⏳ Ожидают: {pending}\n💰 Доход: {fmt_price(earned)} ₽',
            call.message.chat.id, call.message.message_id, reply_markup=back_to_admin_markup())
    elif call.data == 'admin_promos':
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(types.InlineKeyboardButton('➕ Создать', callback_data='promo_create'),
               types.InlineKeyboardButton('📋 Список', callback_data='promo_list'))
        mk.add(types.InlineKeyboardButton('🗑 Удалить', callback_data='promo_delete'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='admin_back'))
        bot.edit_message_text('🎟 <b>Промокоды</b>', call.message.chat.id, call.message.message_id, reply_markup=mk)
    elif call.data == 'admin_mailing':
        msg = bot.send_message(call.message.chat.id, 'Отправьте текст или фото для рассылки:')
        bot.register_next_step_handler(msg, process_mailing_content)
    elif call.data == 'admin_prices':
        mk = types.InlineKeyboardMarkup(row_width=2)
        mk.add(types.InlineKeyboardButton('🛒 UC', callback_data='price_cat_uc'),
               types.InlineKeyboardButton('🔥 Популярность', callback_data='price_cat_pop'))
        mk.add(types.InlineKeyboardButton('👑 Подписки', callback_data='price_cat_sub'),
               types.InlineKeyboardButton('⭐️ Telegram Stars', callback_data='price_cat_tg'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='admin_back'))
        bot.edit_message_text('💸 <b>Изменение цен</b>\n\nВыберите категорию:', call.message.chat.id, call.message.message_id, reply_markup=mk)


@bot.callback_query_handler(func=lambda c: c.data == 'promo_create')
def promo_create(call):
    if is_admin(call.from_user.id):
        msg = bot.send_message(call.message.chat.id, 'Введите код промокода:')
        bot.register_next_step_handler(msg, process_promo_code)


def process_promo_code(message):
    if not is_admin(message.from_user.id):
        return
    code = (message.text or '').strip().upper()
    if not code:
        bot.send_message(message.chat.id, 'Код пустой')
        return
    msg = bot.send_message(message.chat.id, 'Скидка 1-100:')
    bot.register_next_step_handler(msg, lambda m: process_promo_discount(m, code))


def process_promo_discount(message, code):
    if not is_admin(message.from_user.id):
        return
    try:
        d = int(message.text)
        if d < 1 or d > 100:
            raise ValueError
    except Exception:
        bot.send_message(message.chat.id, 'Введите 1-100')
        return
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute('INSERT INTO promocodes (code, discount, created_at, active) VALUES (?,?,?,1)', (code, d, str(datetime.now())))
        conn.commit(); bot.send_message(message.chat.id, '✅ Создано')
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, 'Уже существует')
    conn.close()


@bot.callback_query_handler(func=lambda c: c.data == 'promo_list')
def promo_list(call):
    if not is_admin(call.from_user.id):
        return
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT code, discount FROM promocodes ORDER BY created_at DESC')
    rows = c.fetchall(); conn.close()
    txt = '🎟 <b>Список промокодов</b>\n\n' + ('\n'.join([f'• {r["code"]} — {r["discount"]}%' for r in rows]) if rows else 'Пусто')
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=back_to_admin_markup('admin_promos'))


@bot.callback_query_handler(func=lambda c: c.data == 'promo_delete')
def promo_delete(call):
    if not is_admin(call.from_user.id):
        return
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT code, discount FROM promocodes ORDER BY created_at DESC')
    rows = c.fetchall(); conn.close()
    mk = types.InlineKeyboardMarkup(row_width=1)
    for r in rows:
        mk.add(types.InlineKeyboardButton(f'{r["code"]} — {r["discount"]}%', callback_data=f'promo_del_{r["code"]}'))
    mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='admin_promos'))
    bot.edit_message_text('Выберите промокод для удаления:', call.message.chat.id, call.message.message_id, reply_markup=mk)


@bot.callback_query_handler(func=lambda c: c.data.startswith('promo_del_'))
def promo_del_confirm(call):
    if not is_admin(call.from_user.id):
        return
    code = call.data.replace('promo_del_', '', 1)
    conn = get_conn(); c = conn.cursor()
    c.execute('DELETE FROM promocodes WHERE code=?', (code,))
    c.execute('DELETE FROM user_promos WHERE promo_code=?', (code,))
    conn.commit(); conn.close()
    bot.answer_callback_query(call.id, 'Удалено')
    promo_delete(call)


@bot.callback_query_handler(func=lambda c: c.data.startswith('price_cat_') or c.data.startswith('price_set_'))
def price_flow(call):
    if not is_admin(call.from_user.id):
        return
    data = call.data
    if data == 'price_cat_uc':
        mk = types.InlineKeyboardMarkup(row_width=1)
        for uc in sorted(UC_PRICES.keys()):
            p = get_price(f'uc:{uc}', UC_PRICES[uc])
            mk.add(types.InlineKeyboardButton(f'{uc} UC — {fmt_price(p)} ₽', callback_data=f'price_set_uc:{uc}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='admin_prices'))
        bot.edit_message_text('Выберите пакет UC:', call.message.chat.id, call.message.message_id, reply_markup=mk)
    elif data == 'price_cat_pop':
        mk = types.InlineKeyboardMarkup(row_width=1)
        for key, cfg in POPULARITY_ITEMS.items():
            mk.add(types.InlineKeyboardButton(cfg['title'], callback_data=f'price_cat_pop:{key}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='admin_prices'))
        bot.edit_message_text('Выберите тип популярности:', call.message.chat.id, call.message.message_id, reply_markup=mk)
    elif data.startswith('price_cat_pop:'):
        key = data.split(':', 1)[1]
        cfg = POPULARITY_ITEMS[key]
        mk = types.InlineKeyboardMarkup(row_width=1)
        for i, (label, fallback) in enumerate(cfg['prices']):
            p = get_price(f'pop:{key}:{i}', fallback)
            mk.add(types.InlineKeyboardButton(f'{label} — {fmt_price(p)} ₽', callback_data=f'price_set_pop:{key}:{i}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='price_cat_pop'))
        bot.edit_message_text(f'Выберите пакет: {cfg["title"]}', call.message.chat.id, call.message.message_id, reply_markup=mk)
    elif data == 'price_cat_sub':
        mk = types.InlineKeyboardMarkup(row_width=1)
        for i, (label, fallback) in enumerate(SUBSCRIPTION_ITEMS):
            p = get_price(f'sub:{i}', fallback)
            mk.add(types.InlineKeyboardButton(f'{label} — {fmt_price(p)} ₽', callback_data=f'price_set_sub:{i}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='admin_prices'))
        bot.edit_message_text('Выберите подписку:', call.message.chat.id, call.message.message_id, reply_markup=mk)
    elif data == 'price_cat_tg':
        p = get_price('tgstars:unit', 1.5)
        mk = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('💫 Изменить цену за 1 звезду', callback_data='price_set_tg:unit'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='admin_prices'))
        bot.edit_message_text(f'Текущая цена за 1 звезду: {fmt_price(p)} ₽', call.message.chat.id, call.message.message_id, reply_markup=mk)
    elif data.startswith('price_set_'):
        target = data.replace('price_set_', '', 1)
        msg = bot.send_message(call.message.chat.id, 'Введите новую цену (число):')
        bot.register_next_step_handler(msg, lambda m: process_price_input(m, target))


def process_price_input(message, target):
    if not is_admin(message.from_user.id):
        return
    try:
        value = float((message.text or '').strip().replace(',', '.'))
        if value <= 0:
            raise ValueError
    except Exception:
        bot.send_message(message.chat.id, '❌ Неверная цена')
        return

    if target.startswith('uc:'):
        set_price(target, int(value))
    elif target.startswith('pop:'):
        set_price(target, int(value))
    elif target.startswith('sub:'):
        set_price(target, int(value))
    elif target == 'tg:unit':
        set_price('tgstars:unit', value)
    bot.send_message(message.chat.id, f'✅ Цена обновлена: {fmt_price(value)} ₽')


def process_mailing_content(message):
    if not is_admin(message.from_user.id):
        return
    data = {'type': None, 'text': None, 'photo': None, 'caption': None}
    if message.content_type == 'text':
        data['type'] = 'text'; data['text'] = message.text or ''
    elif message.content_type == 'photo':
        data['type'] = 'photo'; data['photo'] = message.photo[-1].file_id; data['caption'] = message.caption or ''
    else:
        bot.send_message(message.chat.id, 'Только текст/фото')
        return
    bot.mailing_data = data
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton('✅ Подтвердить', callback_data='mailing_confirm'),
           types.InlineKeyboardButton('❌ Отмена', callback_data='mailing_cancel'))
    bot.send_message(message.chat.id, 'Подтвердите рассылку', reply_markup=mk)


@bot.callback_query_handler(func=lambda c: c.data in ('mailing_confirm', 'mailing_cancel'))
def mailing_action(call):
    if not is_admin(call.from_user.id):
        return
    if call.data == 'mailing_cancel':
        bot.edit_message_text('Отменено', call.message.chat.id, call.message.message_id)
        return
    m = getattr(bot, 'mailing_data', None)
    if not m:
        return
    conn = get_conn(); c = conn.cursor(); c.execute('SELECT user_id FROM users'); users = c.fetchall(); conn.close()
    ok = 0
    for u in users:
        try:
            if m['type'] == 'photo':
                bot.send_photo(u['user_id'], m['photo'], caption=m['caption'])
            else:
                bot.send_message(u['user_id'], m['text'])
            ok += 1; time.sleep(0.05)
        except Exception:
            pass
    bot.send_message(call.message.chat.id, f'Готово: {ok}')


@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    try:
        handle_callback(call)
    except Exception:
        traceback.print_exc()


def handle_callback(call):
    uid = call.from_user.id
    set_state(uid, menu_chat_id=call.message.chat.id, menu_message_id=call.message.message_id)
    data = call.data

    if data == 'back_main':
        clear_state(uid, keep_menu=True)
        send_or_update_main_menu(call.from_user.id, call.from_user.id)
        return

    if data == 'menu_uc':
        mk = types.InlineKeyboardMarkup(row_width=2)
        for uc in sorted(UC_PRICES.keys()):
            p = get_price(f'uc:{uc}', UC_PRICES[uc])
            mk.add(types.InlineKeyboardButton(f'{uc} UC — {fmt_price(p)} ₽', callback_data=f'ucsel_{uc}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='back_main'))
        edit_menu(uid, '🛒 <b>ВЫБЕРИТЕ ПАКЕТ UC</b>', mk)
        return

    if data.startswith('ucsel_'):
        uc = int(data.split('_')[1])
        price = int(get_price(f'uc:{uc}', UC_PRICES[uc]))
        edit_menu(uid, f'🎮 Пакет: {uc} UC\n💰 Сумма: {fmt_price(price)} ₽\n\nВведите PUBG ID:',
                  types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ Назад', callback_data='menu_uc')))
        set_state(uid, awaiting='uc_player_id', draft={'uc_amount': uc, 'price': price})
        return

    if data == 'menu_popularity':
        mk = types.InlineKeyboardMarkup(row_width=1)
        mk.add(types.InlineKeyboardButton('🔥 Популярность', callback_data='pop_menu_pop_regular'))
        mk.add(types.InlineKeyboardButton('🏠 Популярность для дома', callback_data='pop_menu_pop_home'))
        mk.add(types.InlineKeyboardButton('⏱ На последней минуте', callback_data='pop_menu_pop_last'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='back_main'))
        edit_menu(uid, 'Выберите тип популярности:', mk)
        return

    if data.startswith('pop_menu_'):
        key = data.replace('pop_menu_', '', 1)
        cfg = POPULARITY_ITEMS[key]
        mk = types.InlineKeyboardMarkup(row_width=1)
        for i, (label, fallback) in enumerate(cfg['prices']):
            p = int(get_price(f'pop:{key}:{i}', fallback))
            mk.add(types.InlineKeyboardButton(f'{label} — {fmt_price(p)} ₽', callback_data=f'popsel|{key}|{i}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='menu_popularity'))
        edit_menu(uid, cfg['description'], mk)
        return

    if data.startswith('popsel|'):
        _, key, idx = data.split('|')
        cfg = POPULARITY_ITEMS[key]
        qty, fallback = cfg['prices'][int(idx)]
        price = int(get_price(f'pop:{key}:{idx}', fallback))
        edit_menu(uid, f'Вы выбрали: <b>{escape_html(qty)}</b>\nВведите PUBG ID:',
                  types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ Назад', callback_data=f'pop_menu_{key}')))
        set_state(uid, awaiting='pop_player_id', draft={'product_name': cfg['product_label'], 'quantity_text': qty, 'price': price})
        return

    if data == 'menu_subs':
        mk = types.InlineKeyboardMarkup(row_width=1)
        for i, (label, fallback) in enumerate(SUBSCRIPTION_ITEMS):
            p = int(get_price(f'sub:{i}', fallback))
            mk.add(types.InlineKeyboardButton(f'{label} — {fmt_price(p)} ₽', callback_data=f'subsel_{i}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='back_main'))
        edit_menu(uid, f'{SUBSCRIPTION_INFO_TEXT}\n\nВыберите пакет:', mk)
        return

    if data.startswith('subsel_'):
        i = int(data.split('_')[1])
        label, fallback = SUBSCRIPTION_ITEMS[i]
        price = int(get_price(f'sub:{i}', fallback))
        edit_menu(uid, f'Вы выбрали: <b>{escape_html(label)}</b>\nВведите PUBG ID:',
                  types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ Назад', callback_data='menu_subs')))
        set_state(uid, awaiting='sub_player_id', draft={'product_name': label, 'price': price})
        return

    if data == 'menu_tgstars':
        edit_menu(uid, 'Введите Telegram username получателя (@username):',
                  types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ Назад', callback_data='back_main')))
        set_state(uid, awaiting='tgstars_username', draft={})
        return

    if data == 'menu_profile':
        conn = get_conn(); c = conn.cursor(); c.execute('SELECT * FROM users WHERE user_id=?', (uid,)); row = c.fetchone(); conn.close()
        edit_menu(uid, f'👤 Профиль\n\n🆔 <code>{uid}</code>\n📦 Заказов: {row["total_orders"] if row else 0}', back_to_menu_markup())
        return

    if data == 'menu_leaders':
        conn = get_conn(); c = conn.cursor(); c.execute('SELECT first_name,total_uc FROM users WHERE total_uc>0 ORDER BY total_uc DESC LIMIT 10'); rows = c.fetchall(); conn.close()
        if not rows:
            text = 'Лидеров пока нет.'
        else:
            text = '🏆 <b>ТОП-10</b>\n\n' + '\n'.join([f'{i+1}. {escape_html(mask_name(r["first_name"]))} — {r["total_uc"]} UC' for i, r in enumerate(rows)])
        edit_menu(uid, text, back_to_menu_markup())
        return

    if data == 'menu_reviews':
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton('⭐️ Перейти к отзывам', url=f'https://t.me/{REVIEWS_CHANNEL}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='back_main'))
        edit_menu(uid, 'Отзывы:', mk)
        return

    if data == 'menu_support':
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton('📞 Поддержка', url=f'https://t.me/{SUPPORT_USERNAME}'))
        mk.add(types.InlineKeyboardButton('⬅️ Назад', callback_data='back_main'))
        edit_menu(uid, 'Поддержка 24/7', mk)
        return

    if data == 'menu_promo':
        edit_menu(uid, 'Введите промокод:', types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ Назад', callback_data='back_main')))
        set_state(uid, awaiting='promo_input', draft={})
        return

    if data.startswith('paid_'):
        order = int(data.split('_')[1])
        edit_menu(uid, f'✅ Заказ №{order} отправлен на проверку администратору.', back_to_menu_markup())
        notify_admin_about_paid_order(order)
        return

    if data.startswith('user_cancel_'):
        order = int(data.split('_')[2])
        conn = get_conn(); c = conn.cursor()
        c.execute("UPDATE orders SET status='cancelled', completed_at=? WHERE order_number=? AND status='pending'", (str(datetime.now()), order))
        conn.commit(); conn.close()
        send_or_update_main_menu(call.from_user.id, call.from_user.id)
        return

    if data.startswith('admin_done_'):
        if not is_admin(uid):
            return
        order = int(data.split('_')[2])
        done = finalize_order_success(order)
        if done:
            bot.send_message(done['user_id'], f'✅ Заказ №{order} выполнен!')
        bot.edit_message_text(f'✅ Заказ №{order} подтверждён.', call.message.chat.id, call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ В админ-панель', callback_data='admin_back')))
        return

    if data.startswith('admin_deny_'):
        if not is_admin(uid):
            return
        order = int(data.split('_')[2])
        user_id = finalize_order_denied(order)
        if user_id:
            bot.send_message(user_id, f'❌ Заказ №{order} отклонён.')
        bot.edit_message_text(f'❌ Заказ №{order} отклонён.', call.message.chat.id, call.message.message_id,
                              reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('⬅️ В админ-панель', callback_data='admin_back')))


@bot.message_handler(content_types=['text'])
def text_router(message):
    if message.text and (message.text.startswith('/start') or message.text.startswith('/admin')):
        return
    ensure_user(message)
    st = get_state(message.from_user.id)
    awaiting = st.get('awaiting')
    if not awaiting:
        return

    delete_user_message(message)

    if awaiting == 'uc_player_id':
        handle_uc_player_id(message, st)
    elif awaiting == 'pop_player_id':
        handle_pop_player_id(message, st)
    elif awaiting == 'sub_player_id':
        handle_sub_player_id(message, st)
    elif awaiting == 'tgstars_username':
        handle_tg_username(message)
    elif awaiting == 'tgstars_amount':
        handle_tg_amount(message, st)
    elif awaiting == 'promo_input':
        handle_user_promo(message)


def valid_pubg_id(text):
    v = (text or '').strip()
    return v if v.isdigit() and v.startswith('5') else None


def handle_uc_player_id(message, state):
    pid = valid_pubg_id(message.text)
    if not pid:
        edit_menu(message.from_user.id, '❌ Неверный PUBG ID. Введите ID, который начинается с 5.', back_to_menu_markup())
        return
    d = state['draft']
    order = create_order(message.from_user, 'uc', 'UC', f'{d["uc_amount"]} UC', d['price'], pid, 'player_id', uc_amount=d['uc_amount'])
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, build_payment_text(order, 'UC', f'{d["uc_amount"]} UC', d['price'], pid, 'player_id'), payment_markup(order))


def handle_pop_player_id(message, state):
    pid = valid_pubg_id(message.text)
    if not pid:
        edit_menu(message.from_user.id, '❌ Неверный PUBG ID. Введите ID, который начинается с 5.', back_to_menu_markup())
        return
    d = state['draft']
    order = create_order(message.from_user, 'popularity', d['product_name'], d['quantity_text'], d['price'], pid, 'player_id')
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, build_payment_text(order, d['product_name'], d['quantity_text'], d['price'], pid, 'player_id'), payment_markup(order))


def handle_sub_player_id(message, state):
    pid = valid_pubg_id(message.text)
    if not pid:
        edit_menu(message.from_user.id, '❌ Неверный PUBG ID. Введите ID, который начинается с 5.', back_to_menu_markup())
        return
    d = state['draft']
    order = create_order(message.from_user, 'subscription', 'Подписки', d['product_name'], d['price'], pid, 'player_id')
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, build_payment_text(order, 'Подписки', d['product_name'], d['price'], pid, 'player_id'), payment_markup(order))


def normalize_username(text):
    username = (text or '').strip().replace('https://t.me/', '').lstrip('@')
    allowed = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
    if not username or len(username) < 5 or len(username) > 32 or any(ch not in allowed for ch in username):
        return None
    return '@' + username


def handle_tg_username(message):
    username = normalize_username(message.text)
    if not username:
        edit_menu(message.from_user.id, '❌ Неверный username.', back_to_menu_markup())
        return
    set_state(message.from_user.id, awaiting='tgstars_amount', draft={'username': username})
    unit = get_price('tgstars:unit', 1.5)
    edit_menu(message.from_user.id, f'Цена за 1 звезду: {fmt_price(unit)} ₽\nВведите количество (мин. 50):', back_to_menu_markup())


def handle_tg_amount(message, state):
    try:
        amount = int((message.text or '').strip())
        if amount < 50:
            raise ValueError
    except Exception:
        edit_menu(message.from_user.id, '❌ Минимум 50 звёзд.', back_to_menu_markup())
        return
    unit = get_price('tgstars:unit', 1.5)
    price = amount * unit
    username = state['draft']['username']
    order = create_order(message.from_user, 'telegram_stars', 'Telegram Stars', f'{amount} звёзд', price, username, 'telegram_username')
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, build_payment_text(order, 'Telegram Stars', f'{amount} звёзд', price, username, 'telegram_username'), payment_markup(order))


def handle_user_promo(message):
    code = (message.text or '').strip().upper()
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT discount, code FROM promocodes WHERE UPPER(code)=? AND active=1', (code,))
    p = c.fetchone()
    if not p:
        conn.close(); edit_menu(message.from_user.id, '❌ Промокод не найден.', back_to_menu_markup()); clear_state(message.from_user.id, keep_menu=True); return
    c.execute('INSERT OR REPLACE INTO user_promos (user_id, promo_code, discount, activated_at) VALUES (?,?,?,?)',
              (message.from_user.id, p['code'], p['discount'], str(datetime.now())))
    conn.commit(); conn.close()
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, f'✅ Промокод активирован: {p["discount"]}%', back_to_menu_markup())


if __name__ == '__main__':
    init_db()
    print('✅ БОТ ЗАПУЩЕН')
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            print('Ошибка:', e)
            traceback.print_exc()
            time.sleep(5)
