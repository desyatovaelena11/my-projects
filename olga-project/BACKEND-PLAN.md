# Backend Plan — NailBook Platform

Мультимастерская SaaS-платформа для Telegram Mini App.
Один бот на всех мастеров, каждый мастер — изолированный аккаунт с белым лейблом.

---

## Архитектурные решения (зафиксированы)

| Вопрос | Решение |
|---|---|
| Бот | Один общий бот, маршрутизирует по `master_id` |
| Настройка мастера | Веб-панель `/admin` в браузере |
| Фото | Cloudflare R2 |
| Оплата подписки | YooKassa |
| Тема / брендинг | Full white-label после оплаты |
| Бот-консультант | FAQ по скрипту + приём заявок |
| Запись | Реальные слоты, клиент выбирает время |
| Бизнес-модель | Ежемесячная подписка |

---

## Тарифные планы

| Тариф | Цена | Услуги | Слоты и запись | Тема |
|---|---|---|---|---|
| **Free** | 0 ₽ | до 5 активных | только заявка (без времени) | нет |
| **Pro** | 490 ₽/мес | до 15 | календарь + реальные слоты | нет |
| **Unlimited** | 990 ₽/мес | без ограничений | календарь | white-label (цвет + лого) |

---

## Стек технологий

| Слой | Технология |
|---|---|
| Язык | Python 3.11+ |
| API-фреймворк | FastAPI |
| База данных | PostgreSQL 15 |
| ORM | SQLAlchemy 2 + Alembic (миграции) |
| Бот | python-telegram-bot v20 |
| Файлы | Cloudflare R2 (S3-совместимый API) |
| Оплата | YooKassa Python SDK |
| Фоновые задачи | APScheduler (напоминания, истечение подписок) |
| Авторизация | JWT (access 24h + refresh 30d) |
| Хостинг | Railway или Render (старт бесплатно) |
| Переменные среды | `.env` файл |

---

## База данных

### Таблица `masters`

Один мастер = одна строка.

```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
telegram_id      BIGINT UNIQUE NOT NULL   -- Telegram user ID мастера
slug             VARCHAR(64) UNIQUE NOT NULL  -- URL: platform.com/app?m=olga
name             VARCHAR(128) NOT NULL    -- отображаемое имя
specialty        VARCHAR(128)             -- "мастер маникюра"
city             VARCHAR(128)
address          VARCHAR(256)
phone            VARCHAR(32)
telegram_username VARCHAR(64)            -- @username без @
avatar_url       TEXT                    -- R2 URL
bio              TEXT
trust_text       VARCHAR(256)            -- "5.0 · 5000+ клиентов · 7 лет"
working_hours    JSONB                   -- {"mon":"9:00-21:00","sun":null}
cancellation_hours INT DEFAULT 2        -- за сколько часов можно отменить
plan             VARCHAR(16) DEFAULT 'free'  -- free | pro | unlimited
plan_expires_at  TIMESTAMPTZ
-- White-label (доступно только на unlimited)
brand_name       VARCHAR(128)            -- имя бренда (вместо имени мастера)
brand_logo_url   TEXT                    -- R2 URL
accent_color     VARCHAR(16)             -- hex, например #16c47f
created_at       TIMESTAMPTZ DEFAULT now()
updated_at       TIMESTAMPTZ DEFAULT now()
```

---

### Таблица `services`

Услуги мастера.

```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
master_id        UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE
category         VARCHAR(64)             -- manicure|pedicure|design|extension
name             VARCHAR(256) NOT NULL
description_short TEXT                  -- одна строка в каталоге
description_full  TEXT                  -- полное описание на карточке
price            INT NOT NULL            -- рублей
duration_min     INT NOT NULL            -- минут
icon             VARCHAR(8)              -- эмодзи
photo_url        TEXT                    -- R2 URL (может быть null)
gradient         VARCHAR(256)            -- CSS-градиент если нет фото
is_popular       BOOLEAN DEFAULT false   -- бейдж «Хит»
is_active        BOOLEAN DEFAULT true
sort_order       INT DEFAULT 0
created_at       TIMESTAMPTZ DEFAULT now()
```

