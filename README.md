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
python -m bot.main

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
