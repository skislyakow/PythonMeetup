from asgiref.sync import sync_to_async
from django.utils import timezone

from bot.models.telegram_user import TelegramUser
from bot.models.event import Event


@sync_to_async
def get_user_role(user_id):
    try:
        user = TelegramUser.objects.get(user_id=user_id)
        return user.role
    except TelegramUser.DoesNotExist:
        return "guest"


@sync_to_async
def get_active_speaker():
    return Event.objects.filter(is_active=True).select_related("speaker").first()


@sync_to_async
def get_all_events():
    return list(
        Event.objects.all().select_related("speaker").order_by("start_time")
    )


@sync_to_async
def has_active_speaker():
    return Event.objects.filter(is_active=True).exists()


@sync_to_async
def get_upcoming_speaker_events_count(user_id):
    return Event.objects.filter(
        speaker_id=user_id, start_time__gt=timezone.now()
    ).count()


@sync_to_async
def set_user_role(user_id, role):
    TelegramUser.objects.filter(user_id=user_id).update(role=role)


@sync_to_async
def get_organizers():
    return list(TelegramUser.objects.filter(role="organizer"))
