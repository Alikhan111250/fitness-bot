"""
Фитнес-Расписание — Telegram Бот
Запуск: python fitness_bot.py
"""

import os
import json
import logging
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

# ─────────────────────────────────────────────
# ТОКЕН — вставьте свой токен от @BotFather
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8607739583:AAGIWYXZBdJFW0Uil__NTIwmDL9e2lbd8Zc")
BOOKINGS_FILE = os.environ.get("BOOKINGS_FILE", "bookings.json")
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
# день: 0=Вс, 1=Пн, 2=Вт, 3=Ср, 4=Чт, 5=Пт, 6=Сб
# ─────────────────────────────────────────────
_RAW_EVENTS = [
    # Воскресенье
    {"id": 1,  "day": 0, "title": "Кинезиофитнес", "description": "Любовь",     "timeRange": ["08:30", "09:30"]},
    {"id": 2,  "day": 0, "title": "ЭроТреверс",    "description": "Айгерим",    "timeRange": ["10:00", "11:30"]},
    {"id": 3,  "day": 0, "title": "ЭроТревис",     "description": "Айгерим",    "timeRange": ["18:30", "20:00"]},
    # Понедельник
    {"id": 4,  "day": 1, "title": "Кинезиофитнес", "description": "Любовь",     "timeRange": ["08:30", "09:30"]},
    {"id": 5,  "day": 1, "title": "ЭроТреверс",    "description": "Айгерим",    "timeRange": ["10:00", "11:30"]},
    {"id": 6,  "day": 1, "title": "ЭроТревис",     "description": "Айгерим",    "timeRange": ["18:30", "20:00"]},
    # Вторник
    {"id": 7,  "day": 2, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["07:30", "08:30"]},
    {"id": 8,  "day": 2, "title": "Зумба",           "description": "Аннастасия","timeRange": ["08:30", "09:30"]},
    {"id": 9,  "day": 2, "title": "Суставная Йога",  "description": "Наталья",    "timeRange": ["17:00", "18:00"]},
    {"id": 10, "day": 2, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["18:00", "19:00"]},
    {"id": 11, "day": 2, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["19:00", "20:00"]},
    # Среда
    {"id": 12, "day": 3, "title": "Кинезиофитнес",  "description": "Любовь",     "timeRange": ["08:00", "09:00"]},
    {"id": 13, "day": 3, "title": "ЭроТревис",      "description": "Айгерим",    "timeRange": ["18:30", "20:00"]},
    # Четверг
    {"id": 14, "day": 4, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["07:30", "08:30"]},
    {"id": 15, "day": 4, "title": "Кинезиофитнес",  "description": "Любовь",     "timeRange": ["08:30", "09:30"]},
    {"id": 16, "day": 4, "title": "ЭроТреверс",     "description": "Айгерим",    "timeRange": ["10:00", "11:30"]},
    {"id": 17, "day": 4, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["18:00", "19:00"]},
    {"id": 18, "day": 4, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["19:00", "20:00"]},
    # Пятница
    {"id": 19, "day": 5, "title": "Кинезиофитнес",  "description": "Любовь",     "timeRange": ["08:30", "09:30"]},
    {"id": 20, "day": 5, "title": "ЭроТреверс",     "description": "Айгерим",    "timeRange": ["10:00", "11:30"]},
    # Суббота
    {"id": 21, "day": 6, "title": "Лимфодренаж",    "description": "",            "timeRange": ["07:30", "08:30"]},
    {"id": 22, "day": 6, "title": "ХатхаЙога",      "description": "Наталья",    "timeRange": ["09:00", "10:00"]},
    {"id": 23, "day": 6, "title": "Суставная Йога",  "description": "Наталья",    "timeRange": ["10:00", "11:00"]},
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
# Наш schedule day:  0=Вс, 1=Пн, 2=Вт, 3=Ср, 4=Чт, 5=Пт, 6=Сб
# ─────────────────────────────────────────────
_PYTHON_TO_SCHEDULE = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}

