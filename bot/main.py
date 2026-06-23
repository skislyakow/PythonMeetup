import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
django.setup()

from telegram.ext import ApplicationBuilder
from bot.config import BOT_TOKEN


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # TODO: подключить хендлеры
    # from bot.handlers.guest import handlers as guest_handlers
    # from bot.handlers.speaker import handlers as speaker_handlers
    # from bot.handlers.organizer import handlers as organizer_handlers
    # for h in guest_handlers + speaker_handlers + organizer_handlers:
    #     app.add_handler(h)

    app.run_polling()


if __name__ == "__main__":
    main()
