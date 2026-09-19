# Football API — CRUD-сервис футбольной статистики

Backend-сервис для модуля по масштабированию баз данных.
Стек: **Python 3.12 + FastAPI + PostgreSQL 16**, чистый SQL (без ORM), Docker Compose.

---

## О проекте

Предметная область — **футбольная статистика**:

* команды играют в турнирах (одна команда может участвовать в нескольких турнирах);
* за каждой командой закреплены игроки;
* команды встречаются в матчах (хозяева и гости);
* в каждом матче происходят события (`match_events`) — голы, голевые передачи,
  жёлтые и красные карточки, замены;
* по событиям считаются отчёты: бомбардиры, статистика по турнирам и по командам.

Сервис реализует CRUD по всем основным сущностям, запросы со связями, фильтрацию,
пагинацию, сортировку и агрегирующие отчёты.

---

## Запуск

```bash
docker compose up --build
```

Поднимаются семь контейнеров: `postgres` (primary), `postgres_replica` (реплика только
для чтения), три независимых шарда `shard_0`, `shard_1`, `shard_2`, `backend` и `scheduler`.
При первом запуске реплика копирует базу с primary через `pg_basebackup`, backend ждёт,
пока реплика и все шарды станут healthy.
При старте backend автоматически:

1. накатывает миграции на primary и на каждый шард (`python -m app.migrate`),
2. создаёт недостающие партиции `match_events` на текущий месяц и 3 месяца вперёд
   (`python -m app.jobs.create_partitions`),
3. заливает небольшой набор тестовых данных, если база пустая (`python -m app.seed`),
4. запускает API.

`scheduler` стартует только после того, как backend стал healthy (значит, миграции уже
применены): раз в сутки создаёт будущие партиции, каждые 5 минут проверяет, что они есть,
и при проблеме шлёт алерт в Telegram — см. раздел «Партиционирование и алерты».

После запуска:

| Что | Адрес |
|---|---|
| API | http://localhost:8001 |
| Swagger UI | http://localhost:8001/docs |
| ReDoc | http://localhost:8001/redoc |
| OpenAPI JSON | http://localhost:8001/openapi.json |
| Health check | http://localhost:8001/health |
| PostgreSQL primary | `localhost:5436`, база/логин/пароль: `football` |
| PostgreSQL replica | `localhost:5437`, только чтение, тот же логин/пароль |
| PostgreSQL shard 0 / 1 / 2 | `localhost:5440` / `5441` / `5442`, тот же логин/пароль |

> Нестандартные порты (8001, 5436, 5437, 5440–5442) выбраны, чтобы сервис не конфликтовал с
> другими проектами на той же машине. Внутри docker-сети backend ходит в базу
> по обычному `postgres:5432`.

Полный сброс базы:

```bash
docker compose down -v && docker compose up --build
```

---

## Архитектура

```
Client
  ↓
Backend API (FastAPI)
  ↓ запись и чтение              ↓ GET /api/events              ↓ /api/shards/* (router по match_id)
PostgreSQL primary  ── WAL ──▶  PostgreSQL replica             shard_0   shard_1   shard_2
```

Внутри backend строго три слоя, роутеры в базу не ходят:

```
app/api/*.py           Controller — HTTP: маршруты, параметры, коды ответов
        ↓
app/services/*.py      Service    — бизнес-логика, проверки связей, транзакции
        ↓
app/repositories/*.py  Repository — SQL-запросы, единственное место работы с БД
        ↓
PostgreSQL
```

Структура проекта:

