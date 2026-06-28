from telegram import ReplyKeyboardMarkup
from bot.services.user_utils import get_user_role, has_active_speaker

# ─── Константы кнопок ─────────────────────────────────

BUTTON_SCHEDULE = "📅 Программа"
BUTTON_ASK = "❓ Задать вопрос"
BUTTON_SPEAKER = "📥 Мои вопросы (Спикер)"
BUTTON_ACTIVATE = "📅 Управление событиями"
BUTTON_BROADCAST = "📢 Рассылка"
BUTTON_SCHEDULE_CREATE = "✏️ Создать доклад"
BUTTON_CLOSE = "🔒 Закрыть меню"
BUTTON_DONATE = "❤️ Поддержать проект"
BUTTON_HELP = "ℹ️ Справка"


def guest_keyboard(*, show_ask=True) -> ReplyKeyboardMarkup:
    row = [BUTTON_SCHEDULE]
    if show_ask:
        row.append(BUTTON_ASK)
    return ReplyKeyboardMarkup(
        [row, [BUTTON_DONATE, BUTTON_HELP]],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def speaker_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[BUTTON_SCHEDULE, BUTTON_SPEAKER, BUTTON_DONATE], [BUTTON_HELP]],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие...",
    )


def organizer_keyboard(*, show_ask=True) -> ReplyKeyboardMarkup:
    row1 = [BUTTON_SCHEDULE]
    if show_ask:
        row1.append(BUTTON_ASK)
    return ReplyKeyboardMarkup(
        [
            row1,
            [BUTTON_ACTIVATE, BUTTON_BROADCAST],
            [BUTTON_SCHEDULE_CREATE],
            [BUTTON_HELP, BUTTON_CLOSE],
        ],
        resize_keyboard=True,
    )


async def get_role_based_keyboard(user_id: int, *, show_ask: bool | None = None) -> ReplyKeyboardMarkup:
    role = await get_user_role(user_id)
    if show_ask is None:
        show_ask = await has_active_speaker()
    if role == "organizer":
        return organizer_keyboard(show_ask=show_ask)
    elif role == "speaker":
        return speaker_keyboard()
    return guest_keyboard(show_ask=show_ask)
