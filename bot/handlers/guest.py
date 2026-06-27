import warnings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

warnings.filterwarnings("ignore", "If 'per_message=False'")
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from asgiref.sync import sync_to_async
from django.utils import timezone

from bot.models.telegram_user import TelegramUser
from bot.models.event import Event
from bot.models.question import Question
from bot.services.auth import is_organizer
from bot.services.keyboards import organizer_keyboard, BUTTON_ASK

SELECTING_SPEAKER, TYPING_QUESTION = range(2)


# ─── Утилиты ──────────────────────────────────────────


@sync_to_async
def get_active_speaker():
    event = (
        Event.objects.filter(is_active=True).select_related("speaker").first()
    )
    return event


@sync_to_async
def get_all_events():
    return list(
        Event.objects.all().select_related("speaker").order_by("start_time")
    )


@sync_to_async
def save_question(from_user_id, to_speaker_id, text):
    Question.objects.create(
        from_user_id=from_user_id,
        to_speaker_id=to_speaker_id,
        text=text,
        created_at=timezone.now(),
    )


@sync_to_async
def get_or_create_user(user_id, full_name, username):
    user, _ = TelegramUser.objects.get_or_create(
        user_id=user_id,
        defaults={
            "full_name": full_name or "",
            "username": username or "",
        },
    )
    return user


# ─── /start ───────────────────────────────────────────


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await get_or_create_user(user.id, user.full_name, user.username)

    event = await get_active_speaker()

    buttons = []
    if event:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"Задать вопрос {event.speaker.full_name}",
                    callback_data="ask_question",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton("Программа", callback_data="schedule")]
    )

    status = (
        f"Сейчас выступает: {event.speaker.full_name} — {event.title}"
        if event
        else "В данный момент доклады не идут"
    )

    if await is_organizer(user.id):
        markup = organizer_keyboard()
    else:
        markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_text(
        f"Привет, {user.full_name}!\n\n{status}",
        reply_markup=markup,
    )


# ─── Программа ────────────────────────────────────────


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    events = await get_all_events()
    lines = ["Программа:\n"]
    for e in events:
        marker = "\U0001f7e2" if e.is_active else "\U00002b1b"
        lines.append(
            f"{marker} {e.start_time.strftime('%H:%M')} — {e.speaker.full_name}: {e.title}"
        )

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Назад", callback_data="back_to_menu")]]
        ),
    )


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    event = await get_active_speaker()
    buttons = []
    if event:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"Задать вопрос {event.speaker.full_name}",
                    callback_data="ask_question",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton("Программа", callback_data="schedule")]
    )
    status = (
        f"Сейчас выступает: {event.speaker.full_name} — {event.title}"
        if event
        else "В данный момент доклады не идут"
    )
    await query.edit_message_text(
        status,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


# ─── Задать вопрос (Conversation) ─────────────────────


async def ask_question_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    event = await get_active_speaker()
    if not event:
        await query.edit_message_text("Сейчас нет активного докладчика.")
        return ConversationHandler.END

    context.user_data["speaker_id"] = event.speaker_id
    context.user_data["speaker_name"] = event.speaker.full_name

    await query.edit_message_text(
        f"Напишите ваш вопрос для {event.speaker.full_name}:"
        "\n\n_Отправьте /cancel чтобы отменить_"
    )
    return TYPING_QUESTION


async def ask_question_start_from_msg(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    event = await get_active_speaker()
    if not event:
        await update.message.reply_text("Сейчас нет активного докладчика.")
        return ConversationHandler.END

    assert context.user_data is not None
    context.user_data["speaker_id"] = event.speaker_id
    context.user_data["speaker_name"] = event.speaker.full_name

    assert update.message is not None
    await update.message.reply_text(
        f"Напишите ваш вопрос для {event.speaker.full_name}:"
        "\n\n_Отправьте /cancel чтобы отменить_"
    )
    return TYPING_QUESTION


async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    speaker_id = context.user_data.get("speaker_id")
    text = update.message.text

    await save_question(user.id, speaker_id, text)

    await update.message.reply_text("Вопрос отправлен!")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    context.user_data.clear()
    return ConversationHandler.END


# ─── Сборка хендлеров ─────────────────────────────────

conv_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(ask_question_start, pattern="^ask_question$"),
        MessageHandler(filters.Text(BUTTON_ASK), ask_question_start_from_msg),
    ],
    states={
        TYPING_QUESTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

guest_handlers = [
    CommandHandler("start", start),
    CallbackQueryHandler(show_schedule, pattern="^schedule$"),
    CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"),
    conv_handler,
]
