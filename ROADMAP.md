# 🗺️ План расширения: Трэш-диетолог v2.0

Текущий MVP — один файл. Этот план описывает, что добавить для production-ready версии.

---

## Этап 1: Модульная архитектура

### Целевая структура проекта

```
trash_diet/
├── bot.py                  # Инициализация бота, polling/webhook
├── config.py               # Настройки из env, константы
├── database.py             # SQLite/PostgreSQL слой (users, analyses, payments)
├── gemini_client.py        # Gemini API с retry, кэшированием, fallback
├── formatters.py           # Форматирование ответов (roast-стили, шаблоны)
├── keyboards.py            # Все Inline-клавиатуры
├── handlers/
│   ├── commands.py         # /start, /help, /stats, /history
│   ├── photo.py            # Обработка фото
│   ├── callbacks.py        # Callback-кнопки
│   └── payments.py         # Обработка платежей
├── middlewares/
│   ├── throttling.py       # Rate-limit на сообщения
│   └── logging.py          # Логирование действий
├── utils/
│   ├── photo_validator.py  # Проверка фото
│   └── image_hash.py       # Хэш фото для кэширования
├── migrations/             # Миграции БД (alembic)
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml      # Бот + PostgreSQL (опционально)
└── tests/
    ├── test_gemini.py
    ├── test_handlers.py
    └── test_database.py
```

### Что изменить:
1. Разбить `fridge_bot.py` на модули по зонам ответственности
2. Вынести Gemini-клиент в отдельный класс с интерфейсом
3. Добавить middleware для троттлинга (защита от спама)

---

## Этап 2: База данных (SQLite → PostgreSQL)

### Схема БД

```sql
-- Пользователи
CREATE TABLE users (
    id INTEGER PRIMARY KEY,           -- Telegram user_id
    username TEXT,
    first_name TEXT,
    language_code TEXT DEFAULT 'ru',
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP,
    referral_code TEXT UNIQUE,
    referred_by INTEGER REFERENCES users(id)
);

-- Анализы холодильников
CREATE TABLE analyses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    photo_file_id TEXT,               -- Telegram file_id (кэш)
    photo_hash TEXT,                  -- perceptual hash (дедупликация)
    products JSONB,                   -- Распознанные продукты
    recipe TEXT,
    calories TEXT,
    roast TEXT,
    verdict TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Платежи
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    invoice_payload TEXT,
    currency TEXT,
    total_amount INTEGER,
    status TEXT DEFAULT 'pending',    -- pending / success / failed
    created_at TIMESTAMP DEFAULT NOW()
);

-- Лимиты (для гибкого управления)
CREATE TABLE daily_limits (
    user_id INTEGER REFERENCES users(id),
    date DATE,
    free_used INTEGER DEFAULT 0,
    paid_used INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, date)
);
```

### Миграции
- Использовать `alembic` для управления схемой
- Автоматическое применение миграций при старте контейнера

---

## Этап 3: Продвинутый Gemini-клиент

### Улучшения:

```python
class GeminiClient:
    def __init__(self, api_key: str, cache_ttl: int = 3600):
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        self.cache = {}  # photo_hash → result
        self.cache_ttl = cache_ttl

    async def analyze(self, image_bytes: bytes) -> dict:
        # 1. Проверить кэш по хэшу
        # 2. Вызвать API с retry + exponential backoff
        # 3. Валидировать JSON-ответ
        # 4. Сохранить в кэш
        # 5. Вернуть результат
```

### Дополнительные фичи:
- **Кэширование**: одинаковые фото → один запрос к Gemini
- **Fallback-модель**: если `gemini-1.5-flash` недоступен → `gemini-1.5-pro`
- **Температура ответа**: `generation_config=GenerationConfig(temperature=0.9)` для более креативных roast
- **Системные промпты по настроению**:
  - `sarcastic` — сарказм
  - `dark_humor` — чёрный юмор
  - `absurd` — полный абсурд
  - `supportive` — "поддерживающий" трэш (иронично-добрый)

---

## Этап 4: Реферальная система

### Логика:
1. Каждый юзер получает уникальный код: `/invite` → `t.me/trashdiet_bot?start=ref_12345`
2. Реферер получает +1 бесплатный анализ за каждого приглашённого
3. Топ рефереров — публичный рейтинг

### Команды:
- `/invite` — получить реферальную ссылку
- `/referrals` — сколько людей пригласил
- `/top` — топ рефереров месяца

---

## Этап 5: Расширенная монетизация

### Что добавить:

| Фича | Цена | Описание |
|------|------|----------|
| Расширенный анализ | 5 ⭐ | Gemini анализирует ещё: срок годности, сочетаемость продуктов, "диету по знаку зодиака" |
| Подписка на неделю | 25 ⭐ | Безлимитные анализы + эксклюзивные roast-стили |
| Подписка на месяц | 75 ⭐ | Всё выше + ранний доступ к новым фичам |
| Кастомный промпт | 10 ⭐ | Юзер выбирает стиль roast (сарказм, стендап, поэзия) |

