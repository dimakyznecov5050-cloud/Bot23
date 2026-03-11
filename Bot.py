import asyncio
import logging
from typing import Dict, Any

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage


# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = "8783525882:AAE0QrrgJUy_BBFZLAMZFAoIuZir0hHAj-8"
ADMIN_ID = 8052884471  # <-- сюда впиши Telegram ID админа
SHOP_IMAGE_PATH = "shop.jpg"  # <-- путь к твоей картинке

SBP_DETAILS = "Оплата по СБП: +7XXXXXXXXXX\nПолучатель: APEX UC SHOP"
CARD_DETAILS = "Оплата по карте: 0000 0000 0000 0000\nПолучатель: APEX UC SHOP"

CARD_EXTRA_FEE = 2  # наценка по карте в рублях

PACKAGES = {
    "uc_60": {"title": "60 UC", "uc": 60, "price": 78},
    "uc_325": {"title": "325 UC", "uc": 325, "price": 387},
    "uc_660": {"title": "660 UC", "uc": 660, "price": 782},
    "uc_1800": {"title": "1800 UC", "uc": 1800, "price": 1958},
    "uc_3850": {"title": "3850 UC", "uc": 3850, "price": 3968},
    "uc_8100": {"title": "8100 UC", "uc": 8100, "price": 7779},
}

# Цена за 1 UC для "своего количества"
CUSTOM_UC_RATE = 1.30


# =========================
# ЛОГИ
# =========================

logging.basicConfig(level=logging.INFO)


# =========================
# FSM
# =========================

class OrderState(StatesGroup):
    choosing_custom_uc = State()
    waiting_pubg_id = State()
    waiting_payment_proof = State()


# =========================
# ХРАНЕНИЕ ЗАЯВОК
# =========================

# order_id -> dict
orders: Dict[int, Dict[str, Any]] = {}
order_counter = 1000


# =========================
# КЛАВИАТУРЫ
# =========================

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Купить UC", callback_data="buy_uc")],
            [InlineKeyboardButton(text="👑 Подписки", callback_data="subs")],
            [InlineKeyboardButton(text="ℹ️ Информация", callback_data="info")],
            [InlineKeyboardButton(text="📢 Мой ТГК", callback_data="tgk")],
            [InlineKeyboardButton(text="⚡ Мой профиль", callback_data="profile")],
        ]
    )


def shop_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ 60 UC — 78₽", callback_data="add_uc_60")],
            [InlineKeyboardButton(text="➕ 325 UC — 387₽", callback_data="add_uc_325")],
            [InlineKeyboardButton(text="➕ 660 UC — 782₽", callback_data="add_uc_660")],
            [InlineKeyboardButton(text="➕ 1800 UC — 1958₽", callback_data="add_uc_1800")],
            [InlineKeyboardButton(text="➕ 3850 UC — 3968₽", callback_data="add_uc_3850")],
            [InlineKeyboardButton(text="➕ 8100 UC — 7779₽", callback_data="add_uc_8100")],
            [InlineKeyboardButton(text="✍️ Купить своё количество", callback_data="custom_uc")],
            [InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout")],
            [InlineKeyboardButton(text="🧹 Очистить корзину", callback_data="clear_cart")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="home")],
        ]
    )


def confirm_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue_order")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")],
        ]
    )


def get_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆔 Купить по ID", callback_data="method_id")],
            [InlineKeyboardButton(text="🔐 Купить кодом", callback_data="method_code")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")],
        ]
    )


def payment_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📱 СБП", callback_data="pay_sbp")],
            [InlineKeyboardButton(text="💳 Карта", callback_data="pay_card")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_order")],
        ]
    )


def user_paid_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data="i_paid")],
            [InlineKeyboardButton(text="❌ Отменить заказ", callback_data="cancel_order")],
        ]
    )


def admin_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm_{order_id}"),
                InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_reject_{order_id}"),
            ]
        ]
    )


# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================

async def ensure_cart(state: FSMContext):
    data = await state.get_data()
    if "cart" not in data:
        await state.update_data(cart=[])


