from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from asgiref.sync import sync_to_async

from bot.services.auth import is_organizer
from bot.models.telegram_user import TelegramUser


@sync_to_async
def find_and_set_speaker(username):
    user = TelegramUser.objects.filter(username=username).first()
    if user:
        user.role = "speaker"
        user.save()
    return user


@sync_to_async
def get_speaker_events(speaker_id):
    from bot.models.event import Event

    return list(Event.objects.filter(speaker_id=speaker_id))


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    if not await is_organizer(update.effective_user.id):
        await update.message.reply_text("Нет доступа")
        return
    await update.message.reply_text("Ты организатор!")


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


organizer_handlers = [
    CommandHandler("admin", admin_panel),
    CommandHandler("add_speaker", add_speaker),
]
