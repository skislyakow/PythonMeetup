import warnings
from functools import wraps
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)

from bot.services.keyboards import (
    organizer_keyboard,
    guest_keyboard,
    speaker_keyboard,
    BUTTON_ACTIVATE,
    BUTTON_BROADCAST,
    BUTTON_SCHEDULE_CREATE,
    BUTTON_CLOSE,
)


from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from asgiref.sync import sync_to_async
from datetime import datetime
from django.utils import timezone

from bot.services.auth import is_organizer
from bot.models.telegram_user import TelegramUser
from bot.models.event import Event
from bot.services import db_direct

warnings.filterwarnings("ignore", "If 'per_message=False'")

TITLE, START_TIME, END_TIME, SPEAKER, CONFIRM = range(5)

# Состояния для редактирования события
ES_FIELD, ES_TITLE, ES_DATE, ES_START, ES_END, ES_SPEAKER, ES_SAVE = range(
    10, 17
)

BROADCAST_TEXT = 20

create_event_async = sync_to_async(db_direct.create_event)
logger = logging.getLogger(__name__)


def organizer_required(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        if not update.message or not update.effective_user:
            return
        if not await is_organizer(update.effective_user.id):
            await update.message.reply_text("Нет доступа")
            return
        return await func(update, context, *args, **kwargs)

    return wrapper


@sync_to_async
def find_speaker_by_username(username):
    return TelegramUser.objects.filter(username=username).first()


@organizer_required
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message is not None
    await update.message.reply_text(
        "Ты организатор!", reply_markup=organizer_keyboard()
    )


def parse_time(text: str) -> datetime | None:
    try:
        hour, minute = map(int, text.split(":"))
        now = timezone.localtime()
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (ValueError, AttributeError):
        return None


@sync_to_async
def get_all_users():
    return list(TelegramUser.objects.all())


@sync_to_async
def get_active_event():
    return Event.objects.filter(is_active=True).select_related("speaker").first()


@organizer_required
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message is not None
    text = " ".join(context.args or [])
    if text:
        await _send_broadcast(update, context, text)
        return ConversationHandler.END
    await update.message.reply_text(
        "Введите текст рассылки:", reply_markup=ReplyKeyboardRemove()
    )
    return BROADCAST_TEXT


async def broadcast_text_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.message is not None
    await _send_broadcast(update, context, update.message.text)
    return ConversationHandler.END


async def _send_broadcast(update, context, text):
    users = await get_all_users()
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u.user_id, text=text)
            sent += 1
        except Exception as e:
            logger.warning("Failed to send to %s: %s", u.user_id, e)
    await update.message.reply_text(
        f"Сообщение отправлено {sent} из {len(users)} пользователям",
        reply_markup=organizer_keyboard(),
    )


@organizer_required
async def set_schedule_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.message is not None
    await update.message.reply_text(
        "Название доклада?", reply_markup=ReplyKeyboardRemove()
    )
    return TITLE


async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or context.user_data is None:
        return TITLE
    context.user_data["title"] = update.message.text
    await update.message.reply_text("Время начала? (например, 14:00)")
    return START_TIME


async def get_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or context.user_data is None:
        return START_TIME
    text = (update.message.text or "").strip()
    start_dt = parse_time(text)
    if start_dt is None:
        await update.message.reply_text(
            "Неверный формат. Напиши время так: 14:00"
        )
        return START_TIME
    context.user_data["start_time"] = start_dt
    await update.message.reply_text("Время конца? (например, 15:00)")
    return END_TIME


async def get_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or context.user_data is None:
        return END_TIME
    text = (update.message.text or "").strip()
    end_dt = parse_time(text)
    if end_dt is None:
        await update.message.reply_text(
            "Неверный формат. Напиши время так: 15:00"
        )
        return END_TIME
    if end_dt <= context.user_data["start_time"]:
        await update.message.reply_text(
            "Время конца должно быть позже начала. Попробуй ещё:"
        )
        return END_TIME
    context.user_data["end_time"] = end_dt
    await update.message.reply_text("Username спикера? (например, @ivanov)")
    return SPEAKER


