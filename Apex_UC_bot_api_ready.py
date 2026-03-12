
import math
import os
import sqlite3
import threading
import time
import traceback
from datetime import datetime, timedelta

import requests
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
MAIN_MENU_IMAGE = 'IMG_2822.jpeg'
MAIN_MENU_IMAGE_FALLBACK = 'IMG_2811.jpeg'

CARDS = [
    {'bank': 'СБЕР', 'card': '2202 2084 1737 7224', 'recipient': 'Дмитрий'},
    {'bank': 'ВТБ', 'card': '2200 2479 5387 8262', 'recipient': 'Дмитрий'}
]

UC_PRICES = {
    60: 78,
    325: 385,
    660: 779,
    1800: 1951,
    3850: 3950,
    8100: 7750
}

# ---------- HUTAO API ----------
HUTAO_API_BASE = 'https://hutao.syntex.az/api/v1'
HUTAO_API_TOKEN = '58e84617-f28f-48cd-8b5d-981b107caf89'
HUTAO_GAME_CODE = 'oxide'
HUTAO_PRODUCT_IDS = {
    60: '1',
    325: '2',
    660: '3',
    1800: '8',
    3850: '10',
    8100: '9'
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
        'admin_label': 'Популярность',
        'prices': [
            ('10 000 ПП', 150),
            ('20 000 ПП', 300),
            ('40 000 ПП', 600),
            ('60 000 ПП', 900),
            ('100 000 ПП', 1500),
            ('200 000 ПП', 3000),
            ('500 000 ПП', 7500),
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
        'admin_label': 'ПП для дома',
        'prices': [
            ('20 000 ПП для дома', 250),
            ('40 000 ПП для дома', 500),
            ('60 000 ПП для дома', 750),
            ('100 000 ПП для дома', 1250),
            ('200 000 ПП для дома', 2500),
            ('500 000 ПП для дома', 6250),
        ]
    },
    'pop_last': {
        'title': '✨Популярность для последних минут раунда✨',
        'description': (
            '✨<b>Популярность для последних минут раунда</b> ✨\n\n'
            '➤Оформляйте заказ заранее и популярность вам поступит в последние 1-2 минуты раунда\n\n'
            '❕Оформляйте заказ не позже 30 минут до конца раунда'
        ),
        'product_label': 'Популярность на последней минуте',
        'admin_label': 'Популярность на последней минуте',
        'prices': [
            ('50 000 ПП', 1300),
            ('100 000 ПП', 2600),
            ('150 000 ПП', 3900),
            ('200 000 ПП', 5200),
            ('500 000 ПП', 13000),
        ]
    }
}

SUBSCRIPTION_INFO_TEXT = (
    '⭐️<b>Prime</b> (1 месяц) - 60 UC\n'
    '⭐️<b>Prime</b> (3 месяца) - 180 UC\n'
    '⭐️<b>Prime</b> (6 месяцев) - 360 UC\n'
    '⭐️<b>Prime</b> (12 месяцев) - 720 UC\n'
    '❗️А также - 3 UC, 5 RP очков каждый день\n\n'
    '👑\n'
    '<b>PRIME PLUS</b> (1 месяц)\n'
    '- 660 UC сразу + 240 UC в течении месяца\n'
    '+300 PR очков + скидочные купоны + МАГАЗИН BP + ГАРДЕРОБ\n\n'
    '👑\n'
    '<b>PRIME PLUS</b> (3 месяца)\n'
    '- 1980 UC сразу + 730 UC в течении 3-х месяцев\n'
    '+900 PR очков + скидочные купоны + МАГАЗИН BP + ГАРДЕРОБ\n\n'
    '👑\n'
    '<b>PRIME PLUS</b> (6 месяцев)\n'
    '- 3960 UC сразу + 1460 UC в течении 6-ти месяцев\n'
    '+1,800 PR очков + скидочные купоны + МАГАЗИН BP + ГАРДЕРОБ\n\n'
    '👑\n'
    '<b>PRIME PLUS</b> (12 месяцев)\n'
    '- 7920 UC сразу + 2920 UC в течении года\n'
    '+3,600 PR очков + скидочные купоны + МАГАЗИН BP + ГАРДЕРОБ\n\n'
    '🔺Миф Кристал: покупается 1 раз в неделю\n'
    '⚪️Набор «первой покупки»: можно купить 1 раз\n'
    '🟡Набор «материалов»: можно купить 1 раз\n'
    '🔴Набор «миф. эмблем»: можно купить 1 раз'
)

SUBSCRIPTION_ITEMS = [
    ('Prime (1 месяц)', 120),
    ('Prime (3 месяца)', 320),
    ('Prime (6 месяцев)', 557),
    ('Prime (12 месяцев)', 1007),
    ('Prime Plus (1 месяц)', 850),
    ('Prime Plus (3 месяца)', 2550),
    ('Prime Plus (6 месяцев)', 5100),
    ('Prime Plus (12 месяцев)', 6960),
    ('Миф.Кристал', 330),
]

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

def mask_leader_name(name):
    name = str(name or 'Игрок').strip()
    if not name:
        return 'Игрок'
    visible = max(2, math.ceil(len(name) / 2))
    visible = min(visible, len(name))
    hidden = max(0, len(name) - visible)
    return name[:visible] + ('*' * hidden)

def get_main_menu_image_path():
    image_names = [MAIN_MENU_IMAGE, MAIN_MENU_IMAGE_FALLBACK]
    candidates = []
    for image_name in image_names:
        candidates.extend([
            image_name,
            os.path.join(os.getcwd(), image_name),
            os.path.join(os.path.dirname(__file__), image_name),
            os.path.join('/mnt/data', image_name),
        ])
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None

def get_table_columns(cursor, table_name):
    cursor.execute(f'PRAGMA table_info({table_name})')
    return [col[1] for col in cursor.fetchall()]

