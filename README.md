# promo service

## что внутри

- jwt логин по email/password
- `get /api/auth/users/me`
- кампании и промокоды с фильтрами
- активация промокода с проверкой дат, активности и лимитов
- разделение прав user/admin
- история изменений промокода
- снапшот данных промокода в активации
- демо данные через миграции
- docker compose, dockerfile, makefile
- pytest тесты на happy path и негативные сценарии

## стек

- python
- fastapi
- pydantic
- uvicorn
- postgresql
- sqlalchemy
- alembic
- pytest

## структура проекта

```text
app/
  api/
  core/
  models/
  schemas/
  services/
alembic/
tests/
README.md
Makefile
Dockerfile
docker-compose.yml
```

## переменные окружения

можно взять из `.env.example`

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/promocodes
SECRET_KEY=misha-privet
ACCESS_TOKEN_EXPIRE_MINUTES=120
JWT_ALGORITHM=HS256
MOSCOW_TIMEZONE=Europe/Moscow
```

## запуск локально

```bash
make install
cp .env.example .env
make migrate
make run
```

сервис будет доступен на `http://localhost:8000`

docs swagger будут на `http://localhost:8000/docs`

в swagger authorize можно сразу ввести логин и пароль

- `username` = email пользователя
- `password` = пароль

## запуск через docker compose

```bash
docker compose up --build
```

при старте контейнера приложения автоматически выполняется `alembic upgrade head`, затем поднимается uvicorn

## полезные команды

```bash
make test
make up
make down
make logs
```

## демо данные

демо данные создаются миграцией `0001_initial`

учетные записи

- admin
  - email: `admin@example.com`
  - password: `admin123`
- user
  - email: `user@example.com`
  - password: `user123`

демо сущности

- активная кампания `welcome campaign`
- истекшая кампания `old campaign`
- общий промокод `WELCOME100`
- персональный промокод `PERSONAL500` для `user@example.com`
- отключенный промокод `PAUSED50`

## основные ручки

### auth

- `POST /api/auth/jwt/login`
- `POST /api/auth/token` для swagger authorize
- `GET /api/auth/users/me`

### campaigns

- `POST /api/promo-campaigns` только admin
- `PATCH /api/promo-campaigns/{campaign_id}` только admin
- `GET /api/promo-campaigns`

### promos

- `POST /api/promos` только admin
- `PATCH /api/promos/{promo_id}` только admin
- `POST /api/promos/{promo_id}/disable` только admin
- `GET /api/promos`
- `GET /api/promos/{promo_id}`
- `POST /api/promos/{promo_id}/activate`
- `GET /api/promos/activations/my`
- `GET /api/promos/activations` только admin

## фильтры

### `GET /api/promo-campaigns`

- `is_active`

### `GET /api/promos`

- `promo_type`
- `is_active`
- `campaign_id`

## примеры запросов

### логин

```bash
curl -X POST http://localhost:8000/api/auth/jwt/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### получить себя

```bash
curl http://localhost:8000/api/auth/users/me \
  -H 'Authorization: Bearer <access_token>'
```

### активировать промокод

```bash
curl -X POST http://localhost:8000/api/promos/<promo_id>/activate \
  -H 'Authorization: Bearer <access_token>'
```

## формат ошибок

все доменные ошибки отдаются в едином формате

```json
{
  "error": {
    "code": "promo_per_user_limit_exceeded",
    "message": "достигнут лимит активаций промокода на пользователя",
    "context": {
      "promo_id": "...",
      "per_user_limit": 1
    }
  }
}
```

для ошибок валидации возвращается `validation_error` и список проблемных полей в `context.fields`

## тесты

```bash
make test
```

покрыты ключевые сценарии

- успешный логин
- невалидный логин
- `me` с валидным и невалидным токеном
- видимость доступных промокодов
- запрет доступа к чужому персональному промокоду
- успешная активация
- превышение `per_user_limit`
- активация в истекшей кампании
- создание и отключение промокода админом
- запрет менять критичные поля после активации
- невалидные даты кампании
- история изменений промокода

# сценарии ручной проверки

1. залогиниться под `admin@example.com / admin123` и убедиться, что приходит `access_token`
2. залогиниться под `user@example.com / user123` и вызвать `GET /api/auth/users/me`
3. под пользователем вызвать `GET /api/promo-campaigns` и убедиться, что видна только активная доступная кампания
4. под пользователем вызвать `GET /api/promos` и убедиться, что видны только общий активный промокод и персональный промокод этого пользователя
5. под пользователем активировать `WELCOME100` и проверить запись в `GET /api/promos/activations/my`
6. повторно активировать `WELCOME100` тем же пользователем и получить `promo_per_user_limit_exceeded`
7. под другим пользователем попробовать активировать персональный промокод `PERSONAL500` и получить `promo_for_another_user`
8. под пользователем попробовать активировать промокод из истекшей кампании и получить `campaign_expired`
9. под админом создать новую кампанию и новый промокод, затем получить их в списках
10. под админом отключить промокод через `POST /api/promos/{promo_id}/disable` и убедиться, что `is_active=false`
11. сначала активировать промокод, затем под админом попробовать изменить `promo_type` или `target_user_id` и получить `promo_immutable_after_activation`
12. под админом открыть `GET /api/promos/{promo_id}` и убедиться, что в ответе есть `history`

# заметка по устройству кампаний, типам промокодов, ограничениям активации и снапшоту

## как устроены кампании

кампания — это контейнер для группы промокодов

у кампании есть имя, флаг активности и окно действия по датам

промокод можно активировать только если одновременно выполняются условия по кампании и по самому промокоду

## какие бывают типы промокодов

`generic`

- общий промокод
- доступен всем пользователям, если проходит фильтры активности, дат и лимитов
- не должен иметь `target_user_id`

`personal`

- персональный промокод
- доступен только одному конкретному пользователю
- обязан иметь `target_user_id`
- другой пользователь не может его просматривать как доступный и не может активировать

## какие ограничения есть у активации

при активации проверяются

- активность кампании
- окно действия кампании
- активность промокода
- окно действия промокода
- принадлежность персонального промокода нужному пользователю
- общий лимит `max_activations`
- лимит на пользователя `per_user_limit`

активация всегда привязывается к текущему пользователю из bearer токена

## зачем нужен снапшот

если после активации админ изменит описание, код или бонусные баллы промокода, старая активация не должна переписаться задним числом

поэтому в `PromoActivation` сохраняются отдельные snapshot поля

- `applied_bonus_points`
- `promo_code_snapshot`
- `promo_description_snapshot`
- `promo_type_snapshot`
- `campaign_name_snapshot`

это гарантирует консистентную историю и делает аудит предсказуемым