**Ограничение по плану:** при запросе услуг:
- free → возвращать только первые 5 (`WHERE is_active ORDER BY sort_order LIMIT 5`)
- pro → первые 15
- unlimited → все

---

### Таблица `time_slots`

Слоты рабочего времени мастера.

```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
master_id        UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE
starts_at        TIMESTAMPTZ NOT NULL
ends_at          TIMESTAMPTZ NOT NULL
status           VARCHAR(16) DEFAULT 'available'
                 -- available | booked | blocked
booking_id       UUID REFERENCES bookings(id)
UNIQUE(master_id, starts_at)
```

Слоты создаются мастером из панели (или генерируются автоматически по расписанию `working_hours`).

---

### Таблица `bookings`

Каждая запись клиента.

```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
master_id        UUID NOT NULL REFERENCES masters(id)
service_id       UUID NOT NULL REFERENCES services(id)
slot_id          UUID REFERENCES time_slots(id)   -- null на free-тарифе
client_tg_id     BIGINT NOT NULL                  -- Telegram ID клиента
client_name      VARCHAR(256)
client_username  VARCHAR(64)                       -- без @
status           VARCHAR(16) DEFAULT 'pending'
                 -- pending | confirmed | cancelled
cancelled_at     TIMESTAMPTZ
cancellation_by  VARCHAR(16)                       -- master | client
note             TEXT                              -- комментарий клиента
reminder_sent    BOOLEAN DEFAULT false             -- отправлено ли напоминание
created_at       TIMESTAMPTZ DEFAULT now()
```

---

### Таблица `faq_items`

FAQ-скрипт бота для каждого мастера.

```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
master_id        UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE
question         TEXT NOT NULL              -- "Нужна ли предоплата?"
answer           TEXT NOT NULL              -- "Нет, оплата по итогу"
keywords         TEXT[]                     -- ["предоплата", "оплата", "деньги"]
sort_order       INT DEFAULT 0
is_active        BOOLEAN DEFAULT true
```

Бот ищет вопрос клиента по ключевым словам из массива `keywords`.

---

### Таблица `subscriptions`

История платежей.

```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
master_id        UUID NOT NULL REFERENCES masters(id)
plan             VARCHAR(16) NOT NULL        -- pro | unlimited
amount           INT NOT NULL                -- рублей
yookassa_id      VARCHAR(128) UNIQUE         -- ID платежа в YooKassa
status           VARCHAR(16) DEFAULT 'pending'
                 -- pending | succeeded | cancelled | refunded
period_start     TIMESTAMPTZ
period_end       TIMESTAMPTZ
created_at       TIMESTAMPTZ DEFAULT now()
```

---

### Таблица `admin_sessions`

Сессии веб-панели мастера.

```sql
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
master_id        UUID NOT NULL REFERENCES masters(id) ON DELETE CASCADE
token            VARCHAR(256) UNIQUE NOT NULL
expires_at       TIMESTAMPTZ NOT NULL
created_at       TIMESTAMPTZ DEFAULT now()
```

---

## API

Все эндпоинты начинаются с `/api/v1`.

### Публичные (вызывает TMA, без авторизации)

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/masters/:slug` | Профиль мастера (имя, город, часы, тема) |
| GET | `/masters/:slug/services` | Список услуг (фильтр по категории, лимит по плану) |
| GET | `/masters/:slug/slots?date=2026-03-15` | Свободные слоты на дату |
| GET | `/masters/:slug/faq` | FAQ-список мастера |
| POST | `/bookings` | Создать запись |

**POST `/bookings` — тело запроса:**
```json
{
  "master_slug": "olga",
  "service_id": "uuid",
  "slot_id": "uuid",           // null на free-тарифе
  "client_tg_id": 123456789,
  "client_name": "Анна",
  "client_username": "anna_tg",
  "note": ""
}
```

При создании записи:
1. Слот переводится в `booked`
2. Мастеру отправляется уведомление в бот
3. Клиенту отправляется подтверждение в бот

---

### Панель мастера `/admin` (требует JWT)

**Авторизация:**

| Метод | Путь | Что делает |
|---|---|---|
| POST | `/admin/auth/request` | Отправить код в Telegram мастеру |
| POST | `/admin/auth/verify` | Проверить код, вернуть JWT |
| POST | `/admin/auth/refresh` | Обновить access token |

Мастер входит в панель: вводит свой `@username` → бот присылает 6-значный код → вводит код → получает JWT.

**Профиль:**

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/admin/profile` | Получить свой профиль |
| PUT | `/admin/profile` | Обновить: имя, адрес, телефон, bio, часы работы |
| POST | `/admin/profile/avatar` | Загрузить аватар → R2, вернуть URL |