DAY_NAMES = {
    0: "Воскресенье",
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
}
DAY_SHORT = {0: "Вс", 1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб"}
ACTIVE_DAYS = sorted(SCHEDULE_DATA.keys())  # [0,1,2,3,4,5,6]

# ── Inline-кнопки меню ──
def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Сегодня", callback_data="nav:today"),
            InlineKeyboardButton("🗓 Вся неделя", callback_data="nav:week"),
        ],
        [
            InlineKeyboardButton("Пн", callback_data="nav:day:1"),
            InlineKeyboardButton("Вт", callback_data="nav:day:2"),
            InlineKeyboardButton("Ср", callback_data="nav:day:3"),
        ],
        [
            InlineKeyboardButton("Чт", callback_data="nav:day:4"),
            InlineKeyboardButton("Пт", callback_data="nav:day:5"),
            InlineKeyboardButton("Сб", callback_data="nav:day:6"),
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

def _clip(text: str, width: int) -> str:
    if len(text) <= width:
        return text.ljust(width)
    return text[:max(0, width - 1)] + "…"

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

def _week_text(filter_titles: set = None) -> str:
    sections = []
    for day_idx in ACTIVE_DAYS:
        events = SCHEDULE_DATA.get(day_idx, [])
        if filter_titles is not None:
            events = [e for e in events if e["title"] in filter_titles]
        if not events:
            continue

        lines = [f"*{DAY_NAMES[day_idx]}*"]
        lines.append("┌─────────────┬────────────────────┐")
        lines.append("│ Время       │ Занятие            │")
        lines.append("├─────────────┼────────────────────┤")
        for ev in events:
            s, e = ev["timeRange"]
            title = f"{_emoji_for_class(ev['title'])} {ev['title']}"
            instructor = ev.get("description", "").strip()
            if instructor:
                title = f"{title}, {instructor}"
            lines.append(f"│ {_clip(f'{s}-{e}', 11)} │ {_clip(title, 18)} │")
        lines.append("└─────────────┴────────────────────┘")
        sections.append("\n".join(lines))

    if not sections:
        return "🗓 *Вся неделя*\n\n_Занятий не найдено._"
    return "🗓 *Вся неделя*\n\n" + "\n\n".join(sections)

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
    if view == "week":
        return _week_text()
    if view.startswith("day:"):
        return _day_text(int(view.split(":", 1)[1]))
    if view == "mybookings":
        return _my_bookings_text(context, user_id)
    return _home_text()

async def _edit_screen(query, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    try:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except Exception as exc:
        if "Message is not modified" not in str(exc):
            raise

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
        await update.message.reply_text(
            "Нижнее меню убрано.",
            reply_markup=ReplyKeyboardRemove(),
        )

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
        _home_text(name),
        parse_mode="Markdown",
        reply_markup=_main_menu_kb(),
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _remove_old_reply_keyboard(update)
    await update.message.reply_text(
        "🤖 *Помощь*\n\n"
        "Всё управление через кнопки под сообщением.\n\n"
        "📅 Сегодня — расписание на сегодня\n"
        "🗓 Вся неделя — все дни сразу\n"
        "Пн / Вт / Ср / Чт / Пт / Сб — конкретный день\n"
        "📝 Записаться — выбрать занятие, день и время\n"
        "📌 Мои занятия — ваши записи",
        parse_mode="Markdown",
        reply_markup=_main_menu_kb(),
    )

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
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Бот запущен… Ctrl-C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
    {"id": 5,  "day": 1, "title": "ЭроТреверс",    "description": "Айгерим",    "timeRange": ["10:00", "11:30"]},
    {"id": 6,  "day": 1, "title": "ЭроТревис",     "description": "Айгерим",    "timeRange": ["18:30", "20:00"]},
    # Вторник
    {"id": 7,  "day": 2, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["07:30", "08:30"]},
    {"id": 8,  "day": 2, "title": "Зумба",           "description": "Аннастасия","timeRange": ["08:30", "09:30"]},
    {"id": 9,  "day": 2, "title": "Суставная Йога",  "description": "Наталья",    "timeRange": ["17:00", "18:00"]},
    {"id": 10, "day": 2, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["18:00", "19:00"]},
    {"id": 11, "day": 2, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["19:00", "20:00"]},
    # Среда
    {"id": 12, "day": 3, "title": "Кинезиофитнес",  "description": "Любовь",     "timeRange": ["08:00", "09:00"]},
    {"id": 13, "day": 3, "title": "ЭроТревис",      "description": "Айгерим",    "timeRange": ["18:30", "20:00"]},
    # Четверг
    {"id": 14, "day": 4, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["07:30", "08:30"]},
    {"id": 15, "day": 4, "title": "Кинезиофитнес",  "description": "Любовь",     "timeRange": ["08:30", "09:30"]},
    {"id": 16, "day": 4, "title": "ЭроТреверс",     "description": "Айгерим",    "timeRange": ["10:00", "11:30"]},
    {"id": 17, "day": 4, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["18:00", "19:00"]},
    {"id": 18, "day": 4, "title": "Шейпинг",        "description": "Наталья",    "timeRange": ["19:00", "20:00"]},
    # Пятница
    {"id": 19, "day": 5, "title": "Кинезиофитнес",  "description": "Любовь",     "timeRange": ["08:30", "09:30"]},
    {"id": 20, "day": 5, "title": "ЭроТреверс",     "description": "Айгерим",    "timeRange": ["10:00", "11:30"]},
    # Суббота
    {"id": 21, "day": 6, "title": "Лимфодренаж",    "description": "",            "timeRange": ["07:30", "08:30"]},
    {"id": 22, "day": 6, "title": "ХатхаЙога",      "description": "Наталья",    "timeRange": ["09:00", "10:00"]},
    {"id": 23, "day": 6, "title": "Суставная Йога",  "description": "Наталья",    "timeRange": ["10:00", "11:00"]},


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
# Наш schedule day:  0=Вс, 1=Пн, 2=Вт, 3=Ср, 4=Чт, 5=Пт, 6=Сб
# ─────────────────────────────────────────────
_PYTHON_TO_SCHEDULE = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}

DAY_NAMES = {
    0: "Воскресенье",
    1: "Понедельник",
    2: "Вторник",
    3: "Среда",
    4: "Четверг",
    5: "Пятница",
    6: "Суббота",
}
DAY_SHORT = {0: "Вс", 1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб"}
ACTIVE_DAYS = sorted(SCHEDULE_DATA.keys())  # [0,1,2,3,4,5,6]

# ── Inline-кнопки меню ──
def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Сегодня", callback_data="nav:today"),
            InlineKeyboardButton("🗓 Вся неделя", callback_data="nav:week"),
        ],
        [
            InlineKeyboardButton("Пн", callback_data="nav:day:1"),
            InlineKeyboardButton("Вт", callback_data="nav:day:2"),
            InlineKeyboardButton("Ср", callback_data="nav:day:3"),
        ],
        [
            InlineKeyboardButton("Чт", callback_data="nav:day:4"),
            InlineKeyboardButton("Пт", callback_data="nav:day:5"),
            InlineKeyboardButton("Сб", callback_data="nav:day:6"),
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

def _clip(text: str, width: int) -> str:
    if len(text) <= width:
        return text.ljust(width)
    return text[:max(0, width - 1)] + "…"

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

def _week_text(filter_titles: set = None) -> str:
    rows = []
    for day_idx in ACTIVE_DAYS:
        events = SCHEDULE_DATA.get(day_idx, [])
        if filter_titles is not None:
            events = [e for e in events if e["title"] in filter_titles]
        for ev in events:
            s, e = ev["timeRange"]
            rows.append([
                DAY_SHORT[day_idx],
                f"{s}-{e}",
                ev["title"],
                ev.get("description", "").strip() or "-",
            ])
    if not rows:
        return "🗓 *Вся неделя*\n\n_Занятий не найдено._"

    lines = [
        "День Время       Занятие          Тренер",
        "---- ----------- ---------------- -------",
    ]
    for day, time_range, title, instructor in rows:
        lines.append(
            f"{_clip(day, 4)} "
            f"{_clip(time_range, 11)} "
            f"{_clip(title, 16)} "
            f"{_clip(instructor, 7)}"
        )
    return "🗓 *Вся неделя*\n\n```" + "\n".join(lines) + "```"

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
    if view == "week":
        return _week_text()
    if view.startswith("day:"):
        return _day_text(int(view.split(":", 1)[1]))
    if view == "mybookings":
        return _my_bookings_text(context, user_id)
    return _home_text()

async def _edit_screen(query, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    try:
        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
    except Exception as exc:
        if "Message is not modified" not in str(exc):
            raise

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

# ─────────────────────────────────────────────
# Обработчики команд
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "друг"
    if not _user_registered(context, user_id):
        _ensure_user(context, user_id)
    await update.message.reply_text(
        _home_text(name),
        parse_mode="Markdown",
        reply_markup=_main_menu_kb(),
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤖 *Помощь*\n\n"
        "Всё управление через кнопки под сообщением.\n\n"
        "📅 Сегодня — расписание на сегодня\n"
        "🗓 Вся неделя — все дни сразу\n"
        "Пн / Вт / Ср / Чт / Пт / Сб — конкретный день\n"
        "📝 Записаться — выбрать занятие, день и время\n"
        "📌 Мои занятия — ваши записи",
        parse_mode="Markdown",
        reply_markup=_main_menu_kb(),
    )

# ─────────────────────────────────────────────
# Обработчик кнопок меню (текстовые сообщения)
# ─────────────────────────────────────────────

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Используйте кнопки под этим сообщением 👇",
        reply_markup=_main_menu_kb(),
    )

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
        sent_count = await _notify_booking(context, query.from_user, ev)
        notify_line = (
            f"\n\n_Уведомление отправлено: {sent_count}_"
            if sent_count
            else "\n\n_Уведомления пока не настроены._"
        )
        await _edit_screen(
            query,
            "✅ *Вы записаны!*\n\n" + _booking_text(ev).replace("📝 *Запись на занятие*\n\n", "") + notify_line,
            _after_booking_kb(),
        )
        return

    await query.answer("⚠️ Неизвестное действие.", show_alert=True)

# ─────────────────────────────────────────────
# Inline-режим (@бот в любом чате)
# ─────────────────────────────────────────────

async def handle_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query
    search = query.query.strip().lower()
    results = []
    for title in ALL_CLASS_TITLES:
        if search and search not in title.lower():
            continue
        emoji = _emoji_for_class(title)
        lines = [f"{emoji} *{title}*\n"]
        for day_idx in ACTIVE_DAYS:
            evs = [e for e in SCHEDULE_DATA.get(day_idx, []) if e["title"] == title]
            for ev in evs:
                s, e = ev["timeRange"]
                instr = ev.get("description", "").strip()
                instr_part = f" │ 👤 {instr}" if instr else ""
                lines.append(f"  {DAY_SHORT[day_idx]}: 🕒 {s}–{e} ⏱ {_duration_str(s, e)}{instr_part}")
        results.append(InlineQueryResultArticle(
            id=title,
            title=f"{emoji} {title}",
            description="Поделиться расписанием этого класса",
            input_message_content=InputTextMessageContent(
                "\n".join(lines), parse_mode="Markdown"
            ),
        ))
    await query.answer(results[:50], cache_time=10, is_personal=True)

# ─────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────

def main() -> None:
    if BOT_TOKEN == "PASTE_YOUR_TOKEN_HERE": 
        raise RuntimeError("Вставьте токен бота в переменную BOT_TOKEN в начале файла!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["bookings"] = _load_bookings()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(InlineQueryHandler(handle_inline))

    logger.info("Бот запущен… Ctrl-C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
