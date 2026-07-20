import asyncio
from collections.abc import Sequence
from typing import Protocol

import httpx

from fact_checker.config import Settings


class ModelGateway(Protocol):
    model_id: str

    async def complete(self, messages: Sequence[dict[str, str]]) -> str: ...

    async def ready(self) -> bool: ...

    async def close(self) -> None: ...


class ModelGatewayError(RuntimeError):
    pass


class OpenAIModelGateway:
    def __init__(self, settings: Settings) -> None:
        self.model_id = settings.model_id
        self._max_tokens = settings.model_max_tokens
        self._retries = settings.model_retries
        self._backoff = settings.model_retry_backoff_seconds
        self._semaphore = asyncio.Semaphore(settings.model_max_concurrency)
        api_key = settings.model_api_key.get_secret_value()
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.AsyncClient(
            base_url=settings.model_base_url.rstrip("/") + "/",
            headers=headers,
            timeout=httpx.Timeout(settings.model_timeout_seconds),
        )

    async def complete(self, messages: Sequence[dict[str, str]]) -> str:
        payload = {
            "model": self.model_id,
            "messages": list(messages),
            "temperature": 0,
            "max_tokens": self._max_tokens,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }

        async with self._semaphore:
            for attempt in range(self._retries + 1):
                try:
                    response = await self._client.post("chat/completions", json=payload)
                    if response.status_code == 429 or response.status_code >= 500:
                        response.raise_for_status()
                    if response.is_error:
                        raise ModelGatewayError(
                            f"model server returned HTTP {response.status_code}"
                        )

                    body = response.json()
                    content = body["choices"][0]["message"]["content"]
                    if not isinstance(content, str) or not content.strip():
                        raise ModelGatewayError("model server returned an empty completion")
                    return content
                except ModelGatewayError:
                    raise
                except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
                    if attempt >= self._retries:
                        raise ModelGatewayError("model server request failed") from error
                    await asyncio.sleep(self._backoff * (attempt + 1))

        raise ModelGatewayError("model server request failed")

    async def ready(self) -> bool:
        try:
            response = await self._client.get("models", timeout=3.0)
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()