def add_column_if_not_exists(cursor, table, column, col_type, default=None):
    columns = get_table_columns(cursor, table)
    if column not in columns:
        if default is not None:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type} DEFAULT {default}')
        else:
            cursor.execute(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}')

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        join_date TEXT,
        total_uc INTEGER DEFAULT 0,
        total_orders INTEGER DEFAULT 0
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number INTEGER UNIQUE,
        user_id INTEGER,
        username TEXT,
        player_id TEXT,
        uc_amount INTEGER,
        price REAL,
        status TEXT,
        created_at TEXT,
        completed_at TEXT,
        discount INTEGER DEFAULT 0,
        promocode TEXT DEFAULT NULL,
        product_type TEXT DEFAULT 'uc',
        product_name TEXT DEFAULT 'UC',
        quantity_text TEXT DEFAULT NULL,
        target_value TEXT DEFAULT NULL,
        target_type TEXT DEFAULT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS promocodes (
        code TEXT PRIMARY KEY,
        discount INTEGER,
        created_at TEXT,
        max_uses INTEGER DEFAULT 0,
        used_count INTEGER DEFAULT 0,
        expires_at TEXT DEFAULT NULL,
        active INTEGER DEFAULT 1
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_promos (
        user_id INTEGER,
        promo_code TEXT,
        discount INTEGER,
        activated_at TEXT,
        PRIMARY KEY (user_id, promo_code)
    )""")
    add_column_if_not_exists(c, 'users', 'total_orders', 'INTEGER', '0')
    add_column_if_not_exists(c, 'orders', 'discount', 'INTEGER', '0')
    add_column_if_not_exists(c, 'orders', 'promocode', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'orders', 'product_type', 'TEXT', "'uc'")
    add_column_if_not_exists(c, 'orders', 'product_name', 'TEXT', "'UC'")
    add_column_if_not_exists(c, 'orders', 'quantity_text', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'orders', 'target_value', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'orders', 'target_type', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'promocodes', 'max_uses', 'INTEGER', '0')
    add_column_if_not_exists(c, 'promocodes', 'used_count', 'INTEGER', '0')
    add_column_if_not_exists(c, 'promocodes', 'expires_at', 'TEXT', 'NULL')
    add_column_if_not_exists(c, 'promocodes', 'active', 'INTEGER', '1')
    conn.commit()
    conn.close()

def ensure_user(message):
    user_id = message.from_user.id
    username = message.from_user.username or 'Нет username'
    first_name = message.from_user.first_name or 'Игрок'
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT OR IGNORE INTO users
                 (user_id, username, first_name, join_date, total_uc, total_orders)
                 VALUES (?,?,?,?,?,?)""",
              (user_id, username, first_name, str(datetime.now()), 0, 0))
    c.execute("""UPDATE users SET username = ?, first_name = ? WHERE user_id = ?""",
              (username, first_name, user_id))
    conn.commit()
    conn.close()

def get_next_order_number():
    conn = get_conn()
    c = conn.cursor()
    c.execute('SELECT MAX(order_number) FROM orders')
    max_num = c.fetchone()[0]
    conn.close()
    return (max_num or 0) + 1

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
        current = user_states.get(user_id, {})
        menu_chat_id = current.get('menu_chat_id') if keep_menu else None
        menu_message_id = current.get('menu_message_id') if keep_menu else None
        menu_message_type = current.get('menu_message_type') if keep_menu else None
        user_states[user_id] = {}
        if keep_menu and menu_chat_id and menu_message_id:
            user_states[user_id]['menu_chat_id'] = menu_chat_id
            user_states[user_id]['menu_message_id'] = menu_message_id
            user_states[user_id]['menu_message_type'] = menu_message_type or 'text'

