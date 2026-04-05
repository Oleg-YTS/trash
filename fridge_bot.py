"""
🍔 Трэш-диетолог — Telegram Bot
Анализирует фото холодильника через Groq (Llama 4 Scout) и выдаёт абсурдные советы.
"""

import base64
import io
import json
import logging
import os
import random
import re
import time
from datetime import datetime

from groq import Groq
import telebot
from dotenv import load_dotenv
from PIL import Image
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)

# ──────────── КОНФИГУРАЦИЯ ────────────
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise RuntimeError(
        "Не заданы TELEGRAM_TOKEN или GROQ_API_KEY в .env файле. "
        "Скопируй .env.example в .env и вставь свои ключи. "
        "GROQ_API_KEY → https://console.groq.com"
    )

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Groq клиент
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Бот
bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="Markdown")

# ──────────── КОНСТАНТЫ ────────────
MAX_ANALYSES_PER_DAY = 3  # Бесплатных анализов в день
PHOTO_MIN_SIZE = (120, 120)  # Минимальный размер фото (отсеем стикеры)
TYPING_TIMEOUT = 8  # Секунд "печатает..." перед анализом
GROQ_RETRIES = 3  # Попыток запроса к Groq
GROQ_RETRY_DELAY = 2  # Секунд между попытками
MAX_IMAGE_SIZE = 4 * 1024 * 1024  # 4MB лимит Groq для base64

# Рандомные фразы при анализе
ANALYSIS_PHRASES = [
    "🔍 *Анализирую содержимое твоего холодильника...*\n_(Это может быть травматично)_",
    "🔍 *Загружаю нейросеть позора...*\n_(Пристёгивайся)_",
    "🔍 *Сканирую твой кулинарный кризис...*\n_(Готовься к правде)_",
    "🔍 *Мой ИИ нервничает, но анализирую...*\n_(Холодильник напуган)_",
    "🔍 *Вскрываю содержимое твоего холодильника...*\n_(Обратного пути нет)_",
    "🔍 *Подключаю нейронки...*\n_(Щекотно будет обоим)_",
    "🔍 *Диагностирую пищевую катастрофу...*\n_(Спойлер: всё плохо)_",
    "🔍 *Изучаю улики...*\n_(Холодильник — место преступления)_",
]

# Системный промпт — структурированный анализ по шагам
DIETITIAN_PROMPT = """Ты — трэш-диетолог с чёрным юмором, который застрял в теле ИИ-анализатора холодильников. Твой стиль: язвительный стендап, сравнения с мемами и знаменитостями, абсурдные аналогии.

Анализируй фото холодильника ПО ШАГАМ:

ШАГ 1 — РАСПОЗНАВАНИЕ:
- Перечисли ВСЕ продукты, которые видишь (включая специи, соусы, банки, пакеты)
- Укажи состояние: сырое / готовое / замороженное / просроченное (по виду упаковки)
- Если одинаковых предметов несколько — укажи количество ("три банки газировки", "пять пакетов молока")
- Обрати внимание на бренды, если они видны

ШАГ 2 — РЕЦЕПТ:
- Придумай РЕАЛЬНОЕ блюдо, которое можно приготовить ИМЕННО из этих продуктов
- Укажи конкретные шаги: что нарезать, как жарить/варить, сколько минут
- Если ингредиентов мало — это всё равно рецепт (яичница из 2 яиц и сосиски — тоже блюдо)
- Если продуктов много — комбинируй их в интересное сочетание
- Название должно быть абсурдным и смешным, но инструкция — настоящая

ШАГ 3 — КАЛОРИИ:
- Посчитай примерно по реальным продуктам
- Подай цифру с пафосом и сарказмом

ШАГ 4 — ROAST:
- ОБЯЗАТЕЛЬНО сравни владельца холодильника со знаменитостью или мемом
- Примеры: "Гордон Рамзи бы заплакал", "Это холодильник Шрека", "Как у Шелдона из Теории Большого взрыва, только хуже", "Шварценеггер в Терминаторе питался лучше"
- Будь язвительным, но без мата
- 30-50 слов

ШАГ 5 — ВЕРДИКТ:
- ПОЗОР — только вредная еда, алкоголь, сладости или пустота с майонезом
- НОРМ — есть и полезное, и вкусное, баланс
- ЗОЖНИК — овощи, белок, минимум мусора, зелёный смузи
- СРОЧНО В МАГАЗИН — холодильник пустой, только свет и одиночество

Верни ТОЛЬКО JSON (без лишнего текста) в формате:
{
    "products": ["продукт1 (сырое)", "продукт2 (3 шт)", "продукт3 (просрочен?)"],
    "recipe": "АбсурдноеНазвание: Шаг 1. Шаг 2. Шаг 3.",
    "calories": "цифра + пафосный комментарий",
    "roast": "сравнение со знаменитостью/мемом + язвительность (30-50 слов)",
    "verdict": "ПОЗОР / НОРМ / ЗОЖНИК / СРОЧНО В МАГАЗИН"
}

ПРАВИЛА:
- Отвечай ТОЛЬКО на русском языке
- Без markdown-обёрток вокруг JSON (никаких ```json)
- Без пояснений до или после JSON
- Не используй мат, только эвфемизмы
- Будь остроумным, а не просто злым"""

