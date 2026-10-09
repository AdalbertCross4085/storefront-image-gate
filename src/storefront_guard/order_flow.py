from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .infrai_images import InfraiImages


class OrderState(StrEnum):
    IMAGE_REVIEW = "image_review"
    PAYMENT_CAPTURED = "payment_captured"
    FULFILLMENT_READY = "fulfillment_ready"
    IMAGE_REJECTED = "image_rejected"


class ModerationAssessment(BaseModel):
    safe: bool
    reason: str | None = None


class CheckoutImage(BaseModel):
    order_id: str = Field(min_length=1)
    customer_email: str = Field(min_length=3)
    filename: str = Field(min_length=1)
    image_base64: str = Field(min_length=1)
    moderation: ModerationAssessment


class CustomerUpdate(BaseModel):
    channel: str
    message: str


class CheckoutResult(BaseModel):
    order_id: str
    state: OrderState
    publish_image: bool
    image_id: str | None
    receipt_status: str
    customer_update: CustomerUpdate


class StorefrontOrderFlow:
    def __init__(self, images: InfraiImages) -> None:
        self._images = images

    async def submit(self, request: CheckoutImage, image_bytes: bytes) -> CheckoutResult:
        if not request.moderation.safe:
            reason = request.moderation.reason or "The product image needs review"
            return CheckoutResult(
                order_id=request.order_id,
                state=OrderState.IMAGE_REJECTED,
                publish_image=False,
                image_id=None,
                receipt_status="not_issued",
                customer_update=CustomerUpdate(
                    channel="email",
                    message=f"Order {request.order_id} is paused: {reason}.",
                ),
            )

        uploaded = await self._images.upload(
            image_bytes,
            request.filename,
            idempotency_key=f"checkout-image:{request.order_id}",
        )
        return CheckoutResult(
            order_id=request.order_id,
            state=OrderState.FULFILLMENT_READY,
            publish_image=True,
            image_id=uploaded.image_id,
            receipt_status="issued",
            customer_update=CustomerUpdate(
                channel="email",
                message=f"Order {request.order_id} is paid and ready for fulfillment.",
            ),
        )