async def get_cart_text(state: FSMContext) -> str:
    data = await state.get_data()
    cart = data.get("cart", [])

    total_uc = sum(item["uc"] for item in cart)
    total_price = sum(item["price"] for item in cart)

    if not cart:
        return (
            "🧺 Ваша корзина пуста.\n\n"
            "Выберите пакеты UC:"
        )

    lines = ["🧺 Ваша корзина:\n"]
    for item in cart:
        lines.append(f"— {item['title']} × {item['qty']} = {item['price']}₽")

    lines.append(f"\n• Всего UC: {total_uc}")
    lines.append(f"• Общая сумма: {total_price} ₽")
    lines.append("\nДобавьте ещё или оформите заказ.")

    return "\n".join(lines)


async def add_to_cart(state: FSMContext, title: str, uc: int, price: int, qty: int = 1):
    await ensure_cart(state)
    data = await state.get_data()
    cart = data.get("cart", [])
    cart.append({
        "title": title,
        "uc": uc,
        "price": price,
        "qty": qty,
    })
    await state.update_data(cart=cart)


async def clear_cart(state: FSMContext):
    await state.update_data(cart=[], pubg_id=None, receive_method=None, payment_method=None)


async def build_checkout_text(state: FSMContext) -> str:
    data = await state.get_data()
    cart = data.get("cart", [])

    if not cart:
        return "Корзина пуста."

    total_sbp = sum(item["price"] for item in cart)
    total_card = total_sbp + CARD_EXTRA_FEE

    lines = ["✅ Подтверждение заказа:\n", "🛒 Состав заказа:"]
    for item in cart:
        lines.append(f"— {item['title']} × {item['qty']}")

    lines.append("\n💳 Сумма:")
    lines.append(f"📱 По СБП: {total_sbp} ₽")
    lines.append(f"💳 По карте: {total_card} ₽")
    lines.append("\nВсё верно?")

    return "\n".join(lines)


def calc_custom_price(uc_amount: int) -> int:
    return round(uc_amount * CUSTOM_UC_RATE)


def make_order_text(order_id: int, order: Dict[str, Any]) -> str:
    lines = [
        f"🆕 Новая заявка #{order_id}",
        f"👤 Пользователь: @{order['username']}" if order["username"] else f"👤 User ID: {order['user_id']}",
        f"🧾 Способ получения: {order['receive_method']}",
        f"🎮 PUBG ID: {order.get('pubg_id', '—')}",
        f"💳 Способ оплаты: {order['payment_method']}",
        f"💰 Сумма: {order['amount']} ₽",
        "",
        "🛒 Состав заказа:",
    ]
    for item in order["cart"]:
        lines.append(f"— {item['title']} × {item['qty']}")
    return "\n".join(lines)


# =========================
# БОТ
# =========================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())


# =========================
# СТАРТ
# =========================

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(cart=[])

    photo = FSInputFile(SHOP_IMAGE_PATH)
    caption = (
        "🎮 <b>APEX UC SHOP</b>\n\n"
        "Пополнение UC и игровых услуг 24/7\n"
        "Самые дешёвые и выгодные UC на рынке.\n\n"
        "⚡ Простота\n"
        "💸 Низкие цены\n"
        "🚀 Быстрая доставка\n\n"
        "Выберите действие:"
    )

    await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=main_menu_kb()
    )


# =========================
# МЕНЮ
# =========================

@dp.callback_query(F.data == "home")
async def home_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(cart=[])

    photo = FSInputFile(SHOP_IMAGE_PATH)
    caption = (
        "🎮 <b>APEX UC SHOP</b>\n\n"
        "Пополнение UC и игровых услуг 24/7\n"
        "Самые дешёвые и выгодные UC на рынке.\n\n"
        "⚡ Простота\n"
        "💸 Низкие цены\n"
        "🚀 Быстрая доставка\n\n"
        "Выберите действие:"
    )

    await callback.message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "buy_uc")
async def buy_uc_callback(callback: CallbackQuery, state: FSMContext):
    await ensure_cart(state)
    text = (
        "🧾 Выберите пакеты UC:\n\n"
        f"{await get_cart_text(state)}"
    )
    await callback.message.answer(text, reply_markup=shop_kb())
    await callback.answer()


@dp.callback_query(F.data == "subs")
async def subs_callback(callback: CallbackQuery):
    await callback.message.answer("👑 Раздел подписок пока в разработке.")
    await callback.answer()


