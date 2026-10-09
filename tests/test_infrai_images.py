from __future__ import annotations

import asyncio
import base64

import httpx

from storefront_guard.infrai_images import InfraiImages


def test_approved_upload_uses_json() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/image/upload"
        assert request.headers["content-type"] == "application/json"
        assert request.headers["idempotency-key"] == "checkout-image:order-1"
        assert request.headers["authorization"] == "Bearer test-key"
        import json

        assert json.loads(request.content) == {
            "file": base64.b64encode(b"image bytes").decode("ascii"),
            "filename": "sample.png",
        }
        return httpx.Response(200, json={"ok": True, "data": {"id": "image-1"}})

    async def run() -> None:
        images = InfraiImages(api_key="test-key", transport=httpx.MockTransport(respond))
        try:
            result = await images.upload(b"image bytes", "sample.png", idempotency_key="checkout-image:order-1")
            assert result.image_id == "image-1"
        finally:
            await images.close()

    asyncio.run(run())
