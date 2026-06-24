import os
import django
from datetime import datetime

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"  # nosec
django.setup()

from django.utils import timezone
from bot.models.telegram_user import TelegramUser
from bot.models.event import Event
from bot.models.question import Question


def _dt(hour: int, minute: int = 0) -> datetime:
    return timezone.make_aware(datetime(2026, 6, 24, hour, minute))


def seed():
    # --- Пользователи ---
    org, _ = TelegramUser.objects.update_or_create(
        user_id=100,
        defaults={
            "role": "organizer",
            "username": "org",
            "full_name": "Организатор",
        },
    )
    s1, _ = TelegramUser.objects.update_or_create(
        user_id=200,
        defaults={
            "role": "speaker",
            "username": "ivanov",
            "full_name": "Иван Иванов",
        },
    )
    s2, _ = TelegramUser.objects.update_or_create(
        user_id=300,
        defaults={
            "role": "speaker",
            "username": "petrov",
            "full_name": "Пётр Петров",
        },
    )

    # --- События ---
    Event.objects.update_or_create(
        id=1,
        defaults={
            "speaker": s1,
            "title": "Async Python: от основ до продакшена",
            "start_time": _dt(14, 0),
            "end_time": _dt(15, 0),
        },
    )
    Event.objects.update_or_create(
        id=2,
        defaults={
            "speaker": s2,
            "title": "Django ORM: советы бывалого",
            "start_time": _dt(15, 0),
            "end_time": _dt(16, 0),
        },
    )

    # --- Вопросы ---
    Question.objects.update_or_create(
        id=1,
        defaults={
            "from_user": org,
            "to_speaker": s1,
            "text": "С чего начать изучение asyncio?",
            "answer": "Начни с официальной документации и простых примеров.",
            "created_at": _dt(14, 15),
        },
    )
    Question.objects.update_or_create(
        id=2,
        defaults={
            "from_user": org,
            "to_speaker": s1,
            "text": "Асинхронность подойдёт для микросервисов?",
            "answer": None,
            "created_at": _dt(14, 30),
        },
    )
    Question.objects.update_or_create(
        id=3,
        defaults={
            "from_user": org,
            "to_speaker": s2,
            "text": "ORM или raw SQL — что выбрать для нового проекта?",
            "answer": None,
            "created_at": _dt(15, 10),
        },
    )

    print("Test data loaded")


if __name__ == "__main__":
    seed()
