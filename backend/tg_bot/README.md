# МОГГНИТ · Telegram-бот

Карманный пульт диспетчера для Smart Caspian Transit.

## Возможности

Бот берёт данные **с того же API, что и сайт** (`/overview`, `/shipments`, `/tracking`, `/notifications`).

- Сводка Обзора (`/summary`)
- Уведомления сайта (`/alerts`)
- Live-штормы с карты (`/storms`)
- Статус груза (`/status SCT-2048`)
- Обходы маршрута (`/routes SCT-2048`)
- Пуш новых событий с сайта (`/subscribe`)
- Вопросы по проекту → `/assistant/chat`

## Запуск

1. API на `8002` должен работать.
2. В `backend/.env`:

```
TELEGRAM_BOT_TOKEN=...
SCT_API_BASE=http://127.0.0.1:8002/api/v1
API_KEY=demo-key
```

3. Из папки `backend`:

```bash
.venv/bin/pip install python-dotenv httpx
.venv/bin/python -m tg_bot
```

Бот использует long polling через Telegram Bot API + ваш FastAPI (`httpx`).

Токен не коммитьте в git (файл `.env` в `.gitignore`).