# ──────────── УТИЛИТЫ ────────────

# Простая in-memory база для MVP (юзер → кол-во анализов сегодня)
_user_analyses: dict[int, dict] = {}  # {user_id: {"count": int, "date": str}}


def get_today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_analysis_count(user_id: int) -> int:
    today = get_today()
    data = _user_analyses.get(user_id)
    if data and data["date"] == today:
        return data["count"]
    return 0


def increment_analysis_count(user_id: int) -> None:
    today = get_today()
    if user_id not in _user_analyses or _user_analyses[user_id]["date"] != today:
        _user_analyses[user_id] = {"count": 0, "date": today}
    _user_analyses[user_id]["count"] += 1


def is_photo_valid(image_bytes: bytes) -> bool:
    """Проверяет, что фото достаточно большое и не битое."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        if w < PHOTO_MIN_SIZE[0] or h < PHOTO_MIN_SIZE[1]:
            return False
        img.verify()  # Проверка целостности
        return True
    except Exception:
        return False


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Сжимает и кодирует изображение в base64 для Groq API."""
    # Открываем и сжимаем если нужно (лимит 4MB)
    img = Image.open(io.BytesIO(image_bytes))

    # Конвертируем в RGB если нужно
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    # Сжимаем до 4MB
    if len(image_bytes) > MAX_IMAGE_SIZE:
        # Уменьшаем качество и размер
        max_dimension = 2048
        w, h = img.size
        if w > max_dimension or h > max_dimension:
            ratio = min(max_dimension / w, max_dimension / h)
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

        # Сохраняем с низким качеством
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=75)
        image_bytes = output.getvalue()

        # Если всё ещё слишком большое — ещё сжимаем
        if len(image_bytes) > MAX_IMAGE_SIZE:
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=50)
            image_bytes = output.getvalue()

    return base64.b64encode(image_bytes).decode("utf-8")


def call_groq_with_retry(image_bytes: bytes, retries: int = GROQ_RETRIES) -> dict | None:
    """Отправляет фото в Groq (Llama 4 Scout) с повторными попытками."""
    try:
        base64_image = encode_image_to_base64(image_bytes)
    except Exception as e:
        logger.error(f"Ошибка кодирования изображения: {e}")
        return None

    data_url = f"data:image/jpeg;base64,{base64_image}"

    for attempt in range(1, retries + 1):
        try:
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": DIETITIAN_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                        ],
                    }
                ],
                temperature=0.9,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )

            text = response.choices[0].message.content
            if not text:
                logger.warning(f"Groq вернул пустой ответ (попытка {attempt})")
                time.sleep(GROQ_RETRY_DELAY)
                continue

            # Извлекаем JSON
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                required_keys = {"products", "recipe", "calories", "roast", "verdict"}
                if required_keys.issubset(result.keys()):
                    return result

            logger.warning(f"Не удалось распарсить JSON (попытка {attempt}): {text[:200]}")
            time.sleep(GROQ_RETRY_DELAY)

        except Exception as e:
            logger.error(f"Ошибка Groq (попытка {attempt}): {e}")
            time.sleep(GROQ_RETRY_DELAY)

    return None


# ──────────── FALLBACK (когда Groq недоступен) ────────────