```
app/
  main.py               точка входа, подключение роутеров, обработка ошибок
  config.py             DATABASE_URL, REPLICA_DATABASE_URL, SHARD_URLS, Telegram, какие таблицы партиционируются
  db.py                 пулы соединений psycopg3: primary, реплика и по одному на каждый шард; запрос в один или во все шарды
  sharding.py           router: hash(key) % N и consistent hash ring с виртуальными узлами
  errors.py             NotFoundError / ConflictError / ShardUnavailableError -> 404 / 409 / 503
  schemas.py            pydantic-модели запросов и ответов
  migrate.py            система миграций (primary и шарды)
  seed.py               заливка тестовых данных
  telegram.py           отправка сообщений через Telegram Bot API
  api/                  teams, tournaments, players, matches, events, reports, shards, health
  services/             бизнес-логика (partitions.py — job, проверка партиций, алерты)
  repositories/         SQL (partitions.py — системный каталог и состояние алертов)
  jobs/
    create_partitions.py  CreatePartitionsJob
    check_partitions.py   PartitionHealthCheck + алерт
    scheduler.py          ежедневный запуск job и периодическая проверка
sql/
  migrations/001_init.sql                    схема БД
  migrations/002_indexes.sql                 индексы match_events (лаба №1)
  migrations/003_match_events_created_at.sql индекс по created_at (лаба №2)
  migrations/004_partition_match_events.sql  match_events → партиции по месяцам (лаба №3)
  migrations/005_partition_alerts.sql        состояние алертов по партициям
  seed.sql                                   небольшой набор тестовых данных
  shard_migrations/001_match_events.sql      таблица match_events на каждом шарде (лаба №5)
scripts/
  generate_data.py      массовая генерация данных через COPY
  replication_lag.py    замер отставания реплики (лаба №4)
  shard_load.py         раскладка match_events с primary по шардам через router (лаба №5)
  shard_compare.py      сколько записей переедет при 3 → 4 шардах: % N против hash ring (лаба №5)
  shard_queries.py      COUNT / AVG / DISTINCT / top-N / ORDER BY LIMIT по шардам, замеры (лаба №6)
  shard_hotspot.py      нагрузка на шарды: случайные матчи против одного горячего (лаба №6)
postgres/
  pg_hba.conf           доступ к primary, в том числе для репликации
  init-replication.sql  роль replicator
  replica-entrypoint.sh клонирование primary через pg_basebackup и запуск реплики
```

### Миграции

Схема БД не создаётся руками: все изменения — только через `.sql` файлы в `sql/migrations`.
Файлы применяются по порядку имён ровно один раз, применённые записываются в таблицу
`schema_migrations`.

Новая миграция = новый файл `sql/migrations/006_....sql`, применяется при следующем запуске
или вручную:

```bash
docker compose exec backend python -m app.migrate
```

---

## Схема БД

```
tournaments ──N───N── teams ──1───N── players
      │                 │  │              │
      1                 1  1              1
      │                 │  │              │
      N                 N  N              N
   matches ────────────────┘           match_events
      │                                    ▲
      └────────────────1───N───────────────┘
```

Словами: команда участвует во многих турнирах и турнир содержит много команд
(many-to-many через `team_tournaments`); у команды много игроков; матч принадлежит
турниру и связан с двумя командами (хозяева и гости); у матча много событий,
и у игрока много событий.

| Таблица | Назначение | Ключи и связи |
|---|---|---|
| `teams` | команды | PK `id` |
| `tournaments` | турниры | PK `id`, UNIQUE `name` |
| `team_tournaments` | команда ↔ турнир | составной PK (`team_id`, `tournament_id`), два FK — **many-to-many** |
| `players` | игроки | PK `id`, FK `team_id → teams.id` (one-to-many) |
| `matches` | матчи | PK `id`, FK `tournament_id → tournaments.id`, FK `home_team_id → teams.id`, FK `away_team_id → teams.id`, CHECK на статус и на `home_team_id <> away_team_id` |
| `match_events` | **события матчей** | PK (`id`, `created_at`), FK `match_id → matches.id`, FK `player_id → players.id`, CHECK на тип события и минуту; партиционирована по `created_at` (RANGE, по месяцам) |

`match_events`:

