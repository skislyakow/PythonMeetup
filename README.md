# PythonMeetup Bot

Telegram-бот для Python-митапов.

## Установка

```bash
git clone <repo-url>
cd PythonMeetup
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполнить BOT_TOKEN и ORGANIZER_IDS
python manage.py migrate   # создать таблицы в SQLite
python -m bot.main         # запустить бота

> Каждый разработчик создаёт **своего тестового бота** через [@BotFather](https://t.me/BotFather) (`/newbot`) и вписывает свой токен в `.env`. Так никто не мешает друг другу.
> В `ORGANIZER_IDS` каждый пишет свой Telegram ID — бот при старте сделает вас организатором.
```

## Ветки

- `main` — защищённая, PRы от всех разработчиков
Просто примеры
- `feature/guest` — гость и спикер
- `feature/speaker` - спикер
- `feature/organizer` — организатор

Структура — в `STRUCTURE.md`.


Вот пошагово, что сделать:
1. Создать .env с тестовым токеном
Скопируй .env.example → .env и впиши токен бота от @BotFather (https://t.me/BotFather) и свой Telegram ID:
BOT_TOKEN=123456:ABCdef...
ORGANIZER_IDS=123456789
DJANGO_SECRET_KEY=любая_строка_123

сделать миграцию
python manage.py migrate

2. Запустить бота
python -m bot.main
Если всё ок — бот запустится и начнёт polling (ничего не сломается, хотя хендлеры пустые).
4. Проверить админку (она особо щас не нужна но можно просто проверить что БД работает)
python manage.py createsuperuser

Введёшь логин, email (можно пропустить), пароль — и готово для входа в /admin/.

python manage.py runserver

Открыть http://127.0.0.1:8000/admin/ — зайти под созданным суперпользователем.
5. Написать тестовый хендлер (по аналогии делается у спикера и организатора, но это у каждого свой)
В bot/handlers/guest.py добавь:
from telegram.ext import CommandHandler
from bot.models.telegram_user import TelegramUser

def start(update, context):
    user, _ = TelegramUser.objects.get_or_create(
        user_id=update.effective_user.id,
        defaults={"full_name": update.effective_user.full_name},
    )
    update.message.reply_text(f"Привет, {user.full_name}! Ты в базе ✅")

handlers = [CommandHandler("start", start)]
В bot/main.py раскомментируй подключение хендлеров и перезапусти бота. 
Остановить: Ctrl+C в терминале, где запущен бот.
Запустить заново:
python -m bot.main
Напиши /start в Telegram.