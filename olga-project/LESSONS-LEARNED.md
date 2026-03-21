# Разбор ошибок проекта: Telegram Mini App для мастера маникюра

Документ создан: 2026-03-19
Цель: не повторять эти ошибки в будущих проектах.

---

## 1. Supabase: прямое подключение не работает на VPS

**Что случилось:**
Приложение не могло подключиться к базе данных. Бот не отвечал на `/start`, вебхук возвращал 500.

**Причина:**
Стандартный (Direct Connection) URL Supabase использует IPv6. Большинство бюджетных VPS работают только с IPv4 и не умеют подключаться по IPv6.

```
# НЕ РАБОТАЕТ на IPv4-VPS:
postgresql://postgres:password@db.xxx.supabase.co:5432/postgres  ← IPv6

# РАБОТАЕТ:
postgresql://...@aws-1-eu-central-1.pooler.supabase.com:5432/postgres  ← Session Pooler, IPv4
```

**Правило:**
При деплое на VPS всегда использовать **Session Pooler** URL из Supabase (вкладка Connect → Session pooler). Никогда не использовать Direct Connection, пока не проверен IPv6.

---

## 2. Telegram Mini App: `tg.sendData()` немедленно закрывает приложение

**Что случилось:**
После нажатия "Записаться" TMA мгновенно закрывалась и возвращала в бота. Экран успеха не показывался. Пользователь думал, что заявка не отправилась.

**Причина:**
`tg.sendData()` — это финализирующий вызов. Telegram немедленно закрывает Mini App после него. Весь код ПОСЛЕ `sendData()` не выполняется.

```js
// НЕПРАВИЛЬНО — goTo('success') никогда не выполнится:
tg.sendData(payload);
goTo('success');  // ← мёртвый код

// ПРАВИЛЬНО — сначала показать UI, потом отправить данные:
goTo('success');
tg.sendData(payload);
```

**Правило:**
`tg.sendData()` — всегда последняя строка в функции. Перед ней показать пользователю финальный экран.

---

## 3. TMA: кнопки-дубли появляются вне Telegram

**Что случилось:**
На экране подтверждения было две кнопки "Записаться" — одна из HTML (fallback), одна от Telegram MainButton.

**Причина:**
HTML-кнопки отображались всегда, без проверки контекста. В Telegram они дублировали MainButton.

```js
// НЕПРАВИЛЬНО — кнопки видны всегда:
document.getElementById('btn').style.display = 'block';

// ПРАВИЛЬНО — проверить контекст:
const inTelegram = window.Telegram?.WebApp?.initData !== '';
if (!inTelegram) {
  document.getElementById('btn').style.display = 'block';
}
```

**Правило:**
В TMA всегда разделять UI для Telegram-контекста и браузерного fallback. Проверять `window.Telegram?.WebApp?.initData !== ''`, а не просто наличие объекта `tg`.

---

## 4. TMA: SSL-сертификат не принимается Telegram WebView

**Что случилось:**
TMA показывала демо-данные вместо реальных. API запросы молча падали.

**Причина:**
Telegram WebView отклоняет самоподписанные SSL-сертификаты. API был доступен через `http://` или `https://` с самоподписанным сертификатом.

**Решение:**
Получить валидный Let's Encrypt сертификат. Без реального домена можно использовать **nip.io** — сервис, который резолвит `<IP>.nip.io` в этот IP. Например: `155.212.139.51.nip.io`.

```bash
# Certbot для nip.io домена:
certbot --nginx -d 155.212.139.51.nip.io
```

