# 05 · API

- Машинный контракт: [`openapi.json`](./openapi.json) (генерируется из FastAPI, спецификация OpenAPI 3.1).
- Интерактивная документация: `http://localhost:8000/docs` (Swagger UI) и `/redoc`.
- Коллекция запросов: [`postman_collection.json`](./postman_collection.json).

Базовый префикс: `/api`. Все защищённые запросы — `Authorization: Bearer <JWT>`.

## Аутентификация

| Метод | Путь | Описание |
|---|---|---|
| POST | `/auth/login` | Вход, возвращает JWT, пользователя и компанию |
| GET | `/auth/me` | Проверка сессии и восстановление профиля |
| GET | `/auth/demo-accounts` | Список тестовых учётных записей (публично, для демо) |

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"ivan@vesna.ru","password":"demo1234"}'
```

## Клиентские методы

| Метод | Путь | Роль | Описание |
|---|---|---|---|
| GET | `/dashboard` | client | Обзор: лимит, риск-профиль, статистика, рекомендации |
| GET | `/products` | — | Каталог продуктов |
| GET | `/products/{code}` | — | Карточка продукта |
| GET | `/products/{code}/eligibility?amount=&term_months=` | client | Предварительная проверка требований |
| GET | `/applications` | client | Список заявок компании |
| POST | `/applications` | client | Создание и (опционально) отправка заявки |
| GET | `/applications/{id}` | client | Карточка заявки: статус, события, документы, скоринг |
| POST | `/applications/{id}/submit` | client | Отправка черновика |
| POST | `/applications/{id}/offer/accept` | client | Принять (`accept: true`) или отклонить оферту |
| POST | `/applications/{id}/sign` | client | Подписать пакет документов → выдача |
| POST | `/applications/{id}/info` | client | Ответ на запрос уточнений |
| POST | `/applications/{id}/documents` | client | Загрузка документа (метаданные) |
| GET | `/news?category=&limit=` | client | Персональная лента с объяснением релевантности |
| GET | `/company` | client | Профиль компании: реквизиты, финансы, БКИ, ЕГРЮЛ |

### Пример: создание заявки

```bash
curl -s -X POST http://localhost:8000/api/applications \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "product_code": "working_capital",
    "amount": 800000,
    "term_months": 12,
    "purpose": "Закупка товара",
    "purpose_details": "Кофе и упаковка на ноябрь",
    "submit": true
  }'
```

Ответ `201`:

```json
{
  "id": 2,
  "number": "ALF-261019-8102",
  "status": "submitted",
  "status_label": "Заявка отправлена",
  "next_action": "Ожидайте решения банка — обычно это занимает несколько минут",
  "progress_percent": 15
}
```

## Бэк-офис (роль `bank`)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/bank/tasks?tab=queue\|waiting\|decided\|all&search=` | Очередь с SLA и скорингом |
| GET | `/bank/applications/{id}` | Полная карточка: клиент, БКИ, ЕГРЮЛ, скоринг, история |
| POST | `/bank/applications/{id}/decision` | Решение: `approve`, `counter_offer`, `request_info`, `decline` |
| GET | `/bank/pipeline` | Воронка по статусам |
| GET | `/bank/metrics` | SLA, автоматизация, доля отказов, портфель |

### Пример: контрпредложение

```bash
curl -s -X POST http://localhost:8000/api/bank/applications/3/decision \
  -H "Authorization: Bearer $BANK_TOKEN" -H 'Content-Type: application/json' \
  -d '{
    "action": "counter_offer",
    "comment": "Снижаем сумму для комфортной нагрузки",
    "offer_amount": 1500000,
    "offer_rate": 21.5,
    "offer_term_months": 24
  }'
```

## Коды ответов

| Код | Когда |
|---|---|
| 200 / 201 | Успех |
| 401 | Нет токена / токен истёк / неверный пароль |
| 403 | Роль не имеет доступа к разделу |
| 404 | Объект не найден или принадлежит другой компании |
| 409 | Недопустимый переход состояния |
| 422 | Ошибка валидации (в т.ч. лимиты продукта, отсутствие цели) |

Единый формат ошибки: `{"detail": "человекочитаемое описание"}`.

## Основные поля заявки

| Поле | Тип | Описание |
|---|---|---|
| `status` | string | Статус (см. диаграмму состояний) |
| `score`, `risk_class`, `pd_percent` | int, string, float | Результат скоринга |
| `offer` | object \| null | `amount`, `rate`, `term_months`, `monthly_payment`, `is_counter_offer`, `expires_at`, `requested_amount` |
| `required_docs` | list[str] | Пакет документов по продукту |
| `signature_docs` | list[object] | Документы к подписанию и статус подписи |
| `credit_account` | string | Счёт зачисления после выдачи |
| `events` | list[object] | Журнал: тип, переход, автор, комментарий, payload |
| `next_action` | string | Подсказка клиенту, что делать дальше |
