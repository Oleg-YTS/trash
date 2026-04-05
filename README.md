# 🍔 Трэш-диетолог — Telegram Bot

Telegram-бот, который анализирует фото холодильника через **Groq (Llama 4 Scout)** и выдаёт абсурдные, но убедительные советы по питанию.

## Возможности

- 📸 Анализ фото холодильника через Groq (Llama 4 Scout — vision)
- 🍳 **Реальные рецепты** из продуктов на фото (в трэш-подаче)
- 🤡 Roast-вердикты, калории, абсурдные названия блюд
- ⭐ Монетизация через **Telegram Stars** (донаты + покупка анализов)
- 🔄 Retry-логика при ошибках Groq
- 🖼️ Валидация и сжатие фото (до 4MB для Groq API)
- 📊 Лимит бесплатных анализов (3/день)
- 💤 Fallback-режим когда AI недоступен

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка ключей

```bash
cp .env.example .env
```

Вставь свои ключи в `.env`:

```
TELEGRAM_TOKEN=123456:ABC-DEF...
GROQ_API_KEY=gsk_...
```

**Где взять:**
- Telegram токен → [@BotFather](https://t.me/BotFather)
- Groq API → [console.groq.com](https://console.groq.com) (бесплатно)

### 3. Запуск

```bash
python fridge_bot.py
```

---

## 🚀 Деплой на Render.com (бесплатно, 24/7)

Render даёт **750 бесплатных часов/мес** — бот работает круглосуточно без остановок.

### Шаг 1: Push в GitHub

```bash
git init
git add .
git commit -m "init: trash-diet bot"
git remote add origin https://github.com/твой-username/trash-diet.git
git push -u origin main
```

### Шаг 2: Подключи Render

1. Зайди на [render.com](https://render.com) → **Sign Up** (GitHub)
2. Нажми **New +** → **Blueprint**
3. Подключи свой GitHub-репозиторий
4. Render найдёт `render.yaml` и настроит всё сам

**Или вручную:**

1. **New +** → **Web Service**
2. Подключи репозиторий
3. Настройки:
   - **Name:** `trash-diet`
   - **Runtime:** `Docker`
   - **Plan:** **Free**
   - **Instance Type:** Free

### Шаг 3: Переменные окружения

В разделе **Environment** сервиса добавь:

| Ключ | Значение |
|------|----------|
| `TELEGRAM_TOKEN` | Твой токен от @BotFather |
| `GROQ_API_KEY` | Твой ключ от console.groq.com |

### Шаг 4: Deploy

Нажми **Deploy** → подожди 2-3 минуты → бот работает!

### Проверка

Открой `https://trash-diet.onrender.com` — должно быть `OK — trash-diet bot is running`

---

## 🐳 Деплой через Docker (локально)

```bash
# Сборка
docker build -t trash-diet .

# Запуск
docker run -d \
  -e TELEGRAM_TOKEN=your_token \
  -e GROQ_API_KEY=your_groq_key \
  -p 10000:10000 \
  trash-diet
```

---

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие |
| `/help` | Как пользоваться |
| `/stats` | Твоя статистика |
| `/history` | История анализов |

## Монетизация

Бот использует **Telegram Stars** (валюта `XTR`):

| Платёж | Цена | Что даёт |
|--------|------|----------|
| ⭐ Звезда | 1 ⭐ | Донат создателю |
| +5 анализов | 3 ⭐ | Расширение лимита на день |

## Архитектура

```
fridge_bot.py       # Весь бот (polling + Groq + handlers)
healthcheck.py      # HTTP сервер для Render healthcheck
.env                # Секреты (не коммитить!)
.env.example        # Шаблон для .env
requirements.txt    # Зависимости
Dockerfile          # Контейнер
render.yaml         # Конфиг для Render
run_bot.sh          # Скрипт автоперезапуска (PythonAnywhere)
```

## Лимиты и затраты

| Сервис | Бесплатно | Платно |
|--------|-----------|--------|
| Groq (Llama 4 Scout) | ~10-50 запросов/мин | $0.05/1M токенов |
| Telegram | ∞ | ∞ |
| Render | 750 часов/мес | $7/мес за доп. сервисы |

---

> ⚠️ **Дисклеймер:** Бот создан для развлечения. Все советы — абсурд и юмор. Не используйте их как реальную диету.