FALLBACK_ANALYSES = [
    {
        "products": ["кефир 1% (просрочен)", "сосиски (2 шт, готовые)", "майонез (полпакета)", "луковица (сырая)"],
        "recipe": "Салат «Отчаяние по-холостяцки»: нарежь сосиски кружочками (1 мин). Лук — тонкими кольцами (2 мин). Выложи на тарелку, полей кефиром (30 сек). Сверху — щедрую шапку майонеза. Не перемешивай — это искусство, а не еда.",
        "calories": "1800 ккал — Гордон Рамзи бы заплакал, а ты съешь и не заметишь",
        "roast": "Твой холодильник как у Шелдона из Теории Большого взрыва — только у Шелдона хотя бы есть расписание приёмов пищи. Гордон Рамзи увидел бы это и ушёл в монастырь. Кефир просрочен? Зато он бесплатный, если не считать стоимость твоего достоинства.",
        "verdict": "ПОЗОР",
    },
    {
        "products": ["пиво Жигулёвское (3 банки)", "пиво Балтика 7 (2 банки)", "сырок «Дружба» (2 шт)", "хлеб белый (зачерствел)"],
        "recipe": "Коктейль «Пятничный философ»: открой банку пива (5 сек). Раскроши сырок прямо в банку (10 сек). Отломи хлеб и используй как ложку. Повтори 5 раз. Завтра не вспомнишь — в этом и суть.",
        "calories": "900 ккал — калории настоящего мужика в расцвете сил и с похмельем",
        "roast": "Это не холодильник, это бар «У Ашота» с одной закуской. Шварценеггер в Терминаторе питался лучше — и он был РОБОТ. Если бы овощи могли выбирать хозяина, они бы сбежали к соседу с дачей и теплицей.",
        "verdict": "ПОЗОР",
    },
    {
        "products": ["гречка (пакет, сырая)", "куриная грудка (замороженная)", "огурец свежий (2 шт)", "кетчуп Heinz"],
        "recipe": "«Фитнес-мечта ленивого»: разморозь грудку 2 часа (или кидай так — ты же ленивый). Свари гречку (15 мин). Обжарь грудку 7 мин с каждой стороны. Порежь огурец (1 мин). Полей всё кетчупом — потому что соусы это не чит, это стиль жизни.",
        "calories": "650 ккал — почти как у нормального человека, но с кетчупом",
        "roast": "О, кто-то пытается питаться правильно! Куриная грудка без кожи? Ты или очень здоровый, или очень грустный. Как мем «This is fine» с горящей собакой — вроде всё ок, но кетчуп на гречке говорит об обратном.",
        "verdict": "НОРМ",
    },
    {
        "products": ["брокколи (свежая)", "авокадо (спелый)", "йогурт греческий", "шпинат (пучок)", "лимон (1 шт)"],
        "recipe": "«Зелёный гуру смузи-боул»: брось брокколи, шпинат и авокадо в блендер (2 мин). Выжми лимон (30 сек). Добавь йогурт для текстуры. Взбей до однородности (1 мин). Выложи в бокал. Сфотографируй для Instagram. Ешь и чувствуй превосходство.",
        "calories": "320 ккал — ты живёшь на фотосинтезе и чувстве морального превосходства",
        "roast": "У тебя холодильник как у фитнес-блогера из Instagram. Один вопрос: тебе не скучно жить без майонеза? Ты как Дэн Хармони из мемов — все думают что ты страдаешь, но ты просто «осознанно питаешься».",
        "verdict": "ЗОЖНИК",
    },
    {
        "products": ["ничего", "свет от лампочки", "одиночество", "паутина (в углу)"],
        "recipe": "«Воздушный десерт»: открой холодильник (2 сек). Вдохни пустоту (3 сек). Закрой дверцу (1 сек). Вот и весь ужин. Десерт из воздуха — мишленовский шеф бы оценил минимализм.",
        "calories": "0 ккал — диета мечты каждого диетолога и кошмар твоей мамы",
        "roast": "Твой холодильник настолько пустой, что в нём живёт экзистенциальный кризис. Даже свет внутри — единственный гость. Это как мем «Empty refrigerator, empty soul» — только в жизни, и смеяться некому. Шрёдингер бы сказал: «Пока не открыл — там есть еда». Спойлер: нет.",
        "verdict": "СРОЧНО В МАГАЗИН",
    },
    {
        "products": ["торт Наполеон (целый)", "шоколадка Алёнка (надкусана)", "печенье Орео (пачка)", "мармелад (полкило)"],
        "recipe": "«Сахарный взрыв по-десертному»: раскроши Орео (1 мин). Наломай шоколадку кусочками (30 сек). Отрежь торт (10 сек). Перемешай всё руками (2 мин). Ешь без тарелки — тарелки для слабаков. Запей колой, если найдёшь.",
        "calories": "4200 ккал — дневная норма сахара за полгода, зато весело",
        "roast": "Это не холодильник, это кондитерская с одним посетителем — тобой. Поджелудочная уже написала заявление об увольнении. Ты как Гомер Симпсон — только у Гомера хотя бы есть Мардж, чтобы остановить. Твой стоматолог уже знает твой номер наизусть.",
        "verdict": "ПОЗОР",
    },
]


