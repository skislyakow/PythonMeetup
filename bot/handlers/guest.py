from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from asgiref.sync import sync_to_async
from django.utils import timezone

from bot.models.telegram_user import TelegramUser
from bot.models.question import Question
from bot.services.keyboards import (
    get_role_based_keyboard,
    BUTTON_SCHEDULE,
    BUTTON_ASK,
)
from bot.services.user_utils import (
    get_active_speaker,
    get_all_events,
    format_schedule,
)

TYPING_QUESTION = 1


# ─── Утилиты ──────────────────────────────────────────


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

    markup = await get_role_based_keyboard(user.id, show_ask=event is not None)

    status = (
        f"Сейчас выступает: {event.speaker.full_name} — {event.title}"
        if event
        else "В данный момент доклады не идут"
    )

    await update.message.reply_text(
        f"Привет, {user.full_name}!\n\n{status}",
        reply_markup=markup,
    )


# ─── Программа ────────────────────────────────────────


async def show_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    events = await get_all_events()
    await update.message.reply_text(format_schedule(events))


# ─── Задать вопрос (Conversation) ─────────────────────


async def ask_question_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    event = await get_active_speaker()
    if not event:
        await update.message.reply_text("Сейчас нет активного докладчика.")
        return ConversationHandler.END

    context.user_data["speaker_id"] = event.speaker_id
    context.user_data["speaker_name"] = event.speaker.full_name

    await update.message.reply_text(
        f"Напишите ваш вопрос для {event.speaker.full_name}:"
        "\n\n_Отправьте /cancel чтобы отменить_",
        reply_markup=ReplyKeyboardRemove(),
    )
    return TYPING_QUESTION


async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    speaker_id = context.user_data.get("speaker_id")
    text = update.message.text

    await save_question(user.id, speaker_id, text)

    markup = await get_role_based_keyboard(user.id)
    await update.message.reply_text("Вопрос отправлен!", reply_markup=markup)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = await get_role_based_keyboard(update.effective_user.id)
    await update.message.reply_text("Отменено.", reply_markup=markup)
    context.user_data.clear()
    return ConversationHandler.END


# ─── Сборка хендлеров ─────────────────────────────────

conv_handler = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Text([BUTTON_ASK]), ask_question_start),
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
    MessageHandler(filters.Text([BUTTON_SCHEDULE]), show_schedule),
    conv_handler,
]