def delete_user_message(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

def build_inline_button(text, callback_data, emoji_id=None):
    kwargs = {'text': text, 'callback_data': callback_data}
    if emoji_id:
        try:
            return types.InlineKeyboardButton(icon_custom_emoji_id=str(emoji_id), **kwargs)
        except TypeError:
            pass
    return types.InlineKeyboardButton(**kwargs)

def build_url_button(text, url, emoji_id=None):
    kwargs = {'text': text, 'url': url}
    if emoji_id:
        try:
            return types.InlineKeyboardButton(icon_custom_emoji_id=str(emoji_id), **kwargs)
        except TypeError:
            pass
    return types.InlineKeyboardButton(**kwargs)

def menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(build_inline_button('Купить UC', 'menu_uc', '5199565907654892301'))
    markup.add(
        build_inline_button('Популярность', 'menu_popularity', '5253698266704408740'),
        build_inline_button('Подписки', 'menu_subs', '5253686910810878689')
    )
    markup.add(
        build_inline_button('Промокоды', 'menu_promo', '5377599075237502153'),
        build_inline_button('Информация', 'menu_info', '5447410659077661506')
    )
    markup.add(build_inline_button('Пополнить Telegram звезды', 'menu_tgstars', '5422740611742585475'))
    markup.add(
        build_inline_button('Поддержка', 'menu_support', '5213179235996294999'),
        build_inline_button('Отзывы', 'menu_reviews', '5463289097336405244')
    )
    return markup

def back_to_menu_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(build_inline_button('В меню', 'back_main', '5255703720078879038'))
    return markup

def render_main_menu_text(first_name='Игрок'):
    return """<tg-emoji emoji-id=\"5404617696589390973\">👋</tg-emoji> <b>ДОБРО ПОЖАЛОВАТЬ В APEX UC SHOP!</b>

<tg-emoji emoji-id=\"5253558615842785529\">✅</tg-emoji> <b>Наши преимущества:</b>
• Быстрая доставка 5-15 минут
• 100% гарантия пополнения
• Круглосуточная поддержка
• Низкие цены

<tg-emoji emoji-id=\"5301038027601098171\">👇</tg-emoji> Нажми <b>КУПИТЬ UC</b> чтобы начать"""

def send_or_update_main_menu(chat_id, user_id, first_name='Игрок'):
    text = render_main_menu_text(first_name)
    markup = menu_keyboard()
    state = get_state(user_id)
    menu_message_id = state.get('menu_message_id')
    menu_chat_id = state.get('menu_chat_id', chat_id)
    image_path = get_main_menu_image_path()
    if menu_message_id and menu_chat_id == chat_id:
        try:
            bot.delete_message(chat_id, menu_message_id)
        except Exception:
            pass
    clear_state(user_id, keep_menu=False)
    if image_path:
        try:
            with open(image_path, 'rb') as photo:
                sent = bot.send_photo(chat_id, photo, caption=text, reply_markup=markup)
            set_state(user_id, menu_chat_id=chat_id, menu_message_id=sent.message_id, menu_message_type='photo')
            return
        except Exception:
            pass
    sent = bot.send_message(chat_id, text, reply_markup=markup)
    set_state(user_id, menu_chat_id=chat_id, menu_message_id=sent.message_id, menu_message_type='text')

def edit_menu(user_id, text, reply_markup):
    state = get_state(user_id)
    chat_id = state.get('menu_chat_id')
    message_id = state.get('menu_message_id')
    if not chat_id or not message_id:
        return False
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass
    try:
        sent = bot.send_message(chat_id, text, reply_markup=reply_markup)
        set_state(user_id, menu_chat_id=chat_id, menu_message_id=sent.message_id, menu_message_type='text')
        return True
    except Exception:
        return False

def show_main_menu_for_user(user):
    send_or_update_main_menu(chat_id=user.id, user_id=user.id, first_name=user.first_name or 'Игрок')

def format_uc_cart_summary(cart):
    parts = []
    for uc_amount in sorted(cart):
        count = int(cart.get(uc_amount, 0))
        if count > 0:
            parts.append(f"{uc_amount} UC × {count}")
    return ', '.join(parts) if parts else 'Корзина пуста'

def calc_uc_cart(cart):
    total_uc = 0
    total_price = 0
    total_packs = 0
    normalized = {}
    for key, value in (cart or {}).items():
        try:
            uc_amount = int(key)
            count = int(value)
        except Exception:
            continue
        if uc_amount in UC_PRICES and count > 0:
            normalized[uc_amount] = count
            total_uc += uc_amount * count
            total_price += UC_PRICES[uc_amount] * count
            total_packs += count
    return normalized, total_uc, total_price, total_packs

def parse_quantity_text_to_cart(quantity_text):
    cart = {}
    if not quantity_text:
        return cart
    for chunk in str(quantity_text).split(','):
        chunk = chunk.strip()
        if 'UC' not in chunk or '×' not in chunk:
            continue
        try:
            left, right = chunk.split('×', 1)
            uc_amount = int(''.join(ch for ch in left if ch.isdigit()))
            count = int(''.join(ch for ch in right if ch.isdigit()))
            if uc_amount > 0 and count > 0:
                cart[uc_amount] = cart.get(uc_amount, 0) + count
        except Exception:
            continue
    return cart

def build_uc_cart_text(cart, discount=0, promo_code=None):
    cart, total_uc, total_price, total_packs = calc_uc_cart(cart)
    lines = [
        '<b>🛒 КОРЗИНА UC</b>', '',
        f'📦 Паков выбрано: <b>{total_packs}</b>',
        f'🎮 Всего UC: <b>{total_uc}</b>',
        f'💰 Общая сумма: <b>{fmt_price(total_price)} ₽</b>', ''
    ]
    if cart:
        lines.append('<b>Вы выбрали:</b>')
        for uc_amount in sorted(cart):
            count = cart[uc_amount]
            subtotal = UC_PRICES[uc_amount] * count
            lines.append(f'• {uc_amount} UC × {count} — {fmt_price(subtotal)} ₽')
        if discount:
            discounted = int(total_price * (100 - discount) / 100)
            lines.extend(['', f'🎟 Промокод: <b>{escape_html(promo_code or "активен")}</b> (-{discount}%)', f'💳 К оплате со скидкой: <b>{fmt_price(discounted)} ₽</b>'])
    else:
        lines.append('Корзина пока пуста. Нажимайте на нужные паки ниже, чтобы добавить их.')
    lines.extend(['', 'Нажмите на пак, чтобы сразу добавить его в корзину.'])
    return '\n'.join(lines)

def build_uc_cart_markup(cart, active_uc=None):
    cart, *_ = calc_uc_cart(cart)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for uc_amount in sorted(UC_PRICES):
        price = UC_PRICES[uc_amount]
        label = f'{uc_amount} UC — {fmt_price(price)} ₽'
        if int(cart.get(uc_amount, 0)) > 0:
            markup.row(
                build_inline_button(f'{uc_amount} UC +1', f'ucadd_{uc_amount}'),
                build_inline_button('Удалить 1', f'ucrem_{uc_amount}')
            )
        else:
            markup.add(build_inline_button(label, f'ucsel_{uc_amount}'))
    if cart:
        markup.add(build_inline_button('Купить', 'uc_checkout', '5253558615842785529'))
        markup.add(build_inline_button('Очистить корзину', 'uc_clear', '5255732655273570754'))
    markup.add(build_inline_button('Назад', 'back_main', '5255703720078879038'))
    return markup

def build_payment_text(order_number, product_name, quantity_text, price, target_value, target_type, uc_amount=0):
    lines = [f'<tg-emoji emoji-id="5253558615842785529">✅</tg-emoji> <b>ЗАКАЗ №{order_number} СОЗДАН!</b>', '',
             '<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> <b>Детали заказа:</b>',
             f'• Товар: {escape_html(product_name)}']
    if quantity_text:
        lines.append(f'• Выбрано: {escape_html(quantity_text)}')
    if product_name == 'UC' and uc_amount:
        lines.append(f'• Всего UC: {uc_amount}')
    if target_type == 'player_id':
        lines.append(f'• PUBG ID: <code>{escape_html(target_value)}</code>')
    elif target_type == 'telegram_username':
        lines.append(f'• Получатель: <code>{escape_html(target_value)}</code>')
    lines.append(f'• Сумма: {fmt_price(price)} ₽')
    lines.append('')
    lines.append('<tg-emoji emoji-id="5253558615842785529">✅</tg-emoji> <b>РЕКВИЗИТЫ ДЛЯ ОПЛАТЫ:</b>')
    lines.append('')
    for card in CARDS:
        bank_emoji = '5201863929906620821' if card['bank'] == 'СБЕР' else '5201870565631093696'
        lines.extend([
            f'<tg-emoji emoji-id="{bank_emoji}">🏦</tg-emoji> {card["bank"]}',
            f'<tg-emoji emoji-id="5287761106868140153">💳</tg-emoji> Карта: <code>{card["card"]}</code>',
            f'<tg-emoji emoji-id="5458789419014182183">👤</tg-emoji> Получатель: {escape_html(card["recipient"])}',
            ''
        ])
    lines.extend([f'<tg-emoji emoji-id="5375296873982604963">💰</tg-emoji> <b>Сумма: {fmt_price(price)} ₽</b>', '',
                  '<tg-emoji emoji-id="5447644880824181073">⚠️</tg-emoji> <b>Важно:</b>',
                  '1. Переведите точную сумму.',
                  '2. После оплаты нажмите кнопку «Я оплатил».',
                  '3. Кнопка «Отмена» вернёт вас в главное меню.'])
    return '\n'.join(lines)

def create_order(user, product_type, product_name, quantity_text, price, target_value, target_type, uc_amount=0, discount=0, promo_code=None):
    order_number = get_next_order_number()
    conn = get_conn()
    c = conn.cursor()
    c.execute("""INSERT INTO orders
                 (order_number, user_id, username, player_id, uc_amount, price, status, created_at,
                  completed_at, discount, promocode, product_type, product_name, quantity_text, target_value, target_type)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (order_number, user.id, user.username or 'Нет username',
               target_value if target_type == 'player_id' else None, uc_amount, price, 'pending',
               str(datetime.now()), None, discount, promo_code, product_type, product_name,
               quantity_text, target_value, target_type))
    if promo_code:
        c.execute('DELETE FROM user_promos WHERE user_id = ? AND promo_code = ?', (user.id, promo_code))
    conn.commit()
    conn.close()
    return order_number

def payment_markup(order_number):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        build_inline_button('Я оплатил', f'paid_{order_number}', '5253558615842785529'),
        build_inline_button('Отмена', f'user_cancel_{order_number}', '5255732655273570754')
    )
    return markup

def notify_admin_about_paid_order(order_number):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT user_id, username, product_name, quantity_text, price, target_value, target_type, uc_amount
                 FROM orders WHERE order_number = ?""", (order_number,))
    order = c.fetchone()
    conn.close()
    if not order:
        return
    username = order['username'] or 'Нет username'
    target_label = 'PUBG ID' if order['target_type'] == 'player_id' else 'Telegram username'
    admin_text = [f'💰 <b>ПОДТВЕРЖДЕНИЕ ОПЛАТЫ №{order_number}</b>', '',
                  f'👤 Пользователь: @{escape_html(username)}',
                  f'🆔 User ID: <code>{order["user_id"]}</code>',
                  f'🛒 Товар: {escape_html(order["product_name"])}']
    if order['quantity_text']:
        admin_text.append(f'📦 Выбрано: {escape_html(order["quantity_text"])}')
    if order['product_name'] == 'UC' and order['uc_amount']:
        admin_text.append(f'🎮 Всего UC: {order["uc_amount"]}')
    admin_text.extend([f'💰 Сумма: {fmt_price(order["price"])} ₽',
                       f'{target_label}: <code>{escape_html(order["target_value"] or "-")}</code>', '',
                       '👇 <b>Выберите действие:</b>'])
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        build_inline_button('Выполнил', f'admin_done_{order_number}', '5253558615842785529'),
        build_inline_button('Отказать', f'admin_deny_{order_number}', '5255732655273570754')
    )
    try:
        bot.send_message(ADMIN_ID, '\n'.join(admin_text), reply_markup=markup)
    except Exception:
        traceback.print_exc()