@dp.callback_query(F.data == "info")
async def info_callback(callback: CallbackQuery):
    await callback.message.answer(
        "ℹ️ <b>Информация</b>\n\n"
        "APEX UC SHOP — магазин пополнения UC.\n"
        "Оплата проверяется вручную администратором.\n"
        "После оплаты нажмите кнопку <b>«Я оплатил»</b>."
    )
    await callback.answer()


@dp.callback_query(F.data == "tgk")
async def tgk_callback(callback: CallbackQuery):
    await callback.message.answer("📢 Ссылка на ТГК: вставь сюда свою ссылку.")
    await callback.answer()


@dp.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery):
    user = callback.from_user
    await callback.message.answer(
        f"⚡ <b>Мой профиль</b>\n\n"
        f"ID: <code>{user.id}</code>\n"
        f"Username: @{user.username if user.username else 'нет'}"
    )
    await callback.answer()


# =========================
# КОРЗИНА
# =========================

@dp.callback_query(F.data.startswith("add_uc_"))
async def add_package_callback(callback: CallbackQuery, state: FSMContext):
    package_key = callback.data.replace("add_", "")
    package = PACKAGES.get(package_key)

    if not package:
        await callback.answer("Пакет не найден.", show_alert=True)
        return

    await add_to_cart(
        state=state,
        title=package["title"],
        uc=package["uc"],
        price=package["price"],
        qty=1
    )

    await callback.message.answer(
        f"✅ Добавлено в корзину: {package['title']} — {package['price']}₽\n\n{await get_cart_text(state)}",
        reply_markup=shop_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "custom_uc")
async def custom_uc_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.choosing_custom_uc)
    await callback.message.answer("✍️ Введите нужное количество UC числом, например: 150")
    await callback.answer()


@dp.message(OrderState.choosing_custom_uc)
async def custom_uc_input(message: Message, state: FSMContext):
    text = (message.text or "").strip()

    if not text.isdigit():
        await message.answer("Введите только число, например: 150")
        return

    uc_amount = int(text)
    if uc_amount <= 0:
        await message.answer("Количество UC должно быть больше нуля.")
        return

    price = calc_custom_price(uc_amount)
    await add_to_cart(
        state=state,
        title=f"{uc_amount} UC",
        uc=uc_amount,
        price=price,
        qty=1
    )
    await state.clear()
    await state.update_data(cart=(await state.get_data()).get("cart", []))

    await message.answer(
        f"✅ Добавлено: {uc_amount} UC — {price}₽\n\n{await get_cart_text(state)}",
        reply_markup=shop_kb()
    )


@dp.callback_query(F.data == "clear_cart")
async def clear_cart_callback(callback: CallbackQuery, state: FSMContext):
    await clear_cart(state)
    await callback.message.answer("🧹 Корзина очищена.", reply_markup=shop_kb())
    await callback.answer()


@dp.callback_query(F.data == "checkout")
async def checkout_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])

    if not cart:
        await callback.answer("Корзина пуста.", show_alert=True)
        return

    await callback.message.answer(await build_checkout_text(state), reply_markup=confirm_order_kb())
    await callback.answer()


# =========================
# ОФОРМЛЕНИЕ
# =========================

@dp.callback_query(F.data == "continue_order")
async def continue_order_callback(callback: CallbackQuery):
    await callback.message.answer("Выберите способ получения UC:", reply_markup=get_method_kb())
    await callback.answer()


@dp.callback_query(F.data == "cancel_order")
async def cancel_order_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.update_data(cart=[])
    await callback.message.answer("❌ Заказ отменён.", reply_markup=main_menu_kb())
    await callback.answer()


@dp.callback_query(F.data == "method_id")
async def method_id_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(receive_method="Купить по ID")
    await state.set_state(OrderState.waiting_pubg_id)
    await callback.message.answer("Введите ваш PUBG ID:")
    await callback.answer()


@dp.callback_query(F.data == "method_code")
async def method_code_callback(callback: CallbackQuery, state: FSMContext):
    await state.update_data(receive_method="Купить кодом")
    await callback.message.answer(
        "💰 Выберите способ оплаты:\n\n"
        "📱 СБП — подходит для всех банков\n"
        "Даже если у вас веб-версия банка, оплачивайте по QR-коду\n\n"
        "💳 Карта — если нет доступа к онлайн-банку",
        reply_markup=payment_method_kb()
    )
    await callback.answer()


