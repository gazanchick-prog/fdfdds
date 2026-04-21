import os
import asyncio
import aiosqlite
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from telethon import TelegramClient
from telethon.errors import UserDeactivatedError, AuthKeyUnregisteredError
from dotenv import load_dotenv

# --- КОНФИГУРАЦИЯ ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH")
TON_WALLET = os.getenv("TON_WALLET", "UQDlFKmdWxZqtT1ueKC58L6Kj77RLY6tGu3wW_aaZHGXt46O")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
DB_NAME = "sifon_market.db"

# Глобальный TelegramClient для сессий (не пересоединяется)
telegram_clients = {}  # {session_path: client}

class ShopStates(StatesGroup):
    # Admin states
    wait_bal_id = State()
    wait_bal_amount = State()
    wait_acc_file = State()
    wait_acc_price = State()
    wait_acc_geo = State()
    wait_acc_stay = State()
    wait_acc_type = State()
    wait_broadcast_text = State()
    # User states
    wait_totp_code = State()

# --- БАЗА ДАННЫХ ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица пользователей с реферальной системой
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            referrer_id INTEGER,
            ref_earnings REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Таблица товаров (аккаунтов)
        await db.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            price REAL,
            session_path TEXT,
            geo TEXT,
            stay TEXT,
            type TEXT,
            is_sold INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Таблица покупок
        await db.execute("""CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            price REAL,
            purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )""")
        
        # Таблица реферальных ссылок
        await db.execute("""CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            referred_user_id INTEGER,
            earned REAL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(referred_user_id) REFERENCES users(user_id)
        )""")
        
        await db.commit()

# --- ФУНКЦИИ БД ---
async def get_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()

async def create_user(user_id, referrer_id=None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, referrer_id) VALUES (?, ?)",
            (user_id, referrer_id)
        )
        await db.commit()

async def get_user_balance(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else 0

async def add_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_products_by_geo(geo):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, type, stay, price FROM products WHERE geo = ? AND is_sold = 0 ORDER BY created_at DESC",
            (geo,)
        )
        return await cursor.fetchall()

async def get_product(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, phone, price, session_path, geo, stay, type FROM products WHERE id = ?",
            (product_id,)
        )
        return await cursor.fetchone()

async def get_user_purchases(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT p.id, pr.phone, pr.id as product_id, p.price FROM purchases p "
            "JOIN products pr ON p.product_id = pr.id WHERE p.user_id = ? ORDER BY p.purchase_date DESC",
            (user_id,)
        )
        return await cursor.fetchall()

# --- КЛАВИАТУРЫ ---
def main_kb_user():
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text="🛒 Купить аккаунты"),
        types.KeyboardButton(text="👤 Профиль")
    )
    builder.row(
        types.KeyboardButton(text="💰 Пополнить баланс"),
        types.KeyboardButton(text="🛍 Мои покупки")
    )
    builder.row(
        types.KeyboardButton(text="🤝 Реферальная ссылка"),
        types.KeyboardButton(text="🆘 Поддержка")
    )
    return builder.as_markup(resize_keyboard=True)

def main_kb_admin():
    builder = ReplyKeyboardBuilder()
    builder.row(
        types.KeyboardButton(text="🛒 Купить аккаунты"),
        types.KeyboardButton(text="👤 Профиль")
    )
    builder.row(
        types.KeyboardButton(text="💰 Пополнить баланс"),
        types.KeyboardButton(text="🛍 Мои покупки")
    )
    builder.row(
        types.KeyboardButton(text="🤝 Реферальная ссылка"),
        types.KeyboardButton(text="🆘 Поддержка")
    )
    builder.row(
        types.KeyboardButton(text="➕ Добавить товар"),
        types.KeyboardButton(text="💎 Выдать баланс")
    )
    builder.row(types.KeyboardButton(text="📢 Рассылка"))
    return builder.as_markup(resize_keyboard=True)

