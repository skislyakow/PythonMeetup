from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from bot.services.user_utils import get_user_role
from bot.services.keyboards import get_role_based_keyboard, BUTTON_HELP

HELP_TEXTS = {
    "guest": (
        "📖 <b>Справка по Python Meetup</b>\n\n"
        "Вы — <b>гость</b>. Доступные действия:\n\n"
        "📅 <b>Программа</b> — расписание всех докладов\n"
        "❓ <b>Задать вопрос</b> — вопрос текущему докладчику\n"
        "❤️ <b>Поддержать проект</b> — донат (тестовый режим)\n\n"
        "Команды:\n"
        "/start — перезапуск\n"
        "/help — эта справка"
    ),
    "speaker": (
        "📖 <b>Справка по Python Meetup</b>\n\n"
        "Вы — <b>спикер</b>. Доступные действия:\n\n"
        "📅 <b>Программа</b> — расписание\n"
        "📥 <b>Мои вопросы (Спикер)</b> — ответы на вопросы от гостей\n"
        "❤️ <b>Поддержать проект</b> — донат\n\n"
        "Команды:\n"
        "/speaker — панель спикера\n"
        "/help — эта справка"
    ),
    "organizer": (
        "📖 <b>Справка по Python Meetup</b>\n\n"
        "Вы — <b>организатор</b>. Доступные действия:\n\n"
        "📅 <b>Программа</b> — расписание\n"
        "📅 <b>Управление событиями</b> — активировать/редактировать доклады\n"
        "📢 <b>Рассылка</b> — сообщение всем пользователям\n"
        "✏️ <b>Создать доклад</b> — новое событие\n"
        "🔒 <b>Закрыть меню</b> — убрать клавиатуру\n\n"
        "Команды:\n"
        "/admin — панель организатора\n"
        "/help — эта справка"
    ),
}


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    role = await get_user_role(user.id)
    text = HELP_TEXTS.get(role, HELP_TEXTS["guest"])
    markup = await get_role_based_keyboard(user.id)
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)


help_handlers = [
    CommandHandler("help", help_command),
    MessageHandler(filters.Text([BUTTON_HELP]), help_command),
]
