# Smart Caspian Transit — MVP Product & Architecture Brief

**Статус данных:** все расписания, прогнозы и статусы документов в MVP — **демонстрационные / синтетические**, пока не подключены подтверждённые внешние источники.  
**Не означает:** реальное таможенное разрешение, реальное качество модели на проде, подтверждённую экономию.

---

## 1. Продукт и ценность

**Smart Caspian Transit** — предиктивный цифровой двойник мультимодальной перевозки в каспийском звене коридора «Север — Юг».

**Для кого:** логист / диспетчер мультимодального оператора.

**Проблема:** рассинхронизация ж/д ↔ порт ↔ море ↔ авто, очереди и погода ломают стыковки; документы и статусы разрознены; сравнение альтернатив делается вручную.

**Ценность MVP (один сквозной сценарий):**
1. Раньше увидеть риск пропустить морской рейс и пересчитать ETA с учётом следующего отправления.
2. Сравнить 2–3 допустимых плана по времени, стоимости и CO₂e в одном окне.
3. Проверить комплектность документов и обменять тестовые статусы через защищённый API (без претензии на юридическую силу).

**Формулировка ценности для защиты:** «Логист за минуты видит сорванную стыковку, новый ETA и выбирает план по времени / деньгам / выбросам — вместо часов ручной сверки».

---

## 2. Границы MVP и отложено

### Входит в MVP (72 ч)
- Список перевозок: статус, риск, план/прогноз ETA, задержка (ч).
- Карточка груза: маршрут (ж/д → РФ порт → море → IR порт → авто), таймлайн событий.
- Baseline-прогноз (историческая медиана по типу плеча / порту) + опциональный CatBoost при наличии синтетического history.
- Пересчёт связанных этапов при событии (погода, очередь, документы).
- Симулятор условий (демо-слайдеры).
- 2–3 альтернативы с расписаниями, перегрузкой, совместимостью; объяснение «нет допустимых».
- Проверка комплекта документов + тестовый API pre-declaration со статусами и audit log.
- Приближённый CO₂e с единицами и явными допущениями.
- Docker Compose (Postgres + API + UI).

### Отложено (не в первом MVP)
- Блокчейн, 3D / digital twin визуализация порта.
- Реальные интеграции: РЖД, портовые TOS, AIS, таможня, погодные API в проде.
- Вероятности / prediction intervals без калибровки.
- Оптимизация флота, биллинг, роли SSO enterprise.
- Полный граф коридора за пределами демо-сценария Каспия.
- Автовыбор «лучшего» плана без решения логиста.

---

## 3. Архитектура и схема данных

### 3.1 Архитектура (модульный монолит)

```
┌─────────────┐     REST/JSON      ┌──────────────────────────────────────┐
│  React UI   │ ◄────────────────► │  FastAPI monolith                     │
│  (Vite+TS)  │                    │  /shipments /events /simulate         │
└─────────────┘                    │  /documents /alternatives /predictions│
                                   │  modules: forecast | connections |    │
                                   │  routes | docs | co2 | simulator      │
                                   └──────────────┬───────────────────────┘
                                                  │
                                   ┌──────────────▼───────────────────────┐
                                   │  PostgreSQL (prod/compose)            │
                                   │  SQLite fallback (local без Docker)   │
                                   └──────────────────────────────────────┘
```

**Принципы:** один процесс API; доменная логика в `services/`; UI только отображает и вызывает API; синтетический seed явно помечен `data_quality=synthetic_demo`.

### 3.2 Сущности

| Сущность | Назначение |
|----------|------------|
| **Shipment** | Перевозка: груз, маршрут-план, статусы, план/факт/прогноз ETA |
| **TransportLeg** | Плечо: mode (rail/sea/road/port_handling), origin/dest, planned/actual/predicted times |
| **Port** | Порт: timezone, capacity proxy, handling norms |
| **ScheduledService** | Демо-расписание рейса/слота (НЕ реальное расписание линии) |
| **Event** | Факт/симуляция: weather, queue, doc_delay, arrival, departure |
| **WeatherForecast** | Прогноз погоды на момент `as_of` (доступность признака) |
| **Document** | Документ комплекта + статус pre-check (тестовый) |
| **Prediction** | Снимок прогноза: model, features_as_of, predicted_eta, delay_h, factors (ассоциации) |