# --- ОСНОВНЫЕ КОМАНДЫ ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем есть ли реферер
    referrer_id = None
    if message.text.startswith("/start "):
        try:
            referrer_id = int(message.text.split()[1])
            if referrer_id == user_id:
                referrer_id = None
        except:
            pass
    
    # Создаем юзера
    await create_user(user_id, referrer_id)
    
    # Если есть реферер, добавляем связь
    if referrer_id:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT OR IGNORE INTO referrals (user_id, referred_user_id) VALUES (?, ?)",
                (referrer_id, user_id)
            )
            await db.commit()
    
    text = (
        "🎉 **Добро пожаловать в Minon Shop!**\n\n"
        "✨ Покупайте качественные Telegram аккаунты\n"
        "💰 Мгновенная выдача после оплаты\n"
        "🔐 Автоматическое получение кодов входа\n"
        "🤝 Реферальная система: 10% от покупок друга\n"
        "🎯 Круглосуточная поддержка\n\n"
        "Выберите действие:"
    )
    
    kb = main_kb_admin() if user_id == ADMIN_ID else main_kb_user()
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "🆘 Поддержка")
async def support(message: types.Message):
    await message.answer(
        "🆘 **По всем вопросам обратитесь:**\n"
        "@zyozp",
        parse_mode="Markdown"
    )

# --- ПРОФИЛЬ И БАЛАНС ---
@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user_id = message.from_user.id
    balance = await get_user_balance(user_id)
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM referrals WHERE user_id = ?",
            (user_id,)
        )
        ref_count_row = await cursor.fetchone()
        ref_count = ref_count_row[0] if ref_count_row else 0
        
        cursor = await db.execute(
            "SELECT ref_earnings FROM users WHERE user_id = ?",
            (user_id,)
        )
        ref_earnings_row = await cursor.fetchone()
        ref_earnings = ref_earnings_row[0] if ref_earnings_row else 0
    
    text = (
        f"👤 **ПРОФИЛЬ**\n\n"
        f"🆔 ID: `{user_id}`\n"
        f"💰 Баланс: **{balance:.4f} TON**\n"
        f"🤝 Рефералов: **{ref_count}**\n"
        f"💵 Заработано на рефералах: **{ref_earnings:.4f} TON**"
    )
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "💰 Пополнить баланс")
async def topup(message: types.Message):
    user_id = message.from_user.id
    text = (
        f"💎 **ПОПОЛНЕНИЕ БАЛАНСА (TON)**\n\n"
        f"📍 **Адрес кошелька:**\n`{TON_WALLET}`\n\n"
        f"💬 **Комментарий (ВАЖНО!):**\n`{user_id}`\n\n"
        f"⚠️ **ВНИМАНИЕ!** Обязательно укажите комментарий с вашим ID!\n"
        f"Без комментария баланс не будет зачислен."
    )
    
    await message.answer(text, parse_mode="Markdown")

# --- РЕФЕРАЛЬНАЯ СИСТЕМА ---
@dp.message(F.text == "🤝 Реферальная ссылка")
async def referral_link(message: types.Message):
    user_id = message.from_user.id
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT COUNT(*), COALESCE(SUM(price), 0) FROM purchases p "
            "JOIN referrals r ON p.user_id = r.referred_user_id WHERE r.user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        ref_count = row[0] if row else 0
        total_sales = row[1] if row else 0
        ref_earnings = (total_sales * 0.1) if total_sales else 0
    
    ref_link = f"https://t.me/MiYQvJk7_bot?start={user_id}"
    
    text = (
        f"🤝 **РЕФЕРАЛЬНАЯ ПРОГРАММА**\n\n"
        f"💰 Комиссия: **10%** от каждой покупки друга\n"
        f"👥 Ваши рефералы: **{ref_count}**\n"
        f"💵 Заработано: **{ref_earnings:.4f} TON**\n\n"
        f"🔗 **Ваша ссылка:**\n`{ref_link}`\n\n"
        f"Делитесь ссылкой и получайте 10% от покупок своих друзей!"
    )
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(
        text="📋 Скопировать ссылку",
        callback_data=f"copy_ref_{user_id}"
    ))
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- МАГАЗИН ---
@dp.message(F.text == "🛒 Купить аккаунты")
async def shop_cats(message: types.Message):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT DISTINCT geo, COUNT(*) FROM products WHERE is_sold = 0 GROUP BY geo ORDER BY geo"
        )
        cats = await cursor.fetchall()
    
    if not cats:
        return await message.answer(
            "📦 **Товаров нет!**\n\nПроверьте позже.",
            parse_mode="Markdown"
        )
    
    kb = InlineKeyboardBuilder()
    for geo, count in cats:
        kb.row(types.InlineKeyboardButton(
            text=f"📍 {geo} ({count} шт.)",
            callback_data=f"cat_{geo}"
        ))
    
    await message.answer(
        "📁 **Выберите страну:**",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("cat_"))
