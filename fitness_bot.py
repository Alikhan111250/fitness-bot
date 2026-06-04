"""
Фитнес-Расписание — Telegram Бот
Запуск: python fitness_bot.py
"""

import os
import json
import base64
import logging
from io import BytesIO
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.error import TelegramError

# ─────────────────────────────────────────────
# ТОКЕН — вставьте свой токен от @BotFather
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8607739583:AAGIWYXZBdJFW0Uil__NTIwmDL9e2lbd8Zc")
BOOKINGS_FILE = os.environ.get("BOOKINGS_FILE", "bookings.json")
SCHEDULE_IMAGE_FILE = os.environ.get("SCHEDULE_IMAGE_FILE", "schedule.jpg")
SCHEDULE_IMAGE_BASE64_FILE = os.environ.get("SCHEDULE_IMAGE_BASE64_FILE", "schedule_image.b64")
NOTIFY_CHAT_IDS = [
    int(chat_id.strip())
    for chat_id in os.environ.get("NOTIFY_CHAT_IDS", "").split(",")
    if chat_id.strip().lstrip("-").isdigit()
]
INSTRUCTOR_CHAT_IDS = {}
for _item in os.environ.get("INSTRUCTOR_CHAT_IDS", "").split(","):
    if ":" not in _item:
        continue
    _name, _chat_id = _item.split(":", 1)
    if _chat_id.strip().lstrip("-").isdigit():
        INSTRUCTOR_CHAT_IDS[_name.strip()] = int(_chat_id.strip())

# ─────────────────────────────────────────────
# Логирование
# ─────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s │ %(levelname)s │ %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Данные расписания
# день: 0=Пн, 1=Вт, 2=Ср, 3=Чт, 4=Пт, 5=Сб
# ─────────────────────────────────────────────
_RAW_EVENTS = [
    # Понедельник
    {"id": 1,  "day": 0, "title": "Кинезиофитнес", "description": "Любовь",      "timeRange": ["08:30", "09:30"]},
    {"id": 2,  "day": 0, "title": "ЭроТреверс",    "description": "Айгерим",     "timeRange": ["10:00", "11:30"]},
    {"id": 3,  "day": 0, "title": "ЭроТревис",     "description": "Айгерим",     "timeRange": ["18:30", "20:00"]},
    # Вторник
    {"id": 4,  "day": 1, "title": "Шейпинг",        "description": "Наталья",     "timeRange": ["07:30", "08:30"]},
    {"id": 5,  "day": 1, "title": "Зумба",          "description": "Аннастасия",  "timeRange": ["08:30", "09:30"]},
    {"id": 6,  "day": 1, "title": "Суставная Йога", "description": "Наталья",     "timeRange": ["17:00", "18:00"]},
    {"id": 12, "day": 1, "title": "Шейпинг",        "description": "Наталья",     "timeRange": ["18:00", "19:00"]},
    {"id": 7,  "day": 1, "title": "Шейпинг",        "description": "Наталья",     "timeRange": ["19:00", "20:00"]},
    # Среда
    {"id": 9,  "day": 2, "title": "Кинезиофитнес", "description": "Любовь",      "timeRange": ["08:00", "09:00"]},
    {"id": 10, "day": 2, "title": "ЭроТревис",     "description": "Айгерим",     "timeRange": ["18:30", "20:00"]},
    # Четверг
    {"id": 11, "day": 3, "title": "Шейпинг",       "description": "Наталья",     "timeRange": ["07:30", "08:30"]},
    {"id": 13, "day": 3, "title": "Шейпинг",       "description": "Наталья",     "timeRange": ["18:00", "19:00"]},
    {"id": 14, "day": 3, "title": "Шейпинг",       "description": "Наталья",     "timeRange": ["19:00", "20:00"]},
    # Пятница
    {"id": 15, "day": 4, "title": "Кинезиофитнес", "description": "Любовь",      "timeRange": ["08:30", "09:30"]},
    {"id": 16, "day": 4, "title": "ЭроТреверс",    "description": "Айгерим",     "timeRange": ["10:00", "11:30"]},
    # Суббота
    {"id": 17, "day": 5, "title": "Лимфодренаж",   "description": "",            "timeRange": ["07:30", "08:30"]},
    {"id": 18, "day": 5, "title": "ХатхаЙога",     "description": "Наталья",     "timeRange": ["09:00", "10:00"]},
    {"id": 19, "day": 5, "title": "Суставная Йога", "description": "Наталья",    "timeRange": ["10:00", "11:00"]},
]

