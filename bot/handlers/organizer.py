from datetime import datetime

from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import asyncio
from asgiref.sync import sync_to_async
from django.utils import timezone

from bot.services.auth import is_organizer
from bot.models.telegram_user import TelegramUser
from bot.models.event import Event
from bot.services import db_direct

TITLE, START_TIME, END_TIME, SPEAKER, CONFIRM = range(5)


# --- sync helpers ---


@sync_to_async
def find_and_set_speaker(username):
    user = TelegramUser.objects.filter(username=username).first()
    if user:
        user.role = "speaker"
        user.save()
    return user


@sync_to_async
def find_speaker_by_username(username):
    return TelegramUser.objects.filter(username=username).first()


# --- admin_panel ---


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_organizer(update.effective_user.id):
        await update.message.reply_text("Нет доступа")
        return
    await update.message.reply_text("Ты организатор!")


# --- add_speaker ---


async def add_speaker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_organizer(update.effective_user.id):
        await update.message.reply_text("Нет доступа")
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            "Использование: /add_speaker @username"
        )
        return
    username = args[0].lstrip("@")
    user = await find_and_set_speaker(username)
    if not user:
        await update.message.reply_text(
            f"Пользователь @{username} не найден. Нужно сначала написать боту /start"
        )
        return
    await update.message.reply_text(f"@{username} теперь спикер!")


# --- set_schedule (ConversationHandler) ---


@sync_to_async
def get_all_users():
    return list(TelegramUser.objects.all())


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_organizer(update.effective_user.id):
        return

    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Использование: /broadcast <текст>")
        return

    users = await get_all_users()
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u.user_id, text=text)
            sent += 1
        except Exception:
            pass  # пользователь заблокировал бота

    await update.message.reply_text(
        f"Сообщение отправлено {sent} из {len(users)} пользователям"
    )


async def set_schedule_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    if not await is_organizer(update.effective_user.id):
        await update.message.reply_text("Нет доступа")
        return ConversationHandler.END
    await update.message.reply_text("Название доклада?")
    return TITLE


async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text
    await update.message.reply_text("Время начала? (например, 14:00)")
    return START_TIME


async def get_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        hour, minute = map(int, text.split(":"))
        now = timezone.localtime()
        start_dt = now.replace(
            hour=hour, minute=minute, second=0, microsecond=0
        )
    except (ValueError, AttributeError):
        await update.message.reply_text(
            "Неверный формат. Напиши время так: 14:00"
        )
        return START_TIME
    context.user_data["start_time"] = start_dt
    await update.message.reply_text("Время конца? (например, 15:00)")
    return END_TIME


async def get_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        hour, minute = map(int, text.split(":"))
        now = timezone.localtime()
        end_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    except (ValueError, AttributeError):
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
    username = update.message.text.strip().lstrip("@")
    speaker = await find_speaker_by_username(username)
    if not speaker:
        await update.message.reply_text(
            f"Пользователь @{username} не найден. Убедись, что он написал /start боту."
        )
        return SPEAKER
    if speaker.role != "speaker":
        await update.message.reply_text(
            f"@{username} не является спикером. Сначала назначь через /add_speaker @{username}"
        )
        return SPEAKER
    context.user_data["speaker_id"] = speaker.user_id
    title = context.user_data["title"]
    await update.message.reply_text(f"Добавить доклад «{title}»? (да/нет)")
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    if text == "да":
        create = sync_to_async(db_direct.create_event)
        await create(
            context.user_data["speaker_id"],
            context.user_data["title"],
            context.user_data["start_time"],
            context.user_data["end_time"],
        )
        await update.message.reply_text("Доклад добавлен!")
    elif text == "нет":
        await update.message.reply_text("Отменено.")
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("Напиши да или нет")
        return CONFIRM


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    context.user_data.clear()
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("set_schedule", set_schedule_start)],
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
    fallbacks=[CommandHandler("cancel", cancel)],
)

organizer_handlers = [
    CommandHandler("admin", admin_panel),
    CommandHandler("add_speaker", add_speaker),
    CommandHandler("broadcast", broadcast),
    conv_handler,
]
