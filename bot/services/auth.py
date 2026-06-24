from asgiref.sync import sync_to_async
from bot.models.telegram_user import TelegramUser


@sync_to_async
def is_organizer(user_id: int) -> bool:
    user = TelegramUser.objects.filter(user_id=user_id).first()
    return user is not None and user.role == "organizer"