### Интеграции:
- **Telegram Stars** — основной способ (0% комиссии Telegram)
- **YooKassa** — для RU аудитории (карты, СБП)
- **CryptoBot** — криптовалюта в Telegram

---

## Этап 6: Контент-улучшения

### 1. Сезонные рецепты
```python
def get_seasonal_prompt() -> str:
    month = datetime.now().month
    if month in (12, 1, 2):
        return "Зима. Предлагай горячее и согревающее, даже если это абсурд."
    elif month in (6, 7, 8):
        return "Лето. Предлагай холодные блюда и окрошку (всегда окрошку)."
    # ...
```

### 2. Персонализация
- Запоминать прошлые анализы юзера
- Ссылаться на них: "Опять майонез? Ты неисправим."
- Отслеживать "прогресс": стал ли холодильник лучше

### 3. Достижения (gamification)
```
🏆 "Первый позор" — первый анализ с verdict ПОЗОР
🏆 "Холодильный маньяк" — 10 анализов за день
🏆 "ЗОЖ-воин" — verdict ЗОЖНИК 3 раза подряд
🏆 "Алкогольная пятница" — только алкоголь в холодильнике
```

### 4. Мемы и GIF
- Прикреплять GIF с реакцией к verdict (через Giphy API или локальную коллекцию)
- "ПОЗОР" → GIF с плачущим человеком
- "ЗОЖНИК" → GIF с аплодисментами

---

## Этап 7: Инфраструктура

### Docker Compose (production)

```yaml
version: "3.9"
services:
  bot:
    build: .
    restart: unless-stopped
    env_file: .env
    depends_on:
      - db
    deploy:
      resources:
        limits:
          memory: 512M

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: trashdiet
      POSTGRES_USER: trashdiet
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  # Опционально: кэш
  redis:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  pgdata:
```

### Webhook vs Polling
- **Polling** (сейчас) — просто, но неэффективно при большом трафике
- **Webhook** — нужно HTTPS, но быстрее и надёжнее
- Переключиться на webhook при >100 пользователей

### Мониторинг
- **Healthcheck endpoint** — `/health` (если webhook)
- **Sentry** — отслеживание ошибок
- **Prometheus + Grafana** — метрики (запросы/мин, latency, error rate)

### CI/CD
```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t trash-diet .
      - run: docker push your-registry/trash-diet:latest
      - run: ssh prod "docker compose pull && docker compose up -d"
```

---

## Этап 8: Тесты

### Что покрыть:
1. **Юнит-тесты**:
   - Парсинг JSON из Gemini-ответа
   - Валидация фото
   - Форматирование ответов
   - Логика лимитов

2. **Интеграционные тесты**:
   - Mock Gemini API → тест обработчика фото
   - Mock Telegram API → тест отправки сообщений

3. **E2E тесты** (опционально):
   - Реальный бот в тест-чате с реальным Gemini

### Пример:
```python
# tests/test_gemini.py
def test_parse_gemini_json():
    response = '```json\n{"products": ["кефир"], "recipe": "...", "calories": "...", "roast": "...", "verdict": "ПОЗОР"}\n```'
    result = parse_gemini_response(response)
    assert result["products"] == ["кефир"]
    assert result["verdict"] == "ПОЗОР"
```

---

## Приоритизация (что делать в первую очередь)

| Приоритет | Задача | Сложность | Ценность |
|-----------|--------|-----------|----------|
| 🔴 P0 | Модульная архитектура | Средняя | Высокая |
| 🔴 P0 | База данных (SQLite) | Низкая | Высокая |
| 🟡 P1 | Кэширование фото | Низкая | Средняя |
| 🟡 P1 | Рефералка | Средняя | Высокая |
| 🟢 P2 | Подписки | Высокая | Высокая |
| 🟢 P2 | Достижения | Средняя | Средняя |
| 🟢 P2 | Webhook + Docker Compose | Высокая | Высокая |
| ⚪ P3 | Мониторинг (Sentry) | Низкая | Средняя |
| ⚪ P3 | Тесты | Высокая | Средняя |

---

## Оценка затрат (время одного разработчика)

| Этап | Время |
|------|-------|
| Модульная архитектура | 2-3 часа |
| БД + миграции | 3-4 часа |
| Gemini-клиент с кэшем | 2 часа |
| Рефералка | 3-4 часа |
| Монетизация (подписки) | 4-6 часов |
| Docker Compose + webhook | 2-3 часа |
| Тесты | 4-6 часов |
| **Итого** | **20-28 часов** |

---

## Что можно сделать прямо сейчас (после MVP)

1. **Замени `_user_analyses` на SQLite** — данные не будут теряться при рестарте
2. **Добавь кэширование фото** — сэкономишь на Gemini API
3. **Включи webhook** — для стабильной работы на сервере
4. **Напиши 5-10 тестов** — чтобы не бояться рефакторить