**Разделение времён:**
- `planned_*` — план;
- `actual_*` — факт события;
- `predicted_*` — прогноз на `as_of_ts`;
- признаки только с `available_at <= as_of_ts` (без утечки из будущего).

**Часовые пояса:** хранение UTC; отображение в TZ порта/логиста (`Europe/Moscow`, `Asia/Tehran`).

### 3.3 ER (логически)

```
Shipment 1──* TransportLeg
Shipment 1──* Event
Shipment 1──* Document
Shipment 1──* Prediction
Port 1──* ScheduledService
Port 1──* WeatherForecast
TransportLeg *──1 Port (origin/dest, nullable для pure legs)
Event *──? TransportLeg
```

---

## 4. Контракты API (примеры)

Base: `http://localhost:8000/api/v1`  
Auth MVP: заголовок `X-API-Key: demo-key` (тестовый).

### GET `/shipments`
```json
{
  "items": [{
    "id": "shp_demo_001",
    "reference": "SCT-2026-001",
    "status": "in_transit",
    "risk_level": "high",
    "planned_eta": "2026-11-18T14:00:00Z",
    "predicted_eta": "2026-11-20T06:00:00Z",
    "delay_hours": 40.0,
    "data_quality": "synthetic_demo",
    "missed_connection": true
  }]
}
```

### GET `/shipments/{id}`
Полная карточка: legs, timeline, predictions, documents summary, active risks.

### POST `/shipments/{id}/simulate`
```json
// request
{ "weather_severity_index": 0.8, "port_queue_hours": 18, "document_delay_hours": 6 }
// response
{
  "shipment_id": "shp_demo_001",
  "missed_connection": true,
  "missed_service_id": "svc_ferry_anz_07",
  "next_service_id": "svc_ferry_anz_09",
  "predicted_eta": "2026-11-20T06:00:00Z",
  "delay_hours": 40.0,
  "risk_factors": [
    {"code": "port_queue", "label": "Очередь в порту отправления", "contribution_hours": 12.0, "note": "ассоциативный фактор модели/правил, не доказанная причина"},
    {"code": "missed_sailing", "label": "Пропущен морской рейс", "contribution_hours": 24.0, "note": "следствие стыковки по правилам расписания"}
  ],
  "data_quality": "synthetic_demo"
}
```

### GET `/shipments/{id}/alternatives`
```json
{
  "shipment_id": "shp_demo_001",
  "alternatives": [
    {
      "id": "alt_wait_next",
      "title": "Ждать следующий паром",
      "feasible": true,
      "eta": "2026-11-20T06:00:00Z",
      "total_hours": 112,
      "cost_usd": 4200,
      "co2e_kg": 1850,
      "assumptions": ["Демо-тариф", "EF морской участок из таблицы допущений"]
    }
  ],
  "infeasible_reason": null,
  "data_quality": "synthetic_demo"
}
```

### Documents
- `GET /shipments/{id}/documents` — комплект + `completeness`
- `POST /documents/predeclare` — предварительная подача (тестовая)
- `GET /documents/{id}/history` — журнал статусов

```json
// POST /documents/predeclare
{
  "shipment_id": "shp_demo_001",
  "document_type": "commercial_invoice",
  "payload": {"invoice_no": "INV-DEMO-1"}
}
// response
{
  "document_id": "doc_...",
  "status": "accepted_for_review",
  "disclaimer": "Тестовый статус. Не является таможенным разрешением.",
  "data_quality": "synthetic_demo"
}
```

### GET `/health` — liveness.

---

## 5. Экраны и действия

| Экран | Действия |
|-------|----------|
| **Список перевозок** | Фильтр по риску/статусу; открыть карточку |
| **Карточка груза** | Таймлайн; план vs прогноз ETA; факторы риска; бейдж «synthetic_demo» |
| **Симулятор** | Задать погоду / очередь / docs delay → «Пересчитать» |
| **Альтернативы** | Сравнить 2–3 плана; выбрать план (фиксирует выбор в API) |
| **Документы** | Видеть комплект; отправить pre-declare; смотреть журнал |
| **Пустое / нет маршрутов** | Текст причины (`infeasible_reason`) |

