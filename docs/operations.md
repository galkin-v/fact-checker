# Эксплуатация

## Конфигурация

Все настройки API имеют префикс `FACT_CHECKER_`.

| Переменная | Значение по умолчанию |
|---|---|
| `FACT_CHECKER_CHECKLIST_PATH` | `data/checklists.json` |
| `FACT_CHECKER_MODEL_BASE_URL` | `http://model:8000/v1` |
| `FACT_CHECKER_MODEL_ID` | `galkinv42/qwen3_5_sft_74869` |
| `FACT_CHECKER_MODEL_API_KEY` | `local-model-token` |
| `FACT_CHECKER_MODEL_TIMEOUT_SECONDS` | `180` |
| `FACT_CHECKER_MODEL_MAX_TOKENS` | `4096` |
| `FACT_CHECKER_MODEL_MAX_CONCURRENCY` | `5` |
| `FACT_CHECKER_MODEL_RETRIES` | `2` |
| `FACT_CHECKER_MODEL_RETRY_BACKOFF_SECONDS` | `1` |
| `FACT_CHECKER_LOG_LEVEL` | `INFO` |

Compose дополнительно использует `HF_TOKEN`, `MODEL_MAX_LEN`,
`MODEL_GPU_MEMORY_UTILIZATION`, `GPU_COUNT` и `CHECKLIST_FILE`.

## Секреты и данные

- Передавайте `HF_TOKEN` и API keys через secret manager или закрытый `.env`; не помещайте их в
  образ, compose-файл или CI logs.
- Храните полный чеклист вне Git и монтируйте конкретную версию read-only.
- Сервис не сохраняет текст запросов и не пишет его в access log. В JSON logs остаются request ID,
  endpoint, код ответа и длительность.
- Ограничьте доступ к `/metrics`, `/docs` и API на уровне ingress, если сервис выходит за пределы
  доверенной сети.

## Проверка состояния

`/health/live` показывает, что процесс API работает. `/health/ready` дополнительно обращается к
`/v1/models` inference backend и возвращает 503 при его недоступности. Для оркестратора используйте
первый endpoint как liveness probe, второй как readiness probe.

Prometheus endpoint `/metrics` публикует число запросов по endpoint и статусу, а также latency
histogram. Высокая доля HTTP 503 означает проблему inference backend. Долю `degraded` следует считать
по прикладным ответам или на уровне вызывающего сервиса.

## Обновление модели и чеклиста

1. Разверните новую модель под отдельным immutable tag или revision.
2. Выполните smoke test на закрытом наборе, не помещая его в образ.
3. Подключите новый файл чеклиста с новым полем `version`.
4. Проверьте readiness и несколько известных положительных и отрицательных случаев.
5. Переключите трафик и сохраните старую пару model/checklist для отката.

Не меняйте вопросы внутри существующей версии: дословный вопрос является ключом безопасного
сопоставления с ID.

