import base64
import json
import logging
import os
import urllib.request
from datetime import datetime
from io import BytesIO

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    ReplyKeyboardRemove,
    Update,
)
from telegram.error import TelegramError
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes


BOT_TOKEN = os.environ.get("BOT_TOKEN", "8607739583:AAGIWYXZBdJFW0Uil__NTIwmDL9e2lbd8Zc")
BOOKINGS_FILE = os.environ.get("BOOKINGS_FILE", "bookings.json")
SCHEDULE_IMAGE_FILE = os.environ.get("SCHEDULE_IMAGE_FILE", "schedule.jpg")
SCHEDULE_IMAGE_BASE64_FILE = os.environ.get("SCHEDULE_IMAGE_BASE64_FILE", "schedule_image.b64")
SCHEDULE_IMAGE_BASE64_URL = os.environ.get(
    "SCHEDULE_IMAGE_BASE64_URL",
    "https://raw.githubusercontent.com/Alikhan111250/fitness-bot/main/schedule_image.b64",
)
NOTIFY_CHAT_IDS = [
    int(chat_id.strip())
    for chat_id in os.environ.get("NOTIFY_CHAT_IDS", "").split(",")
    if chat_id.strip().lstrip("-").isdigit()
]
INSTRUCTOR_CHAT_IDS = {}
for item in os.environ.get("INSTRUCTOR_CHAT_IDS", "").split(","):
    if ":" not in item:
        continue
    name, chat_id = item.split(":", 1)
    if chat_id.strip().lstrip("-").isdigit():
        INSTRUCTOR_CHAT_IDS[name.strip()] = int(chat_id.strip())


logging.basicConfig(format="%(asctime)s │ %(levelname)s │ %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


RAW_EVENTS = [
    {"id": 1, "day": 0, "title": "Кинезиофитнес", "description": "Любовь", "timeRange": ["08:30", "09:30"]},
    {"id": 2, "day": 0, "title": "ЭроТреверс", "description": "Айгерим", "timeRange": ["10:00", "11:30"]},
    {"id": 3, "day": 0, "title": "ЭроТреверс", "description": "Айгерим", "timeRange": ["18:30", "20:00"]},
    {"id": 4, "day": 1, "title": "Шейпинг", "description": "Наталья", "timeRange": ["07:30", "08:30"]},
    {"id": 5, "day": 1, "title": "Зумба", "description": "Аннастасия", "timeRange": ["08:30", "09:30"]},
    {"id": 6, "day": 1, "title": "Суставная Йога", "description": "Наталья", "timeRange": ["17:00", "18:00"]},
    {"id": 12, "day": 1, "title": "Шейпинг", "description": "Наталья", "timeRange": ["18:00", "19:00"]},
    {"id": 7, "day": 1, "title": "Шейпинг", "description": "Наталья", "timeRange": ["19:00", "20:00"]},
    {"id": 9, "day": 2, "title": "Кинезиофитнес", "description": "Любовь", "timeRange": ["08:00", "09:00"]},
    {"id": 10, "day": 2, "title": "ЭроТреверс", "description": "Айгерим", "timeRange": ["18:30", "20:00"]},
    {"id": 11, "day": 3, "title": "Шейпинг", "description": "Наталья", "timeRange": ["07:30", "08:30"]},
    {"id": 13, "day": 3, "title": "Шейпинг", "description": "Наталья", "timeRange": ["18:00", "19:00"]},
    {"id": 14, "day": 3, "title": "Шейпинг", "description": "Наталья", "timeRange": ["19:00", "20:00"]},
    {"id": 15, "day": 4, "title": "Кинезиофитнес", "description": "Любовь", "timeRange": ["08:30", "09:30"]},
    {"id": 16, "day": 4, "title": "ЭроТреверс", "description": "Айгерим", "timeRange": ["10:00", "11:30"]},
    {"id": 17, "day": 5, "title": "Лимфодренаж", "description": "", "timeRange": ["07:30", "08:30"]},
    {"id": 18, "day": 5, "title": "ХатхаЙога", "description": "Наталья", "timeRange": ["09:00", "10:00"]},
    {"id": 19, "day": 5, "title": "Суставная Йога", "description": "Наталья", "timeRange": ["10:00", "11:00"]},
]
EVENT_BY_ID = {event["id"]: event for event in RAW_EVENTS}
CLASS_TITLES = sorted({event["title"] for event in RAW_EVENTS})
CLASS_ID_TO_TITLE = {idx: title for idx, title in enumerate(CLASS_TITLES, start=1)}

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


def _plain(text: str) -> str:
    return text.replace("*", "").replace("_", "")


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


def _emoji_for_class(title: str) -> str:
    lowered = title.lower()
    if "йога" in lowered or "хатха" in lowered:
        return "🔵"
    if "шейпинг" in lowered or "зумба" in lowered:
        return "🟡"
    if "кинезио" in lowered or "лимфо" in lowered:
        return "✅"
    if "эро" in lowered or "треверс" in lowered:
        return "🟣"
    return "💪"


def _duration(start: str, end: str) -> str:
    start_h, start_m = map(int, start.split(":"))
    end_h, end_m = map(int, end.split(":"))
    minutes = end_h * 60 + end_m - start_h * 60 - start_m
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours}ч {minutes}м"
    if hours:
        return f"{hours}ч"
    return f"{minutes}м"