SCHEDULE_DATA: dict[int, list[dict]] = {}
for _e in _RAW_EVENTS:
    SCHEDULE_DATA.setdefault(_e["day"], []).append(_e)
for _d in SCHEDULE_DATA.values():
    _d.sort(key=lambda x: x["timeRange"][0])

ALL_CLASS_TITLES: list[str] = sorted({e["title"] for e in _RAW_EVENTS})
EVENT_BY_ID: dict[int, dict] = {e["id"]: e for e in _RAW_EVENTS}
CLASS_ID_TO_TITLE: dict[int, str] = {
    idx: title for idx, title in enumerate(ALL_CLASS_TITLES, start=1)
}
TITLE_TO_CLASS_ID: dict[str, int] = {
    title: idx for idx, title in CLASS_ID_TO_TITLE.items()
}

# ─────────────────────────────────────────────
# Дни недели
# Python weekday(): 0=Пн … 6=Вс
# Наш schedule day:  0=Пн, 1=Вт, 2=Ср, 3=Чт, 4=Пт, 5=Сб
# ─────────────────────────────────────────────
_PYTHON_TO_SCHEDULE = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}

DAY_NAMES = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}
DAY_SHORT = {0: "Пн", 1: "Вт", 2: "Ср", 3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"}
ACTIVE_DAYS = sorted(SCHEDULE_DATA.keys())  # [0,1,2,3,4,5]

# ── Inline-кнопки меню ──
def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Сегодня", callback_data="nav:today"),
            InlineKeyboardButton("🗓 Вся неделя", callback_data="nav:week"),
        ],
        [
            InlineKeyboardButton("Пн", callback_data="nav:day:0"),
            InlineKeyboardButton("Вт", callback_data="nav:day:1"),
            InlineKeyboardButton("Ср", callback_data="nav:day:2"),
        ],
        [
            InlineKeyboardButton("Чт", callback_data="nav:day:3"),
            InlineKeyboardButton("Пт", callback_data="nav:day:4"),
            InlineKeyboardButton("Сб", callback_data="nav:day:5"),
        ],
        [
            InlineKeyboardButton("📝 Записаться", callback_data="nav:signup"),
            InlineKeyboardButton("📌 Мои занятия", callback_data="nav:mybookings"),
        ],
    ])

# ─────────────────────────────────────────────
# Хранилище пользователей (in-memory)
# ─────────────────────────────────────────────

def _ensure_user(context, user_id: int) -> None:
    context.bot_data.setdefault("users", {}).setdefault(user_id, {})

def _add_booking(context, user_id: int, booking: dict) -> None:
    users = context.bot_data.setdefault("users", {})
    users.setdefault(user_id, {}).setdefault("bookings", []).append(booking)
    context.bot_data.setdefault("bookings", []).append(booking)
    _save_bookings(context.bot_data["bookings"])

def _user_registered(context, user_id: int) -> bool:
    return user_id in context.bot_data.setdefault("users", {})

def _load_bookings() -> list[dict]:
    if not os.path.exists(BOOKINGS_FILE):
        return []
    try:
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Не удалось загрузить записи: %s", exc)
        return []
    return data if isinstance(data, list) else []

def _save_bookings(bookings: list[dict]) -> None:
    try:
        with open(BOOKINGS_FILE, "w", encoding="utf-8") as file:
            json.dump(bookings, file, ensure_ascii=False, indent=2)
    except OSError as exc:
        logger.warning("Не удалось сохранить записи: %s", exc)

def _delete_booking(context, user_id: int, booking_index: int):
    user_bookings = _user_bookings(context, user_id)
    if booking_index < 0 or booking_index >= len(user_bookings):
        return None

    removed = user_bookings[booking_index]
    bookings = context.bot_data.setdefault("bookings", [])
    try:
        bookings.remove(removed)
    except ValueError:
        return None

    user_data = context.bot_data.setdefault("users", {}).setdefault(user_id, {})
    if "bookings" in user_data:
        try:
            user_data["bookings"].remove(removed)
        except ValueError:
            pass

    _save_bookings(bookings)
    return removed

# ─────────────────────────────────────────────
# Форматирование
# ─────────────────────────────────────────────

def _emoji_for_class(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["йога", "хатха"]):            return "🔵"
    if any(k in t for k in ["шейпинг", "зумба"]):         return "🟡"
    if any(k in t for k in ["кинезио", "лимфо"]):         return "✅"
    if any(k in t for k in ["эро", "треверс", "тревис"]): return "🟣"
    return "💪"

def _duration_str(start: str, end: str) -> str:
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    total = (eh * 60 + em) - (sh * 60 + sm)
    h, m = divmod(total, 60)
    if h and m: return f"{h}ч {m}м"
    if h:       return f"{h}ч"
    return f"{m}м"

