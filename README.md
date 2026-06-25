# PythonMeetup Bot

Telegram-бот для Python-митапов. Гости задают вопросы спикерам, организаторы управляют программой через админку Django.

## Быстрый старт

```bash
git clone <repo-url>
cd PythonMeetup
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполнить BOT_TOKEN и свой Telegram ID
python manage.py migrate
python -m bot.seed     # загрузить тестовые данные
python -m bot.main     # запустить бота
```

Каждый разработчик создаёт **своего тестового бота** через [@BotFather](https://t.me/BotFather) (`/newbot`) и вписывает свой токен в `.env`. В `ORGANIZER_IDS` — свой Telegram ID (узнать: @userinfobot).

## Админка Django

```bash
python manage.py createsuperuser   # создать админа (1 раз)
python manage.py runserver         # запустить админку
```

Открыть `http://127.0.0.1:8000/admin/` — там можно:
- Менять роли пользователям (`guest` / `speaker` / `organizer`)
- Включать активного докладчика (галочка `is_active`)
- Смотреть вопросы

## Роли и команды

| Роль | Команды бота |
|------|-------------|
| **Гость** | `/start` — меню: задать вопрос, программа |
| **Спикер** | `/questions` — список вопросов, `/answer <id> <текст>` |
| **Организатор** | `/add_speaker @username`, `/set_schedule`, `/broadcast` |

## Ветки

- `main` — защищённая, актуальная версия, PRы от всех разработчиков
- `feature/guest` — гость и спикер
- `feature/organizer` — организатор

Структура проекта — в `STRUCTURE.md`.
