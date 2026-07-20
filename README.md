# Fact Checker

Сервис проверяет уже распознанный текст консультации по полному чеклисту выбранного продукта и
возвращает только найденные фактологические нарушения. Он реализует финальный проверочный контур:
контекстная привязка, классификация ответа, логическая верификация и безопасное сопоставление с ID
на стороне приложения.

В репозитории нет ASR, управления сессиями, пользовательского интерфейса, обучающей выборки,
эталонной разметки или весов модели. Приложенный чеклист состоит из трех синтетических записей и
нужен только для проверки запуска.

## Контракт

Вход содержит накопленный текст разговора и ключ продукта:

```json
{
  "product": "demo_card",
  "request_id": "contest-demo-001",
  "text": "Клиент: Сколько стоит выпуск виртуальной карты?\nСотрудник: Выпуск стоит 299 рублей."
}
```

Сервис возвращает нарушения, найденные относительно версии чеклиста:

```json
{
  "request_id": "contest-demo-001",
  "product": "demo_card",
  "checklist_version": "demo-2026-07",
  "model": "galkinv42/qwen3_5_sft_74869",
  "status": "complete",
  "violations": [
    {
      "checklist_id": 101,
      "question": "Сколько стоит выпуск виртуальной карты?",
      "expected_answer": "Выпуск виртуальной карты бесплатный.",
      "explanation": "Сотрудник назвал плату, хотя по чеклисту выпуск бесплатный."
    }
  ],
  "warnings": []
}
```

`status=degraded` означает, что ответ модели пришлось восстановить либо часть элементов была
отклонена. Такой ответ нельзя интерпретировать как подтверждение отсутствия нарушений.

## Запуск в Docker

Требуются Docker Compose, NVIDIA Container Toolkit и Hugging Face token с доступом к приватной
модели `galkinv42/qwen3_5_sft_74869`.

```bash
cp .env.example .env
# Укажите HF_TOKEN в .env
docker compose up --build
```

Первый запуск загружает модель в именованный Docker volume. API станет доступен на порту `8080`
после прохождения healthcheck модельного сервера.

```bash
curl --fail-with-body \
  -H 'Content-Type: application/json' \
  --data @examples/request.json \
  http://localhost:8080/v1/fact-check
```

Полный чеклист подключается без пересборки образа:

```bash
CHECKLIST_FILE=/secure/checklists/checklists-2026-07.json docker compose up --build
```

Файл монтируется read-only. Его формат описан в [data/README.md](data/README.md).

## Разработка

Проект использует Python 3.12 и `uv`.

```bash
uv sync --frozen
make check
make run
```

Тесты не загружают модель и не требуют GPU: модельный шлюз заменяется детерминированной заглушкой.
Для подключения уже развернутого OpenAI-compatible inference endpoint запустите API-образ отдельно
и задайте `FACT_CHECKER_MODEL_BASE_URL`, `FACT_CHECKER_MODEL_ID` и
`FACT_CHECKER_MODEL_API_KEY`.

## Эксплуатационные endpoints

| Endpoint | Назначение |
|---|---|
| `POST /v1/fact-check` | Проверить накопленный текст диалога |
| `GET /health/live` | Проверить процесс API |
| `GET /health/ready` | Проверить доступность модельного backend |
| `GET /metrics` | Получить Prometheus-метрики |
| `GET /docs` | Открыть интерактивную OpenAPI-схему |

Подробности: [архитектура](docs/architecture.md), [API](docs/api.md) и
[эксплуатация](docs/operations.md).
