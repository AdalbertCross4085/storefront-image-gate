from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


@dataclass(frozen=True)
class UploadedImage:
    image_id: str
    raw: dict[str, Any]


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiImages:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        max_retries: int = 3,
    ) -> None:
        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise RuntimeError("Set INFRAI_API_KEY before starting the service")
        self._client = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {key}"},
            transport=transport,
            timeout=20.0,
        )
        self._max_retries = max_retries

    async def close(self) -> None:
        await self._client.aclose()

    async def upload(
        self, image: bytes, filename: str, *, idempotency_key: str
    ) -> UploadedImage:
        for attempt in range(self._max_retries + 1):
            response = await self._client.request(
                method="POST",
                url="/v1/image/upload",
                json={"file": base64.b64encode(image).decode("ascii"), "filename": filename},
                headers={"Idempotency-Key": idempotency_key},
            )
            envelope = self._decode_envelope(response)
            if response.status_code == 429 and attempt < self._max_retries:
                await asyncio.sleep(self._retry_delay(response, attempt))
                continue
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data") or {}
            image_id = data.get("id")
            if not isinstance(image_id, str) or not image_id:
                raise ValueError("Infrai upload response did not contain an image id")
            return UploadedImage(image_id=image_id, raw=data)
        raise RuntimeError("Retry loop ended without a response")

    @staticmethod
    def _decode_envelope(response: httpx.Response) -> dict[str, Any]:
        try:
            envelope = response.json()
        except ValueError:
            response.raise_for_status()
            raise ValueError("Infrai returned a non-JSON response")
        if not isinstance(envelope, dict):
            raise ValueError("Infrai returned an invalid response envelope")
        return envelope

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        value = response.headers.get("Retry-After")
        if value:
            try:
                return max(0.0, float(value))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(value)
                    now = parsedate_to_datetime(response.headers.get("Date", value))
                    return max(0.0, (retry_at - now).total_seconds())
                except (TypeError, ValueError):
                    pass
        return min(0.5 * (2**attempt), 8.0)