async def get_speaker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or context.user_data is None:
        return SPEAKER
    username = (update.message.text or "").strip().lstrip("@")
    speaker = await find_speaker_by_username(username)
    if not speaker:
        await update.message.reply_text(
            f"Пользователь @{username} не найден. Убедись, что он написал /start боту."
        )
        return SPEAKER
    if speaker.role != "speaker":
        speaker.role = "speaker"
        await sync_to_async(speaker.save)()

    start_str = context.user_data["start_time"].strftime("%H:%M")
    end_str = context.user_data["end_time"].strftime("%H:%M")
    try:
        await context.bot.send_message(
            chat_id=speaker.user_id,
            text=(
                "🎤 Вы назначены докладчиком на Python Meetup!\n"
                f"Тема доклада: {context.user_data['title']}\n"
                f"Начало: {start_str}\n"
                f"Конец: {end_str}"
            ),
        )
    except Exception:
        logger.warning("Не удалось уведомить спикера %s", speaker.user_id)
    context.user_data["speaker_id"] = speaker.user_id
    title = context.user_data["title"]
    await update.message.reply_text(f"Добавить доклад «{title}»? (да/нет)")
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or context.user_data is None:
        return CONFIRM
    text = (update.message.text or "").strip().lower()
    if text == "да":
        await create_event_async(
            context.user_data["speaker_id"],
            context.user_data["title"],
            context.user_data["start_time"],
            context.user_data["end_time"],
        )
        await update.message.reply_text(
            "Доклад добавлен!", reply_markup=organizer_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    elif text == "нет":
        await update.message.reply_text(
            "Отменено.", reply_markup=organizer_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("Напиши да или нет")
        return CONFIRM


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or context.user_data is None:
        return ConversationHandler.END
    await update.message.reply_text(
        "Отменено.", reply_markup=organizer_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message is not None
    await update.message.reply_text(
        "Меню закрыто. Нажмите /admin чтобы вернуть.",
        reply_markup=ReplyKeyboardRemove(),
    )


@sync_to_async
def get_all_events_with_speakers():
    return list(
        Event.objects.all().select_related("speaker").order_by("start_time")
    )


@sync_to_async
def activate_event(event_id):
    event = Event.objects.get(pk=event_id)
    event.is_active = True
    event.save()
    return event.speaker_id


@sync_to_async
def deactivate_all_events():
    speaker_id = (
        Event.objects.filter(is_active=True)
        .values_list("speaker_id", flat=True)
        .first()
    )
    Event.objects.filter(is_active=True).update(is_active=False)
    return speaker_id


@sync_to_async
def get_event(event_id):
    return Event.objects.select_related("speaker").get(pk=event_id)


@sync_to_async
def delete_event(event_id):
    Event.objects.get(pk=event_id).delete()


@sync_to_async
def get_all_speakers():
    return list(
        TelegramUser.objects.filter(role="speaker").order_by("full_name")
    )


@sync_to_async
def get_upcoming_speaker_events_count(user_id):
    from django.utils import timezone
    return Event.objects.filter(
        speaker_id=user_id, start_time__gt=timezone.now()
    ).count()


@sync_to_async
def set_user_role(user_id, role):
    TelegramUser.objects.filter(user_id=user_id).update(role=role)


@organizer_required
async def activate_speaker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message is not None
    events = await get_all_events_with_speakers()
    if not events:
        await update.message.reply_text("Нет докладов в программе")
        return

    lines = ["Программа:\n"]

    if not any(e.is_active for e in events):
        lines.append("⏸ Никто не выступает\n")

    assert context.user_data is not None
    context.user_data["program_message_ids"] = []

    header = await update.message.reply_text("\n".join(lines))
    context.user_data["program_message_ids"].append(header.message_id)

    for e in events:
        marker = "\U0001f7e2" if e.is_active else "\U00002b1b"
        status = " (сейчас активен)" if e.is_active else ""
        text = f"{marker} {e.start_time.strftime('%H:%M')} — {e.speaker.full_name}: {e.title}{status}"

        delete_btn = InlineKeyboardButton(
            "🗑️", callback_data=f"delete_event_{e.id}"
        )
        if e.is_active:
            btn = [
                [
                    InlineKeyboardButton(
                        "⏹ Завершить", callback_data=f"deactivate_{e.id}"
                    ),
                    InlineKeyboardButton(
                        "✏️", callback_data=f"edit_event_{e.id}"
                    ),
                    delete_btn,
                ]
            ]
        else:
            btn = [
                [
                    InlineKeyboardButton(
                        "✅ Сделать активным",
                        callback_data=f"activate_event_{e.id}",
                    ),
                    InlineKeyboardButton(
                        "✏️", callback_data=f"edit_event_{e.id}"
                    ),
                    delete_btn,
                ]
            ]

        msg = await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(btn)
        )
        context.user_data["program_message_ids"].append(msg.message_id)


async def set_active_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    assert query is not None
    await query.answer()

    user_id = query.from_user.id
    if not await is_organizer(user_id):
        await query.edit_message_text("Нет доступа")
        return

    assert query.data is not None

    assert context.user_data is not None
    assert update.effective_chat is not None
    assert query.message is not None
    program_ids = context.user_data.pop("program_message_ids", [])
    await context.bot.delete_message(
        chat_id=update.effective_chat.id, message_id=query.message.message_id
    )
    for msg_id in program_ids:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, message_id=msg_id
            )
        except Exception:
            pass

    if query.data.startswith("deactivate_"):
        prev_event = await get_active_event()
        prev_speaker_id = await deactivate_all_events()
        if prev_speaker_id:
            await context.bot.send_message(
                chat_id=prev_speaker_id,
                text="⏸ Ваш доклад завершён. Вы теперь гость.",
                reply_markup=guest_keyboard(),
            )
            upcoming = await get_upcoming_speaker_events_count(prev_speaker_id)
            if not upcoming:
                await set_user_role(prev_speaker_id, "guest")

        if prev_event:
            users = await get_all_users()
            notification = (
                f"⏸ <b>Доклад завершён</b>\n\n"
                f"«{prev_event.title}»\n"
                f"Спикер: {prev_event.speaker.full_name}"
            )
            for u in users:
                if u.user_id == user_id or u.user_id == prev_speaker_id:
                    continue
                try:
                    await context.bot.send_message(
                        chat_id=u.user_id, text=notification, parse_mode="HTML"
                    )
                except Exception:
                    pass

        await update.effective_chat.send_message("⏸ Доклад завершён")
        return

    event_id = int(query.data.split("_")[-1])
    event = await get_event(event_id)
    speaker_id = await activate_event(event_id)

    await context.bot.send_message(
        chat_id=speaker_id,
        text=(
            "🎤 Вы сейчас выступаете!\n"
            "Нажмите /speaker чтобы открыть панель спикера"
        ),
        reply_markup=speaker_keyboard(),
    )

    users = await get_all_users()
    notification = (
        f"🎤 <b>Начался доклад!</b>\n\n"
        f"«{event.title}»\n"
        f"Спикер: {event.speaker.full_name}"
    )
    sent = 0
    for u in users:
        if u.user_id == user_id or u.user_id == speaker_id:
            continue
        try:
            await context.bot.send_message(chat_id=u.user_id, text=notification, parse_mode="HTML")
            sent += 1
        except Exception:
            pass

    await update.effective_chat.send_message(
        f"✅ Доклад «{event.title}» запущен. Уведомлено {sent} участников."
    )


def _build_edit_menu(event, changes):
    title = changes.get("title", event.title)
    speaker_name = changes.get("speaker_name", event.speaker.full_name)
    date = changes.get("date", event.start_time.strftime("%d.%m.%Y"))
    start = changes.get("start", event.start_time.strftime("%H:%M"))
    end = changes.get("end", event.end_time.strftime("%H:%M"))

    text = (
        "✏️ **Редактирование доклада**\n\n"
        f"📝 Название: {title}\n"
        f"👤 Спикер: {speaker_name}\n"
        f"📅 {date}  🕐 {start} — {end}"
    )

    keyboard = [
        [
            InlineKeyboardButton("📝 Название", callback_data="es_title"),
            InlineKeyboardButton("👤 Спикер", callback_data="es_speaker"),
        ],
        [
            InlineKeyboardButton("📅 Дата", callback_data="es_date"),
            InlineKeyboardButton("🕐 Начало", callback_data="es_start"),
            InlineKeyboardButton("🕐 Конец", callback_data="es_end"),
        ],
        [
            InlineKeyboardButton("✅ Сохранить", callback_data="es_save"),
            InlineKeyboardButton("❌ Отмена", callback_data="es_cancel"),
        ],
    ]
    return text, InlineKeyboardMarkup(keyboard)


async def show_edit_menu(query, context, event_id=None):
    assert context.user_data is not None
    if event_id:
        context.user_data["edit_event_id"] = event_id
        context.user_data["edit_changes"] = {}

    event = await get_event(context.user_data["edit_event_id"])
    changes = context.user_data.get("edit_changes", {})
    text, markup = _build_edit_menu(event, changes)
    await query.edit_message_text(text, reply_markup=markup)
    return ES_FIELD


async def show_edit_menu_from_msg(update, context):
    assert context.user_data is not None
    event = await get_event(context.user_data["edit_event_id"])
    changes = context.user_data.get("edit_changes", {})
    text, markup = _build_edit_menu(event, changes)
    await update.message.reply_text(text, reply_markup=markup)
    return ES_FIELD


async def edit_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    assert query is not None
    await query.answer()
    assert query.data is not None
    event_id = int(query.data.split("_")[-1])
    return await show_edit_menu(query, context, event_id)


async def edit_field_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    assert query is not None
    await query.answer()
    assert context.user_data is not None

    field = query.data

    if field == "es_save":
        event = await get_event(context.user_data["edit_event_id"])
        changes = context.user_data.get("edit_changes", {})

        title = changes.get("title", event.title)
        speaker_name = changes.get("speaker_name", event.speaker.full_name)
        date = changes.get("date", event.start_time.strftime("%d.%m.%Y"))
        start = changes.get("start", event.start_time.strftime("%H:%M"))
        end = changes.get("end", event.end_time.strftime("%H:%M"))

        text = (
            "✅ **Подтверждение изменений**\n\n"
            f"📝 Название: {title}\n"
            f"👤 Спикер: {speaker_name}\n"
            f"📅 {date}  🕐 {start} — {end}\n\n"
            "Сохранить?"
        )
        keyboard = [
            [
                InlineKeyboardButton("✓", callback_data="es_yes"),
                InlineKeyboardButton("✕", callback_data="es_no"),
            ],
        ]
        await query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ES_SAVE

    if field == "es_title":
        await query.edit_message_text("📝 Введите новое название доклада:")
        return ES_TITLE

    if field == "es_date":
        await query.edit_message_text("📅 Введите новую дату (ДД.ММ.ГГГГ):")
        return ES_DATE

    if field == "es_start":
        await query.edit_message_text("🕐 Введите новое время начала (ЧЧ:ММ):")
        return ES_START

    if field == "es_end":
        await query.edit_message_text("🕐 Введите новое время конца (ЧЧ:ММ):")
        return ES_END

    if field == "es_speaker":
        speakers = await get_all_speakers()
        if not speakers:
            await query.edit_message_text("Нет спикеров в базе.")
            return ES_FIELD

        keyboard = [
            [
                InlineKeyboardButton(
                    s.full_name, callback_data=f"es_speaker_{s.user_id}"
                )
            ]
            for s in speakers
        ]
        keyboard.append(
            [InlineKeyboardButton("« Назад", callback_data="es_back")]
        )
        await query.edit_message_text(
            "👤 Выберите спикера:", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ES_SPEAKER

    return ES_FIELD


async def edit_title_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.message is not None
    assert update.message.text is not None
    assert context.user_data is not None
    context.user_data.setdefault("edit_changes", {})["title"] = (
        update.message.text
    )
    return await show_edit_menu_from_msg(update, context)


async def edit_date_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.message is not None
    assert update.message.text is not None
    assert context.user_data is not None
    try:
        datetime.strptime(update.message.text, "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите ДД.ММ.ГГГГ:")
        return ES_DATE
    context.user_data.setdefault("edit_changes", {})["date"] = (
        update.message.text
    )
    return await show_edit_menu_from_msg(update, context)


async def edit_start_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.message is not None
    assert update.message.text is not None
    assert context.user_data is not None
    try:
        datetime.strptime(update.message.text, "%H:%M")
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите ЧЧ:ММ:")
        return ES_START
    context.user_data.setdefault("edit_changes", {})["start"] = (
        update.message.text
    )
    return await show_edit_menu_from_msg(update, context)


async def edit_end_received(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    assert update.message is not None
    assert update.message.text is not None
    assert context.user_data is not None
    try:
        datetime.strptime(update.message.text, "%H:%M")
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите ЧЧ:ММ:")
        return ES_END
    context.user_data.setdefault("edit_changes", {})["end"] = (
        update.message.text
    )
    return await show_edit_menu_from_msg(update, context)


async def edit_speaker_selected(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    assert query is not None
    await query.answer()
    assert context.user_data is not None

    if query.data == "es_back":
        return await show_edit_menu(query, context)

    assert query.data is not None
    speaker_id = int(query.data.split("_")[-1])
    speaker = await sync_to_async(TelegramUser.objects.get)(user_id=speaker_id)
    context.user_data.setdefault("edit_changes", {})["speaker_id"] = speaker_id
    context.user_data["edit_changes"]["speaker_name"] = speaker.full_name
    return await show_edit_menu(query, context)


@sync_to_async
def _apply_edit(event_id, changes):
    event = Event.objects.get(pk=event_id)
    if "title" in changes:
        event.title = changes["title"]
    if "speaker_id" in changes:
        event.speaker = TelegramUser.objects.get(pk=changes["speaker_id"])

    if "date" in changes or "start" in changes or "end" in changes:
        date_str = changes.get("date", event.start_time.strftime("%d.%m.%Y"))
        start_str = changes.get("start", event.start_time.strftime("%H:%M"))
        end_str = changes.get("end", event.end_time.strftime("%H:%M"))
        event.start_time = datetime.strptime(
            f"{date_str} {start_str}", "%d.%m.%Y %H:%M"
        )
        event.end_time = datetime.strptime(
            f"{date_str} {end_str}", "%d.%m.%Y %H:%M"
        )

    event.save()


async def edit_save_confirm(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    assert query is not None
    await query.answer()
    assert context.user_data is not None
    assert update.effective_chat is not None

    if query.data == "es_no":
        assert query.message is not None
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=query.message.message_id,
        )
        for msg_id in context.user_data.pop("program_message_ids", []):
            try:
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id, message_id=msg_id
                )
            except Exception:
                pass
        await update.effective_chat.send_message(
            "Меню организатора:", reply_markup=organizer_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END

    event_id = context.user_data["edit_event_id"]
    changes = context.user_data.get("edit_changes", {})
    await _apply_edit(event_id, changes)

    program_ids = context.user_data.pop("program_message_ids", [])
    context.user_data.clear()

    assert query.message is not None
    await context.bot.delete_message(
        chat_id=update.effective_chat.id, message_id=query.message.message_id
    )
    for msg_id in program_ids:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, message_id=msg_id
            )
        except Exception:
            pass
    await update.effective_chat.send_message(
        "Меню организатора:", reply_markup=organizer_keyboard()
    )
    return ConversationHandler.END


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert context.user_data is not None
    program_ids = context.user_data.pop("program_message_ids", [])
    assert update.effective_chat is not None
    for msg_id in program_ids:
        try:
            chat_id = update.effective_chat.id
            await context.bot.delete_message(
                chat_id=chat_id, message_id=msg_id
            )
        except Exception:
            pass
    context.user_data.clear()
    if update.callback_query:
        assert update.callback_query.message is not None
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.callback_query.message.message_id,
        )
        await update.effective_chat.send_message(
            "Меню организатора:", reply_markup=organizer_keyboard()
        )
    elif update.message:
        await update.message.reply_text(
            "❌ Редактирование отменено.", reply_markup=organizer_keyboard()
        )
    return ConversationHandler.END


edit_conv = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(edit_event_start, pattern=r"^edit_event_(\d+)$")
    ],
    states={
        ES_FIELD: [
            CallbackQueryHandler(
                edit_field_selected, pattern=r"^es_(?!cancel)"
            )
        ],
        ES_TITLE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, edit_title_received
            )
        ],
        ES_DATE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_date_received)
        ],
        ES_START: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, edit_start_received
            )
        ],
        ES_END: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_end_received)
        ],
        ES_SPEAKER: [
            CallbackQueryHandler(
                edit_speaker_selected, pattern=r"^es_speaker_|^es_back$"
            )
        ],
        ES_SAVE: [
            CallbackQueryHandler(edit_save_confirm, pattern=r"^es_(yes|no)$")
        ],
    },
    fallbacks=[
        CallbackQueryHandler(edit_cancel, pattern=r"^es_cancel$"),
        CommandHandler("cancel", edit_cancel),
        MessageHandler(filters.Regex(f"^{BUTTON_CLOSE}$"), edit_cancel),
    ],
)


conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler("set_schedule", set_schedule_start),
        MessageHandler(filters.Text([BUTTON_SCHEDULE_CREATE]), set_schedule_start),
    ],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        START_TIME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_start_time)
        ],
        END_TIME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_end_time)
        ],
        SPEAKER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_speaker)
        ],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BUTTON_CLOSE}$"), cancel),
    ],
)

broadcast_conv = ConversationHandler(
    entry_points=[
        CommandHandler("broadcast", broadcast_start),
        MessageHandler(filters.Text([BUTTON_BROADCAST]), broadcast_start),
    ],
    states={
        BROADCAST_TEXT: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, broadcast_text_received
            )
        ],
    },
    fallbacks=[
        CommandHandler("cancel", cancel),
        MessageHandler(filters.Regex(f"^{BUTTON_CLOSE}$"), cancel),
    ],
)

async def delete_event_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    assert query is not None
    await query.answer()

    user_id = query.from_user.id
    if not await is_organizer(user_id):
        return

    assert query.data is not None
    event_id = int(query.data.split("_")[-1])
    await delete_event(event_id)

    assert update.effective_chat is not None
    assert query.message is not None
    await context.bot.delete_message(
        chat_id=update.effective_chat.id, message_id=query.message.message_id
    )


organizer_handlers = [
    CommandHandler("admin", admin_panel),
    broadcast_conv,
    CommandHandler("activate", activate_speaker),
    CallbackQueryHandler(
        set_active_callback, pattern="^(activate_event_|deactivate_)"
    ),
    CallbackQueryHandler(
        delete_event_callback, pattern="^delete_event_"
    ),
    conv_handler,
    edit_conv,
    MessageHandler(filters.Regex(f"^{BUTTON_CLOSE}$"), close_menu),
    MessageHandler(filters.Regex(f"^{BUTTON_ACTIVATE}$"), activate_speaker),
]