def hutao_headers():
    return {'X-Api-Token': HUTAO_API_TOKEN, 'Content-Type': 'application/json', 'Accept': 'application/json'}

def send_uc_via_hutao(player_id, quantity_text, order_number):
    cart = parse_quantity_text_to_cart(quantity_text)
    if not cart:
        raise RuntimeError('Не удалось определить состав UC корзины')
    for uc_amount in sorted(cart):
        count = int(cart.get(uc_amount, 0))
        product_id = HUTAO_PRODUCT_IDS.get(uc_amount)
        if not product_id:
            raise RuntimeError(f'Не найден product_id для {uc_amount} UC')
        for idx in range(count):
            payload = {
                'game_code': HUTAO_GAME_CODE,
                'product_id': str(product_id),
                'player_id': str(player_id),
                'idempotency_key': f'order_{order_number}_{uc_amount}_{idx + 1}'
            }
            response = requests.post(f'{HUTAO_API_BASE}/order', headers=hutao_headers(), json=payload, timeout=30)
            try:
                data = response.json()
            except Exception:
                data = {'raw': response.text}
            if response.status_code >= 400:
                raise RuntimeError(f'Hutao API HTTP {response.status_code}: {data}')
            if not data.get('api_order_id'):
                raise RuntimeError(f'Hutao API не вернул api_order_id: {data}')