async def show_items(callback: types.CallbackQuery):
    geo = callback.data.split("_", 1)[1]
    items = await get_products_by_geo(geo)
    
    if not items:
        return await callback.answer("Товаров в этой категории нет", show_alert=True)
    
    kb = InlineKeyboardBuilder()
    for i in items:
        kb.row(types.InlineKeyboardButton(
            text=f"⚙️ {i[1]} | ⏳ {i[2]} | 💵 {i[3]:.4f} TON",
            callback_data=f"buy_{i[0]}"
        ))
    
    await callback.message.edit_text(
        f"📱 **Аккаунты ({geo})**\n\n"
        f"Выберите аккаунт:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    product = await get_product(product_id)
    if not product:
        return await callback.answer("❌ Товар не найден", show_alert=True)
    
    _, phone, price, session_path, geo, stay, prod_type = product
    balance = await get_user_balance(user_id)
    
    if balance < price:
        needed = price - balance
        return await callback.answer(
            f"❌ Недостаточно средств\n\n"
            f"Не хватает: {needed:.4f} TON",
            show_alert=True
        )
    
    # Проверяем сессию перед продажей
    try:
        if session_path not in telegram_clients:
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            is_auth = await client.is_user_authorized()
            
            if not is_auth:
                return await callback.answer(
                    "❌ Ошибка сессии\n\n"
                    "Обратитесь к администратору за заменой",
                    show_alert=True
                )
            
            telegram_clients[session_path] = client
    except Exception as e:
        return await callback.answer(
            "❌ Ошибка подключения к сессии\n\n"
            "Обратитесь к администратору",
            show_alert=True
        )
    
    # Проводим покупку
    async with aiosqlite.connect(DB_NAME) as db:
        # Снимаем баланс у покупателя
        await db.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (price, user_id)
        )
        
        # Отмечаем товар как проданный
        await db.execute("UPDATE products SET is_sold = 1 WHERE id = ?", (product_id,))
        
        # Добавляем покупку
        await db.execute(
            "INSERT INTO purchases (user_id, product_id, price) VALUES (?, ?, ?)",
            (user_id, product_id, price)
        )
        
        # Начисляем рефералу если есть
        cursor = await db.execute("SELECT referrer_id FROM users WHERE user_id = ?", (user_id,))
        ref_row = await cursor.fetchone()
        if ref_row and ref_row[0]:
            ref_earnings = price * 0.1
            await db.execute(
                "UPDATE users SET ref_earnings = ref_earnings + ? WHERE user_id = ?",
                (ref_earnings, ref_row[0])
            )
        
        await db.commit()
    
    await callback.message.answer(
        f"✅ **ПОКУПКА УСПЕШНА!**\n\n"
        f"📱 Аккаунт: `{phone}`\n"
        f"💵 Потрачено: **{price:.4f} TON**\n\n"
        f"Перейдите в 'Мои покупки' чтобы получить код входа",
        parse_mode="Markdown"
    )
    
    await callback.answer()

