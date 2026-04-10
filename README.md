# Call Analytics - Анализ звонков отдела продаж из Битрикс24

Система автоматизированного аудита звонков отдела продаж. Подключается к Битрикс24, выгружает звонки менеджеров, транскрибирует через faster-whisper, анализирует через Claude API и формирует Excel-отчёты.

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Backend API | FastAPI (Python 3.11+) |
| Очередь задач | Celery + Redis |
| Планировщик | Celery Beat |
| Транскрибация | faster-whisper (модель small) |
| LLM-анализ | Claude API (claude-sonnet-4-20250514) |
| БД | PostgreSQL 16 |
| Хранилище аудио | MinIO (S3-совместимое) |
| Frontend | React + Tailwind CSS + Recharts |
| Контейнеризация | Docker Compose |

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repo-url>
cd soveshaniye
cp .env.example .env
```

### 2. Настройка переменных окружения

Отредактируйте `.env`:

```env
BITRIX_WEBHOOK_URL=https://your-domain.bitrix24.ru/rest/1/webhook-key/
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Запуск

```bash
docker compose up --build
```

### 4. Доступ

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000/docs
- **MinIO Console**: http://localhost:9001 (minioadmin / changeme_minio_password)

## Использование

### 1. Запуск выгрузки

Перейдите на страницу **Выгрузки** → выберите период → нажмите «Запустить выгрузку».

Система автоматически:
1. Выгрузит сотрудников и звонки из Битрикс24
2. Скачает аудиозаписи в MinIO
3. Транскрибирует через faster-whisper
4. Проанализирует каждый звонок через Claude API
5. Сформирует Excel-отчёт (7 листов)

### 2. Просмотр результатов

- **Дашборд** — сводка: кол-во звонков, средние оценки, рейтинг менеджеров, тренды
- **Звонки** — таблица всех звонков с фильтрами по сотруднику, периоду, направлению
- **Детали звонка** — аудиоплеер с синхронизацией транскрипта + карточка анализа
- **Сотрудники** — рейтинг с агрегированными оценками, профили с динамикой
- **Скрипты** — загрузка скриптов продаж (PDF, DOCX, TXT) для оценки соответствия

### 3. Критерии оценки (1-10)

1. **Приветствие** — представление, уточнение имени, цель звонка
2. **Выявление потребностей** — открытые вопросы, SPIN, бюджет/сроки/ЛПР
3. **Презентация** — привязка к потребностям, язык выгод, кейсы
4. **Работа с возражениями** — алгоритм обработки, настойчивость
5. **Закрытие** — следующий шаг, дата/время, инициатива
6. **Инициатива** — кто ведёт, проактивность, создание срочности

### 4. Excel-отчёт (7 листов)

1. **Сводка** — общие показатели, топ проблемы и рекомендации
2. **Рейтинг менеджеров** — таблица с условным форматированием
3. **Все звонки** — полная таблица с фильтрами
4. **Транскрипции** — тексты всех разговоров
5. **Анализ по сделкам** — группировка по сделкам
6. **Детальный анализ** — все оценки и цитаты
7. **Рекомендации** — приоритизированные действия

## Автоматизация

- **Celery Beat** — автовыгрузка каждый понедельник в 02:00 (МСК)
- **Bitrix24 Webhook** — real-time обработка при завершении звонка (`POST /api/webhooks/bitrix24/call-end`)
- **Telegram-бот** — уведомления о проанализированных звонках, алерты при низких оценках
- **Email-рассылка** — еженедельный отчёт руководителю с Excel-приложением
- **CRM-интеграция** — автозапись комментариев в сделку + создание follow-up задач

### Настройка уведомлений

В `.env`:
```env
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_CHAT_ID=-1001234567890
TELEGRAM_NOTIFICATIONS=true

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=user@gmail.com
SMTP_PASSWORD=app-password
NOTIFY_EMAIL_TO=manager@company.ru
EMAIL_NOTIFICATIONS=true

# CRM auto-comment
CRM_AUTO_COMMENT=true
LOW_SCORE_ALERT_THRESHOLD=4
```

### Настройка Bitrix24 Webhook (real-time)

1. Перейдите в Битрикс24 → Настройки → Вебхуки → Добавить исходящий вебхук
2. Событие: `ONVOXIMPLANTCALLEND`
3. URL: `https://your-server/api/webhooks/bitrix24/call-end`

## Архитектура

```
                                ┌─── Telegram Bot
                                │
Битрикс24 API ──→ [export_task] ──→ PostgreSQL
       │                │
  Webhook (RT)     MinIO (аудио)
       │                │
       └────→ [transcribe_task]
                        │
                  faster-whisper
                        │
                  [analyze_task] ──→ CRM (auto-comment)
                        │               │
                   Claude API      Telegram Alert
                        │
                  [report_task] ──→ Email + Telegram
                        │
                  Excel (MinIO)
```

## API документация

После запуска доступна по адресу: http://localhost:8000/docs

### Основные эндпоинты

```
POST   /api/exports                  — запустить выгрузку
GET    /api/exports                  — список выгрузок
GET    /api/exports/{id}             — статус выгрузки
GET    /api/exports/{id}/report      — скачать отчёт

GET    /api/calls                    — список звонков (фильтры)
GET    /api/calls/{id}               — детали + транскрипт + анализ
POST   /api/calls/{id}/reanalyze     — перезапустить анализ
GET    /api/calls/{id}/audio         — URL аудио

GET    /api/employees                — список сотрудников
GET    /api/employees/{id}           — профиль
GET    /api/employees/{id}/scores    — динамика оценок

GET/POST/PUT/DELETE /api/scripts     — управление скриптами

GET    /api/dashboard/summary        — сводка
GET    /api/dashboard/scores         — рейтинг
GET    /api/dashboard/trends         — тренды

POST   /api/webhooks/bitrix24/call-end — webhook real-time обработка
GET    /api/health                   — проверка здоровья
```