Figma «Диспетчерская» заявлена как визуальный ориентир; **на момент проектирования edit-доступ к файлу не выдан** — UI реализован как operational dispatch theme с пометкой сверки после шаринга.

---

## 6. Алгоритм прогноза и пересчёта стыковок

### 6.1 Baseline (основной для демо)
Для каждого типа плеча / пары порт+mode:
`predicted_duration_h = median(historical_duration_h | features available at as_of)`  
на time-based split (train до cutoff, test после).

Метрика: **MAE (часы)** vs факт на holdout; сравнение CatBoost vs median.

### 6.2 CatBoost (если есть history ≥ порога)
Признаки только с `available_at <= as_of`: queue proxy, weather severity, doc pending hours, mode, port load index.  
**Не называть** feature importance «причинами задержки» — только ассоциативные факторы риска в UI.

### 6.3 Пересчёт стыковок
1. Применить события к текущему/следующему незавершённому плечу → сдвиг `ready_at`.
2. Для морского плеча: найти `ScheduledService` с `departure >= ready_at + cutoff` и совместимостью груза/порта.
3. Если текущий рейс недоступен → `missed_connection=true`, взять следующий; если нет — альтернативы / `infeasible`.
4. Каскадом пересчитать downstream legs (handling + road).
5. Записать `Prediction` snapshot.

### 6.4 CO₂e (приближение)
`co2e_kg = distance_km * ef_kg_per_tkm * cargo_tonnes`  
EF из таблицы допущений (rail/sea/road); единицы кг CO₂e; пометка «оценка, не верифицированный LCA».

---

## 7. План 72 часа и ответственность

| Окно | Frontend | Backend | ML/Data | Product |
|------|----------|---------|---------|---------|
| **0–8 ч** | Каркас UI, список, карточка-заглушка | Модели БД, seed, health | Схема признаков, synthetic history | Сценарий, допущения, критерии |
| **8–24 ч** | Таймлайн, риски, симулятор UI | Events, simulate, ETA cascade | Median baseline + MAE notebook | Копирайт дисклеймеров |
| **24–48 ч** | Альтернативы, документы UI | Alternatives, documents API+audit | CatBoost optional + сравнение | Скрипт защиты 3 мин |
| **48–64 ч** | Полировка, согласование с API | Docker Compose, фиксы | Валидация no-leakage | Чеклист приёмки |
| **64–72 ч** | Демо-прогон UI | Стабильность API | Цифры MAE на synth | Репетиция защиты |

**Owner сквозного сценария:** Backend + Product (данные) → ML (цифры) → Frontend (показ).

---

## 8. Критерии приёмки и защита (3 мин)

### Приёмка
- [ ] Один груз проходит ж/д → РФ порт → море → IR порт → авто.
- [ ] Симуляция очереди/погоды даёт `missed_connection` и новый ETA по следующему демо-рейсу.
- [ ] UI ETA/delay совпадает с API (±1 ч округления).
- [ ] ≥2 альтернативы с time/cost/CO₂e **или** явное `infeasible_reason`.
- [ ] Неполный комплект документов блокирует/помечает риск; pre-declare пишет audit; disclaimer виден.
- [ ] Везде `synthetic_demo` / дисклеймеры; нет выдачи демо-расписаний за реальные.
- [ ] `docker compose up` поднимает стек (или `make local` на SQLite).
- [ ] MAE baseline задокументирован на synthetic holdout; CatBoost — только если обучен без future leak.

### Скрипт защиты ~3 мин
1. **Проблема (20 с):** стыковки на Каспии рвутся из‑за очередей/погоды/доков.  
2. **Решение (20 с):** цифровой двойник одного коридорного плеча — прогноз, документы, выбор плана.  
3. **Демо (90 с):** список → карточка → симулятор → пропуск рейса → альтернативы → документы.  
4. **Честно (20 с):** синтетика; baseline+MAE; не таможня; не 3D/blockchain.  
5. **Next (20 с):** реальные фиды порта/погоды, калибровка модели, пилот с оператором.

---

## Зафиксированные допущения
См. `docs/ASSUMPTIONS.md`.