| Колонка | Тип | Комментарий |
|---|---|---|
| `id` | BIGINT | значение из последовательности `match_events_id_seq`, часть PK |
| `match_id` | BIGINT | FK на `matches` |
| `player_id` | BIGINT | FK на `players` |
| `event_type` | TEXT | `GOAL` / `ASSIST` / `YELLOW_CARD` / `RED_CARD` / `SUBSTITUTION` (CHECK) |
| `minute` | INTEGER | минута матча, 0..130 (CHECK) |
| `created_at` | TIMESTAMPTZ | момент события — временное поле основной сущности, часть PK и ключ партиционирования |
| `updated_at` | TIMESTAMPTZ | последнее изменение записи |

`created_at` есть также у `teams`, `players`, `matches`.

### Индексы

Изначально дополнительных индексов не было — только PRIMARY KEY и UNIQUE. По условиям
модуля сначала нужно было получить исходное, неоптимизированное состояние и самим
измерить, какие запросы деградируют при росте объёма данных.

По итогам лабораторной №1 миграцией `002_indexes.sql` добавлены два индекса на
`match_events`:

| Индекс | Колонки | Зачем |
|---|---|---|
| `idx_match_events_player_created_at` | `(player_id, created_at desc)` | фильтр `GET /api/events?player_id=` вместе с сортировкой по умолчанию `created_at desc` и пагинацией: убирает и Seq Scan, и узел Sort. Левый префикс `(player_id)` переиспользуется запросами, где фильтр только по игроку |
| `idx_match_events_match_id` | `(match_id)` | фильтр `GET /api/events?match_id=`, а также каскадное удаление `on delete cascade` при удалении матча — без индекса оно вызывало полный проход по таблице |

Замеры до и после, планы выполнения и обоснование порядка колонок — в [labs/1.md](labs/1.md).

По итогам лабораторной №2 миграцией `003_match_events_created_at.sql` добавлен индекс
`idx_match_events_created_at (created_at)`, а count для пагинации в `GET /api/events`
больше не джойнит `matches` и `players`, если нет фильтра по турниру или команде
(`match_id` и `player_id` — NOT NULL с внешними ключами, так что количество строк от этого
не меняется). На 5 млн событий `GET /api/events?from=...&to=...` ускорился примерно
с 0.5–0.8 с до 0.03 с, `GET /api/events` без фильтров — с 3–4 с до 0.15 с.
Замеры на 1/3/5 млн строк и запросы, которым индекс не помог, — в [labs/2.md](labs/2.md).

### Партиционирование и алерты

По итогам лабораторной №3 `match_events` партиционирована миграцией `004_partition_match_events.sql`:

* стратегия `RANGE` по `created_at`, одна партиция на календарный месяц (`match_events_2026_08` и т. д.);
* миграция создаёт партиции от месяца самого старого события (и не позже чем за 24 месяца
  до текущего) до текущего месяца + 3 вперёд и переносит в них данные;
* первичный ключ стал `(id, created_at)` — ключ партиционирования обязан входить в PK;
* индексы объявлены на родительской таблице, PostgreSQL сам создаёт их в каждой партиции.

Запросы с условием на `created_at` (`GET /api/events?from=&to=`, `GET /api/reports/top-scorers?from=&to=`)
читают только партиции нужного периода (partition pruning). Запросы без даты
(`GET /api/events/{id}`, `GET /api/events?player_id=`) обходят все партиции, поиск по `id`
стал немного дороже.

Будущие партиции руками не создаются:

| Что | Команда | Когда запускается |
|---|---|---|
| CreatePartitionsJob | `python -m app.jobs.create_partitions` | при старте backend и раз в сутки в `scheduler` (после `PARTITION_JOB_HOUR`, по умолчанию 1:00 UTC) |
| PartitionHealthCheck | `python -m app.jobs.check_partitions` | в `scheduler` каждые `PARTITION_CHECK_INTERVAL` секунд (по умолчанию 300) |

