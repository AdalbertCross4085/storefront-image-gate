from __future__ import annotations

import base64
import binascii
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException

from .infrai_images import InfraiError, InfraiImages
from .order_flow import CheckoutImage, CheckoutResult, StorefrontOrderFlow


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    images = InfraiImages()
    app.state.flow = StorefrontOrderFlow(images)
    yield
    await images.close()


storefront = FastAPI(title="Storefront image gate", lifespan=lifespan)


@storefront.post("/checkout/image", response_model=CheckoutResult)
async def checkout_image(request: CheckoutImage) -> CheckoutResult:
    try:
        image_bytes = base64.b64decode(request.image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail="image_base64 must be valid base64") from exc
    try:
        return await storefront.state.flow.submit(request, image_bytes)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