def generate_fallback_analysis() -> dict:
    """Возвращает рандомный pre-generated анализ, когда Groq недоступен."""
    return random.choice(FALLBACK_ANALYSES)


# ──────────── КЛАВИАТУРЫ ────────────


def get_premium_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⭐ Кинуть звезду", callback_data="donate_star"),
        InlineKeyboardButton("💎 Премиум-совет", callback_data="premium_tip"),
    )
    keyboard.add(
        InlineKeyboardButton("📊 Рейтинг позора", callback_data="rating"),
        InlineKeyboardButton("🔄 Ещё раз!", callback_data="roast_again"),
    )
    return keyboard


def get_roast_again_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔄 Ещё раз, пожёстче!", callback_data="roast_again"))
    return keyboard


# ──────────── ФОРМИРОВАНИЕ ОТВЕТА ────────────

EMOJI_MAP = {
    "ПОЗОР": "🤡",
    "НОРМ": "👍",
    "ЗОЖНИК": "🥗",
    "СРОЧНО В МАГАЗИН": "🏪",
}


def format_analysis(analysis: dict) -> str:
    verdict = analysis.get("verdict", "НУ ТАКОЕ")
    emoji = EMOJI_MAP.get(verdict, "❓")

    products = analysis.get("products", ["ничего"])
    products_str = ", ".join(products) if isinstance(products, list) else str(products)

    return (
        f"🍽️ *Диагноз:* {emoji} {verdict}\n\n"
        f"📦 *Что я вижу:*\n`{products_str}`\n\n"
        f"🍳 *Что приготовить:*\n{analysis.get('recipe', 'Пиццу закажи. Серьёзно.')}\n\n"
        f"🔥 *Калорийность:* {analysis.get('calories', 'магия')}\n\n"
        f"🎙️ *Вердикт:*\n_{analysis.get('roast', 'Жить будешь. Наверно.')}_\n\n"
        f"---\n⭐ _Кинь звезду — будет ещё смешнее_"
    )


# ──────────── ОБРАБОТЧИКИ КОМАНД ────────────


@bot.message_handler(commands=["start"])
def cmd_start(message):
    user = message.from_user.first_name
    welcome = (
        f"🍔 *{user}, добро пожаловать в холодильный ад!* 🥦\n\n"
        f"Я — трэш-диетолог. Пришли фото своего холодильника, "
        f"а я скажу, почему ты толстый и что из этого можно приготовить.\n\n"
        f"⚠️ *Дисклеймер:* Я даю абсурдные и нелепые советы. "
        f"Это рофл, а не диета.\n\n"
        f"📸 *Отправь фото холодильника* — получишь диагноз!\n\n"
        f"🎁 Бесплатно: {MAX_ANALYSES_PER_DAY} анализа в день. Дальше — за звёзды ⭐"
    )
    bot.send_message(message.chat.id, welcome)


@bot.message_handler(commands=["help"])
def cmd_help(message):
    help_text = (
        "🤖 *Как пользоваться:*\n\n"
        "1. Открой холодильник\n"
        "2. Сфоткай содержимое\n"
        "3. Отправь фото мне\n"
        "4. Получи порцию позора и странный рецепт\n\n"
        "*Команды:*\n"
        "/start — Приветствие\n"
        "/help — Эта справка\n"
        "/stats — Твоя статистика\n"
        "/history — Последние анализы\n\n"
        "Бот создан для смеха. Не ешьте то, что я советую 🙃"
    )
    bot.send_message(message.chat.id, help_text)