Какие таблицы обслуживаются и на сколько вперёд — `PARTITIONED_TABLES` в `app/config.py`
(сейчас `match_events`, шаг — месяц, горизонт — 3). Для ручного запуска по другой таблице
есть параметры `--table`, `--step day|month`, `--ahead`, `--today YYYY-MM-DD`:

```bash
docker compose exec backend python -m app.jobs.create_partitions
docker compose exec scheduler python -m app.jobs.check_partitions
docker compose exec backend python -m app.jobs.create_partitions --table lab3.events --step day --ahead 3
```

Проверку запускайте в контейнере `scheduler`: переменные Telegram переданы только ему, из `backend`
алерт не уйдёт.

Job создаёт только отсутствующие партиции, поэтому её можно запускать сколько угодно раз.
Проверка сравнивает ожидаемые партиции с `pg_inherits`: всё есть — `OK`, чего-то нет —
`CRITICAL` (код выхода 2). Сообщение в Telegram уходит только при смене состояния:
`OK → CRITICAL` — alert, `CRITICAL → OK` — recovery. Последнее состояние хранится в таблице
`partition_alerts`; если отправить сообщение не удалось, состояние не сохраняется и попытка
повторится на следующей проверке.

Чтобы алерты приходили, создайте бота у @BotFather, узнайте `chat_id` и положите в `.env`
рядом с `docker-compose.yml`:

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

затем `docker compose up -d scheduler`. Без этих переменных проверка работает, но вместо
отправки пишет в лог, что Telegram не настроен.

Замеры до и после партиционирования и сценарий «сломали партицию → alert → восстановили →
recovery» — в [labs/3.md](labs/3.md).

---

### Репликация (Primary + Replica)

`postgres` — primary: принимает все `INSERT` / `UPDATE` / `DELETE`. `postgres_replica` — его
физическая копия, получает поток WAL (streaming replication, асинхронно, слот `replica_1`)
и доступна только на чтение.

* primary запускается с `wal_level=replica`, `max_wal_senders`, `max_replication_slots` и своим
  `pg_hba.conf`, где роли `replicator` разрешено подключение `replication`;
* при пустом volume `postgres/replica-entrypoint.sh` делает `pg_basebackup -R -S replica_1`:
  копирует данные primary, создаёт `standby.signal` и `primary_conninfo`;
* в backend два пула (`app/db.py`): `connection()` — primary, `replica_connection()` — реплика.
  На реплику идёт список событий `GET /api/events` (`services/events.py`), всё остальное
  и все записи — на primary.

Реплика асинхронная, поэтому может немного отставать: событие, только что созданное через
`POST`, может ещё не появиться в `GET /api/events`.

```bash
docker compose exec postgres psql -U football -d football -c "select * from pg_stat_replication;"
docker compose exec postgres_replica psql -U football -d football -c "select pg_is_in_recovery();"
docker compose exec backend python scripts/replication_lag.py
```

На роль `replicator` init-скрипт срабатывает только на пустом volume. Если база была
создана раньше, роль создаётся один раз вручную:

```bash
docker compose exec -T postgres psql -U football -d football < postgres/init-replication.sql
```

### Шардирование (лаба №5)

`match_events` разложены по трём независимым PostgreSQL (`shard_0`, `shard_1`, `shard_2`).
Шарды ничего не знают друг о друге и о primary: у каждого своя база, свой volume и своя
таблица `match_events` (миграции из `sql/shard_migrations`, без внешних ключей — таблицы
`matches` и `players` живут на другом сервере). Куда идти, решает код backend.

* **Shard key** — `match_id`: все события одного матча лежат на одном шарде, поэтому
  события матча читаются из одного шарда.
