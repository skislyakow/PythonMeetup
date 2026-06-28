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


_MONTH_NAMES = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def format_event_line(e, *, with_status=False):
    marker = "\U0001f7e2" if e.is_active else "\U00002b1b"
    base = f"{marker} {e.start_time.strftime('%d.%m %H:%M')} — {e.speaker.full_name}: {e.title}"
    if with_status and e.is_active:
        base += " (сейчас активен)"
    return base


def format_schedule(events):
    if not events:
        return "📅 <b>Программа:</b>\n\nНет предстоящих докладов."

    lines = ["📅 <b>Программа:</b>\n"]
    current_key = None
    for e in events:
        d = e.start_time
        key = (d.day, d.month, d.year)
        if key != current_key:
            current_key = key
            lines.append(f"\n——— <b>{d.day} {_MONTH_NAMES[d.month]}</b> ———\n")

        marker = "\U0001f7e2" if e.is_active else "\U00002b1b"
        status = " <b>(сейчас)</b>" if e.is_active else ""
        lines.append(
            f"{marker} <b>{d.strftime('%H:%M')}</b> — {e.speaker.full_name}: {e.title}{status}"
        )

    return "\n".join(lines)
