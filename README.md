# МОГГНИТ · Smart Caspian Transit

Предиктивный цифровой двойник мультимодальной перевозки (каспийское звено «Север — Юг»).

**Веб-диспетчерская · Flutter-приложение · Telegram-бот · общий FastAPI.**

> Расписания, прогнозы и статусы документов — демонстрационные / синтетические.  
> Тестовые статусы документов **не** являются таможенным разрешением.

---

## Состав проекта

| Часть | Стек | Порт |
|--------|------|------|
| `backend/` | FastAPI + SQLite | `8002` |
| `frontend/` | React + TypeScript (Vite) | `5173` |
| `mobile/` | Flutter | симулятор / устройство |
| `backend/tg_bot/` | Telegram long-polling | — |

API-ключ для локального запуска: **`demo-key`** (заголовок `X-API-Key`).

---

## Клонирование

```bash
git clone https://github.com/AlCapone05/smart-caspian-transit.git
cd smart-caspian-transit
```

Дальше запустите **backend**, затем **frontend** (или mobile / Telegram-бот) по разделам ниже.

---

## GitHub Codespaces (запуск в облаке)

1. Откройте репозиторий: https://github.com/AlCapone05/smart-caspian-transit  
2. Нажмите **Code → Codespaces → Create codespace on main**.  
3. Дождитесь сборки контейнера (`post-create` поставит Python/Node зависимости).  
4. Стек **backend + frontend** стартует автоматически после подключения.  
5. Во вкладке **Ports** откройте порт **5173** (Open in Browser).

Полезные команды внутри Codespace:

```bash
./scripts/codespaces-up.sh    # запустить API :8002 и UI :5173
./scripts/codespaces-down.sh  # остановить
```

- UI: порт `5173`  
- API / Swagger: порт `8002` → `/docs`  
- API-ключ: `demo-key`

Flutter и Telegram-бот в Codespaces не обязательны (бот — через `python -m tg_bot` при наличии `TELEGRAM_BOT_TOKEN`).


---

## Требования

- **Python** 3.11+ (рекомендуется 3.13)
- **Node.js** 20+ и npm
- **Flutter** 3.2+ (для мобильного приложения)
- macOS / Linux (инструкция ниже — macOS)
- Опционально: Docker, Telegram Bot Token, DeepSeek API key

---

## 1. Backend (API)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# конфиг
cp .env.example .env
# при необходимости отредактируйте .env

export PYTHONPATH=.
uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Проверка:

- Swagger: http://127.0.0.1:8002/docs  
- Health: http://127.0.0.1:8002/api/v1/health  
- Заголовок: `X-API-Key: demo-key`

При смене схемы БД можно сбросить локальную SQLite:

```bash
rm -f sct.db
```

---

## 2. Frontend (сайт)

В **отдельном** терминале:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Откройте: **http://127.0.0.1:5173**

Vite проксирует `/api` → `http://127.0.0.1:8002`, поэтому backend должен быть уже запущен.

### Одним скриптом (если есть `.venv` и `node_modules`)

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

---

## 3. Мобильное приложение (Flutter)

1. Запустите backend на `8002`.
2. Затем:

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd mobile
flutter pub get

# iOS Simulator
flutter run -d iPhone --dart-define=API_BASE=http://127.0.0.1:8002/api/v1

# Реальный iPhone (тот же Wi‑Fi, что и Mac)
# backend: uvicorn ... --host 0.0.0.0 --port 8002
flutter run --dart-define=API_BASE=http://IP_ВАШЕГО_MAC:8002/api/v1
```

Подробнее: [`mobile/README.md`](mobile/README.md).

---

## 4. Telegram-бот

1. Backend должен работать на `8002`.
2. В `backend/.env` добавьте:

```env
TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
SCT_API_BASE=http://127.0.0.1:8002/api/v1
API_KEY=demo-key
```

3. Запуск:

```bash
cd backend
source .venv/bin/activate
export PYTHONPATH=.
python -m tg_bot
```

Команды: `/start`, `/summary`, `/alerts`, `/storms`, `/status SCT-…`, `/routes`, `/subscribe`.  
Подробнее: [`backend/tg_bot/README.md`](backend/tg_bot/README.md).

---

## 5. Docker Compose (опционально)

```bash
docker compose up --build
```

- UI: http://localhost:5173  
- API: http://localhost:8000  
- Postgres: `sct/sct@localhost:5432/sct`

---

## Переменные окружения (`backend/.env`)

Скопируйте из примера:

```bash
cp backend/.env.example backend/.env
```

| Переменная | Назначение |
|------------|------------|
| `API_KEY` | Ключ доступа к API (`demo-key`) |
| `DATABASE_URL` | SQLite или Postgres |
| `TELEGRAM_BOT_TOKEN` | Токен Telegram-бота |
| `DEEPSEEK_API_KEY` | Ассистент (опционально) |

**Не коммитьте** файл `.env` — он в `.gitignore`.

---

## Быстрый демо-сценарий

1. Откройте **Обзор** → активный груз → карта Каспия.  
2. При шторме выберите **безопасный обход** маршрута.  
3. **Перевозки** → карточка → сценарий «Шторм» / альтернативы.  
4. **Документы** → ТН ВЭД / файл / предпроверка.  
5. **Сравнение** и **Аналитика** — KPI и рейтинг.

---

## Структура репозитория

```
backend/          FastAPI, модели, трекинг, TG-бот
frontend/         React UI диспетчерской
mobile/           Flutter-приложение
docs/             PRODUCT / ASSUMPTIONS / презентация
scripts/          dev.sh, smoke_e2e.sh
docker-compose.yml
```

Документация продукта: [`docs/PRODUCT.md`](docs/PRODUCT.md) · допущения: [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md).

---

## Лицензия / хакатон

Проект подготовлен для хакатона МОГГНИТ / Smart Caspian Transit. Данные синтетические, для демонстрации диспетчерского сценария.