* **Router** — `app/sharding.py`. Хэш — первые 4 байта md5 от ключа (число от 0 до 2³²−1).
  Встроенный `hash()` Python не подходит: для строк он меняется при каждом запуске процесса.
  * `SHARD_STRATEGY=mod` — `shard = hash(match_id) % N`;
  * `SHARD_STRATEGY=ring` (по умолчанию) — consistent hash ring: у каждого шарда
    `SHARD_VNODES` точек на кольце (`shard-0#0`, `shard-0#1`, …, по умолчанию 1000),
    ключ идёт по кольцу по часовой стрелке до первой точки.
* **id** нового события берётся из последовательности `match_events_id_seq` на primary,
  поэтому id уникальны сразу на всех шардах.

| Метод | Путь | Что делает |
|---|---|---|
| GET | `/api/shards` | `COUNT(*)` на каждом шарде и сумма; упавший шард — `ok: false`, `partial: true` |
| GET | `/api/shards/route?match_id=` | хэш ключа и номер шарда |
| GET | `/api/shards/matches/{id}/events` | события матча — один шард, JOIN с игроками и матчем в коде backend |
| GET | `/api/shards/events` | лента событий (`created_at DESC`): с `match_id` — один шард, без него — все шарды + merge |
| GET | `/api/shards/reports/top-scorers` | бомбардиры: частичные суммы по игрокам со всех шардов, сложение и сортировка в backend |
| GET | `/api/shards/events/{id}` | событие по id — shard key неизвестен, спрашиваем все шарды параллельно |
| POST | `/api/shards/events` | создать событие — router выбирает шард по `match_id` |

Остальной сервис (`/api/events`, `/api/reports/*`) по-прежнему работает с `match_events` на primary.
На шардах нет таблиц `matches`, `players`, `teams`, поэтому JOIN с ними делается в коде:
сначала события с шарда, потом один запрос в primary `where p.id = any(...)`.

### Запросы после шардирования (лаба №6)

* **Scatter-gather** — `db.query_shards(fn, shards)` выполняет `fn` на нескольких шардах
  параллельно (`ThreadPoolExecutor`) и возвращает `{шард: результат}`; объединение — в сервисе:
  * `COUNT(*)` — сумма чисел с шардов;
  * `ORDER BY created_at DESC LIMIT n` — с каждого шарда `offset + limit` строк, потом
    `heapq.merge` по `(created_at, id)` и срез нужной страницы;
  * бомбардиры — с каждого шарда `GROUP BY player_id` без `LIMIT`, суммы складываются
    в backend: top-10 каждого шарда давал бы неверный результат.
* **Отказ шарда** — пул шарда ждёт соединение не дольше `SHARD_TIMEOUT` (2 с), после чего
  backend отвечает `503 {"detail": "Шард недоступен: 2", "shards": [2]}`. Запросы в живые
  шарды и весь сервис на primary продолжают работать, `/health` возвращает `degraded`
  со статусом каждого шарда (HTTP 200).

```bash
docker compose exec backend python -m scripts.shard_queries
docker compose exec backend python -m scripts.shard_hotspot
```

`shard_queries` — замеры: `COUNT(*)` по очереди и параллельно, `AVG` и `COUNT(DISTINCT)`
по шардам, наивный и правильный top-10 бомбардиров, `ORDER BY ... LIMIT` с merge, время
запроса от числа шардов. `shard_hotspot` — 3000 запросов через API: матчи случайные и
«финал» (60 % запросов про один матч), нагрузка на шарды по `pg_stat_database`.
Подробности — в [labs/6.md](labs/6.md).

```bash
docker compose exec backend python -m scripts.shard_load
docker compose exec backend python -m scripts.shard_compare
```

`shard_load` очищает шарды и раскладывает все события с primary по текущей стратегии
(или по `--strategy`). После смены стратегии или количества шардов данные надо разложить
заново — иначе router будет искать записи не на том шарде. `shard_compare` берёт данные
с шардов и считает, сколько записей сменит шард при 3 → 4, 4 → 5 и удалении шарда.
На 5 000 029 событиях при 3 → 4: `hash % N` — 74.91 %, hash ring (1000 vnodes) — 25.28 %.
Подробности — в [labs/5.md](labs/5.md).

