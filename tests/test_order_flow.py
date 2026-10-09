from __future__ import annotations

import asyncio

from storefront_guard.order_flow import CheckoutImage, OrderState, StorefrontOrderFlow


class UploadSpy:
    called = False

    async def upload(self, image: bytes, filename: str, *, idempotency_key: str) -> None:
        self.called = True
        raise AssertionError("A rejected image must not be uploaded")


def test_unsafe_image_pauses_order_before_upload_and_receipt() -> None:
    images = UploadSpy()
    request = CheckoutImage(
        order_id="order-unsafe-7",
        customer_email="buyer@example.com",
        filename="listing.jpg",
        image_base64="aW1hZ2U=",
        moderation={"safe": False, "reason": "adult content detected"},
    )

    result = asyncio.run(StorefrontOrderFlow(images).submit(request, b"image"))  # type: ignore[arg-type]

    assert result.state == OrderState.IMAGE_REJECTED
    assert result.publish_image is False
    assert result.receipt_status == "not_issued"
    assert "paused" in result.customer_update.message
    assert images.called is False
