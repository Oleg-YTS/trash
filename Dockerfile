FROM python:3.12-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Render устанавливает PORT, мы биндимся на него
EXPOSE 10000

# Render запускает через gunicorn
# Для локальной разработки используйте: docker run -e USE_POLLING=true ...
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 start:app