**Правило:**
Для TMA API обязателен валидный SSL (Let's Encrypt или аналог). Без домена — nip.io + certbot. Никогда не использовать самоподписанные сертификаты для Telegram WebView.

---

## 5. TMA: `masterSlug` не передаётся через reply keyboard

**Что случилось:**
TMA открывалась, но не знала, чьи услуги показывать — `masterSlug` был `null`.

**Причина:**
`tg.initDataUnsafe.start_param` работает только когда TMA открыта через **inline кнопку** (`InlineKeyboardButton`). Reply keyboard кнопки (`KeyboardButton`) не устанавливают `start_param`.

**Решение:**
Передавать slug в URL параметре и читать его из обоих источников:
```js
// В боте — добавить параметр в URL:
tma_url = f"{TMA_BASE_URL}?startapp={master.slug}"

// В TMA — читать из обоих источников:
const masterSlug = tg?.initDataUnsafe?.start_param
  || new URLSearchParams(window.location.search).get('startapp')
  || null;
```

**Правило:**
Параметры в TMA всегда читать из двух источников: `start_param` И `URLSearchParams`. Это гарантирует работу и через inline, и через reply keyboard.

---

## 6. TMA vs. Bot: `tg.sendData()` работает только с reply keyboard

**Что случилось:**
`tg.sendData()` вызывал ошибку или не отправлял данные, когда TMA была открыта через inline keyboard кнопку.

**Причина:**
Telegram ограничение: `sendData()` работает **только** если TMA открыта через `KeyboardButton` (reply keyboard). Через `InlineKeyboardButton` или прямую ссылку — не работает.

**Правило:**
Для флоу с `sendData()` — обязательно использовать reply keyboard (`keyboard`, а не `inline_keyboard`). Проверять тип кнопки при добавлении новых точек входа в TMA.

---

## 7. BotFather: `web_app` URL должен быть зарегистрирован

**Что случилось:**
При попытке открыть TMA через кнопку Telegram возвращал ошибку `BUTTON_URL_INVALID`.

**Причина:**
URL `https://t.me/Ma_master_bot/app` использовался как web_app URL, но TMA не была зарегистрирована в BotFather через `/newapp`.

**Правило:**
Перед использованием TMA обязательно зарегистрировать её в BotFather командой `/newapp`. Для reply keyboard кнопки можно использовать прямой GitHub Pages URL без регистрации, но для inline — регистрация обязательна.

---

## 8. API: отсутствие валидации входных данных

**Что случилось:**
- Можно было сохранить мастера с пустым именем `""` или `"   "`
- Отрицательная цена (`-100`) принималась без ошибки
- Услуга с нулевой длительностью (`0` минут) создавалась успешно
- Пустое название услуги принималось

**Причина:**
Pydantic модели без ограничений принимают любые значения нужного типа.

**Решение:**
```python
# НЕПРАВИЛЬНО:
class ServiceCreate(BaseModel):
    name: str
    price: int
    duration_min: int

# ПРАВИЛЬНО:
from pydantic import Field

class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    price: int = Field(..., ge=0)       # ge=0: больше или равно 0
    duration_min: int = Field(..., gt=0) # gt=0: строго больше 0
```

Для строк с пробелами — дополнительная проверка:
```python
if body.name is not None:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Имя не может быть пустым")
```

**Правило:**
Всегда добавлять `Field(...)` с ограничениями для числовых и строковых полей в Pydantic моделях. Строки с `min_length=1` всё равно могут содержать только пробелы — нужна явная проверка `.strip()`.

---

## 9. Безопасность: `.env` файл в git

**Что случилось:**
Файл `.env` с токенами, паролями и ключами мог попасть в публичный репозиторий на GitHub.

**Причина:**
`.gitignore` не содержал правила для `.env` файлов.

**Решение:**
```gitignore
# Добавить в .gitignore:
.env
*.env
**/.env
```

**Правило:**
`.gitignore` с правилами для `.env` — обязателен с первого коммита в любом проекте. Токены и пароли никогда не хранить в коде.

---

## 10. Диагностика: попытка решить следствие вместо причины

**Что случилось:**
Когда TMA показывала демо-данные (не грузила API), было предложено переехать на Railway для нового деплоя. Это потребовало бы часов работы.

**Реальная причина:**
Telegram WebView отклонял самоподписанный SSL-сертификат — одна строка в nginx конфиге + certbot.

**Правило:**
Перед радикальными решениями (смена платформы, переписывание) — исчерпать все варианты диагностики на текущем стеке. Проверить логи, проверить сетевые запросы в браузере, проверить конфиг nginx/SSL.

---

## 11. BotFather: команда `/empty` работает не везде

**Что случилось:**
При настройке TMA в BotFather на шаге загрузки фото команда `/empty` не была распознана (фото обязательно). На шаге GIF она сработала.

**Правило:**
В BotFather команда `/empty` пропускает только необязательные шаги. Для обязательных полей (например, фото приложения) нужно загрузить реальный файл. Перед отправкой `/empty` прочитать подсказку BotFather — он указывает, обязательно ли поле.

---

## 12. Telegram: подчёркивания в username ломают Markdown

**Что случилось:**
Мастеру не приходило уведомление о новой заявке. В логах: `Bad Request: can't parse entities: Can't find end of the entity starting at byte offset 60`.

**Причина:**
Username `@elena_desyatova` содержит `_`. В режиме `parse_mode="Markdown"` символ `_` открывает курсив. Telegram не нашёл закрывающий `_` — сообщение не отправилось.

```python
# НЕПРАВИЛЬНО — username с _ сломает Markdown:
client_mention = f"@{client_username}"  # @elena_desyatova

# ПРАВИЛЬНО — экранировать подчёркивания:
client_mention = f"@{client_username.replace('_', '\\_')}"
```

**Правило:**
Любой пользовательский текст (username, имя, название услуги) перед вставкой в Markdown-сообщение экранировать: заменять `_` → `\_`, `*` → `\*`, `[` → `\[`. Либо не использовать `parse_mode` там, где есть пользовательские данные.

---

## 13. Telegram: меню-кнопка бота открывает TMA без `startapp`

**Что случилось:**
Кнопка «Записаться» (меню-кнопка слева от поля ввода) открывала приложение со старыми данными и не отправляла заявку. Кнопка «Открыть каталог услуг» работала корректно.

**Причина:**
Меню-кнопка (`setChatMenuButton`) была настроена с URL без параметра `?startapp=olga-manicure`. В TMA `masterSlug` оказывался `null` — приложение не знало какого мастера загрузить и показывало дефолтные данные из HTML.

**Решение:**
```python
# При настройке меню-кнопки через API — добавлять startapp в URL:
tma_url = f"{TMA_BASE_URL}?startapp={master.slug}"
await tg_send(bot_token, "setChatMenuButton", {
    "menu_button": {
        "type": "web_app",
        "text": "Записаться",
        "web_app": {"url": tma_url}
    }
})

# В TMA — добавить запасной slug на случай любого сценария открытия:
const masterSlug = tg?.initDataUnsafe?.start_param
  || new URLSearchParams(window.location.search).get('startapp')
  || 'olga-manicure';  // ← запасной вариант
```

**Правило:**
Меню-кнопка и клавиатурная кнопка — разные точки входа. Каждую нужно настраивать отдельно и убеждаться, что URL содержит нужные параметры. В TMA всегда делать запасной slug чтобы приложение работало при любом способе открытия.

---

## 14. SQLAlchemy `create_all` не обновляет существующие таблицы

**Что случилось:**
Вкладка «Записи» в админке показывала «Ошибка загрузки». В логах: `column bookings.client_telegram_id does not exist`.

**Причина:**
Таблица `bookings` уже существовала в Supabase, но с другой схемой (старая версия модели: `service_id`, `starts_at`, `client_tg_id` вместо `service_name`, `booking_date`, `client_telegram_id`). `Base.metadata.create_all()` создаёт только **отсутствующие** таблицы и никогда не изменяет структуру существующих.

**Решение:**
Вручную добавить недостающие колонки через `ALTER TABLE`:
```sql
ALTER TABLE bookings ADD COLUMN client_telegram_id BIGINT;
ALTER TABLE bookings ADD COLUMN service_name VARCHAR(256) NOT NULL DEFAULT '';
ALTER TABLE bookings ADD COLUMN booking_date VARCHAR(10) NOT NULL DEFAULT '';
ALTER TABLE bookings ADD COLUMN booking_time VARCHAR(5) NOT NULL DEFAULT '';
```

**Правило:**
`create_all` — только для первоначального создания. При изменении модели всегда использовать миграции (Alembic) или явные `ALTER TABLE`. Перед деплоем новой схемы проверять реальные колонки в БД:
```sql
SELECT column_name FROM information_schema.columns WHERE table_name = 'bookings';
```

---

## 15. Сервер может содержать старые версии файлов

**Что случилось:**
На сервере отсутствовали `models/booking.py` и запись `Booking` в `models/__init__.py`, хотя локально они были. Сохранение записей в БД молча не работало.

**Причина:**
Файлы были созданы локально, но никогда не задеплоены на сервер. Деплой делался вручную через paramiko/SFTP, и новые файлы просто забыли скопировать.

**Правило:**
После добавления нового файла в проект — сразу проверять что он есть на сервере. При ручном деплое составить чеклист файлов. В идеале — автоматизировать деплой (GitHub Actions, rsync-скрипт) чтобы ничего не потерялось.

---

## Сводная таблица ошибок

| # | Категория | Ошибка | Где проявилась |
|---|-----------|--------|----------------|
| 1 | База данных | Direct Supabase URL — IPv6 only | VPS + Supabase |
| 2 | TMA логика | `sendData()` выполнялся до показа success-экрана | tg-app/index.html |
| 3 | TMA UI | Дублирующиеся кнопки без проверки контекста | tg-app/index.html |
| 4 | Инфраструктура | Самоподписанный SSL отклонён Telegram | nginx на VPS |
| 5 | TMA данные | `masterSlug` читался только из `start_param` | tg-app/index.html |
| 6 | Telegram API | `sendData()` несовместим с inline keyboard | webhooks/telegram.py |
| 7 | BotFather | TMA не зарегистрирована перед использованием | BotFather настройка |
| 8 | API валидация | Нет ограничений на числа и строки в Pydantic | api/admin.py |
| 9 | Безопасность | `.env` не добавлен в `.gitignore` | .gitignore |
| 10 | Диагностика | Лечили следствие, а не причину (Railway vs SSL) | Процесс отладки |
| 11 | BotFather | `/empty` не работает на обязательных шагах | BotFather настройка |
| 12 | Telegram API | Подчёркивание в username ломает Markdown — сообщение не уходит | webhooks/telegram.py |
| 13 | TMA данные | Меню-кнопка открывает TMA без startapp — приложение не знает мастера | setChatMenuButton + tg-app |
| 14 | База данных | `create_all` не мигрирует существующие таблицы — нужен ALTER TABLE | Supabase / миграции |
| 15 | Деплой | Новые файлы модели не задеплоены на сервер — функция молча не работает | Ручной деплой |
| 16 | База данных | Нет уникального ограничения на слот — двойное бронирование возможно | bookings таблица |
| 17 | API безопасность | Webhook принимал заявки на прошедшие даты без проверки | webhooks/telegram.py |
| 18 | База данных | Схема БД и Python-модель разошлись: дублирующие колонки client_tg_id/starts_at | models/booking.py |
| 19 | TMA UI | Счётчики услуг в категориях захардкожены — не обновляются при изменении каталога | tg-app/index.html |
| 20 | TMA UI | Политика отмены и рабочие часы захардкожены — не берутся из профиля мастера | tg-app/index.html |

---

## 16. Нет защиты от двойного бронирования

**Что случилось:**
Два клиента могли одновременно видеть один слот свободным и оба записаться на него. Ольга получала двух клиентов в одно время.

**Причина:**
Не было ни уникального ограничения в БД, ни проверки на сервере перед сохранением записи.

**Решение:**
```sql
-- Уникальный частичный индекс: отменённые записи не блокируют слот
CREATE UNIQUE INDEX uq_master_active_slot
ON bookings (master_id, booking_date, booking_time)
WHERE status != 'cancelled'
  AND booking_date IS NOT NULL
  AND booking_time IS NOT NULL;
```
И в webhook перед сохранением:
```python
conflict = await db.execute(
    select(Booking).where(
        Booking.master_id == master.id,
        Booking.booking_date == booking_date,
        Booking.booking_time == booking_time,
        Booking.status != "cancelled",
    )
)
if conflict.scalar_one_or_none():
    # сообщить клиенту что время занято
    return
```

**Правило:**
Любой ресурс с ограниченной доступностью (время, место, товар) требует:
1. Уникального ограничения на уровне БД (последний рубеж)
2. Проверки на уровне приложения перед записью (быстрый ответ клиенту)

---

## 17. Webhook принимал заявки без валидации

**Что случилось:**
Клиент мог отправить запись на прошедшую дату. Webhook сохранял её без вопросов — Ольга видела фантомные записи из прошлого.

**Причина:**
Обработчик `_handle_booking` сохранял данные как есть, без проверок.

**Решение:**
```python
from datetime import date as date_cls

if date_cls.fromisoformat(booking_date) < date_cls.today():
    await tg_send(bot_token, "sendMessage", {
        "chat_id": client_chat_id,
        "text": "❌ Нельзя записаться на прошедшую дату.",
    })
    return
```

**Правило:**
Данные от клиента всегда проверять на сервере: дата не в прошлом, время в рабочих часах, слот свободен. Клиентский код не гарантия — данные можно подменить.

---

## 18. Python-модель и схема БД разошлись

**Что случилось:**
В таблице `bookings` были колонки `client_tg_id` и `client_telegram_id` (дубли), `starts_at` и `booking_date`+`booking_time` (два подхода к дате). Python-модель знала только о новых полях, а старые висели в БД как мусор.

**Причина:**
Схема менялась итеративно через Supabase UI без удаления старых колонок. Python-модель создавалась с нуля под новый подход.

**Решение:**
```sql
ALTER TABLE bookings DROP COLUMN IF EXISTS client_tg_id;
ALTER TABLE bookings DROP COLUMN IF EXISTS starts_at;
ALTER TABLE bookings DROP COLUMN IF EXISTS service_id;
```

**Правило:**
При изменении схемы всегда писать SQL-миграцию и сразу удалять устаревшие колонки. Периодически сверять `information_schema.columns` с Python-моделями.

---

## 19. Статичные счётчики услуг в TMA

**Что случилось:**
На главном экране TMA написано "3 услуги", "2 услуги" — хардкодом. После того как Ольга добавила новые услуги через панель, счётчики не обновились. Клиент видел неверные цифры.

**Решение:**
```js
// После загрузки услуг из API — пересчитать счётчики:
function updateCategoryCounts() {
  document.querySelectorAll('.category-item[data-cat]').forEach(item => {
    const count = SERVICES.filter(s => s.category === item.dataset.cat).length;
    item.querySelector('.category-count').textContent =
      count + ' ' + pluralServices(count);
  });
}
```

**Правило:**
Любые числа и тексты, которые зависят от данных в БД — генерировать динамически после загрузки данных из API.

---

## 20. Захардкоженные тексты не отражают настройки профиля

**Что случилось:**
В TMA текст "Отмена за 2 часа" и "Работает пн–сб с 9:00 до 21:00" был прописан в HTML. После изменения `cancellation_hours` или `working_hours` в панели мастера — клиенты видели старую информацию.

**Решение:**
```js
// После загрузки профиля — обновить тексты:
const cancelHours = profile.cancellation_hours ?? 2;
document.querySelector('.service-policy').textContent =
  `Без предоплаты · Отмена за ${cancelHours} ${pluralHours(cancelHours)} — без вопросов`;
```

**Правило:**
Всё что мастер может изменить в панели — должно автоматически отображаться в TMA. Никаких захардкоженных бизнес-правил в HTML.

