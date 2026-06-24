from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from bot.services.auth import is_organizer


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_organizer(update.effective_user.id):
        await update.message.reply_text("Нет доступа")
        return
    await update.message.reply_text("Ты организатор!")


async def add_speaker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_organizer(update.effective_user.id):
        return
    args = context.args
    if not args:
        await update.message.reply_text(
            "Использование: /add_speaker @username"
        )
        return
    username = args[0].lstrip("@")
    user = TelegramUser.objects.filter(username=username).first()
    if not user:
        await update.message.reply_text(
            f"Пользователь @{username} не найден. Нужно сначала написать боту /start"
        )
        return
    user.role = "speaker"
    user.save()
    await update.message.reply_text(f"@{username} теперь спикер!")


organizer_handlers = [
    CommandHandler("admin", admin_panel),
    CommandHandler("add_speaker", add_speaker),
]
