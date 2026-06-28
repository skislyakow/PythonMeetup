from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from asgiref.sync import sync_to_async

from bot.models.telegram_user import TelegramUser
from bot.services.keyboards import (
    guest_keyboard,
    speaker_keyboard,
    organizer_keyboard,
    BUTTON_DONATE,
)

WAITING_FOR_AMOUNT = 1


@sync_to_async
def get_user_role(user_id):
    try:
        user = TelegramUser.objects.get(user_id=user_id)
        return user.role
    except TelegramUser.DoesNotExist:
        return "guest"


async def start_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💖 Спасибо за желание поддержать проект!\n\n"
        "Введите сумму доната в рублях (целое число, например: 100, 500, 1000):\n\n"
        "<i>Отправьте /cancel чтобы отменить</i>",
        parse_mode="HTML",
    )
    return WAITING_FOR_AMOUNT


async def process_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() or int(text) < 10:
        await update.message.reply_text(
            "Пожалуйста, введите корректную сумму (только цифры, от 10 рублей):"
        )
        return WAITING_FOR_AMOUNT

    amount = int(text)
    user = update.effective_user
    role = await get_user_role(user.id)

    if role == "organizer":
        markup = organizer_keyboard()
    elif role == "speaker":
        markup = speaker_keyboard()
    else:
        markup = guest_keyboard()

    await update.message.reply_text(
        f"✅ <b>Спасибо за вашу поддержку, {user.full_name}!</b>\n\n"
        f"❤️ Ваш донат в размере <b>{amount} руб.</b> успешно принят.\n\n"
        f"<i>Это тестовый режим — реального списания не произошло.</i>",
        parse_mode="HTML",
        reply_markup=markup,
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    role = await get_user_role(user.id)
    if role == "organizer":
        markup = organizer_keyboard()
    elif role == "speaker":
        markup = speaker_keyboard()
    else:
        markup = guest_keyboard()
    await update.message.reply_text("❌ Донат отменён.", reply_markup=markup)
    context.user_data.clear()
    return ConversationHandler.END


donate_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Text([BUTTON_DONATE]), start_donate),
    ],
    states={
        WAITING_FOR_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_amount)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
