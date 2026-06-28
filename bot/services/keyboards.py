from telegram import ReplyKeyboardMarkup

# ─── Константы кнопок ─────────────────────────────────

BUTTON_SCHEDULE = "📅 Программа"
BUTTON_ASK = "❓ Задать вопрос"
BUTTON_SPEAKER = "📥 Мои вопросы (Спикер)"
BUTTON_ACTIVATE = "📅 Управление событиями"
BUTTON_BROADCAST = "📢 Рассылка"
BUTTON_SCHEDULE_CREATE = "✏️ Создать доклад"
BUTTON_CLOSE = "🔒 Закрыть меню"
BUTTON_DONATE = "❤️ Поддержать проект"


def guest_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BUTTON_SCHEDULE, BUTTON_ASK], [BUTTON_DONATE]],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def speaker_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BUTTON_SCHEDULE, BUTTON_ASK], [BUTTON_SPEAKER, BUTTON_DONATE]],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def organizer_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [BUTTON_SCHEDULE, BUTTON_ASK],
            [BUTTON_ACTIVATE, BUTTON_BROADCAST],
            [BUTTON_SCHEDULE_CREATE],
            [BUTTON_CLOSE],
        ],
        resize_keyboard=True,
    )
