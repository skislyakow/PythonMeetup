from telegram import ReplyKeyboardMarkup


BUTTON_ACTIVATE = "📅 Управление событиями"
BUTTON_BROADCAST = "📢 Рассылка"
BUTTON_SCHEDULE = "✏️ Создать доклад"
BUTTON_ASK = "❓ Задать вопрос"
BUTTON_CLOSE = "🔒 Закрыть меню"


def organizer_keyboard():
    return ReplyKeyboardMarkup(
        [
            [BUTTON_ACTIVATE, BUTTON_BROADCAST],
            [BUTTON_SCHEDULE, BUTTON_ASK],
            [BUTTON_CLOSE],
        ],
        resize_keyboard=True,
    )