@dp.message(OrderState.waiting_pubg_id)
async def pubg_id_input(message: Message, state: FSMContext):
    pubg_id = (message.text or "").strip()
    if len(pubg_id) < 4:
        await message.answer("Введите корректный PUBG ID.")
        return

    await state.update_data(pubg_id=pubg_id)
    await message.answer(
        "💰 Выберите способ оплаты:\n\n"
        "📱 СБП — подходит для всех банков\n"
        "Даже если у вас веб-версия банка, оплачивайте по QR-коду\n\n"
        "💳 Карта — если нет доступа к онлайн-банку",
        reply_markup=payment_method_kb()
    )


@dp.callback_query(F.data.in_({"pay_sbp", "pay_card"}))
async def pay_method_callback(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await callback.answer("Корзина пуста.", show_alert=True)
        return

    total_sbp = sum(item["price"] for item in cart)
    total_card = total_sbp + CARD_EXTRA_FEE

    if callback.data == "pay_sbp":
        payment_method = "СБП"
        amount = total_sbp
        details = SBP_DETAILS
    else:
        payment_method = "Карта"
        amount = total_card
        details = CARD_DETAILS

    await state.update_data(payment_method=payment_method, amount=amount)
    await state.set_state(OrderState.waiting_payment_proof)

    await callback.message.answer(
        f"💳 <b>Способ оплаты:</b> {payment_method}\n"
        f"💰 <b>К оплате:</b> {amount} ₽\n\n"
        f"{details}\n\n"
        f"После перевода нажмите кнопку ниже:",
        reply_markup=user_paid_kb()
    )
    await callback.answer()


# =========================
# Я ОПЛАТИЛ -> ЗАЯВКА АДМИНУ
# =========================

@dp.callback_query(F.data == "i_paid")
async def i_paid_callback(callback: CallbackQuery, state: FSMContext):
    global order_counter

    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await callback.answer("Корзина пуста.", show_alert=True)
        return

    receive_method = data.get("receive_method", "Не выбран")
    pubg_id = data.get("pubg_id", "—")
    payment_method = data.get("payment_method", "Не выбран")
    amount = data.get("amount", 0)

    order_counter += 1
    order_id = order_counter

    orders[order_id] = {
        "user_id": callback.from_user.id,
        "username": callback.from_user.username,
        "cart": cart,
        "receive_method": receive_method,
        "pubg_id": pubg_id,
        "payment_method": payment_method,
        "amount": amount,
        "status": "pending",
    }

    admin_text = make_order_text(order_id, orders[order_id])

    await bot.send_message(
        ADMIN_ID,
        admin_text,
        reply_markup=admin_order_kb(order_id)
    )

    await callback.message.answer(
        "✅ Заявка на проверку оплаты отправлена администратору.\n\n"
        "Ожидайте подтверждения."
    )
    await callback.answer()


# =========================
# АДМИН: ПОДТВЕРДИТЬ / ОТМЕНИТЬ
# =========================

@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    order_id = int(callback.data.split("_")[-1])
    order = orders.get(order_id)

    if not order:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if order["status"] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    order["status"] = "confirmed"

    await bot.send_message(
        order["user_id"],
        f"✅ Оплата по заявке #{order_id} подтверждена!\n"
        f"Спасибо за покупку в APEX UC SHOP."
    )

    await callback.message.edit_text(
        make_order_text(order_id, order) + "\n\n✅ Статус: ПОДТВЕРЖДЕНО"
    )
    await callback.answer("Оплата подтверждена.")


@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа.", show_alert=True)
        return

    order_id = int(callback.data.split("_")[-1])
    order = orders.get(order_id)

    if not order:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return

    if order["status"] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    order["status"] = "rejected"

    await bot.send_message(
        order["user_id"],
        f"❌ Оплата по заявке #{order_id} отклонена.\n"
        f"Если это ошибка — свяжитесь с администратором."
    )

    await callback.message.edit_text(
        make_order_text(order_id, order) + "\n\n❌ Статус: ОТКЛОНЕНО"
    )
    await callback.answer("Заявка отклонена.")


# =========================
# ЗАПУСК
# =========================

async def main():
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise ValueError("Вставь токен бота в переменную BOT_TOKEN.")
    if ADMIN_ID == 123456789:
        raise ValueError("Вставь Telegram ID админа в переменную ADMIN_ID.")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
