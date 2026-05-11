"""
Фитнес-Расписание — Telegram Бот
Запуск: python fitness_bot.py
"""

import os
import logging
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────────────────────
# ТОКЕН — вставьте свой токен от @BotFather
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8607739583:AAGIWYXZBdJFW0Uil__NTIwmDL9e2lbd8Zc")

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

# ── Кнопки меню ──
BTN_TODAY     = "📅 Сегодня"
BTN_WEEK      = "🗓 Вся неделя"
BTN_MON       = "Пн"
BTN_TUE       = "Вт"
BTN_WED       = "Ср"
BTN_THU       = "Чт"
BTN_FRI       = "Пт"
BTN_SAT       = "Сб"
BTN_MYCLASSES = "🏅 Мои занятия"
BTN_EDIT      = "⚙️ Мои классы"

BTN_TO_DAY = {
    BTN_MON: 1,
    BTN_TUE: 2,
    BTN_WED: 3,
    BTN_THU: 4,
    BTN_FRI: 5,
    BTN_SAT: 6,
}

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BTN_TODAY), KeyboardButton(BTN_WEEK)],
        [KeyboardButton(BTN_MON), KeyboardButton(BTN_TUE), KeyboardButton(BTN_WED)],
        [KeyboardButton(BTN_THU), KeyboardButton(BTN_FRI), KeyboardButton(BTN_SAT)],
        [KeyboardButton(BTN_MYCLASSES), KeyboardButton(BTN_EDIT)],
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите из меню ниже…",
)

# ─────────────────────────────────────────────
# Хранилище пользователей (in-memory)
# ─────────────────────────────────────────────

def _get_user_classes(context, user_id: int) -> set:
    return context.bot_data.setdefault("users", {}).get(user_id, {}).get("classes", set())

def _set_user_classes(context, user_id: int, classes: set) -> None:
    context.bot_data.setdefault("users", {}).setdefault(user_id, {})["classes"] = classes

def _user_registered(context, user_id: int) -> bool:
    return user_id in context.bot_data.setdefault("users", {})

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
        hint = "\n_Попробуйте сбросить фильтр в «⚙️ Мои классы»_" if filter_titles else ""
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
        lines = [f"📅 *{DAY_NAMES[day_idx]}*"]
        lines += [_format_event(ev) for ev in events]
        sections.append("\n".join(lines))
    if not sections:
        return "🗓 *Вся неделя*\n\n_Занятий не найдено._"
    return "🗓 *Вся неделя*\n\n" + "\n\n".join(sections)

def _my_classes_text(chosen: set) -> str:
    if not chosen:
        return (
            "🏅 *Мои занятия*\n\n"
            "_Вы ещё не выбрали занятия._\n"
            "Нажмите «⚙️ Мои классы» чтобы выбрать."
        )
    lines = ["🏅 *Мои занятия*\n"]
    for title in sorted(chosen):
        count = sum(1 for evs in SCHEDULE_DATA.values() for e in evs if e["title"] == title)
        lines.append(f"{_emoji_for_class(title)} *{title}* — {count} раз/нед.")
    total = sum(1 for evs in SCHEDULE_DATA.values() for e in evs if e["title"] in chosen)
    lines.append(f"\n_Итого занятий в неделю: {total}_")
    return "\n".join(lines)

def _today_day() -> int:
    return _PYTHON_TO_SCHEDULE.get(datetime.now().weekday(), 0)

# ─────────────────────────────────────────────
# Inline-клавиатура выбора классов
# ─────────────────────────────────────────────

def _class_picker_kb(selected: set) -> InlineKeyboardMarkup:
    rows = []
    for title in ALL_CLASS_TITLES:
        mark = "✅" if title in selected else "◻️"
        rows.append([InlineKeyboardButton(
            f"{mark} {_emoji_for_class(title)} {title}",
            callback_data=f"toggle:{title}",
        )])
    rows.append([
        InlineKeyboardButton("💾 Сохранить", callback_data="saveclasses"),
        InlineKeyboardButton("Выбрать все",  callback_data="selectall"),
    ])
    rows.append([InlineKeyboardButton("🗑 Сбросить всё", callback_data="clearclasses")])
    return InlineKeyboardMarkup(rows)

