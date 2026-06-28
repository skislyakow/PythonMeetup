from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from bot.services.keyboards import (
    get_role_based_keyboard,
    BUTTON_DONATE,
)
from bot.services.user_utils import get_organizers

WAITING_FOR_AMOUNT = 1


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

    markup = await get_role_based_keyboard(user.id)

    await update.message.reply_text(
        f"✅ <b>Спасибо за вашу поддержку, {user.full_name}!</b>\n\n"
        f"❤️ Ваш донат в размере <b>{amount} руб.</b> успешно принят.\n\n"
        f"<i>Это тестовый режим — реального списания не произошло.</i>",
        parse_mode="HTML",
        reply_markup=markup,
    )

    organizers = await get_organizers()
    for org in organizers:
        try:
            await context.bot.send_message(
                chat_id=org.user_id,
                text=(
                    f"💰 <b>Донат!</b>\n\n"
                    f"Пользователь: {user.full_name}"
                    f"{' (@' + user.username + ')' if user.username else ''}\n"
                    f"Сумма: <b>{amount} руб.</b>"
                ),
                parse_mode="HTML",
            )
        except Exception:
            pass

    return ConversationHandler.END



async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    markup = await get_role_based_keyboard(update.effective_user.id)
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
