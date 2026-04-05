FROM python:3.12-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Render устанавливает PORT, мы биндимся на него
EXPOSE 10000

CMD ["python", "start.py"]
