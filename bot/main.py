from telegram.ext import ApplicationBuilder

from bot.config import BOT_TOKEN


def main() -> None:
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # TODO: register handlers (will be added by B and C)

    app.run_polling()


if __name__ == "__main__":
    main()
