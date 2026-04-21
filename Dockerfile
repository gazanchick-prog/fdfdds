FROM python:3.11-slim

WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем основной файл
COPY main.py .

# Создаем необходимые папки
RUN mkdir -p sessions

# Запускаем бота
CMD ["python", "main.py"]
