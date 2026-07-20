# API

## `POST /v1/fact-check`

Проверяет один накопленный диалог. `product` должен точно совпадать с ключом в подключенном файле
чеклистов. `text` принимает до 100 000 символов. Поле `request_id` необязательно: при его отсутствии
используется `X-Request-ID`, а затем сгенерированный UUID.

Полные примеры находятся в [examples/request.json](../examples/request.json) и
[examples/response.json](../examples/response.json).

### Статусы результата

| Значение | Смысл |
|---|---|
| `complete` | Модель вернула валидный массив, все элементы прошли проверку схемы и привязку |
| `degraded` | Формат восстанавливался либо часть результата была отклонена |

Возможные предупреждения:

| Код | Смысл |
|---|---|
| `model_output_repaired` | Исходная генерация не была валидным JSON |
| `model_output_was_not_an_array` | Модель вернула одиночный объект |
| `model_output_unparseable` | Результат не удалось интерпретировать |
| `model_output_contains_invalid_entries` | Отдельные элементы не прошли схему |
| `model_returned_unknown_questions` | Вопрос отсутствует в выбранном чеклисте |
| `model_output_missing_explanations` | Для нарушения использовано резервное объяснение |

### HTTP ошибки

Ошибки имеют стабильную оболочку:

```json
{
  "error": {
    "code": "product_not_found",
    "message": "unknown product: missing"
  },
  "request_id": "c264ee95-36e2-4f72-bc7e-4f28504fab77"
}
```

| HTTP | Код | Причина |
|---|---|---|
| 404 | `product_not_found` | Нет точного ключа продукта |
| 422 | `invalid_request` | Запрос не соответствует схеме |
| 503 | `model_unavailable` | Модельный backend не ответил после повторов |

Актуальная OpenAPI-схема доступна в `/openapi.json`.

