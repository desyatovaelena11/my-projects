# Telegram Mini App — Ольга · маникюр

## Файлы

```
olga-project/
├── index.html      ← лендинг (отдельный проект, не связан с TMA)
└── tg-app/
    ├── index.html  ← весь Telegram Mini App в одном файле
    └── CLAUDE.md   ← эта документация
```

Весь TMA — один файл `tg-app/index.html`. CSS и JS встроены внутрь.
Единственная внешняя зависимость: Telegram SDK (`telegram-web-app.js`).

---

## Экраны и навигация

```
[home] Главный
    │  тап на категорию
    ▼
[catalog] Каталог  ──── BackButton ───▶  [home]
    │  тап на услугу
    ▼
[service] Карточка услуги  ── BackButton ──▶  [catalog]
    │  MainButton «Записаться»
    ▼
[confirm] Подтверждение  ── BackButton ──▶  [service]
    │  MainButton «Отправить заявку»
    ▼
[success] Успех
    │  MainButton «Готово»
    ▼
  tg.close() — закрыть TMA
```

**Анимация переходов:** translateX 250ms ease-out.
Вперёд — новый экран приходит справа, старый уходит на -30% влево.
Назад — текущий уходит на 100% вправо, предыдущий приходит с -30% слева.

---

## Где менять данные

### Услуги и цены
Массив `SERVICES` в начале `<script>` в `tg-app/index.html`.
Каждый объект:
```js
{
  id:       1,             // уникальный номер
  category: 'manicure',   // manicure | pedicure | design | extension
  icon:     '💅',          // эмодзи (заглушка вместо фото)
  name:     '...',         // название услуги
  desc:     '...',         // одна строка в каталоге
  fullDesc: '...',         // полное описание на карточке
  price:    1500,          // цена (число, в рублях)
  duration: 90,            // длительность (число, в минутах)
  popular:  true,          // true = бейдж «Хит»
  gradient: 'linear-gradient(...)' // цвет фото-заглушки
}
```

### Аватар мастера
Сейчас показывается инициал «О» на градиенте.
Чтобы заменить на реальное фото, найди в HTML:
```html
<div class="master-avatar">О</div>
```
И замени на:
```html
<img src="../фото-ольги.jpg" alt="Ольга" class="master-avatar"
     style="object-fit:cover; font-size:0">
```

### Фото услуг (Экран 3)
Сейчас — цветные градиенты с эмодзи (поле `gradient` + `icon` в данных услуги).
Чтобы добавить реальное фото — внутри `.service-photo` замени структуру:
```html
<img src="фото-услуги.jpg" alt="название" style="width:100%;height:100%;object-fit:cover">
```

### Имя мастера, город, контакты
В HTML-разметке экрана `screen-home` (поиск: `master-profile`).

---

## Telegram SDK — что используется

| Метод / свойство | Где применяется |
|---|---|
| `tg.ready()` | Инициализация, сообщает Telegram что приложение готово |
| `tg.expand()` | Растягивает на весь экран при открытии |
| `tg.BackButton` | Нативная кнопка «Назад» в шапке Telegram |
| `tg.MainButton` | Синяя кнопка внизу экрана |
| `tg.sendData(json)` | Отправляет заявку боту, закрывает TMA |
| `tg.close()` | Закрывает TMA после успеха |
| `tg.initDataUnsafe.user` | Имя и username пользователя для приветствия |
| `tg.HapticFeedback` | Тактильная обратная связь при тапах |
| `tg.enableClosingConfirmation()` | Предупреждение при закрытии на экране подтверждения |

---

## Что получает бот при отправке заявки

`tg.sendData()` передаёт боту JSON-строку:
```json
{
  "service_name":     "Маникюр с гель-лаком",
  "service_price":    1500,
  "service_duration": 90,
  "user_id":          123456789,
  "user_name":        "Анна",
  "user_username":    "anna_tg"
}
```
Бот получает это в поле `message.web_app_data.data`.

---

## Тестирование

**В браузере:** открыть `tg-app/index.html` через локальный сервер.
Внизу появятся fallback-кнопки (Назад + синяя кнопка действия).
Данные пользователя будут пустыми — в приветствии покажется «Привет! 👋».

**В Telegram:**
1. Создать бота через @BotFather → `/newbot`
2. Опубликовать файл (Vercel / GitHub Pages)
3. @BotFather → `/setmenubutton` → указать URL опубликованного файла
4. Открыть бота с телефона

---

## Подключение к боту (следующий шаг)

Когда `tg.sendData()` отправит заявку, бот должен:
1. Принять `web_app_data` через webhook
2. Отправить мастеру сообщение: «📩 Новая заявка! ...»
3. Опционально: ответить клиенту подтверждением

Реализуется отдельно — Python (python-telegram-bot) или Node.js.
