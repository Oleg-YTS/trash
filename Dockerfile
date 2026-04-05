FROM python:3.12-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Render требует PORT переменную для web-сервисов
# Бот использует polling, но healthcheck нужен
EXPOSE 10000

# Запуск: бот + простой healthcheck сервер
CMD ["sh", "-c", "python healthcheck.py & python fridge_bot.py"]