# ─────────────────────────────────────────────
# Обработчики команд
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    name = update.effective_user.first_name or "друг"
    if not _user_registered(context, user_id):
        _set_user_classes(context, user_id, set())
    await update.message.reply_text(
        f"👋 Привет, *{name}*!\n\n"
        "🏋️ *Фитнес-Расписание*\n\n"
        "Используйте кнопки внизу экрана:\n"
        "• *Сегодня* / день недели — расписание на день\n"
        "• *Вся неделя* — полное недельное расписание\n"
        "• *Мои занятия* — только ваши классы\n"
        "• *⚙️ Мои классы* — выбрать / изменить классы",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU,
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🤖 *Помощь*\n\n"
        "Всё управление через кнопки внизу экрана.\n\n"
        "📅 Сегодня — расписание на сегодня\n"
        "🗓 Вся неделя — все дни сразу\n"
        "Пн / Вт / Ср / Чт / Пт / Сб — конкретный день\n"
        "🏅 Мои занятия — ваши выбранные классы\n"
        "⚙️ Мои классы — изменить выбор классов",
        parse_mode="Markdown",
        reply_markup=MAIN_MENU,
    )

# ─────────────────────────────────────────────
# Обработчик кнопок меню (текстовые сообщения)
# ─────────────────────────────────────────────

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    user_id = update.effective_user.id
    chosen = _get_user_classes(context, user_id)
    filter_set = chosen if chosen else None

    if text == BTN_TODAY:
        day = _today_day()
        await update.message.reply_text(
            _day_text(day, filter_set), parse_mode="Markdown", reply_markup=MAIN_MENU
        )
        return

    if text == BTN_WEEK:
        week = _week_text(filter_set)
        if len(week) <= 4000:
            await update.message.reply_text(week, parse_mode="Markdown", reply_markup=MAIN_MENU)
        else:
            for day_idx in ACTIVE_DAYS:
                chunk = _day_text(day_idx, filter_set)
                await update.message.reply_text(chunk, parse_mode="Markdown")
            await update.message.reply_text("☝️ Вся неделя выше.", reply_markup=MAIN_MENU)
        return

    if text in BTN_TO_DAY:
        day = BTN_TO_DAY[text]
        await update.message.reply_text(
            _day_text(day, filter_set), parse_mode="Markdown", reply_markup=MAIN_MENU
        )
        return

    if text == BTN_MYCLASSES:
        await update.message.reply_text(
            _my_classes_text(chosen), parse_mode="Markdown", reply_markup=MAIN_MENU
        )
        return

    if text == BTN_EDIT:
        context.user_data["draft_classes"] = set(chosen)
        await update.message.reply_text(
            "⚙️ *Выберите свои занятия*\n\n"
            "Нажмите на класс чтобы добавить ✅ или убрать ◻️\n"
            "Затем нажмите *Сохранить*:",
            parse_mode="Markdown",
            reply_markup=_class_picker_kb(set(chosen)),
        )
        return

    await update.message.reply_text(
        "Используйте кнопки меню внизу экрана 👇", reply_markup=MAIN_MENU
    )

# ─────────────────────────────────────────────
# Callback — чекбоксы выбора классов
# ─────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    user_id = query.from_user.id

    if data.startswith("toggle:"):
        title = data[len("toggle:"):]
        draft: set = context.user_data.get("draft_classes", set())
        draft.discard(title) if title in draft else draft.add(title)
        context.user_data["draft_classes"] = draft
        try:
            await query.edit_message_reply_markup(_class_picker_kb(draft))
        except Exception:
            pass
        return

    if data == "selectall":
        draft = set(ALL_CLASS_TITLES)
        context.user_data["draft_classes"] = draft
        try:
            await query.edit_message_reply_markup(_class_picker_kb(draft))
        except Exception:
            pass
        return

    if data == "clearclasses":
        context.user_data["draft_classes"] = set()
        try:
            await query.edit_message_reply_markup(_class_picker_kb(set()))
        except Exception:
            pass
        return

    if data == "saveclasses":
        draft: set = context.user_data.pop("draft_classes", set())
        _set_user_classes(context, user_id, draft)
        if draft:
            names = "\n".join(f"  {_emoji_for_class(t)} {t}" for t in sorted(draft))
            msg = f"✅ *Сохранено!*\n\nВаши занятия:\n{names}"
        else:
            msg = "✅ Фильтр сброшен — будет показываться полное расписание."
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=msg,
            parse_mode="Markdown",
            reply_markup=MAIN_MENU,
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
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help",  cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(InlineQueryHandler(handle_inline))

    logger.info("Бот запущен… Ctrl-C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()