Запуск со стратегией `mod`:

```bash
SHARD_STRATEGY=mod docker compose up -d backend
```

---

## Основная сущность для масштабирования

```
Основная сущность для масштабирования: match_events
```

**Почему она подходит:**

* `match_events` — это поток событий, а не справочник. Команд, турниров и игроков
  конечное количество, матчей за сезон тоже ограниченное число, а событий в каждом
  матче десятки — таблица растёт в десятки раз быстрее всех остальных и никогда
  не чистится.
* Есть естественное временное поле `created_at` (момент события) — данные копятся
  строго по времени, что удобно для партиционирования по диапазону дат.
* Записи практически не обновляются после матча — типичная append-only нагрузка,
  удобная для реплик и шардирования.
* Именно `match_events` участвует во всех тяжёлых запросах: JOIN с матчами, игроками
  и командами, фильтрация по типу события и периоду, агрегации бомбардиров и
  статистики команд. При миллионах строк деградируют в первую очередь они.
* Есть очевидный ключ шардирования — `match_id` (или диапазон `created_at`).

---

## Основные endpoint'ы

Полное описание с параметрами и телами запросов — в Swagger: http://localhost:8001/docs

### Служебные

| Метод | Путь | Описание |
|---|---|---|
| GET | `/health` | приложение живо и видит PostgreSQL |
| GET | `/api/shards[/...]` | шардирование `match_events`, см. раздел «Шардирование» |

### CRUD

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/teams` | список команд (`search`, `city`, `tournament`, пагинация, сортировка) |
| GET | `/api/teams/{id}` | команда по id вместе со списком турниров |
| POST | `/api/teams` | создать команду (в теле `tournament_ids` — связи many-to-many) |
| PUT | `/api/teams/{id}` | обновить команду и её турниры |
| DELETE | `/api/teams/{id}` | удалить команду |
| GET/POST/PUT/DELETE | `/api/tournaments[/{id}]` | CRUD по турнирам |
| GET | `/api/players` | список игроков (`search`, `team_id`, `position`, `tournament`, `year_from`, `year_to`, пагинация, сортировка) |
| GET | `/api/players/{id}` | игрок вместе с командой и турнирами команды |
| POST/PUT/DELETE | `/api/players[/{id}]` | остальной CRUD по игрокам |
| GET | `/api/matches` | список матчей (JOIN + фильтры + пагинация) |
| GET | `/api/matches/{id}` | матч по id |
| POST/PUT/DELETE | `/api/matches[/{id}]` | остальной CRUD по матчам |
| GET | `/api/events` | список событий матчей (JOIN + фильтры + пагинация) |
| GET | `/api/events/{id}` | событие по id |
| POST/PUT/DELETE | `/api/events[/{id}]` | остальной CRUD по событиям |

### Связанные сущности

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/teams/{id}/players` | игроки команды |
| GET | `/api/teams/{id}/matches` | матчи команды (дома и в гостях) |
| GET | `/api/teams/{id}/events` | события игроков команды |
| GET | `/api/players/{id}/events` | события конкретного игрока |
| GET | `/api/matches/{id}/events` | события конкретного матча |

### Отчёты (агрегация)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/reports/top-scorers` | бомбардиры за период |
| GET | `/api/reports/tournaments` | матчи и голы по турнирам |
| GET | `/api/reports/teams` | статистика по командам |

### Pagination, filtering, sorting

Пагинация (`page`, `page_size`) есть у `/api/teams`, `/api/players`, `/api/matches`,
`/api/events` и связанных списков. Ответ:

```json
{ "items": [ ... ], "total": 1000029, "page": 1, "page_size": 20 }
```

Примеры:

