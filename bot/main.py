import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
django.setup()

from telegram.ext import ApplicationBuilder
from bot.config import BOT_TOKEN, ORGANIZER_IDS
from bot.handlers.organizer import organizer_handlers
from bot.handlers.guest import guest_handlers
from bot.handlers.speaker import speaker_handlers
from bot.models.telegram_user import TelegramUser


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    # TODO: подключить хендлеры
    # from bot.handlers.guest import handlers as guest_handlers
    # from bot.handlers.speaker import handlers as speaker_handlers
    # from bot.handlers.organizer import handlers as organizer_handlers
    for h in guest_handlers:
        app.add_handler(h)
    for h in speaker_handlers:
        app.add_handler(h)
    for h in organizer_handlers:
        app.add_handler(h)

    for uid in ORGANIZER_IDS:
        TelegramUser.objects.update_or_create(
            user_id=uid, defaults={"role": "organizer"}
        )
    print(
        "Организаторы в БД:",
        list(
            TelegramUser.objects.filter(role="organizer").values_list(
                "user_id", flat=True
            )
        ),
    )
    app.run_polling()


if __name__ == "__main__":
    main()