# --- МОИ ПОКУПКИ ---
@dp.message(F.text == "🛍 Мои покупки")
async def my_purchases(message: types.Message):
    user_id = message.from_user.id
    purchases = await get_user_purchases(user_id)
    
    if not purchases:
        return await message.answer(
            "🛍 **У вас нет покупок**\n\n"
            "Перейдите в 'Купить аккаунты' чтобы начать",
            parse_mode="Markdown"
        )
    
    kb = InlineKeyboardBuilder()
    for p in purchases:
        kb.row(types.InlineKeyboardButton(
            text=f"📱 {p[1]} • {p[3]:.4f} TON",
            callback_data=f"view_{p[2]}"
        ))
    
    await message.answer(
        "🛍 **Ваши покупки:**",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("view_"))
async def view_item(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = await get_product(product_id)
    
    if not product:
        return await callback.answer("Товар не найден", show_alert=True)
    
    _, phone, price, session_path, geo, stay, prod_type = product
    
    text = (
        f"📱 **АККАУНТ**\n\n"
        f"📞 Номер: `{phone}`\n"
        f"📍 Страна: **{geo}**\n"
        f"⏳ Отлега: **{stay}**\n"
        f"⚙️ Тип: **{prod_type}**\n"
        f"💵 Цена: **{price:.4f} TON**"
    )
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(
        text="📩 Получить код входа",
        callback_data=f"get_{product_id}"
    ))
    
    await callback.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("get_"))