**Услуги:**

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/admin/services` | Список всех услуг |
| POST | `/admin/services` | Создать услугу (проверить лимит плана) |
| PUT | `/admin/services/:id` | Обновить услугу |
| DELETE | `/admin/services/:id` | Удалить (soft-delete: is_active=false) |
| POST | `/admin/services/:id/photo` | Загрузить фото услуги → R2 |
| PUT | `/admin/services/reorder` | Изменить порядок (принимает массив id) |

**Слоты:**

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/admin/slots?week=2026-03-10` | Слоты на неделю |
| POST | `/admin/slots/generate` | Сгенерировать слоты на неделю по `working_hours` |
| POST | `/admin/slots` | Добавить один слот вручную |
| PUT | `/admin/slots/:id/block` | Заблокировать слот |
| PUT | `/admin/slots/:id/unblock` | Разблокировать |
| DELETE | `/admin/slots/:id` | Удалить слот (только если не забронирован) |

**Записи:**

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/admin/bookings?status=pending&date=2026-03-15` | Список записей |
| PUT | `/admin/bookings/:id/confirm` | Подтвердить → уведомить клиента |
| PUT | `/admin/bookings/:id/cancel` | Отменить → уведомить клиента, освободить слот |

**FAQ:**

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/admin/faq` | Список вопросов |
| POST | `/admin/faq` | Добавить вопрос |
| PUT | `/admin/faq/:id` | Обновить |
| DELETE | `/admin/faq/:id` | Удалить |

**Подписка:**

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/admin/subscription` | Текущий план, дата истечения |
| POST | `/admin/subscription/checkout` | Создать платёж в YooKassa, вернуть URL |

**White-label (только unlimited):**

| Метод | Путь | Что делает |
|---|---|---|
| PUT | `/admin/branding` | Обновить brand_name, accent_color |
| POST | `/admin/branding/logo` | Загрузить лого → R2 |

---

### Вебхуки (внешние сервисы)

| Метод | Путь | Что делает |
|---|---|---|
| POST | `/webhook/telegram` | Входящие сообщения от Telegram (бот) |
| POST | `/webhook/yookassa` | Уведомления об оплате от YooKassa |

---

## Бот: логика обработки сообщений

Один бот обслуживает всех мастеров и их клиентов.

### Входящее сообщение от клиента

```
Клиент пишет боту → бот ищет master_id в context клиента
(откуда клиент попал в бот?)
  → через TMA: tg.sendData() содержит master_slug
  → через /start olga: deep link ?start=olga
