# МОГГНИТ · Flutter — запуск

Мобильная диспетчерская к тому же FastAPI, что веб и Telegram-бот  
(`X-API-Key: demo-key`).

---

## 0. Что нужно один раз

### Flutter
У вас SDK уже есть:

```bash
export PATH="$HOME/flutter/bin:$PATH"
flutter --version
```

Добавь в `~/.zshrc`, чтобы не писать PATH каждый раз:

```bash
export PATH="$HOME/flutter/bin:$PATH"
```

### Backend
API должен быть запущен на порту **8002**.

### Для iOS (симулятор / iPhone)
1. **Xcode** из App Store (уже есть).
2. Симулятор iOS: Xcode → **Settings → Components** → скачать **iOS Simulator**.
3. **CocoaPods** (нужен для iOS-плагинов):

```bash
sudo gem install cocoapods
# или: brew install cocoapods
```

4. Принять лицензии Xcode:

```bash
sudo xcodebuild -license accept
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

### Для Android (опционально)
Android Studio + SDK. Сейчас Android toolchain не установлен — для хакатона достаточно iOS/macOS.

---

## 1. Запуск API

Из корня проекта:

```bash
cd "/Users/adam/Desktop/проект хакатон/backend"
source .venv/bin/activate
export PYTHONPATH=.
```

### Только симулятор / этот Mac
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

### Реальный iPhone в той же Wi‑Fi
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Проверка:
```bash
curl -s -H "X-API-Key: demo-key" http://127.0.0.1:8002/api/v1/health
```
Должно вернуть `"status":"ok"`.

---

## 2. Запуск приложения

```bash
export PATH="$HOME/flutter/bin:$PATH"
cd "/Users/adam/Desktop/проект хакатон/mobile"
flutter pub get
flutter devices
```

### Вариант A — macOS (работает уже сейчас)
Пока нет iOS Simulator, можно открыть UI на Mac:

```bash
flutter run -d macos
```

API: `http://127.0.0.1:8002/api/v1` (дефолт в коде).

### Вариант B — iOS Simulator
После установки runtime в Xcode:

```bash
open -a Simulator
flutter devices
flutter run -d iPhone
# или: flutter run   и выбрать симулятор в списке
```

Симулятор ходит на `127.0.0.1` Mac — API с `--host 127.0.0.1` достаточно.

### Вариант C — реальный iPhone
1. iPhone и Mac в одной Wi‑Fi.  
2. API с `--host 0.0.0.0`.  
3. IP Mac (пример):

```bash
ipconfig getifaddr en0
# например 192.168.88.216
```

4. На iPhone: Settings → Developer / доверие компьютеру при первой прошивке.  
5. Запуск:

```bash
flutter run -d <id_айфона> \
  --dart-define=API_BASE=http://192.168.88.216:8002/api/v1
```

Подставь свой IP вместо `192.168.88.216`.

Ключ API по умолчанию `demo-key`. Другой ключ:

```bash
flutter run --dart-define=API_BASE=http://192.168.88.216:8002/api/v1 \
  --dart-define=API_KEY=demo-key
```

---

## 3. Что должно открыться

Нижнее меню:
- **Обзор** — KPI + список грузов (`/overview`)
- **Грузы** — список + поиск (`/shipments`)
- **Алерты** — уведомления (`/notifications`)

Тап по грузу → карточка (`/shipments/{id}`).

Потяни вниз для refresh.

---

## 4. Типичные проблемы

| Симптом | Что делать |
|--------|------------|
| `No devices` | `flutter devices`; для iOS — поставить Simulator runtime в Xcode |
| `CocoaPods not installed` | `sudo gem install cocoapods` затем `cd ios && pod install` |
| Нет связи с API на телефоне | API на `0.0.0.0`, верный IP в `--dart-define`, один Wi‑Fi, фаервол macOS |
| `Connection refused` в симуляторе | Backend не запущен или другой порт |
| Белый экран / ATS | В `ios/Runner/Info.plist` уже есть `NSAllowsLocalNetworking` |
| Конфликт портов | `lsof -iTCP:8002 -sTCP:LISTEN` |

Проверка API с телефона (Safari):  
`http://IP_MAC:8002/api/v1/health` — должна открыться JSON-страница.

---

## 5. Полезные команды

```bash
flutter clean && flutter pub get   # если странные ошибки сборки
flutter run -d macos               # быстрый UI без симулятора
flutter logs                       # логи приложения
cd ios && pod install && cd ..     # после смены нативных плагинов
```