async def get_code(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = await get_product(product_id)
    
    if not product:
        return await callback.answer("Товар не найден", show_alert=True)
    
    _, phone, price, session_path, _, _, _ = product
    
    try:
        # Используем существующий клиент или создаем новый
        if session_path not in telegram_clients:
            client = TelegramClient(session_path, API_ID, API_HASH)
            await client.connect()
            telegram_clients[session_path] = client
        else:
            client = telegram_clients[session_path]
        
        # Получаем последнее сообщение с кодом
        try:
            msgs = await client.get_messages(777000, limit=1)
            if msgs and msgs[0].message:
                code = msgs[0].message
                await callback.message.answer(
                    f"📩 **КОД ВХОДА:**\n\n`{code}`\n\n"
                    f"Используйте этот код для подтверждения входа в аккаунт.",
                    parse_mode="Markdown"
                )
            else:
                await callback.message.answer(
                    "⏳ **Код еще не пришел**\n\n"
                    "Попробуйте позже или обратитесь в поддержку @zyozp"
                )
        except:
            await callback.message.answer(
                "⏳ **Код еще не пришел**\n\n"
                "Попробуйте позже или обратитесь в поддержку @zyozp"
            )
    
    except Exception as e:
        await callback.message.answer(
            "❌ **Ошибка подключения**\n\n"
            f"Обратитесь в поддержку @zyozp\n\n"
            f"Номер аккаунта: `{phone}`",
            parse_mode="Markdown"
        )
    
    await callback.answer()

# --- АДМИНКА: ДОБАВЛЕНИЕ ТОВАРА ---
@dp.message(F.text == "➕ Добавить товар", F.from_user.id == ADMIN_ID)
async def add_1(message: types.Message, state: FSMContext):
    await message.answer(
        "📎 **ДОБАВЛЕНИЕ ТОВАРА**\n\n"
        "Отправьте .session файл:"
    )
    await state.set_state(ShopStates.wait_acc_file)

@dp.message(ShopStates.wait_acc_file, F.document)
async def add_2(message: types.Message, state: FSMContext):
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
    
    file_name = message.document.file_name
    path = f"sessions/{file_name}"
    
    await bot.download(message.document, destination=path)
    
    phone = file_name.replace(".session", "")
    await state.update_data(path=path, phone=phone)
    
    await message.answer(
        f"✅ Файл загружен: `{file_name}`\n\n"
        f"Введите цену (TON):"
    )
    await state.set_state(ShopStates.wait_acc_price)

@dp.message(ShopStates.wait_acc_price)
async def add_3(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        
        await message.answer(
            f"✅ Цена: **{price:.4f} TON**\n\n"
            f"Введите страну (например: 🇷🇺 Россия):"
        )
        await state.set_state(ShopStates.wait_acc_geo)
    except:
        await message.answer("❌ Неверный формат. Введите число.")

@dp.message(ShopStates.wait_acc_geo)
async def add_4(message: types.Message, state: FSMContext):
    await state.update_data(geo=message.text)
    
    await message.answer(
        f"✅ Страна: **{message.text}**\n\n"
        f"Введите отлегу (например: 2 месяца):"
    )
    await state.set_state(ShopStates.wait_acc_stay)

@dp.message(ShopStates.wait_acc_stay)
async def add_5(message: types.Message, state: FSMContext):
    await state.update_data(stay=message.text)
    
    await message.answer(
        f"✅ Отлега: **{message.text}**\n\n"
        f"Введите тип (например: New, Premium, Business):"
    )
    await state.set_state(ShopStates.wait_acc_type)

@dp.message(ShopStates.wait_acc_type)
async def add_6(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "INSERT INTO products (phone, price, session_path, geo, stay, type) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (data['phone'], data['price'], data['path'], data['geo'], data['stay'], message.text)
            )
            await db.commit()
        
        await message.answer(
            f"✅ **ТОВАР ДОБАВЛЕН**\n\n"
            f"📱 Телефон: `{data['phone']}`\n"
            f"💵 Цена: **{data['price']:.4f} TON**\n"
            f"📍 Страна: **{data['geo']}**\n"
            f"⏳ Отлега: **{data['stay']}**\n"
            f"⚙️ Тип: **{message.text}**",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    
    await state.clear()

# --- АДМИНКА: ВЫДАЧА БАЛАНСА ---
@dp.message(F.text == "💎 Выдать баланс", F.from_user.id == ADMIN_ID)
async def give_bal(message: types.Message, state: FSMContext):
    await message.answer("🆔 Введите ID пользователя:")
    await state.set_state(ShopStates.wait_bal_id)

@dp.message(ShopStates.wait_bal_id)
async def give_bal_2(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text)
        
        # Проверяем существует ли пользователь
        user = await get_user(uid)
        if not user:
            await create_user(uid)
        
        await state.update_data(uid=uid)
        await message.answer(f"✅ Пользователь: `{uid}`\n\nВведите количество TON:")
        await state.set_state(ShopStates.wait_bal_amount)
    except:
        await message.answer("❌ Неверный ID. Попробуйте снова.")

@dp.message(ShopStates.wait_bal_amount)
async def give_bal_3(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        
        await add_balance(data['uid'], amount)
        
        await message.answer(
            f"✅ **БАЛАНС ВЫДАН**\n\n"
            f"👤 Пользователь: `{data['uid']}`\n"
            f"💰 Сумма: **{amount:.4f} TON**"
        )
    except:
        await message.answer("❌ Неверная сумма. Попробуйте снова.")
    
    await state.clear()

# --- АДМИНКА: РАССЫЛКА ---
@dp.message(F.text == "📢 Рассылка", F.from_user.id == ADMIN_ID)
async def broadcast_1(message: types.Message, state: FSMContext):
    await message.answer("📝 Введите текст для рассылки:")
    await state.set_state(ShopStates.wait_broadcast_text)

@dp.message(ShopStates.wait_broadcast_text)
async def broadcast_2(message: types.Message, state: FSMContext):
    text = message.text
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        users = await cursor.fetchall()
    
    count = 0
    failed = 0
    
    for u in users:
        try:
            await bot.send_message(
                u[0],
                f"📢 **РАССЫЛКА**\n\n{text}",
                parse_mode="Markdown"
            )
            count += 1
        except:
            failed += 1
    
    await message.answer(
        f"✅ **РАССЫЛКА ЗАВЕРШЕНА**\n\n"
        f"✉️ Отправлено: **{count}**\n"
        f"❌ Ошибок: **{failed}**",
        parse_mode="Markdown"
    )
    
    await state.clear()

# --- ЗАПУСК БОТА ---
async def main():
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
    
    await init_db()
    
    print("🚀 Бот запущен...")
    
    try:
        await dp.start_polling(bot)
    finally:
        # Закрываем все клиенты при выключении
        for client in telegram_clients.values():
            try:
                await client.disconnect()
            except:
                pass

if __name__ == "__main__":
    asyncio.run(main())
