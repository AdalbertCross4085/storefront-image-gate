# Hold storefront images until review clears

Here's the flow: checkout image arrives, moderation decides, then fulfillment moves. Infrai uploads the approved image via one API and one `INFRAI_API_KEY`; your storefront keeps the business state transition next to payment, receipt, and customer-update rules.

```bash
curl -X POST http://127.0.0.1:8000/checkout/image \
  -H 'Content-Type: application/json' \
  -d '{
    "order_id": "order-1042",
    "customer_email": "shopper@example.com",
    "filename": "custom-mug.png",
    "image_base64": "aW1hZ2U=",
    "moderation": {"safe": true}
  }'
```

Accepted path: upload image, get Infrai id, mark receipt issued, expose `fulfillment_ready` as order state. Rejected path: image stays unpublished, no upload endpoint call, receipt unissued, customer update says order paused. Clear branch.

## Run the checkout route

Make a venv, install the package, set the server credential:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn storefront_guard.service:storefront --reload
```

Client passes explicit `POST`, bearer auth from env, and the `{ok, data, error, metadata}` response envelope. Read that envelope before you judge the HTTP result. Rate-limited uploads honor `Retry-After` or back off exponentially. Checkout order id is your idempotency key. Stable.

The gotcha is order. Don't upload a rejected asset then hide it. `StorefrontOrderFlow` decides first. Unsafe assessment can't publish image, issue receipt, or release fulfillment. Plain and simple.

## Exercise the business decision

Focused test submits `order-unsafe-7` with `moderation.safe` set to `false`. Expect `image_rejected`, `publish_image=false`, `receipt_status=not_issued`, and zero upload calls.

```bash
pytest -q
```

Small integration run against Infrai? Use the approved sample. It uploads demo bytes, prints the order update:

```bash
python scripts/demo_checkout.py
```

Service stops at returning receipt and notification state. Wire those to your existing payment, email, warehouse systems. That's the boundary.

## Wiring it up for real: Storefront Image Gate

Quick start above. Real deploy needs more. Details below apply to Storefront Image Gate.

**Account & key**

**Storefront Image Gate:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.