def _events_for_day(day: int) -> list[dict]:
    events = [event for event in RAW_EVENTS if event["day"] == day]
    return sorted(events, key=lambda event: event["timeRange"][0])


def _format_event(event: dict) -> str:
    start, end = event["timeRange"]
    instructor = event.get("description", "").strip()
    instructor_text = f" │ 👤 {instructor}" if instructor else ""
    return (
        f"{_emoji_for_class(event['title'])} 🕒 {start}–{end} │ "
        f"{event['title']}{instructor_text} │ ⏱ {_duration(start, end)}"
    )


def _day_text(day: int) -> str:
    events = _events_for_day(day)
    if not events:
        return f"📅 {DAY_NAMES.get(day, 'День')}\n\nЗанятий не запланировано."
    lines = [f"📅 {DAY_NAMES[day]}\n"]
    lines.extend(_format_event(event) for event in events)
    return "\n".join(lines)


def _home_text(name: str) -> str:
    return f"👋 Привет, {name}!\n\n🏋️ Фитнес-Расписание\n\nВыберите действие кнопками ниже:"


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


def _ensure_user(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    context.bot_data.setdefault("users", {}).setdefault(user_id, {})


def _user_bookings(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> list[dict]:
    bookings = context.bot_data.setdefault("bookings", [])
    user_bookings = [booking for booking in bookings if booking.get("user_id") == user_id]
    return sorted(user_bookings, key=lambda b: (b.get("day", 99), b.get("time", ""), b.get("created_at", "")))


def _booked_event_ids(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> set[int]:
    return {
        booking["event_id"]
        for booking in _user_bookings(context, user_id)
        if isinstance(booking.get("event_id"), int)
    }


def _add_booking(context: ContextTypes.DEFAULT_TYPE, user_id: int, event: dict, user) -> dict:
    start, end = event["timeRange"]
    booking = {
        "user_id": user_id,
        "user_name": user.full_name,
        "username": user.username,
        "event_id": event["id"],
        "class_title": event["title"],
        "day": event["day"],
        "time": f"{start}–{end}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    context.bot_data.setdefault("bookings", []).append(booking)
    context.bot_data.setdefault("users", {}).setdefault(user_id, {}).setdefault("bookings", []).append(booking)
    _save_bookings(context.bot_data["bookings"])
    return booking


def _delete_booking(context: ContextTypes.DEFAULT_TYPE, user_id: int, booking_index: int):
    user_bookings = _user_bookings(context, user_id)
    if booking_index < 0 or booking_index >= len(user_bookings):
        return None
    removed = user_bookings[booking_index]
    try:
        context.bot_data.setdefault("bookings", []).remove(removed)
    except ValueError:
        return None
    user_data = context.bot_data.setdefault("users", {}).setdefault(user_id, {})
    if "bookings" in user_data:
        try:
            user_data["bookings"].remove(removed)
        except ValueError:
            pass
    _save_bookings(context.bot_data["bookings"])
    return removed


def _signup_classes_text(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    if len(_booked_event_ids(context, user_id)) >= len(RAW_EVENTS):
        return "📝 Записаться\n\nВы уже записаны на все доступные занятия."
    return "📝 Записаться\n\nВыберите занятие:"


def _signup_classes_kb(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> InlineKeyboardMarkup:
    rows = []
    booked = _booked_event_ids(context, user_id)
    for class_id, title in CLASS_ID_TO_TITLE.items():
        if any(event["title"] == title and event["id"] not in booked for event in RAW_EVENTS):
            rows.append([InlineKeyboardButton(f"{_emoji_for_class(title)} {title}", callback_data=f"signup:class:{class_id}")])
    if not rows:
        rows.append([InlineKeyboardButton("📌 Мои занятия", callback_data="nav:mybookings")])
    rows.append([InlineKeyboardButton("← Назад в меню", callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)


def _signup_times_kb(title: str, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> InlineKeyboardMarkup:
    booked = _booked_event_ids(context, user_id)
    events = [
        event for event in RAW_EVENTS
        if event["title"] == title and event["id"] not in booked
    ]
    events.sort(key=lambda event: (event["day"], event["timeRange"][0]))
    rows = [
        [InlineKeyboardButton(
            f"{DAY_SHORT[event['day']]} {event['timeRange'][0]}–{event['timeRange'][1]}",
            callback_data=f"signup:event:{event['id']}",
        )]
        for event in events
    ]
    rows.append([InlineKeyboardButton("← Выбрать другое занятие", callback_data="nav:signup")])
    rows.append([InlineKeyboardButton("← Назад в меню", callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)


def _after_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📌 Мои занятия", callback_data="nav:mybookings")],
        [InlineKeyboardButton("📝 Записаться ещё", callback_data="nav:signup")],
        [InlineKeyboardButton("← Назад в меню", callback_data="nav:home")],
    ])


def _my_bookings_text(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    bookings = _user_bookings(context, user_id)
    if not bookings:
        return "📌 Мои занятия\n\nВы пока никуда не записаны.\n\nНажмите Записаться, чтобы выбрать занятие."
    lines = ["📌 Мои занятия\n"]
    for index, booking in enumerate(bookings, start=1):
        event = EVENT_BY_ID.get(booking.get("event_id"), {})
        instructor = event.get("description", "").strip()
        instructor_line = f"\n   👤 {instructor}" if instructor else ""
        lines.append(
            f"{index}. {_emoji_for_class(booking.get('class_title', ''))} {booking.get('class_title', 'Занятие')}\n"
            f"   📅 {DAY_NAMES.get(booking.get('day'), 'День не указан')}\n"
            f"   🕒 {booking.get('time', 'время не указано')}"
            f"{instructor_line}"
        )
    return "\n\n".join(lines)


def _my_bookings_kb(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for index, booking in enumerate(_user_bookings(context, user_id), start=1):
        day = DAY_SHORT.get(booking.get("day"), "")
        rows.append([InlineKeyboardButton(
            f"❌ Удалить {index}: {day} {booking.get('time', '')} {booking.get('class_title', '')}",
            callback_data=f"booking:remove:{index - 1}",
        )])
    rows.append([InlineKeyboardButton("📝 Записаться ещё", callback_data="nav:signup")])
    rows.append([InlineKeyboardButton("← Назад в меню", callback_data="nav:home")])
    return InlineKeyboardMarkup(rows)


def _booking_text(event: dict) -> str:
    start, end = event["timeRange"]
    instructor = event.get("description", "").strip() or "не указан"
    return (
        f"{_emoji_for_class(event['title'])} {event['title']}\n"
        f"📅 {DAY_NAMES[event['day']]}\n"
        f"🕒 {start}–{end}\n"
        f"👤 {instructor}"
    )


def _booking_notice_text(user, event: dict) -> str:
    start, end = event["timeRange"]
    username = f"@{user.username}" if user.username else "без username"
    return (
        "Новая запись на занятие\n\n"
        f"Клиент: {user.full_name} ({username})\n"
        f"Telegram ID: {user.id}\n"
        f"Занятие: {event['title']}\n"
        f"День: {DAY_NAMES[event['day']]}\n"
        f"Время: {start}–{end}\n"
        f"Инструктор: {event.get('description', '').strip() or 'не указан'}"
    )


def _schedule_photo():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = SCHEDULE_IMAGE_FILE
    if not os.path.isabs(image_path):
        image_path = os.path.join(base_dir, image_path)
    if os.path.exists(image_path):
        return open(image_path, "rb")

    image_source = ""
    base64_path = SCHEDULE_IMAGE_BASE64_FILE
    if not os.path.isabs(base64_path):
        base64_path = os.path.join(base_dir, base64_path)
    if os.path.exists(base64_path):
        try:
            with open(base64_path, "r", encoding="ascii") as image_file:
                image_source = image_file.read()
        except OSError as exc:
            logger.warning("Не удалось загрузить файл картинки расписания: %s", exc)

    if not image_source:
        try:
            with urllib.request.urlopen(SCHEDULE_IMAGE_BASE64_URL, timeout=10) as response:
                image_source = response.read().decode("ascii")
        except Exception as exc:
            logger.warning("Не удалось скачать картинку расписания: %s", exc)

    if not image_source:
        return None
    try:
        image_data = base64.b64decode(image_source)
    except ValueError as exc:
        logger.warning("Не удалось прочитать картинку расписания: %s", exc)
        return None
    photo = BytesIO(image_data)
    photo.name = "schedule.jpg"
    return photo


async def _edit_screen(query, text: str, reply_markup: InlineKeyboardMarkup) -> None:
    try:
        await query.edit_message_text(_plain(text), reply_markup=reply_markup)
    except Exception as exc:
        if "Message is not modified" in str(exc):
            return
        try:
            await query.message.delete()
            await query.message.chat.send_message(_plain(text), reply_markup=reply_markup)
        except Exception:
            raise exc


async def _show_week_image(query) -> None:
    photo = _schedule_photo()
    if photo is None:
        await _edit_screen(query, "🗓 Вся неделя\n\nКартинка расписания не найдена.", _main_menu_kb())
        return
    try:
        with photo:
            await query.edit_message_media(
                media=InputMediaPhoto(media=photo, caption="🗓 Вся неделя"),
                reply_markup=_main_menu_kb(),
            )
    except TelegramError as exc:
        logger.warning("Не удалось заменить сообщение картинкой: %s", exc)
        photo = _schedule_photo()
        if photo is None:
            await query.message.chat.send_message(
                "🗓 Вся неделя\n\nКартинка расписания не найдена.",
                reply_markup=_main_menu_kb(),
            )
            return
        try:
            with photo:
                await query.message.chat.send_photo(
                    photo=photo,
                    caption="🗓 Вся неделя",
                    reply_markup=_main_menu_kb(),
                )
        except TelegramError as send_exc:
            logger.exception("Не удалось отправить картинку расписания: %s", send_exc)
            await query.message.chat.send_message(
                "🗓 Вся неделя\n\nКартинка расписания временно не отправилась. Попробуйте нажать ещё раз.",
                reply_markup=_main_menu_kb(),
            )


async def _notify_booking(context: ContextTypes.DEFAULT_TYPE, user, event: dict) -> None:
    recipients = set(NOTIFY_CHAT_IDS)
    instructor = event.get("description", "").strip()
    if instructor in INSTRUCTOR_CHAT_IDS:
        recipients.add(INSTRUCTOR_CHAT_IDS[instructor])
    for chat_id in recipients:
        try:
            await context.bot.send_message(chat_id=chat_id, text=_booking_notice_text(user, event))
        except Exception as exc:
            logger.warning("Не удалось отправить уведомление %s: %s", chat_id, exc)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    _ensure_user(context, user_id)
    cleanup = await update.message.reply_text("Нижнее меню убрано.", reply_markup=ReplyKeyboardRemove())
    try:
        await cleanup.delete()
    except Exception as exc:
        logger.warning("Не удалось удалить служебное сообщение: %s", exc)
    await update.message.reply_text(
        _home_text(update.effective_user.first_name or "друг"),
        reply_markup=_main_menu_kb(),
    )


async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Ошибка обработчика Telegram", exc_info=context.error)
    if isinstance(update, Update) and update.callback_query:
        try:
            await update.callback_query.answer("Произошла ошибка. Нажмите /start и попробуйте ещё раз.", show_alert=True)
        except Exception as exc:
            logger.warning("Не удалось показать ошибку пользователю: %s", exc)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    user_id = query.from_user.id
    _ensure_user(context, user_id)

    if data == "nav:home":
        await _edit_screen(query, _home_text(query.from_user.first_name or "друг"), _main_menu_kb())
        return
    if data == "nav:today":
        await _edit_screen(query, _day_text(datetime.now().weekday()), _main_menu_kb())
        return
    if data == "nav:week":
        await _show_week_image(query)
        return
    if data == "nav:signup":
        await _edit_screen(query, _signup_classes_text(context, user_id), _signup_classes_kb(context, user_id))
        return
    if data == "nav:mybookings":
        await _edit_screen(query, _my_bookings_text(context, user_id), _my_bookings_kb(context, user_id))
        return
    if data.startswith("nav:day:"):
        await _edit_screen(query, _day_text(int(data.rsplit(":", 1)[1])), _main_menu_kb())
        return

    if data.startswith("signup:class:"):
        class_id = int(data.rsplit(":", 1)[1])
        title = CLASS_ID_TO_TITLE.get(class_id)
        if not title:
            await query.answer("Занятие не найдено.", show_alert=True)
            return
        await _edit_screen(query, f"📝 {title}\n\nВыберите день и время:", _signup_times_kb(title, context, user_id))
        return

    if data.startswith("signup:event:"):
        event_id = int(data.rsplit(":", 1)[1])
        event = EVENT_BY_ID.get(event_id)
        if not event:
            await query.answer("Время не найдено.", show_alert=True)
            return
        if event_id in _booked_event_ids(context, user_id):
            await query.answer("Вы уже записаны на это время.", show_alert=True)
            await _edit_screen(query, _my_bookings_text(context, user_id), _my_bookings_kb(context, user_id))
            return
        _add_booking(context, user_id, event, query.from_user)
        await _edit_screen(query, "✅ Вы записаны!\n\n" + _booking_text(event), _after_booking_kb())
        await _notify_booking(context, query.from_user, event)
        return

    if data.startswith("booking:remove:"):
        booking_index = int(data.rsplit(":", 1)[1])
        if not _delete_booking(context, user_id, booking_index):
            await query.answer("Запись не найдена.", show_alert=True)
            return
        await _edit_screen(query, "✅ Запись удалена.\n\n" + _my_bookings_text(context, user_id), _my_bookings_kb(context, user_id))
        return

    await query.answer("Неизвестное действие.", show_alert=True)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.bot_data["bookings"] = _load_bookings()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_error_handler(handle_error)
    logger.info("Бот запущен.")
    app.run_polling(allowed_updates=["message", "callback_query"], drop_pending_updates=True)


if __name__ == "__main__":
    main()