@bot.message_handler(commands=["stats"])
def cmd_stats(message):
    user_id = message.from_user.id
    count = get_analysis_count(user_id)
    remaining = max(0, MAX_ANALYSES_PER_DAY - count)

    stats = (
        f"📊 *Твоя статистика:*\n\n"
        f"Анализов сегодня: {count}/{MAX_ANALYSES_PER_DAY}\n"
        f"Осталось бесплатно: {remaining}\n\n"
        f"Всего в системе: {len(_user_analyses)} пользователей"
    )
    bot.send_message(message.chat.id, stats)


@bot.message_handler(commands=["history"])
def cmd_history(message):
    bot.send_message(
        message.chat.id,
        "📜 *История анализов*\n\n"
        "В этой версии история не сохраняется. "
        "В следующей версии будет база данных и полный лог всех твоих холодильников! 🔜",
    )


# ──────────── ОБРАБОТКА ФОТО ────────────


@bot.message_handler(content_types=["text"])
def handle_text(message):
    """Если прислали текст вместо фото."""
    bot.send_message(
        message.chat.id,
        "📸 Мне нужно **ФОТО**, а не текст!\n\n"
        "Открой холодильник, сфоткай содержимое и отправь мне. "
        "Я не умею анализировать тексты, но могу judging по фото 👀",
    )


@bot.message_handler(content_types=["sticker", "animation"])
def handle_sticker(message):
    """Если прислали стикер или GIF."""
    bot.send_message(
        message.chat.id,
        "😑 Милый стикер, но мне нужно **ФОТО ХОЛОДИЛЬНИКА**.\n\n"
        "Не стикер холодильника. Не эмодзи 🧊. Реальное фото содержимого. Открой и сфоткай!",
    )


@bot.message_handler(content_types=["video", "video_note"])
def handle_video(message):
    """Если прислали видео."""
    bot.send_message(
        message.chat.id,
        "🎬 Видео — это круто, но мне нужен **КАДР**.\n\n"
        "Сделай скриншот видео или просто сфоткай холодильник на фото. "
        "Мой ИИ не умеет смотреть видео (пока что) 📹",
    )


@bot.message_handler(content_types=["document"])
def handle_document(message):
    """Если прислали документ."""
    bot.send_message(
        message.chat.id,
        "📎 Документ? Серьёзно? Мне нужно **ФОТО ХОЛОДИЛЬНИКА**.\n\n"
        "Не файл, не PDF, не документ. Фото. Содержимого. Холодильника. 🧊📸",
    )


@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    user_id = message.from_user.id

    # Проверка лимита
    count = get_analysis_count(user_id)
    if count >= MAX_ANALYSES_PER_DAY:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("⭐ Купить +5 анализов (3 звезды)", callback_data="buy_analyses"))
        bot.send_message(
            message.chat.id,
            f"🚫 *Лимит исчерпан!*\n\n"
            f"Ты уже сделал {count} анализов сегодня. "
            f"Бесплатно можно {MAX_ANALYSES_PER_DAY}.\n\n"
            f"Хочешь ещё? Кинь 3 звезды!",
            reply_markup=keyboard,
        )
        return

    # Скачиваем фото
    photo_file = message.photo[-1]  # Наивысшее качество
    file_info = bot.get_file(photo_file.file_id)

    try:
        downloaded_file = bot.download_file(file_info.file_path)
    except Exception as e:
        logger.error(f"Ошибка скачивания фото: {e}")
        bot.send_message(message.chat.id, "❌ Не смог скачать фото. Попробуй ещё раз!")
        return

    # Валидация
    if not is_photo_valid(downloaded_file):
        bot.send_message(
            message.chat.id,
            "🖼️ *Это не фото холодильника!*\n\n"
            "Фото слишком маленькое или битое. "
            "Сфоткай нормально и отправь снова.",
        )
        return

    # Typing indicator
    bot.send_chat_action(message.chat.id, "typing")
    time.sleep(min(TYPING_TIMEOUT, 10))

    status_msg = bot.send_message(
        message.chat.id,
        random.choice(ANALYSIS_PHRASES),
    )

    # Вызов Groq
    analysis = call_groq_with_retry(downloaded_file)

    # Fallback если Groq недоступен
    if analysis is None:
        logger.info("Groq недоступен — использую fallback")
        analysis = generate_fallback_analysis()

    # Формируем и отправляем ответ
    response = format_analysis(analysis)

    # Увеличиваем счётчик
    increment_analysis_count(user_id)

    try:
        bot.edit_message_text(
            response,
            message.chat.id,
            status_msg.message_id,
            reply_markup=get_premium_keyboard(),
        )
    except Exception:
        bot.send_message(
            message.chat.id,
            response,
            reply_markup=get_premium_keyboard(),
        )


