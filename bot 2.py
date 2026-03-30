import asyncio
import html
import logging
import sqlite3
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ButtonStyle, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import CommandStart
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

# ==============================
# Настройки бота
# ==============================
BOT_TOKEN = "8755199526:AAHkuy87TJzPoJnSHIybsJjcTC3t80FUsHw"
ADMIN_ID = 8052884471
SUPPORT_USERNAME = "@Kurator111"
SUPPORT_URL = "https://t.me/Kurator111"
ADMIN_MENTION_URL = f"tg://user?id={ADMIN_ID}"

PAYMENT_DETAILS = {
    "Сбербанк": "2202 2084 1737 7224",
    "ВТБ": "2200 2479 5387 8262",
}

PLANS = {
    "7d": {"title": "7 дней", "price": 120},
    "14d": {"title": "14 дней", "price": 150},
    "1m": {"title": "1 месяц", "price": 200},
    "2m": {"title": "2 месяца", "price": 250},
    "3m": {"title": "3 месяца", "price": 350},
}

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "vpn_shop.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("vpn_shop_bot")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                menu_message_id INTEGER
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                plan_code TEXT NOT NULL,
                plan_title TEXT NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                admin_message_id INTEGER,
                admin_chat_id INTEGER
            )
            """
        )
        self.conn.commit()

    def get_menu_message_id(self, user_id: int) -> Optional[int]:
        row = self.conn.execute(
            "SELECT menu_message_id FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if row:
            return row["menu_message_id"]
        return None

    def set_menu_message_id(self, user_id: int, message_id: int) -> None:
        self.conn.execute(
            """
            INSERT INTO users (user_id, menu_message_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET menu_message_id = excluded.menu_message_id
            """,
            (user_id, message_id),
        )
        self.conn.commit()

    def create_order(self, user: Message | CallbackQuery, plan_code: str) -> int:
        from_user = user.from_user
        plan = PLANS[plan_code]
        created_at = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        full_name = (from_user.full_name or str(from_user.id)).strip()
        username = f"@{from_user.username}" if from_user.username else "—"

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO orders (
                user_id, username, full_name, plan_code, plan_title, amount, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                from_user.id,
                username,
                full_name,
                plan_code,
                plan["title"],
                plan["price"],
                created_at,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_order(self, order_id: int) -> Optional[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM orders WHERE id = ?",
            (order_id,),
        ).fetchone()

    def set_admin_message(self, order_id: int, chat_id: int, message_id: int) -> None:
        self.conn.execute(
            "UPDATE orders SET admin_chat_id = ?, admin_message_id = ? WHERE id = ?",
            (chat_id, message_id, order_id),
        )
        self.conn.commit()

    def set_order_status(self, order_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id),
        )
        self.conn.commit()


db = Database(DB_PATH)


# ==============================
# Тексты
# ==============================
def main_menu_text() -> str:
    return (
        "<b>🌐 VPN SHOP</b>\n\n"
        "Добро пожаловать в магазин VPN.\n"
        "Выберите нужный раздел ниже.\n\n"
        "<b>Тарифы:</b>\n"
        "• 7 дней — 120 ₽\n"
        "• 14 дней — 150 ₽\n"
        "• 1 месяц — 200 ₽\n"
        "• 2 месяца — 250 ₽\n"
        "• 3 месяца — 350 ₽"
    )


def buy_menu_text() -> str:
    return (
        "<b>🛒 Выбор тарифа VPN</b>\n\n"
        "Выберите подходящий срок подписки.\n"
        "После выбора бот покажет реквизиты для оплаты и сумму перевода."
    )


def services_text() -> str:
    return (
        "<b>🚀 Другие сервисы</b>\n\n"
        "Нажмите на нужный магазин — Telegram откроет канал по ссылке."
    )


def payment_text(plan_code: str) -> str:
    plan = PLANS[plan_code]
    return (
        f"<b>💳 Оплата VPN</b>\n\n"
        f"<b>Товар:</b> {plan['title']}\n"
        f"<b>Сумма к переводу:</b> {plan['price']} ₽\n\n"
        f"<b>Реквизиты:</b>\n"
        f"• Сбербанк: <code>{PAYMENT_DETAILS['Сбербанк']}</code>\n"
        f"• ВТБ: <code>{PAYMENT_DETAILS['ВТБ']}</code>\n\n"
        f"После оплаты нажмите <b>«Я оплатил»</b>.\n"
        f"Заявка уйдёт администратору на проверку."
    )


def waiting_text(order_id: int, plan_code: str) -> str:
    plan = PLANS[plan_code]
    return (
        f"<b>⏳ Заявка отправлена</b>\n\n"
        f"<b>Номер заявки:</b> #{order_id}\n"
        f"<b>Тариф:</b> {plan['title']}\n"
        f"<b>Сумма:</b> {plan['price']} ₽\n\n"
        f"Мы передали информацию администратору.\n"
        f"После проверки вам напишут и отправят VPN."
    )


def approved_text(order: sqlite3.Row) -> str:
    return (
        "<b>✅ Оплата подтверждена</b>\n\n"
        f"<b>Тариф:</b> {order['plan_title']}\n"
        f"<b>Сумма:</b> {order['amount']} ₽\n\n"
        f"Администратор скоро свяжется с вами и отправит VPN.\n"
        f"<b>Админ:</b> <a href=\"{ADMIN_MENTION_URL}\">написать</a>\n"
        f"<b>Техподдержка:</b> {SUPPORT_USERNAME}"
    )


def rejected_text(order: sqlite3.Row) -> str:
    return (
        "<b>❌ Заявка отменена</b>\n\n"
        f"По вашей оплате нужна ручная проверка.\n"
        f"Пожалуйста, обратитесь в поддержку: {SUPPORT_USERNAME}\n\n"
        f"Администратор проверит ситуацию и поможет с доступом."
    )


def admin_order_text(order: sqlite3.Row) -> str:
    safe_name = html.escape(order["full_name"])
    username = html.escape(order["username"])
    return (
        "<b>🧾 Новая заявка на VPN</b>\n\n"
        f"<b>Заказ:</b> #{order['id']}\n"
        f"<b>Клиент:</b> <a href=\"tg://user?id={order['user_id']}\">{safe_name}</a>\n"
        f"<b>ID:</b> <code>{order['user_id']}</code>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>Товар:</b> {html.escape(order['plan_title'])}\n"
        f"<b>Сумма:</b> {order['amount']} ₽\n"
        f"<b>Статус:</b> ⏳ Ожидает проверки\n"
        f"<b>Создан:</b> {order['created_at']}"
    )


def admin_done_text(order: sqlite3.Row, approved: bool) -> str:
    status = "✅ Подтверждено" if approved else "❌ Отменено"
    safe_name = html.escape(order["full_name"])
    username = html.escape(order["username"])
    return (
        "<b>🧾 Заявка обработана</b>\n\n"
        f"<b>Заказ:</b> #{order['id']}\n"
        f"<b>Клиент:</b> <a href=\"tg://user?id={order['user_id']}\">{safe_name}</a>\n"
        f"<b>ID:</b> <code>{order['user_id']}</code>\n"
        f"<b>Username:</b> {username}\n"
        f"<b>Товар:</b> {html.escape(order['plan_title'])}\n"
        f"<b>Сумма:</b> {order['amount']} ₽\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Создан:</b> {order['created_at']}"
    )


# ==============================
# Кнопки
# ==============================
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Купить VPN",
                    callback_data="menu:buy",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚀 Другие сервисы",
                    callback_data="menu:services",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🆘 Техподдержка",
                    url=SUPPORT_URL,
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )


def buy_menu_kb() -> InlineKeyboardMarkup:
    rows = []
    for code, info in PLANS.items():
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{info['title']} — {info['price']} ₽",
                    callback_data=f"plan:{code}",
                    style=ButtonStyle.SUCCESS,
                )
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data="menu:main",
                style=ButtonStyle.DANGER,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def services_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="APEX UC SHOP",
                    url="https://t.me/ApexUC_Shop",
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="APEX METRO SHOP",
                    url="https://t.me/Apex_metro",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu:main",
                    style=ButtonStyle.DANGER,
                )
            ],
        ]
    )


def payment_kb(plan_code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Я оплатил",
                    callback_data=f"pay:{plan_code}",
                    style=ButtonStyle.SUCCESS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="menu:main",
                    style=ButtonStyle.DANGER,
                ),
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="menu:buy",
                    style=ButtonStyle.PRIMARY,
                ),
            ],
        ]
    )


def waiting_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆘 Поддержка",
                    url=SUPPORT_URL,
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="menu:main",
                    style=ButtonStyle.SUCCESS,
                )
            ],
        ]
    )


def admin_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"admin:approve:{order_id}",
                    style=ButtonStyle.SUCCESS,
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"admin:reject:{order_id}",
                    style=ButtonStyle.DANGER,
                ),
            ]
        ]
    )


def processed_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆘 Поддержка",
                    url=SUPPORT_URL,
                    style=ButtonStyle.PRIMARY,
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="menu:main",
                    style=ButtonStyle.SUCCESS,
                )
            ],
        ]
    )


# ==============================
# Вспомогательные функции
# ==============================
async def safe_delete_message(message: Message) -> None:
    with suppress(TelegramBadRequest, TelegramForbiddenError):
        await message.delete()


async def render_screen(
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup,
    *,
    source_message: Optional[Message] = None,
) -> None:
    message_id = db.get_menu_message_id(chat_id)

    if source_message:
        message_id = source_message.message_id

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
            db.set_menu_message_id(chat_id, message_id)
            return
        except TelegramBadRequest as exc:
            error_text = str(exc).lower()
            if "message is not modified" in error_text:
                return
            logger.warning("Не удалось отредактировать сообщение %s: %s", message_id, exc)
        except TelegramForbiddenError as exc:
            logger.warning("Нет доступа к чату %s: %s", chat_id, exc)
            return

    sent = await bot.send_message(
        chat_id,
        text,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )
    db.set_menu_message_id(chat_id, sent.message_id)


async def notify_admin(order_id: int) -> None:
    order = db.get_order(order_id)
    if not order:
        return

    sent = await bot.send_message(
        ADMIN_ID,
        admin_order_text(order),
        reply_markup=admin_order_kb(order_id),
        disable_web_page_preview=True,
    )
    db.set_admin_message(order_id, ADMIN_ID, sent.message_id)


# ==============================
# Пользовательские обработчики
# ==============================
@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if message.chat.type != "private":
        return
    await safe_delete_message(message)
    await render_screen(message.chat.id, main_menu_text(), main_menu_kb())


@dp.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery) -> None:
    await callback.answer()
    await render_screen(
        callback.message.chat.id,
        main_menu_text(),
        main_menu_kb(),
        source_message=callback.message,
    )


@dp.callback_query(F.data == "menu:buy")
async def menu_buy(callback: CallbackQuery) -> None:
    await callback.answer()
    await render_screen(
        callback.message.chat.id,
        buy_menu_text(),
        buy_menu_kb(),
        source_message=callback.message,
    )


@dp.callback_query(F.data == "menu:services")
async def menu_services(callback: CallbackQuery) -> None:
    await callback.answer()
    await render_screen(
        callback.message.chat.id,
        services_text(),
        services_kb(),
        source_message=callback.message,
    )


@dp.callback_query(F.data.startswith("plan:"))
async def select_plan(callback: CallbackQuery) -> None:
    plan_code = callback.data.split(":", maxsplit=1)[1]
    if plan_code not in PLANS:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await callback.answer()
    await render_screen(
        callback.message.chat.id,
        payment_text(plan_code),
        payment_kb(plan_code),
        source_message=callback.message,
    )


@dp.callback_query(F.data.startswith("pay:"))
async def pay_order(callback: CallbackQuery) -> None:
    plan_code = callback.data.split(":", maxsplit=1)[1]
    if plan_code not in PLANS:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    order_id = db.create_order(callback, plan_code)
    await callback.answer("Заявка отправлена админу ✅")

    await render_screen(
        callback.message.chat.id,
        waiting_text(order_id, plan_code),
        waiting_kb(),
        source_message=callback.message,
    )

    try:
        await notify_admin(order_id)
    except TelegramForbiddenError:
        logger.warning("Администратор ещё не открыл диалог с ботом")
        await bot.send_message(
            callback.message.chat.id,
            "<b>⚠️ Внимание</b>\n\n"
            "Заявка создана, но администратор ещё не запустил бота.\n"
            "Попросите администратора написать боту команду /start.",
        )


@dp.message(F.chat.type == "private")
async def cleanup_user_messages(message: Message) -> None:
    await safe_delete_message(message)
    if db.get_menu_message_id(message.chat.id) is None:
        await render_screen(message.chat.id, main_menu_text(), main_menu_kb())


# ==============================
# Админские обработчики
# ==============================
@dp.callback_query(F.data.startswith("admin:"))
async def process_admin_action(callback: CallbackQuery) -> None:
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    _, action, raw_order_id = parts
    if not raw_order_id.isdigit():
        await callback.answer("Неверный ID заявки", show_alert=True)
        return

    order_id = int(raw_order_id)
    order = db.get_order(order_id)

    if not order:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    if order["status"] != "pending":
        await callback.answer("Эта заявка уже обработана", show_alert=True)
        return

    approved = action == "approve"
    new_status = "approved" if approved else "rejected"
    db.set_order_status(order_id, new_status)
    updated_order = db.get_order(order_id)

    await callback.message.edit_text(
        admin_done_text(updated_order, approved=approved),
        reply_markup=None,
        disable_web_page_preview=True,
    )

    user_text = approved_text(updated_order) if approved else rejected_text(updated_order)
    await render_screen(
        updated_order["user_id"],
        user_text,
        processed_kb(),
    )

    await callback.answer("Готово")


async def on_startup() -> None:
    await bot.set_my_commands([BotCommand(command="start", description="Запустить бота")])
    logger.info("Бот запущен")


async def main() -> None:
    dp.startup.register(on_startup)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
