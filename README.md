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

## Текущее состояние

### Уже реализовано

| Роль | Команда | Статус |
|------|---------|--------|
| Гость | `/start` — меню: программа, задать вопрос | ✅ |
| Гость | "Программа" — список докладов | ✅ |
| Гость | "Задать вопрос" — выбор активного доклада → текст вопроса | ✅ |
| Организатор | `/admin` — проверка роли | ✅ |
| Организатор | `/add_speaker @username` — назначить спикера | ✅ |
| Админка | Django `/admin/` — управление ролями, is_active | ✅ |
| Админка | TelegramUser в админке (выбор роли из списка) | ✅ |
| — | `seed.py` — тестовые данные | ✅ |
| — | `is_active` — ручное управление активным докладчиком | ✅ |

### В разработке / запланировано

| Роль | Команда | Кто |
|------|---------|-----|
| Спикер | `/questions` — список вопросов | B |
| Спикер | `/answer <id> <текст>` — ответить на вопрос | B |
| Организатор | `/set_schedule` — пошаговое создание расписания | C |
| Организатор | `/broadcast` — рассылка всем пользователям | C |
| — | Уведомление организаторам о новом вопросе | B или C |

## Ветки

- `main` — защищённая, актуальная версия, PRы от всех разработчиков
- `feature/guest` — гость и спикер
- `feature/organizer` — организатор

Структура проекта — в `STRUCTURE.md`.