def _format_event(ev: dict) -> str:
    s, e = ev["timeRange"]
    emoji = _emoji_for_class(ev["title"])
    dur = _duration_str(s, e)
    instructor = ev.get("description", "").strip()
    instr = f" │ 👤 *{instructor}*" if instructor else ""
    return f"{emoji} 🕒 *{s}–{e}* │ *{ev['title']}*{instr} │ ⏱ _{dur}_"

def _day_text(day_index: int, filter_titles: set = None) -> str:
    name = DAY_NAMES.get(day_index, f"День {day_index}")
    events = SCHEDULE_DATA.get(day_index, [])
    if filter_titles is not None:
        events = [e for e in events if e["title"] in filter_titles]
    if not events:
        hint = "\n_Попробуйте выбрать другое занятие в «📝 Записаться»._" if filter_titles else ""
        return f"📅 *{name}*\n\n_Занятий не запланировано._" + hint
    lines = [f"📅 *{name}*\n"]
    lines += [_format_event(ev) for ev in events]
    return "\n".join(lines)

def _event_choice_text(ev: dict) -> str:
    s, e = ev["timeRange"]
    return f"{DAY_SHORT[ev['day']]} {s}–{e}"

def _booking_text(ev: dict) -> str:
    s, e = ev["timeRange"]
    instructor = ev.get("description", "").strip() or "не указан"
    return (
        "📝 *Запись на занятие*\n\n"
        f"{_emoji_for_class(ev['title'])} *{ev['title']}*\n"
        f"📅 *{DAY_NAMES[ev['day']]}*\n"
        f"🕒 *{s}–{e}*\n"
        f"👤 *{instructor}*"
    )

def _signup_classes_text() -> str:
    return "📝 *Записаться*\n\nВыберите занятие:"

def _signup_times_text(title: str) -> str:
    return f"📝 *{title}*\n\nВыберите день и время:"