```
GET /api/events?page=1&page_size=20
GET /api/events?event_type=GOAL
GET /api/events?from=2026-01-01&to=2026-02-01
GET /api/events?team_id=1&sort=-created_at
GET /api/events?match_id=3&sort=minute
GET /api/matches?status=FINISHED&tournament_id=1
GET /api/matches?team_id=2
GET /api/players?search=Зенит
GET /api/players?position=GK&sort=-shirt_number
GET /api/players?tournament=Лига чемпионов
GET /api/teams?city=Москва
```

Сортировка: `?sort=created_at` (ASC) и `?sort=-created_at` (DESC).
Имена колонок берутся из белого списка в репозитории, так что SQL-инъекция невозможна.

---

## Сложные запросы

Все запросы ниже реально выполняются сервисом (лежат в `app/repositories/`),
а не хранятся отдельным `.sql` файлом.

### JOIN-запрос №1 — игроки с командой и турнирами команды

`app/repositories/players.py`, используется в `GET /api/players`,
`GET /api/players/{id}`, `GET /api/teams/{id}/players`.

```sql
select p.id,
       p.full_name,
       p.team_id,
       t.name as team_name,
       t.city as team_city,
       p.position,
       p.birth_year,
       p.shirt_number,
       p.created_at,
       coalesce(
           array_agg(tr.name order by tr.name) filter (where tr.id is not null),
           '{}'
       ) as tournaments
from players p
join teams t                  on t.id = p.team_id
left join team_tournaments tt on tt.team_id = t.id
left join tournaments tr      on tr.id = tt.tournament_id
where (p.full_name ilike %s or t.name ilike %s)
  and exists (
      select 1
      from team_tournaments tt2
      join tournaments tr2 on tr2.id = tt2.tournament_id
      where tt2.team_id = p.team_id and tr2.name ilike %s
  )
group by p.id, t.name, t.city
order by p.full_name asc
limit %s offset %s;
```

Здесь сразу: JOIN двух видов, проход по many-to-many, поиск через `ILIKE`,
агрегация списка турниров, сортировка и пагинация.

### JOIN-запрос №2 — матчи с турниром и обеими командами

`app/repositories/matches.py`, используется в `GET /api/matches`,
`GET /api/matches/{id}`, `GET /api/teams/{id}/matches`.

```sql
select m.id,
       m.tournament_id,
       tr.name  as tournament_name,
       m.home_team_id,
       ht.name  as home_team_name,
       m.away_team_id,
       awt.name as away_team_name,
       m.status, m.started_at, m.home_score, m.away_score, m.created_at
from matches m
join tournaments tr on tr.id  = m.tournament_id
join teams ht       on ht.id  = m.home_team_id
join teams awt      on awt.id = m.away_team_id
where m.status = %s
  and (m.home_team_id = %s or m.away_team_id = %s)
  and m.started_at BETWEEN %s and %s
order by m.started_at desc
limit %s offset %s;
```

Интересен тем, что таблица `teams` присоединяется дважды под разными псевдонимами
(хозяева и гости) — обычный self-join.

### JOIN-запрос №3 — события матчей со всеми участниками

`app/repositories/events.py`, используется в `GET /api/events`,
`GET /api/matches/{id}/events`, `GET /api/players/{id}/events`,
`GET /api/teams/{id}/events`. Самый тяжёлый запрос сервиса.

```sql
select e.id, e.match_id, e.player_id, e.event_type, e.minute,
       e.created_at, e.updated_at,
       p.full_name  as player_name,
       t.id         as team_id,
       t.name       as team_name,
       m.tournament_id,
       m.started_at as match_started_at,
       ht.name      as home_team_name,
       awt.name     as away_team_name
from match_events e
join matches m on m.id  = e.match_id
join players p on p.id  = e.player_id
join teams t   on t.id  = p.team_id
join teams ht  on ht.id = m.home_team_id
join teams awt on awt.id = m.away_team_id
where e.event_type = %s
  and p.team_id = %s
  and m.tournament_id = %s
  and e.created_at BETWEEN %s and %s
order by e.created_at desc
limit %s offset %s;
```

