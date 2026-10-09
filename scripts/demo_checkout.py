from __future__ import annotations

import asyncio
import base64
import json

from storefront_guard.infrai_images import InfraiImages
from storefront_guard.order_flow import CheckoutImage, StorefrontOrderFlow


async def main() -> None:
    images = InfraiImages()
    try:
        request = CheckoutImage(
            order_id="order-1042",
            customer_email="shopper@example.com",
            filename="custom-mug.png",
            image_base64=base64.b64encode(b"demo product image").decode("ascii"),
            moderation={"safe": True},
        )
        result = await StorefrontOrderFlow(images).submit(
            request, base64.b64decode(request.image_base64)
        )
        print(json.dumps(result.model_dump(mode="json"), indent=2))
    finally:
        await images.close()


if __name__ == "__main__":
    asyncio.run(main())