```

**Поток обработки:**
1. Бот извлекает `master_slug` из контекста или deep link
2. Загружает FAQ мастера из БД
3. Ищет совпадение по `keywords` в тексте клиента
4. Если нашёл — отвечает готовым текстом
5. Если не нашёл — «Напишите мастеру напрямую: @{telegram_username}»

### Входящая заявка (web_app_data)

Telegram присылает webhook с `message.web_app_data.data` — JSON из TMA:
```json
{
  "master_slug": "olga",
  "service_name": "Маникюр с гель-лаком",
  "service_price": 1500,
  "service_duration": 90,
  "slot_id": "uuid",
  "client_tg_id": 123456789,
  "client_name": "Анна",
  "client_username": "anna_tg"
}
```

**Бот:**
1. Создаёт `booking` в БД
2. Переводит слот в `booked`
3. Отправляет мастеру:
   ```
   📩 Новая запись!
   Услуга: Маникюр с гель-лаком · 1 500 ₽ · 90 мин
   Время: 15 марта в 14:00
   Клиент: Анна (@anna_tg)
   [✅ Подтвердить] [❌ Отменить]
   ```
4. Отправляет клиенту:
   ```
   ✅ Заявка принята!
   Мастер: Ольга
   Услуга: Маникюр с гель-лаком
   Время: 15 марта в 14:00
   Мастер подтвердит запись в течение часа.
   ```

### Напоминание (APScheduler)

Каждый час: ищет `bookings` со `status=confirmed` и `starts_at` через 23–25 часов и `reminder_sent=false`.
Отправляет клиенту:
```
⏰ Напоминание!
Завтра в 14:00 — Маникюр с гель-лаком у Ольги.
Адрес: ул. Мечникова, 135
Если нужно перенести — напишите @Pogorelova77
```
Ставит `reminder_sent=true`.

### Истечение подписки (APScheduler)

Раз в день: ищет `masters` где `plan != 'free'` и `plan_expires_at < now() + 3 days`.
Отправляет мастеру предупреждение за 3 дня, затем за 1 день.
При истечении: `plan = 'free'`, сервисы сверх лимита деактивируются.

---

## Безопасность

### Авторизация панели мастера
- Вход только через Telegram-код (не пароль, не Google)
- JWT access token: живёт 24 часа
- JWT refresh token: живёт 30 дней
- Каждый запрос к `/admin/*` проверяет JWT и извлекает `master_id`
- Мастер видит и редактирует только свои данные — `WHERE master_id = {из JWT}`

### Верификация TMA-запросов
- Telegram подписывает `initData` при открытии TMA
- Для чувствительных операций (создание записи) проверять HMAC подпись `initData`
- Документация: [Telegram Web Apps validating data](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app)

### Изоляция данных мастеров
- Все таблицы содержат `master_id`
- Middleware проверяет принадлежность ресурса перед каждым изменением
- Мастер не может получить slug другого мастера через свой JWT

---

## Cloudflare R2: работа с файлами

### Что хранится
- `/avatars/{master_id}.webp` — аватар мастера
- `/services/{master_id}/{service_id}.webp` — фото услуги
- `/logos/{master_id}.webp` — лого для white-label

### Загрузка через backend
1. Панель мастера отправляет файл на `POST /admin/services/:id/photo`
2. Backend конвертирует в WebP, сжимает до 800px по длинной стороне
3. Загружает в R2 через S3-совместимый API
4. Возвращает публичный URL

### Публичный доступ
Настроить R2 Public Bucket или Cloudflare Workers для раздачи файлов по URL:
`https://files.platform.com/services/master-id/service-id.webp`

---

## YooKassa: поток оплаты

1. Мастер нажимает «Подключить Pro» в панели
2. Backend вызывает YooKassa API → создаёт платёж:
   ```json
   {
     "amount": {"value": "490.00", "currency": "RUB"},
     "confirmation": {"type": "redirect", "return_url": "..."},
     "description": "Pro тариф — 1 месяц",
     "metadata": {"master_id": "uuid", "plan": "pro"}
   }
   ```
3. Мастер редиректится на страницу оплаты YooKassa
4. После оплаты YooKassa вызывает `/webhook/yookassa`
5. Backend проверяет подпись вебхука
6. Если `status=succeeded`: обновляет `masters.plan`, устанавливает `plan_expires_at = now() + 30 days`
7. Создаёт запись в `subscriptions`
8. Отправляет мастеру уведомление в бот

---

## TMA: как получает данные мастера

TMA загружается по URL: `https://t.me/platform_bot/app?startapp=olga`

Параметр `startapp=olga` — это `slug` мастера.

TMA делает:
```js
// Получить slug из startParam
const slug = tg.initDataUnsafe.start_param; // "olga"

// Загрузить данные мастера
const master = await fetch(`/api/v1/masters/${slug}`).then(r => r.json());

// Применить тему
document.documentElement.style.setProperty('--accent', master.accent_color || '#2AABEE');
```

Ответ `/api/v1/masters/olga`:
```json
{
  "slug": "olga",
  "name": "Ольга · мастер маникюра",
  "city": "Ростов-на-Дону",
  "address": "ул. Мечникова, 135",
  "phone": "+79001234567",
  "telegram_username": "Pogorelova77",
  "avatar_url": "https://files.platform.com/avatars/uuid.webp",
  "trust_text": "5.0 · 5000+ клиентов · 7 лет",
  "working_hours": {"mon": "9:00-21:00", "sun": null},
  "cancellation_hours": 2,
  "plan": "pro",
  "branding": {
    "accent_color": "#16c47f",
    "brand_name": null,
    "brand_logo_url": null
  }
}
```

---

## Структура файлов проекта

```
backend/
├── main.py                  ← точка входа FastAPI
├── bot.py                   ← Telegram bot
├── scheduler.py             ← APScheduler задачи
├── .env                     ← переменные окружения
│
├── api/
│   ├── public/              ← /masters, /bookings
│   └── admin/               ← /admin/*
│
├── models/                  ← SQLAlchemy модели
│   ├── master.py
│   ├── service.py
│   ├── booking.py
│   ├── slot.py
│   ├── faq.py
│   └── subscription.py
│
├── services/                ← бизнес-логика
│   ├── booking_service.py   ← создание записи + уведомления
│   ├── slot_service.py      ← генерация и управление слотами
│   ├── payment_service.py   ← YooKassa
│   ├── storage_service.py   ← Cloudflare R2
│   └── plan_service.py      ← проверка лимитов плана
│
├── webhooks/
│   ├── telegram.py          ← обработка входящих от Telegram
│   └── yookassa.py          ← обработка оплат
│
└── migrations/              ← Alembic
    └── versions/
```

---

## Переменные окружения (.env)

```
DATABASE_URL=postgresql://user:pass@host:5432/db
TELEGRAM_BOT_TOKEN=8425148500:AAE...
TELEGRAM_WEBHOOK_SECRET=случайная_строка
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=test_abc123
R2_ACCOUNT_ID=abc
R2_ACCESS_KEY_ID=abc
R2_SECRET_ACCESS_KEY=abc
R2_BUCKET_NAME=nailbook-files
R2_PUBLIC_URL=https://files.platform.com
JWT_SECRET=случайная_строка_64_символа
ADMIN_PANEL_URL=https://admin.platform.com
```

---

## Порядок разработки

### Фаза 1 — Ядро (минимально рабочая система)
1. Настроить PostgreSQL + создать все таблицы через Alembic
2. Базовая регистрация мастера через бот (`/start` → сохранить `telegram_id`)
3. API: `GET /masters/:slug` + `GET /masters/:slug/services`
4. TMA: загружать данные мастера из API вместо захардкоженного JSON
5. Бот: принимать `web_app_data`, создавать `booking`, уведомлять мастера

### Фаза 2 — Веб-панель
6. Авторизация: Telegram-код → JWT
7. CRUD услуг с загрузкой фото в R2
8. Редактирование профиля

### Фаза 3 — Слоты и календарь
9. Генерация слотов по расписанию
10. `GET /masters/:slug/slots` — публичные свободные слоты
11. TMA: экран выбора даты и времени (новый экран между каталогом и подтверждением)
12. Блокировка слота при бронировании (транзакция, защита от двойного бронирования)

### Фаза 4 — Бот-консультант и напоминания
13. FAQ: поиск по keywords, ответ клиенту
14. Напоминания за 24 часа (APScheduler)
15. Кнопки подтверждения/отмены в сообщении мастеру

### Фаза 5 — Подписки и white-label
16. Интеграция с YooKassa, вебхук оплаты
17. Проверка плана при запросе услуг и слотов
18. White-label: применение `accent_color` и `brand_logo_url` в TMA

---

## Что НЕ входит в план

| Функция | Причина |
|---|---|
| Онлайн-оплата от клиента | Нужно юрлицо мастера — не наша ответственность |
| SMS-уведомления | Telegram покрывает всё |
| Аналитика и отчёты | Фаза 6+ |
| Несколько мастеров в одном аккаунте | Не нужно — каждый мастер отдельный аккаунт |
| Мобильное приложение | TMA заменяет |