Пять JOIN от самой большой таблицы, фильтр по диапазону дат и по типу события,
сортировка по `created_at`. Главный кандидат на проблемы при росте `match_events`.

### Агрегирующий запрос — бомбардиры за период

`app/repositories/reports.py`, используется в `GET /api/reports/top-scorers`.

```sql
select p.id as player_id,
       p.full_name,
       t.name as team_name,
       count(*) filter (where e.event_type = 'GOAL')   as goals,
       count(*) filter (where e.event_type = 'ASSIST') as assists,
       count(*) filter (
           where e.event_type in ('YELLOW_CARD', 'RED_CARD')
       )                                               as cards
from match_events e
join matches m on m.id = e.match_id
join players p on p.id = e.player_id
join teams t   on t.id = p.team_id
where e.created_at >= %s and e.created_at <= %s
  and m.tournament_id = %s
group by p.id, p.full_name, t.name
order by goals desc, assists desc, p.full_name asc
limit %s;
```

Ещё две агрегации:

* `GET /api/reports/tournaments` — количество команд скалярным подзапросом,
  `COUNT DISTINCT` по матчам, голы через `COUNT ... FILTER` и среднее число голов
  за матч делением;
* `GET /api/reports/teams` — `COUNT DISTINCT` по игрокам, голы и карточки через
  `COUNT ... FILTER`, `MAX(created_at)` по последнему событию команды.

---

## Генерация данных

Небольшой набор данных (6 команд, 4 турнира, 24 игрока, 8 матчей, 29 событий)
заливается автоматически при первом `docker compose up` — этого достаточно, чтобы
потрогать API. Имена игроков вымышленные.

Массовая генерация — скрипт `scripts/generate_data.py`, который пишет данные
через `COPY ... FROM STDIN`, а не через API:

```bash
# базовый набор
docker compose exec backend python scripts/generate_data.py \
    --teams 500 --players 15000 --matches 100000 --events 1000000

# только события матчей, ещё 5 млн строк
docker compose exec backend python scripts/generate_data.py --events 5000000

# разброс дат матчей за последний год
docker compose exec backend python scripts/generate_data.py --matches 50000 --days 365
```

Параметры: `--teams`, `--players`, `--matches`, `--events`, `--days`, `--seed`.
Данные добавляются к существующим, ничего не удаляется. События привязываются к
игрокам тех команд, которые реально играли в матче. В конце скрипт выполняет
`ANALYZE` и печатает количество строк в каждой таблице.

События пишутся в партиции `match_events`, а на чистой базе партиции создаются на 24 месяца
назад. Поэтому события для матчей старше 24 месяцев (`--days` больше 730) не вставятся:
`no partition of relation "match_events" found for row`.

Ориентир по скорости (локально, Docker на macOS): **1 000 000 событий ≈ 17 секунд**.

Замер после генерации 1 млн событий без единого дополнительного индекса:

| Запрос | Время |
|---|---|
| `GET /api/events?page_size=20` | ~0.45 с |
| `GET /api/reports/top-scorers` | ~0.82 с |
| `GET /api/reports/teams` | ~1.4 с |
| `GET /api/reports/tournaments` | ~1.7 с |

Это и есть исходное состояние, которое будем оптимизировать на занятиях.

Посмотреть план запроса:

```bash
docker compose exec postgres psql -U football -d football -c "EXPLAIN ANALYZE SELECT count(*) FROM match_events WHERE event_type = 'GOAL';"
```

---

## Локальный запуск без Docker (необязательно)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql://football:football@localhost:5436/football
python -m app.migrate && python -m app.jobs.create_partitions && python -m app.seed
uvicorn app.main:app --reload
```