# ──────────── CALLBACK (КНОПКИ) ────────────


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    bot.answer_callback_query(call.id)

    if call.data == "donate_star":
        bot.send_invoice(
            call.message.chat.id,
            title="⭐ Звезда для трэш-диетолога",
            description="Спасибо за поддержку! Это просто донат, без доп. функций 😄",
            payload="donate_star_001",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="Звезда благодарности", amount=1)],
        )

    elif call.data == "premium_tip":
        premium_text = (
            "💎 *ПРЕМИУМ-СОВЕТ ДНЯ* 💎\n\n"
            "Чтобы похудеть к лету, нужно:\n"
            "1. Выбросить всё из холодильника\n"
            "2. Заклеить дверцу скотчем\n"
            "3. Смотреть TikTok с фитоняшками 8 часов в день\n\n"
            "🤡 *Это шутка. Не делайте так.*\n\n"
            "Хочешь реальный совет? Задонать создателю на кофе ☕"
        )
        bot.send_message(call.message.chat.id, premium_text)

    elif call.data == "rating":
        rating_text = (
            "📊 *Рейтинг позора холодильников:*\n\n"
            "🥇 Пустой холодильник с майонезом — 500 очков позора\n"
            "🥈 Три банки пива и вчерашняя гречка — 350 очков\n"
            "🥉 Овощи и курица — 0 очков, но скучно же\n\n"
            "Отправь фото в чат с друзьями и сравни!"
        )
        bot.send_message(call.message.chat.id, rating_text)

    elif call.data == "roast_again":
        bot.send_message(call.message.chat.id, "🔄 *Перезапускаю генератор язвительности...*")
        bot.send_message(
            call.message.chat.id,
            "😈 *Дополнительный вердикт:*\n\n"
            + random.choice([
                "Этот холодильник — преступление против кулинарии. Ты счастливчик, что я не вызываю полицию нравов.",
                "Мой ИИ чуть не сгорел от стыда, анализируя это. Ты монстр. Но я уважаю твой стиль.",
                "Если бы холодильники могли плакать, этот рыдал бы от твоего отношения к продуктам.",
                "Твои продукты смотрят на тебя с осуждением. И они правы.",
                "Я видел вещи. Вещи, которые не должен видеть ни один диетолог. Ни один ИИ.",
            ]),
        )

    elif call.data == "buy_analyses":
        bot.send_invoice(
            call.message.chat.id,
            title="⭐ +5 анализов холодильника",
            description="Ещё 5 бесплатных анализов на сегодня. Трать с умом (или без)",
            payload="buy_5_analyses",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label="5 анализов", amount=3)],
        )


# ──────────── ОБРАБОТКА ОПЛАТЫ ────────────


@bot.pre_checkout_query_handler(func=lambda query: True)
def handle_pre_checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@bot.message_handler(func=lambda m: m.successful_payment is not None)
def handle_successful_payment(message):
    payment = message.successful_payment
    payload = payment.invoice_payload

    if payload == "donate_star_001":
        bot.send_message(message.chat.id, "⭐ *Спасибо за звезду!* Ты легенда 🫡")
    elif payload == "buy_5_analyses":
        user_id = message.from_user.id
        if user_id in _user_analyses:
            _user_analyses[user_id]["count"] -= 5
        bot.send_message(
            message.chat.id,
            "🎉 *+5 анализов активировано!*\n\n"
            "Теперь можешь мучить свой холодильник ещё 5 раз. Удачи!",
        )
    else:
        bot.send_message(message.chat.id, "✅ Оплата прошла! Спасибо 🙏")

    logger.info(f"Оплата от {message.from_user.id}: {payload}, сумма: {payment.total_amount} {payment.currency}")


# ──────────── ЗАПУСК ────────────


if __name__ == "__main__":
    print("🍔 Трэш-диетолог запущен!")
    print(f"🧠 Модель: Groq {GROQ_MODEL}")
    print(f"📊 Бесплатных анализов/день: {MAX_ANALYSES_PER_DAY}")
    print("🤖 Жду фото холодильников...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