def _user_bookings(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> list[dict]:
    bookings = context.bot_data.setdefault("bookings", [])
    user_bookings = [b for b in bookings if b.get("user_id") == user_id]
    user_bookings.sort(key=lambda b: (b.get("day", 99), b.get("time", ""), b.get("created_at", "")))
    return user_bookings

def _my_bookings_text(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    bookings = _user_bookings(context, user_id)
    if not bookings:
        return (
            "📌 *Мои занятия*\n\n"
            "_Вы пока никуда не записаны._\n\n"
            "Нажмите *Записаться*, чтобы выбрать занятие, день и время."
        )

    lines = ["📌 *Мои занятия*\n"]
    for idx, booking in enumerate(bookings, start=1):
        day = DAY_NAMES.get(booking.get("day"), "День не указан")
        class_title = booking.get("class_title", "Занятие")
        time_range = booking.get("time", "время не указано")
        ev = EVENT_BY_ID.get(booking.get("event_id"))
        instructor = ev.get("description", "").strip() if ev else ""
        instructor_line = f"\n   👤 {instructor}" if instructor else ""
        lines.append(
            f"{idx}. {_emoji_for_class(class_title)} *{class_title}*\n"
            f"   📅 {day}\n"
            f"   🕒 {time_range}"
            f"{instructor_line}"
        )
    return "\n\n".join(lines)

def _my_bookings_kb(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for idx, booking in enumerate(_user_bookings(context, user_id), start=1):
        class_title = booking.get("class_title", "Занятие")
        day = DAY_SHORT.get(booking.get("day"), "")
        time_range = booking.get("time", "")
        rows.append([InlineKeyboardButton(
            f"❌ Удалить {idx}: {day} {time_range} {class_title}",
            callback_data=f"booking:remove:{idx - 1}",
        )])
    rows.append([InlineKeyboardButton("📝 Записаться ещё", callback_data="nav:signup")])
    rows.append([InlineKeyboardButton("← Назад в меню", callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)

def _signup_classes_kb() -> InlineKeyboardMarkup:
    rows = []
    for class_id, title in CLASS_ID_TO_TITLE.items():
        rows.append([InlineKeyboardButton(
            f"{_emoji_for_class(title)} {title}",
            callback_data=f"signup:class:{class_id}",
        )])
    rows.append([InlineKeyboardButton("← Назад в меню", callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)

def _signup_times_kb(title: str) -> InlineKeyboardMarkup:
    rows = []
    events = [ev for ev in _RAW_EVENTS if ev["title"] == title]
    events.sort(key=lambda ev: (ev["day"], ev["timeRange"][0]))
    for ev in events:
        rows.append([InlineKeyboardButton(
            _event_choice_text(ev),
            callback_data=f"signup:event:{ev['id']}",
        )])
    rows.append([InlineKeyboardButton("← Выбрать другое занятие", callback_data="nav:signup")])
    rows.append([InlineKeyboardButton("← Назад в меню", callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)

def _confirm_booking_kb(event_id: int) -> InlineKeyboardMarkup:
    ev = EVENT_BY_ID[event_id]
    class_id = TITLE_TO_CLASS_ID[ev["title"]]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить запись", callback_data=f"signup:confirm:{event_id}")],
        [InlineKeyboardButton("← Выбрать другое время", callback_data=f"signup:class:{class_id}")],
        [InlineKeyboardButton("← Назад в меню", callback_data="nav:home")],
    ])

def _after_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Мои занятия", callback_data="nav:mybookings")],
        [InlineKeyboardButton("📝 Записаться ещё", callback_data="nav:signup")],
        [InlineKeyboardButton("← Назад в меню", callback_data="nav:home")],
    ])

def _booking_notice_text(user, ev: dict) -> str:
    s, e = ev["timeRange"]
    username = f"@{user.username}" if user.username else "без username"
    return (
        "Новая запись на занятие\n\n"
        f"Клиент: {user.full_name} ({username})\n"
        f"Telegram ID: {user.id}\n"
        f"Занятие: {ev['title']}\n"
        f"День: {DAY_NAMES[ev['day']]}\n"
        f"Время: {s}–{e}\n"
        f"Инструктор: {ev.get('description', '').strip() or 'не указан'}"
    )

def _today_day() -> int:
    return _PYTHON_TO_SCHEDULE.get(datetime.now().weekday(), 0)

# ─────────────────────────────────────────────
# Экраны бота
# ─────────────────────────────────────────────

def _home_text(name: str = "друг") -> str:
    return (
        f"👋 Привет, *{name}*!\n\n"
        "🏋️ *Фитнес-Расписание*\n\n"
        "Выберите действие кнопками ниже:"
    )

def _view_text(view: str, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    if view == "today":
        return _day_text(_today_day())
    if view.startswith("day:"):
        return _day_text(int(view.split(":", 1)[1]))
    if view == "mybookings":
        return _my_bookings_text(context, user_id)
    return _home_text()

def _plain(text: str) -> str:
    return text.replace("*", "").replace("_", "")

async def _edit_screen(query, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    text = _plain(text)
    try:
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
        )
    except Exception as exc:
        if "Message is not modified" in str(exc):
            return
        try:
            await query.message.delete()
            await query.message.chat.send_message(
                text=text,
                reply_markup=reply_markup,
            )
        except Exception:
            raise exc

def _schedule_photo():
    if os.path.exists(SCHEDULE_IMAGE_FILE):
        return open(SCHEDULE_IMAGE_FILE, "rb")
    if not os.path.exists(SCHEDULE_IMAGE_BASE64_FILE):
        return None
    try:
        with open(SCHEDULE_IMAGE_BASE64_FILE, "r", encoding="ascii") as image_file:
            image_data = base64.b64decode(image_file.read())
    except (OSError, ValueError) as exc:
        logger.warning("Не удалось загрузить картинку расписания: %s", exc)
        return None
    photo = BytesIO(image_data)
    photo.name = SCHEDULE_IMAGE_FILE
    return photo

async def _show_week_image(query) -> None:
    photo = _schedule_photo()
    if photo is None:
        await _edit_screen(
            query,
            "🗓 *Вся неделя*\n\n_Картинка расписания не найдена._",
            _main_menu_kb(),
        )
        return

    try:
        await query.message.delete()
    except Exception as exc:
        logger.warning("Не удалось удалить старое сообщение: %s", exc)

    try:
        with photo:
            await query.message.chat.send_photo(
                photo=photo,
                caption="🗓 Вся неделя",
                reply_markup=_main_menu_kb(),
            )
    except TelegramError as exc:
        logger.exception("Не удалось отправить картинку расписания: %s", exc)
        await query.message.chat.send_message(
            text="🗓 Вся неделя\n\nКартинка расписания временно не отправилась. Попробуйте нажать ещё раз.",
            reply_markup=_main_menu_kb(),
        )

async def _notify_booking(context: ContextTypes.DEFAULT_TYPE, user, ev: dict) -> int:
    recipients = set(NOTIFY_CHAT_IDS)
    instructor = ev.get("description", "").strip()
    if instructor in INSTRUCTOR_CHAT_IDS:
        recipients.add(INSTRUCTOR_CHAT_IDS[instructor])

    sent = 0
    text = _booking_notice_text(user, ev)
    for chat_id in recipients:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            sent += 1
        except Exception as exc:
            logger.warning("Не удалось отправить уведомление %s: %s", chat_id, exc)
    return sent

async def _remove_old_reply_keyboard(update: Update) -> None:
    if update.message:
        cleanup_message = await update.message.reply_text(
            "Нижнее меню убрано.",
            reply_markup=ReplyKeyboardRemove(),
        )
        try:
            await cleanup_message.delete()
        except Exception as exc:
            logger.warning("Не удалось удалить служебное сообщение: %s", exc)

# ─────────────────────────────────────────────
# Обработчики команд
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "друг"
    if not _user_registered(context, user_id):
        _ensure_user(context, user_id)
    await _remove_old_reply_keyboard(update)
    await update.message.reply_text(
        _plain(_home_text(name)),
        reply_markup=_main_menu_kb(),
    )

async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Ошибка обработчика Telegram", exc_info=context.error)
    if isinstance(update, Update) and update.callback_query:
        try:
            await update.callback_query.answer(
                "Произошла ошибка. Нажмите /start и попробуйте ещё раз.",
                show_alert=True,
            )
        except Exception as exc:
            logger.warning("Не удалось показать ошибку пользователю: %s", exc)

# ─────────────────────────────────────────────
# Callback — навигация и запись на занятия
# ─────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    user_id = query.from_user.id

    if data.startswith("nav:"):
        view = data[len("nav:"):]
        if not _user_registered(context, user_id):
            _ensure_user(context, user_id)

        if view == "home":
            name = query.from_user.first_name or "друг"
            await _edit_screen(query, _home_text(name), _main_menu_kb())
            return

        if view == "signup":
            await _edit_screen(query, _signup_classes_text(), _signup_classes_kb())
            return

        if view == "week":
            await _show_week_image(query)
            return

        if view == "mybookings":
            await _edit_screen(
                query,
                _my_bookings_text(context, user_id),
                _my_bookings_kb(context, user_id),
            )
            return

        text = _view_text(view, context, user_id)
        if len(text) > 4000:
            await query.answer("Слишком длинное сообщение для Telegram.", show_alert=True)
            return
        await _edit_screen(query, text, _main_menu_kb())
        return

    if data.startswith("signup:class:"):
        class_id = int(data[len("signup:class:"):])
        title = CLASS_ID_TO_TITLE.get(class_id)
        if not title:
            await query.answer("Занятие не найдено.", show_alert=True)
            return
        await _edit_screen(query, _signup_times_text(title), _signup_times_kb(title))
        return

    if data.startswith("signup:event:"):
        event_id = int(data[len("signup:event:"):])
        ev = EVENT_BY_ID.get(event_id)
        if not ev:
            await query.answer("Время не найдено.", show_alert=True)
            return
        await _edit_screen(query, _booking_text(ev), _confirm_booking_kb(event_id))
        return

    if data.startswith("signup:confirm:"):
        event_id = int(data[len("signup:confirm:"):])
        ev = EVENT_BY_ID.get(event_id)
        if not ev:
            await query.answer("Запись не найдена.", show_alert=True)
            return

        s, e = ev["timeRange"]
        booking = {
            "user_id": user_id,
            "user_name": query.from_user.full_name,
            "username": query.from_user.username,
            "event_id": event_id,
            "class_title": ev["title"],
            "day": ev["day"],
            "time": f"{s}–{e}",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _add_booking(context, user_id, booking)
        await _edit_screen(
            query,
            "✅ *Вы записаны!*\n\n" + _booking_text(ev).replace("📝 *Запись на занятие*\n\n", ""),
            _after_booking_kb(),
        )
        await _notify_booking(context, query.from_user, ev)
        return

    if data.startswith("booking:remove:"):
        booking_index = int(data[len("booking:remove:"):])
        removed = _delete_booking(context, user_id, booking_index)
        if not removed:
            await query.answer("Запись не найдена.", show_alert=True)
            return
        await _edit_screen(
            query,
            "✅ *Запись удалена.*\n\n" + _my_bookings_text(context, user_id),
            _my_bookings_kb(context, user_id),
        )
        return

    await query.answer("⚠️ Неизвестное действие.", show_alert=True)

# ─────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────

def main() -> None:
    if BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE": 
        raise RuntimeError("Вставьте токен бота в переменную BOT_TOKEN в начале файла!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["bookings"] = _load_bookings()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(handle_error)

    logger.info("Бот запущен… Ctrl-C для остановки.")
    app.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
