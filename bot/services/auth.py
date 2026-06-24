from bot.models.telegram_user import TelegramUser

def is_organizer(user_id: int) -> bool:
    user = TelegramUser.objects.filter(user_id=user_id).first()
    return user is not None and user.role = 'organizer'