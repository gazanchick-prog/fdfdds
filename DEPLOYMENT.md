# 🚀 Гайд по развертыванию на хост-сервисах

## 🌐 Railway (Рекомендуется)

Railway.app - самый простой и бесплатный способ запустить бота.

### Пошаговая инструкция:

#### 1. Подготовка GitHub репозитория

```bash
# Инициализируем Git репозиторий (если еще не сделано)
git init

# Добавляем все файлы
git add .

# Коммитим
git commit -m "Initial commit - Minon Shop Bot"

# Добавляем remote (замените на свой репозиторий)
git remote add origin https://github.com/YOUR_USERNAME/minon-shop.git

# Пушим на GitHub
git push -u origin main
```

#### 2. Развертывание на Railway

1. Перейдите на [railway.app](https://railway.app)
2. Нажмите **"New Project"**
3. Выберите **"Deploy from GitHub"**
4. Подключите ваш GitHub аккаунт
5. Выберите репозиторий `minon-shop`
6. Railway автоматически обнаружит `requirements.txt` и `Dockerfile`

#### 3. Установка переменных окружения

1. На странице проекта нажмите на название приложения
2. Перейдите в **"Variables"**
3. Добавьте переменные:
   - `BOT_TOKEN` = ваш токен
   - `ADMIN_ID` = ваш ID
   - `API_ID` = ваш API ID
   - `API_HASH` = ваш API HASH
   - `TON_WALLET` = ваш кошелек
4. Нажмите **"Save"**

#### 4. Запуск

Railway автоматически задеплойт бота. В разделе **"Logs"** вы увидите:
```
🚀 Бот запущен...
```

**Готово!** Бот работает 24/7

---

## 🐳 Docker + VPS (для опытных)

Если у вас есть свой VPS (DigitalOcean, Linode, Hetzner).

### 1. Подготовка VPS

```bash
# SSH на ваш сервер
ssh root@YOUR_SERVER_IP

# Обновляем систему
apt update && apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Устанавливаем Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### 2. Клонируем репозиторий

```bash
# Клонируем
git clone https://github.com/YOUR_USERNAME/minon-shop.git
cd minon-shop

# Создаем .env файл на сервере
nano .env

# Вставляем (Ctrl+Shift+V):
BOT_TOKEN=YOUR_TOKEN
ADMIN_ID=YOUR_ID
API_ID=YOUR_API_ID
API_HASH=YOUR_API_HASH
TON_WALLET=YOUR_WALLET

# Сохраняем (Ctrl+X, Y, Enter)
```

### 3. Запуск через Docker

```bash
# Собираем образ
docker build -t minon-shop .

# Запускаем контейнер
docker run -d --name minon-shop --env-file .env minon-shop

# Проверяем статус
docker ps

# Смотрим логи
docker logs -f minon-shop
```

### 4. Автозагрузка после перезагрузки сервера

```bash
# Создаем файл systemd
sudo nano /etc/systemd/system/minon-shop.service

# Вставляем:
[Unit]
Description=Minon Shop Bot
After=docker.service
Requires=docker.service

[Service]
Type=simple
WorkingDirectory=/root/minon-shop
ExecStart=/usr/bin/docker run --rm --env-file .env --name minon-shop minon-shop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Сохраняем и включаем
sudo systemctl enable minon-shop.service
sudo systemctl start minon-shop.service

# Проверяем статус
sudo systemctl status minon-shop.service
```

---

## 📦 Heroku (деактивирован, но возможен)

Heroku прекратил бесплатный тарифный план, но если у вас есть платная подписка:

### 1. Подготовка

```bash
# Устанавливаем Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Логинимся
heroku login

# Создаем приложение
heroku create your-bot-name
```

### 2. Развертывание

```bash
# Добавляем переменные
heroku config:set BOT_TOKEN=YOUR_TOKEN
heroku config:set ADMIN_ID=YOUR_ID
heroku config:set API_ID=YOUR_API_ID
heroku config:set API_HASH=YOUR_API_HASH
heroku config:set TON_WALLET=YOUR_WALLET

# Пушим код
git push heroku main

# Смотрим логи
heroku logs --tail
```

---

## 🌍 PythonAnywhere

Простой вариант для Python приложений.

### 1. Регистрация

1. Перейдите на [pythonanywhere.com](https://www.pythonanywhere.com)
2. Создайте бесплатный аккаунт

### 2. Загрузка файлов

1. Перейдите в **"Files"**
2. Создайте папку `minon-shop`
3. Загрузите файлы (main.py, requirements.txt, .env)

### 3. Установка зависимостей

1. Откройте **"Consoles"** → **"Bash console"**
2. Выполните:

```bash
cd minon-shop
pip install -r requirements.txt
```

### 4. Запуск

1. Перейдите в **"Web"** → **"Add a new web app"**
2. Выберите **"Manual configuration"** → **"Python"**
3. В разделе **"Code"** установите **"Working directory"**: `/home/YOUR_USERNAME/minon-shop`
4. Создайте новый WSGI файл или используйте systemd task для запуска

---

## 📱 Replit (для быстрого тестирования)

Replit удобен для разработки, но может быть нестабилен для production.

### 1. Импорт репозитория

1. Перейдите на [replit.com](https://replit.com)
2. Нажмите **"Create"** → **"Import from GitHub"**
3. Вставьте URL вашего репозитория
4. Replit автоматически создаст проект

### 2. Переменные окружения

1. Нажмите на иконку замка в левой панели
2. Добавьте все переменные из .env
3. Сохраните

### 3. Запуск

```bash
# В консоли Replit:
python main.py
```

---

## 🔄 Обновление кода на сервере

### На Railway:
```bash
# Просто пушим изменения в GitHub
git add .
git commit -m "Update bot code"
git push
# Railway автоматически переберет код
```

### На VPS/Docker:
```bash
# Обновляем код из GitHub
git pull

# Перестраиваем образ
docker build -t minon-shop .

# Останавливаем старый контейнер
docker stop minon-shop

# Запускаем новый
docker run -d --name minon-shop --env-file .env minon-shop
```

### На PythonAnywhere:
1. Перейдите в **"Files"** → обновите файлы через загрузку
2. В **"Web"** перезагрузите приложение (кнопка **"Reload"**)

---

## ✅ Проверка что бот работает

```bash
# В любом случае можете проверить логи:
# - Railway: смотреть в веб-интерфейсе
# - Docker: docker logs minon-shop
# - PythonAnywhere: в консоли

# Проверьте что видите строку:
# 🚀 Бот запущен...
```

---

## 🛠️ Решение проблем

### Ошибка: "Module not found"
```bash
# Переустановите зависимости
pip install --upgrade -r requirements.txt
```

### Ошибка: "Cannot connect to Telegram"
- Проверьте что BOT_TOKEN правильный
- Убедитесь что интернет подключен
- На VPS может быть блокировка - используйте VPN

### База данных не сохраняется
- На Railway и других облачных сервисах файловая система временная
- Используйте PostgreSQL или MongoDB вместо SQLite
- Или используйте собственный VPS

### Session файлы теряются
- Разместите их в отдельном хранилище (S3, Cloudinary)
- Или используйте собственный VPS с постоянным хранилищем

---

## 📞 Получение помощи

- Документация Railway: https://docs.railway.app
- Документация Docker: https://docs.docker.com
- Помощь по Telegram Bot API: https://core.telegram.org/bots/api

**Версия гайда:** 1.0  
**Дата обновления:** 2026-04-21
