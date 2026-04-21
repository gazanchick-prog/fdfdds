# 💳 Интеграция платежей

## 🌟 Популярные способы получения платежей

### Вариант 1: TON через @CryptoBot (РЕКОМЕНДУЕТСЯ)

Автоматические платежи в TON через встроенного бота Telegram.

#### Установка:

1. Найдите бота [@CryptoBot](https://t.me/CryptoBot) в Telegram
2. Отправьте `/start`
3. Нажмите **"Create Merchant App"**
4. Заполните информацию:
   - App Name: "Minon Shop"
   - URL: ваш URL (если есть) или оставьте пустым
5. Получите **API Token**

#### Интеграция в бот:

Добавьте в `.env`:
```env
CRYPTOBOT_API_TOKEN=your_token_here
```

Добавьте функцию в `main.py`:

```python
import aiohttp

CRYPTOBOT_API_TOKEN = os.getenv("CRYPTOBOT_API_TOKEN")
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"

async def create_invoice(user_id, amount_ton, description="Balance top-up"):
    """Создать счет для пополнения баланса"""
    
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": str(amount_ton),
        "currency_code": "TON",
        "description": description,
        "paid_btn_url": f"https://t.me/your_bot_username?start={user_id}"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{CRYPTOBOT_API_URL}/createInvoice",
            json=payload,
            headers=headers
        ) as resp:
            data = await resp.json()
            
            if data['ok']:
                return data['result']['pay_url']
            else:
                return None

# Используйте в меню пополнения:
@dp.message(F.text == "💰 Пополнить баланс")
async def topup(message: types.Message):
    text = "💎 **ПОПОЛНЕНИЕ БАЛАНСА**\n\nВыберите сумму:"
    
    kb = InlineKeyboardBuilder()
    for amount in [10, 50, 100, 500]:
        kb.row(types.InlineKeyboardButton(
            text=f"{amount} TON",
            callback_data=f"topup_{amount}"
        ))
    
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("topup_"))
async def process_topup(callback: types.CallbackQuery):
    amount = int(callback.data.split("_")[1])
    
    pay_url = await create_invoice(callback.from_user.id, amount)
    
    if pay_url:
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="💳 Оплатить", url=pay_url))
        
        await callback.message.answer(
            f"💳 **СЧЕТ НА ОПЛАТУ**\n\n"
            f"Сумма: **{amount} TON**\n"
            f"ID: `{callback.from_user.id}`",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await callback.answer("❌ Ошибка создания счета", show_alert=True)
```

#### Проверка платежей:

```python
async def check_cryptobot_payments(user_id):
    """Проверить платежи от CryptoBot"""
    
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_API_TOKEN
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{CRYPTOBOT_API_URL}/getInvoices",
            headers=headers
        ) as resp:
            data = await resp.json()
            
            if data['ok']:
                for invoice in data['result']['items']:
                    # Проверяем если оплачено
                    if invoice['status'] == 'paid':
                        amount = float(invoice['amount'])
                        
                        # Зачисляем баланс
                        await add_balance(user_id, amount)
                        
                        return amount
    
    return None
```

---

### Вариант 2: Юасний перевод через @BotFather

Более простой вариант но требует ручной проверки.

#### Как работает:

1. Пользователь отправляет платеж в TON
2. Администратор проверяет комментарий
3. Администратор выдает баланс через "💎 Выдать баланс"

**Информация для пользователя:**

```text
💎 ПОПОЛНЕНИЕ БАЛАНСА (TON)

📍 Адрес кошелька:
UQDlFKmdWxZqtT1ueKC58L6Kj77RLY6tGu3wW_aaZHGXt46O

💬 Комментарий (ВАЖНО!):
8212981789

⚠️ Без комментария баланс не будет зачислен!

После перевода обратитесь в поддержку.
```

---

### Вариант 3: Обычный платеж в Telegram

Через встроенную систему платежей Telegram.

```python
# Добавить Stripe/PayPal интеграцию

@dp.message(F.text == "💰 Пополнить баланс")
async def topup_stripe(message: types.Message):
    """Пополнение через Stripe"""
    
    # Создаем счет через Stripe
    # https://stripe.com/
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(
        text="💳 Оплатить $10",
        url="https://checkout.stripe.com/your_session_id"
    ))
    
    await message.answer(
        "💳 **Оплата через Stripe**\n\n"
        "Нажмите кнопку ниже чтобы оплатить",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
```

---

### Вариант 4: USDT через @USDTbot

```python
@dp.message(F.text == "💰 Пополнить баланс")
async def topup_usdt(message: types.Message):
    """Пополнение через USDT"""
    
    text = (
        "💵 **ПОПОЛНЕНИЕ ЧЕРЕЗ USDT**\n\n"
        "Отправьте любую сумму USDT на адрес:\n\n"
        "`0x1234567890abcdef1234567890abcdef12345678`\n\n"
        "Комментарий: `8212981789`\n\n"
        "Сеть: TON или Ethereum\n"
        "Минимум: $10"
    )
    
    await message.answer(text, parse_mode="Markdown")
```

---

## 📋 Сравнение методов платежей

| Способ | Комиссия | Скорость | Сложность |
|--------|----------|----------|-----------|
| **CryptoBot (TON)** | 2% | Мгновенно | Средняя |
| **Ручное пополнение** | 0% | 5-10 мин | Низкая |
| **Stripe** | 3-4% | Мгновенно | Высокая |
| **USDT** | 0-1% | 5-30 мин | Средняя |

**Рекомендация:** Используйте CryptoBot для автоматизации.

---

## 🔄 Пример полного workflow с CryptoBot

### Файл `payments.py`:

```python
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class CryptoBotPayments:
    API_TOKEN = os.getenv("CRYPTOBOT_API_TOKEN")
    API_URL = "https://pay.crypt.bot/api"
    
    @classmethod
    async def create_invoice(cls, user_id: int, amount: float) -> str:
        """Создать счет"""
        
        headers = {
            "Crypto-Pay-API-Token": cls.API_TOKEN,
            "Content-Type": "application/json"
        }
        
        payload = {
            "asset": "USDT",
            "amount": str(amount),
            "description": f"Top-up balance for user {user_id}",
            "currency_code": "USD"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{cls.API_URL}/createInvoice",
                json=payload,
                headers=headers
            ) as resp:
                data = await resp.json()
                
                if data.get('ok'):
                    return data['result']['pay_url']
                else:
                    raise Exception(f"Payment API error: {data}")
    
    @classmethod
    async def get_invoices(cls) -> list:
        """Получить все счета"""
        
        headers = {
            "Crypto-Pay-API-Token": cls.API_TOKEN
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{cls.API_URL}/getInvoices",
                headers=headers
            ) as resp:
                data = await resp.json()
                
                if data.get('ok'):
                    return data['result']['items']
                else:
                    return []
    
    @classmethod
    async def get_paid_invoices(cls) -> list:
        """Получить оплаченные счета"""
        
        invoices = await cls.get_invoices()
        return [inv for inv in invoices if inv['status'] == 'paid']

# Использование:
# payment_url = await CryptoBotPayments.create_invoice(user_id, 10)
# paid = await CryptoBotPayments.get_paid_invoices()
```

---

## ✅ Рекомендуемая схема

1. **Маленькие магазины (до 100 юзеров):**
   - Используйте ручное пополнение
   - Пользователь отправляет TON с комментарием
   - Вы выдаете баланс через админ панель

2. **Средние магазины (100-1000 юзеров):**
   - Используйте CryptoBot для автоматизации
   - Минимальные комиссии
   - Автоматическое зачисление

3. **Большие магазины (1000+ юзеров):**
   - Интегрируйте несколько способов платежей
   - Используйте PostgreSQL вместо SQLite
   - Добавьте собственный бэкэнд для обработки платежей

---

## 🔐 Безопасность платежей

1. **Проверяйте комментарий:**
   ```python
   if comment != str(user_id):
       print("❌ Неверный комментарий")
       return
   ```

2. **Проверяйте сумму:**
   ```python
   if amount < 10:
       print("❌ Минимум 10 TON")
       return
   ```

3. **Логируйте все платежи:**
   ```python
   logger.info(f"Payment from {user_id}: {amount} TON")
   ```

4. **Используйте HTTPS:**
   - Все платежные интеграции должны быть на HTTPS
   - Никогда не передавайте ключи по незащищенным каналам

---

**Документация:** https://pay.crypt.bot/api  
**Версия:** 1.0  
**Обновлено:** 2026-04-21