def finalize_order_success(order_number):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""SELECT user_id, product_type, product_name, quantity_text, target_value, uc_amount
                 FROM orders WHERE order_number = ?""", (order_number,))
    order = c.fetchone()
    if not order:
        conn.close()
        return None
    c.execute("UPDATE orders SET status = 'completed', completed_at = ? WHERE order_number = ?",
              (str(datetime.now()), order_number))
    if order['product_type'] == 'uc' and order['uc_amount']:
        c.execute("""UPDATE users SET total_uc = total_uc + ?, total_orders = total_orders + 1 WHERE user_id = ?""",
                  (order['uc_amount'], order['user_id']))
    else:
        c.execute("""UPDATE users SET total_orders = total_orders + 1 WHERE user_id = ?""", (order['user_id'],))
    conn.commit()
    conn.close()
    return order

def finalize_order_denied(order_number):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE orders SET status = 'cancelled', completed_at = ? WHERE order_number = ?",
              (str(datetime.now()), order_number))
    c.execute('SELECT user_id FROM orders WHERE order_number = ?', (order_number,))
    row = c.fetchone()
    conn.commit()
    conn.close()
    return row['user_id'] if row else None

@bot.message_handler(commands=['start'])
def start(message):
    ensure_user(message)
    send_or_update_main_menu(message.chat.id, message.from_user.id, message.from_user.first_name or 'Игрок')

def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton('📊 Статистика', callback_data='admin_stats'),
               types.InlineKeyboardButton('🎟 Промокоды', callback_data='admin_promos'))
    markup.add(types.InlineKeyboardButton('📢 Рассылка', callback_data='admin_mailing'))
    return markup

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, '❌ У вас нет прав администратора!')
        return
    bot.send_message(message.chat.id, '👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:', reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_') and not call.data.startswith('admin_done_') and not call.data.startswith('admin_deny_'))
def admin_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, '❌ Нет прав')
        return
    if call.data == 'admin_stats':
        conn = get_conn()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users'); total_users = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM orders'); total_orders = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'"); completed = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'"); pending = c.fetchone()[0]
        c.execute("SELECT COALESCE(SUM(price), 0) FROM orders WHERE status = 'completed'"); earned = c.fetchone()[0]
        conn.close()
        text = ('📊 <b>СТАТИСТИКА</b>\n\n'
                f'👥 Пользователей: {total_users}\n'
                f'📦 Всего заказов: {total_orders}\n'
                f'✅ Выполнено: {completed}\n'
                f'⏳ В обработке: {pending}\n'
                f'💰 Заработано: {fmt_price(earned)} ₽')
        markup = types.InlineKeyboardMarkup().add(build_inline_button('Назад', 'admin_back', '5255703720078879038'))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data == 'admin_promos':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton('➕ Создать', callback_data='promo_create'),
                   types.InlineKeyboardButton('📋 Список', callback_data='promo_list'))
        markup.add(types.InlineKeyboardButton('🗑 Удалить', callback_data='promo_delete'))
        markup.add(build_inline_button('Назад', 'admin_back', '5255703720078879038'))
        bot.edit_message_text('🎟 <b>Управление промокодами</b>', call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif call.data == 'admin_mailing':
        msg = bot.send_message(call.message.chat.id, '📢 <b>Рассылка</b>\n\nОтправьте сообщение для рассылки. Можно текст или фото с подписью:')
        bot.register_next_step_handler(msg, process_mailing_content)
    elif call.data == 'admin_back':
        bot.edit_message_text('👨‍💼 <b>АДМИН-ПАНЕЛЬ</b>\n\nВыберите действие:', call.message.chat.id, call.message.message_id, reply_markup=admin_keyboard())

@bot.callback_query_handler(func=lambda call: call.data == 'promo_create')
def promo_create_step1(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, '❌ Нет прав')
        return
    msg = bot.send_message(call.message.chat.id, '🎟 <b>Создание промокода</b>\n\nВведите код промокода:')
    bot.register_next_step_handler(msg, process_promo_code)

def process_promo_code(message):
    if not is_admin(message.from_user.id):
        return
    code = (message.text or '').strip().upper()
    if not code:
        bot.send_message(message.chat.id, '❌ Код не может быть пустым.')
        return
    msg = bot.send_message(message.chat.id, f'Код: {escape_html(code)}\nТеперь введите размер скидки (1-100):')
    bot.register_next_step_handler(msg, lambda m: process_promo_discount(m, code))

def process_promo_discount(message, code):
    if not is_admin(message.from_user.id):
        return
    try:
        discount = int(message.text)
        if discount < 1 or discount > 100:
            raise ValueError
    except Exception:
        bot.send_message(message.chat.id, '❌ Введите целое число от 1 до 100.')
        return
    msg = bot.send_message(message.chat.id, 'Введите максимальное количество использований (0 - безлимит):')
    bot.register_next_step_handler(msg, lambda m: process_promo_uses(m, code, discount))

def process_promo_uses(message, code, discount):
    if not is_admin(message.from_user.id):
        return
    try:
        max_uses = int(message.text)
        if max_uses < 0:
            raise ValueError
    except Exception:
        bot.send_message(message.chat.id, '❌ Введите корректное число.')
        return
    msg = bot.send_message(message.chat.id, 'Введите срок действия в днях (0 - бессрочно):')
    bot.register_next_step_handler(msg, lambda m: process_promo_expiry(m, code, discount, max_uses))

def process_promo_expiry(message, code, discount, max_uses):
    if not is_admin(message.from_user.id):
        return
    try:
        days = int(message.text)
        if days < 0:
            raise ValueError
    except Exception:
        bot.send_message(message.chat.id, '❌ Введите корректное число.')
        return
    expires_at = None if days == 0 else str(datetime.now() + timedelta(days=days))
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute('INSERT INTO promocodes (code, discount, created_at, max_uses, used_count, expires_at, active) VALUES (?,?,?,?,?,?,1)',
                  (code, discount, str(datetime.now()), max_uses, 0, expires_at))
        conn.commit()
        bot.send_message(message.chat.id, f'✅ Промокод <b>{escape_html(code)}</b> создан.')
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, '❌ Такой промокод уже существует.')
    finally:
        conn.close()

@bot.callback_query_handler(func=lambda call: call.data == 'promo_list')
def promo_list(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, '❌ Нет прав')
        return
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT code, discount, max_uses, used_count, expires_at, active FROM promocodes ORDER BY created_at DESC')
    promos = c.fetchall(); conn.close()
    if not promos:
        text = '🎟 Промокодов пока нет.'
    else:
        lines = ['🎟 <b>Список промокодов:</b>', '']
        for p in promos:
            expiry = 'бессрочно' if not p['expires_at'] else p['expires_at'][:10]
            limit = 'безлимит' if p['max_uses'] == 0 else p['max_uses']
            status = '✅ Активен' if p['active'] else '❌ Неактивен'
            lines.append(f'• <b>{escape_html(p["code"])}</b> — {p["discount"]}% ({p["used_count"]}/{limit}) {expiry} {status}')
        text = '\n'.join(lines)
    markup = types.InlineKeyboardMarkup().add(build_inline_button('Назад', 'admin_promos', '5255703720078879038'))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'promo_delete')
def promo_delete_menu(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, '❌ Нет прав')
        return
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT code, discount FROM promocodes ORDER BY created_at DESC')
    promos = c.fetchall(); conn.close()
    markup = types.InlineKeyboardMarkup(row_width=1)
    if not promos:
        markup.add(build_inline_button('Назад', 'admin_promos', '5255703720078879038'))
        bot.edit_message_text('🗑 <b>Удаление промокода</b>\n\nПромокодов пока нет.', call.message.chat.id, call.message.message_id, reply_markup=markup)
        return
    for promo in promos:
        markup.add(types.InlineKeyboardButton(f'{promo["code"]} — {promo["discount"]}%', callback_data=f'promo_delete_select:{promo["code"]}'))
    markup.add(build_inline_button('Назад', 'admin_promos', '5255703720078879038'))
    bot.edit_message_text('🗑 <b>Удаление промокода</b>\n\nНажмите на промокод, чтобы удалить его:', call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('promo_delete_select:'))
def promo_delete_select(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, '❌ Нет прав')
        return
    code = call.data.split(':', 1)[1]
    conn = get_conn(); c = conn.cursor()
    c.execute('DELETE FROM promocodes WHERE code = ?', (code,))
    c.execute('DELETE FROM user_promos WHERE promo_code = ?', (code,))
    conn.commit(); conn.close()
    bot.answer_callback_query(call.id, '✅ Промокод удалён')
    promo_delete_menu(call)

def process_mailing_content(message):
    if not is_admin(message.from_user.id):
        return
    mailing_data = {'type': None, 'text': None, 'photo': None, 'caption': None}
    if message.content_type == 'text':
        text = (message.text or '').strip()
        if not text:
            bot.send_message(message.chat.id, '❌ Текст не может быть пустым.')
            return
        mailing_data['type'] = 'text'; mailing_data['text'] = text
    elif message.content_type == 'photo':
        mailing_data['type'] = 'photo'; mailing_data['photo'] = message.photo[-1].file_id; mailing_data['caption'] = (message.caption or '').strip()
    else:
        bot.send_message(message.chat.id, '❌ Поддерживается только текст или фото с подписью.')
        return
    bot.mailing_data = mailing_data
    markup = types.InlineKeyboardMarkup()
    markup.add(build_inline_button('Подтвердить', 'mailing_confirm', '5253558615842785529'),
               build_inline_button('Отмена', 'mailing_cancel', '5255732655273570754'))
    if mailing_data['type'] == 'photo':
        bot.send_photo(message.chat.id, mailing_data['photo'], caption=f'📢 <b>Предпросмотр рассылки:</b>\n\n{escape_html(mailing_data["caption"] or "")}', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, f'📢 <b>Предпросмотр рассылки:</b>\n\n{escape_html(mailing_data["text"])}', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ('mailing_confirm', 'mailing_cancel'))
def mailing_action(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, '❌ Нет прав')
        return
    if call.data == 'mailing_cancel':
        bot.edit_message_text('❌ Рассылка отменена.', call.message.chat.id, call.message.message_id)
        return
    mailing_data = getattr(bot, 'mailing_data', None)
    if not mailing_data:
        bot.answer_callback_query(call.id, '❌ Нет данных для рассылки')
        return
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = c.fetchall(); conn.close()
    sent = 0; errors = 0
    for row in users:
        try:
            if mailing_data['type'] == 'photo':
                bot.send_photo(row['user_id'], mailing_data['photo'], caption=mailing_data['caption'] or None)
            else:
                bot.send_message(row['user_id'], mailing_data['text'])
            sent += 1; time.sleep(0.05)
        except Exception:
            errors += 1
    bot.send_message(call.message.chat.id, f'📢 <b>Рассылка завершена!</b>\n\n✅ Успешно: {sent}\n❌ Ошибок: {errors}')
    bot.mailing_data = None

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    try:
        handle_callback(call)
    except Exception:
        traceback.print_exc()
        try:
            bot.answer_callback_query(call.id, '❌ Произошла ошибка')
        except Exception:
            pass
        try:
            show_main_menu_for_user(call.from_user)
        except Exception:
            pass

def handle_callback(call):
    user_id = call.from_user.id
    set_state(user_id, menu_chat_id=call.message.chat.id, menu_message_id=call.message.message_id, menu_message_type=('photo' if getattr(call.message, 'content_type', '') == 'photo' else 'text'))
    data = call.data
    if data == 'back_main':
        clear_state(user_id, keep_menu=True)
        show_main_menu_for_user(call.from_user); return
    if data == 'menu_uc':
        state = get_state(user_id); cart = state.get('uc_cart', {})
        edit_menu(user_id, build_uc_cart_text(cart), build_uc_cart_markup(cart))
        set_state(user_id, uc_cart=cart, awaiting=None, active_uc=None); return
    if data.startswith('ucsel_'):
        uc_amount = int(data.split('_')[1]); state = get_state(user_id); cart = dict(state.get('uc_cart', {}))
        cart[uc_amount] = int(cart.get(uc_amount, 0)) + 1
        set_state(user_id, uc_cart=cart, awaiting=None, active_uc=None)
        edit_menu(user_id, build_uc_cart_text(cart), build_uc_cart_markup(cart)); return
    if data.startswith('ucadd_'):
        uc_amount = int(data.split('_')[1]); state = get_state(user_id); cart = dict(state.get('uc_cart', {}))
        cart[uc_amount] = int(cart.get(uc_amount, 0)) + 1
        set_state(user_id, uc_cart=cart, awaiting=None, active_uc=None)
        edit_menu(user_id, build_uc_cart_text(cart), build_uc_cart_markup(cart)); return
    if data.startswith('ucrem_'):
        uc_amount = int(data.split('_')[1]); state = get_state(user_id); cart = dict(state.get('uc_cart', {}))
        current_count = int(cart.get(uc_amount, 0))
        if current_count <= 1: cart.pop(uc_amount, None)
        else: cart[uc_amount] = current_count - 1
        set_state(user_id, uc_cart=cart, awaiting=None, active_uc=None)
        edit_menu(user_id, build_uc_cart_text(cart), build_uc_cart_markup(cart)); return
    if data == 'uc_clear':
        set_state(user_id, uc_cart={}, awaiting=None, active_uc=None)
        edit_menu(user_id, build_uc_cart_text({}), build_uc_cart_markup({})); return
    if data == 'uc_checkout':
        state = get_state(user_id)
        cart, total_uc, total_price, total_packs = calc_uc_cart(state.get('uc_cart', {}))
        if not cart:
            bot.answer_callback_query(call.id, 'Корзина пуста')
            edit_menu(user_id, build_uc_cart_text({}), build_uc_cart_markup({})); return
        final_price = total_price; promo_code = None; discount = 0
        conn = get_conn(); c = conn.cursor()
        c.execute('SELECT promo_code, discount FROM user_promos WHERE user_id = ? LIMIT 1', (user_id,))
        promo = c.fetchone(); conn.close()
        if promo:
            promo_code = promo['promo_code']; discount = promo['discount']; final_price = int(total_price * (100 - discount) / 100)
        quantity_text = format_uc_cart_summary(cart)
        text = ('🪪 <b>Введите ваш PUBG ID:</b>\n\n'
                f'📦 Паков выбрано: {total_packs}\n'
                f'🎮 Всего UC: {total_uc}\n'
                f'🛒 Выбрано: {escape_html(quantity_text)}\n'
                f'💰 Сумма: {fmt_price(final_price)} ₽')
        if discount: text += f'\n🎟 Скидка {discount}% по промокоду'
        text += '\n\nID должен начинаться с цифры 5.'
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(build_inline_button('Назад', 'menu_uc', '5255703720078879038'))
        markup.add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))
        edit_menu(user_id, text, markup)
        set_state(user_id, awaiting='uc_player_id', draft={'cart': cart, 'uc_amount': total_uc, 'total_packs': total_packs, 'quantity_text': quantity_text, 'price': final_price, 'original_price': total_price, 'discount': discount, 'promo_code': promo_code})
        return
    if data == 'menu_popularity':
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('✨✨ ПОПУЛЯРНОСТЬ ✨✨', callback_data='pop_menu_pop_regular'))
        markup.add(types.InlineKeyboardButton('🏠🏠 ПОПУЛЯРНОСТЬ ДЛЯ ДОМА 🏠🏠', callback_data='pop_menu_pop_home'))
        markup.add(types.InlineKeyboardButton('⏱⏱ ПОПУЛЯРНОСТЬ НА ПОСЛЕДНЕЙ МИНУТЕ ⏱⏱', callback_data='pop_menu_pop_last'))
        markup.add(build_inline_button('Назад', 'back_main', '5255703720078879038'))
        edit_menu(user_id, '✨ <b>Выберите тип популярности</b>', markup); return
    if data.startswith('pop_menu_'):
        key = data.replace('pop_menu_', '')
        config = POPULARITY_ITEMS[key]
        markup = types.InlineKeyboardMarkup(row_width=1)
        for idx, (label, price) in enumerate(config['prices']):
            markup.add(types.InlineKeyboardButton(f'{label} — {fmt_price(price)} ₽', callback_data=f'popsel_{key}_{idx}'))
        markup.add(build_inline_button('Назад', 'menu_popularity', '5255703720078879038'))
        edit_menu(user_id, config['description'], markup); return
    if data.startswith('popsel_'):
        payload = data[len('popsel_'):]; key, idx = payload.rsplit('_', 1)
        config = POPULARITY_ITEMS[key]; qty, price = config['prices'][int(idx)]
        text = f'Вы выбрали: <b>{escape_html(qty)}</b> 🔥\n🪪<b>Введите ваш PUBG ID:</b>'
        markup = types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))
        edit_menu(user_id, text, markup)
        set_state(user_id, awaiting='pop_player_id', draft={'category': key, 'product_name': config['product_label'], 'quantity_text': qty, 'price': price}); return
    if data == 'menu_subs':
        markup = types.InlineKeyboardMarkup(row_width=1)
        for idx, (label, price) in enumerate(SUBSCRIPTION_ITEMS):
            markup.add(types.InlineKeyboardButton(f'{label} — {fmt_price(price)} ₽', callback_data=f'subsel_{idx}'))
        markup.add(build_inline_button('Назад', 'back_main', '5255703720078879038'))
        edit_menu(user_id, SUBSCRIPTION_INFO_TEXT, markup); return
    if data.startswith('subsel_'):
        idx = int(data.split('_')[1]); label, price = SUBSCRIPTION_ITEMS[idx]
        text = f'Вы выбрали: <b>{escape_html(label)}</b>\n🪪<b>Введите ваш PUBG ID:</b>'
        markup = types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))
        edit_menu(user_id, text, markup)
        set_state(user_id, awaiting='sub_player_id', draft={'product_name': label, 'price': price}); return
    if data == 'menu_info':
        conn = get_conn(); c = conn.cursor()
        c.execute('SELECT username, first_name, total_uc, total_orders FROM users WHERE user_id = ?', (user_id,)); row = c.fetchone()
        c.execute("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'pending'", (user_id,)); pending_orders = c.fetchone()[0]
        conn.close()
        username = 'Без username'
        if row and row['username'] and row['username'] != 'Нет username':
            username = '@' + row['username'].lstrip('@')
        total_uc = row['total_uc'] if row else 0; total_orders = row['total_orders'] if row else 0
        first_name = row['first_name'] if row else (call.from_user.first_name or 'Игрок')
        text = ('<tg-emoji emoji-id="5447410659077661506">ℹ️</tg-emoji> <b>ПРОФИЛЬ ПОКУПАТЕЛЯ</b>\n\n'
                f'👤 Имя: <b>{escape_html(first_name)}</b>\n'
                f'🔗 Username: <code>{escape_html(username)}</code>\n'
                f'🆔 Telegram ID: <code>{user_id}</code>\n\n'
                f'🎮 Всего куплено UC: <b>{total_uc}</b>\n'
                f'📦 Выполнено заказов: <b>{total_orders}</b>\n'
                f'⏳ Заказов в ожидании: <b>{pending_orders}</b>\n\n'
                'Здесь отображаются ваши покупки и заказы, которые ещё ждут подтверждения администратора.')
        edit_menu(user_id, text, back_to_menu_markup()); return
    if data == 'menu_tgstars':
        text = ('<tg-emoji emoji-id="5897920748101571572">⭐️</tg-emoji> <b>Telegram Stars</b>\n\n'
                'Минимальный заказ: 50\n\n'
                'Звёзды будут отправлены на указанный Telegram username анонимно.\n\n'
                '<tg-emoji emoji-id="5458685931777199791">✏️</tg-emoji> <b>Введите Telegram username получателя</b> (с @ или без):')
        markup = types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))
        edit_menu(user_id, text, markup)
        set_state(user_id, awaiting='tgstars_username', draft={}); return
    if data == 'menu_reviews':
        markup = types.InlineKeyboardMarkup()
        markup.add(build_url_button('Перейти к отзывам', f'https://t.me/{REVIEWS_CHANNEL}', '5463289097336405244'))
        markup.add(build_inline_button('Назад', 'back_main', '5255703720078879038'))
        edit_menu(user_id, '<tg-emoji emoji-id="5463289097336405244">📝</tg-emoji> <b>Отзывы</b>\n\n<tg-emoji emoji-id="5463289097336405244">📝</tg-emoji> Нажмите кнопку ниже, чтобы открыть канал с отзывами.', markup); return
    if data == 'menu_support':
        markup = types.InlineKeyboardMarkup()
        markup.add(build_url_button('Написать в поддержку', f'https://t.me/{SUPPORT_USERNAME}', '5213179235996294999'))
        markup.add(build_inline_button('Назад', 'back_main', '5255703720078879038'))
        edit_menu(user_id, '<tg-emoji emoji-id="5213179235996294999">💬</tg-emoji> <b>Поддержка</b>\n\n<tg-emoji emoji-id="5213179235996294999">💬</tg-emoji> Работаем 24/7. Нажмите кнопку ниже.', markup); return
    if data == 'menu_promo':
        markup = types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))
        edit_menu(user_id, '🎟 <b>Введите промокод:</b>', markup)
        set_state(user_id, awaiting='promo_input', draft={}); return
    if data.startswith('paid_'):
        order_number = int(data.split('_')[1])
        conn = get_conn(); c = conn.cursor()
        c.execute('SELECT status FROM orders WHERE order_number = ?', (order_number,)); row = c.fetchone()
        conn.close()
        if not row:
            bot.answer_callback_query(call.id, '❌ Заказ не найден'); show_main_menu_for_user(call.from_user); return
        if row['status'] != 'pending':
            bot.answer_callback_query(call.id, '⚠️ Этот заказ уже обработан'); return
        text = (f'✅ <b>ЗАЯВКА ПРИНЯТА!</b>\n\n'
                f'📋 <b>ЗАКАЗ №{order_number}</b>\n\n'
                '✅ Ваша оплата проверяется.\n'
                '⏱ Ожидайте, оператор проверит платеж.')
        edit_menu(user_id, text, back_to_menu_markup()); notify_admin_about_paid_order(order_number); return
    if data.startswith('user_cancel_'):
        order_number = int(data.split('_')[2])
        conn = get_conn(); c = conn.cursor()
        c.execute("UPDATE orders SET status = 'cancelled', completed_at = ? WHERE order_number = ? AND status = 'pending'", (str(datetime.now()), order_number))
        conn.commit(); conn.close()
        clear_state(user_id, keep_menu=True); show_main_menu_for_user(call.from_user); return
    if data.startswith('admin_done_'):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, '❌ Нет прав'); return
        order_number = int(data.split('_')[2])
        conn = get_conn(); c = conn.cursor()
        c.execute("""SELECT user_id, product_type, product_name, quantity_text, target_value, uc_amount
                     FROM orders WHERE order_number = ?""", (order_number,))
        raw_order = c.fetchone(); conn.close()
        if not raw_order:
            bot.answer_callback_query(call.id, '❌ Заказ не найден'); return
        if raw_order['product_type'] == 'uc':
            try:
                send_uc_via_hutao(player_id=raw_order['target_value'], quantity_text=raw_order['quantity_text'], order_number=order_number)
            except Exception as e:
                bot.answer_callback_query(call.id, '❌ Ошибка отправки UC')
                try:
                    bot.send_message(ADMIN_ID, f'❌ <b>Ошибка API для заказа №{order_number}</b>\n\n<code>{escape_html(str(e))}</code>')
                except Exception:
                    pass
                try:
                    bot.send_message(raw_order['user_id'], f'⏳ <b>Заказ №{order_number} оплачен и принят.</b>\n\nВозникла временная задержка при отправке UC. Пожалуйста, ожидайте.')
                except Exception:
                    pass
                return
        order = finalize_order_success(order_number)
        if not order:
            bot.answer_callback_query(call.id, '❌ Заказ не найден'); return
        review_markup = types.InlineKeyboardMarkup()
        review_markup.add(types.InlineKeyboardButton('⭐️ Оставить отзыв', url=f'https://t.me/{REVIEWS_CHANNEL}'))
        if order['product_type'] == 'uc':
            user_text = (f'✅ <b>Ваш заказ №{order_number} выполнен!</b>\n\n'
                         f'💰 <b>{order["quantity_text"] or str(order["uc_amount"])+" UC"}</b> доставлены на аккаунт.\n\n'
                         'Спасибо за покупку ❤️')
        else:
            user_text = (f'✅ <b>Ваш заказ №{order_number} выполнен!</b>\n\n'
                         f'💰 <b>{escape_html(order["product_name"])}</b> успешно оформлен.\n'
                         f'📦 Выбрано: {escape_html(order["quantity_text"] or order["product_name"])}\n\n'
                         'Спасибо за покупку ❤️')
        bot.send_message(order['user_id'], user_text, reply_markup=review_markup)
        bot.edit_message_text(f'✅ <b>ЗАКАЗ №{order_number} ВЫПОЛНЕН</b>', call.message.chat.id, call.message.message_id); return
    if data.startswith('admin_deny_'):
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, '❌ Нет прав'); return
        order_number = int(data.split('_')[2]); order_user_id = finalize_order_denied(order_number)
        if order_user_id:
            markup = types.InlineKeyboardMarkup()
            markup.add(build_url_button('Написать в поддержку', f'https://t.me/{SUPPORT_USERNAME}', '5213179235996294999'))
            bot.send_message(order_user_id, f'❌ <b>Ваш заказ №{order_number} был отменён.</b>', reply_markup=markup)
        bot.edit_message_text(f'❌ <b>ЗАКАЗ №{order_number} ОТМЕНЁН</b>', call.message.chat.id, call.message.message_id); return

@bot.message_handler(content_types=['text'])
def text_router(message):
    if message.text and message.text.startswith('/start'): return
    if message.text and message.text.startswith('/admin'): return
    ensure_user(message)
    state = get_state(message.from_user.id); awaiting = state.get('awaiting')
    if not awaiting: return
    try:
        if awaiting == 'uc_player_id': handle_uc_player_id(message, state)
        elif awaiting == 'pop_player_id': handle_popularity_player_id(message, state)
        elif awaiting == 'sub_player_id': handle_subscription_player_id(message, state)
        elif awaiting == 'tgstars_username': handle_tgstars_username(message)
        elif awaiting == 'tgstars_amount': handle_tgstars_amount(message, state)
        elif awaiting == 'promo_input': handle_user_promo(message)
    except Exception:
        traceback.print_exc()
        bot.send_message(message.chat.id, '❌ Произошла ошибка. Возвращаю вас в меню.')
        clear_state(message.from_user.id, keep_menu=True); show_main_menu_for_user(message.from_user)

def handle_uc_player_id(message, state):
    player_id = (message.text or '').strip(); delete_user_message(message)
    if not player_id.isdigit() or not player_id.startswith('5'):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(build_inline_button('Назад', 'menu_uc', '5255703720078879038'))
        markup.add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))
        edit_menu(message.from_user.id, '❌ <b>Неверный PUBG ID.</b>\n\nВведите ID только цифрами. ID должен начинаться с 5.', markup); return
    draft = state['draft']
    order_number = create_order(user=message.from_user, product_type='uc', product_name='UC', quantity_text=draft['quantity_text'], price=draft['price'], target_value=player_id, target_type='player_id', uc_amount=draft['uc_amount'], discount=draft.get('discount', 0), promo_code=draft.get('promo_code'))
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, build_payment_text(order_number, 'UC', draft['quantity_text'], draft['price'], player_id, 'player_id', uc_amount=draft['uc_amount']), payment_markup(order_number))

def handle_popularity_player_id(message, state):
    player_id = (message.text or '').strip(); delete_user_message(message)
    if not player_id.isdigit() or not player_id.startswith('5'):
        edit_menu(message.from_user.id, '❌ <b>Неверный PUBG ID.</b>\n\nВведите ID только цифрами. ID должен начинаться с 5.', types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))); return
    draft = state['draft']
    order_number = create_order(user=message.from_user, product_type='popularity', product_name=draft['product_name'], quantity_text=draft['quantity_text'], price=draft['price'], target_value=player_id, target_type='player_id')
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, build_payment_text(order_number, draft['product_name'], draft['quantity_text'], draft['price'], player_id, 'player_id'), payment_markup(order_number))

def handle_subscription_player_id(message, state):
    player_id = (message.text or '').strip(); delete_user_message(message)
    if not player_id.isdigit() or not player_id.startswith('5'):
        edit_menu(message.from_user.id, '❌ <b>Неверный PUBG ID.</b>\n\nВведите ID только цифрами. ID должен начинаться с 5.', types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))); return
    draft = state['draft']
    order_number = create_order(user=message.from_user, product_type='subscription', product_name='Подписки', quantity_text=draft['product_name'], price=draft['price'], target_value=player_id, target_type='player_id')
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, build_payment_text(order_number, 'Подписки', draft['product_name'], draft['price'], player_id, 'player_id'), payment_markup(order_number))

def normalize_username(text):
    username = (text or '').strip()
    if username.startswith('https://t.me/'): username = username.split('https://t.me/', 1)[1]
    username = username.lstrip('@').strip()
    allowed = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'
    if not username or len(username) < 5 or len(username) > 32: return None
    if any(ch not in allowed for ch in username): return None
    return '@' + username

def handle_tgstars_username(message):
    delete_user_message(message)
    username = normalize_username(message.text)
    if not username:
        edit_menu(message.from_user.id, '❌ <b>Неверный username.</b>\n\n<tg-emoji emoji-id="5458685931777199791">✏️</tg-emoji> Введите Telegram username получателя с @ или без @.', types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))); return
    set_state(message.from_user.id, awaiting='tgstars_amount', draft={'username': username})
    text = f'Получатель: <code>{escape_html(username)}</code>\n\n<tg-emoji emoji-id="5458685931777199791">✏️</tg-emoji> <b>Введите количество звёзд</b> (минимум 50):'
    edit_menu(message.from_user.id, text, types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754')))

def handle_tgstars_amount(message, state):
    delete_user_message(message)
    try:
        amount = int((message.text or '').strip())
        if amount < 50: raise ValueError
    except Exception:
        edit_menu(message.from_user.id, '❌ <b>Введите корректное количество звёзд.</b>\n\nМинимальный заказ: 50.', types.InlineKeyboardMarkup().add(build_inline_button('Отмена', 'back_main', '5255732655273570754'))); return
    username = state['draft']['username']; price = amount * 1.5
    order_number = create_order(user=message.from_user, product_type='telegram_stars', product_name='Telegram Stars', quantity_text=f'{amount} звёзд', price=price, target_value=username, target_type='telegram_username')
    clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, build_payment_text(order_number, 'Telegram Stars', f'{amount} звёзд', price, username, 'telegram_username'), payment_markup(order_number))

def handle_user_promo(message):
    delete_user_message(message)
    code = (message.text or '').strip().upper()
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT discount, max_uses, used_count, expires_at, code FROM promocodes WHERE UPPER(code) = ? AND active = 1', (code,))
    promo = c.fetchone()
    if not promo:
        conn.close(); clear_state(message.from_user.id, keep_menu=True)
        edit_menu(message.from_user.id, '❌ <b>Промокод не найден или неактивен.</b>', back_to_menu_markup()); return
    if promo['expires_at']:
        exp = None
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                exp = datetime.strptime(promo['expires_at'], fmt); break
            except ValueError:
                continue
        if exp and datetime.now() > exp:
            conn.close(); clear_state(message.from_user.id, keep_menu=True)
            edit_menu(message.from_user.id, '❌ <b>Срок действия промокода истёк.</b>', back_to_menu_markup()); return
    if promo['max_uses'] > 0 and promo['used_count'] >= promo['max_uses']:
        conn.close(); clear_state(message.from_user.id, keep_menu=True)
        edit_menu(message.from_user.id, '❌ <b>Лимит использований промокода исчерпан.</b>', back_to_menu_markup()); return
    c.execute('SELECT 1 FROM user_promos WHERE user_id = ? AND promo_code = ?', (message.from_user.id, promo['code']))
    if c.fetchone():
        conn.close(); clear_state(message.from_user.id, keep_menu=True)
        edit_menu(message.from_user.id, '❌ <b>Вы уже активировали этот промокод.</b>', back_to_menu_markup()); return
    c.execute('UPDATE promocodes SET used_count = used_count + 1 WHERE code = ?', (promo['code'],))
    c.execute('INSERT INTO user_promos (user_id, promo_code, discount, activated_at) VALUES (?,?,?,?)', (message.from_user.id, promo['code'], promo['discount'], str(datetime.now())))
    conn.commit(); conn.close(); clear_state(message.from_user.id, keep_menu=True)
    edit_menu(message.from_user.id, f'✅ <b>Промокод активирован!</b>\n🎁 Ваша скидка: {promo["discount"]}%\n\nСкидка применится к следующей покупке UC.', back_to_menu_markup())

if __name__ == '__main__':
    print('🔄 Проверяю базу данных...')
    init_db()
    print('✅ База данных готова.')
    print('✅ БОТ ЗАПУЩЕН!')
    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30, skip_pending=True)
        except Exception as e:
            print(f'❌ Ошибка polling: {e}')
            traceback.print_exc()
            time.sleep(5)
