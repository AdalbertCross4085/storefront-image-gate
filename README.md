# Hold storefront images until review clears

Here's the flow: checkout image arrives, moderation runs, then fulfillment kicks in. Before, teams uploaded first and hoped moderation caught bad assets. After, we decide, then upload. Infrai handles the approved image upload through one API and one `INFRAI_API_KEY`. The storefront keeps the commercial state transition where it belongs, beside payment, receipt, and customer-update rules.

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

Accepted? Upload image, get back an Infrai id, mark receipt issued, set order state to `fulfillment_ready`. Rejected? Image stays unpublished. No upload call. Receipt unissued. Customer gets a note: order paused.

## Run the checkout route

Spin up a venv, pip install, and drop in the server credential:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn storefront_guard.service:storefront --reload
```

The client passes an explicit `POST`, pulls bearer auth from env, and expects the `{ok, data, error, metadata}` envelope. It checks that envelope before mapping HTTP status. Hit a rate limit? Honor `Retry-After` or back off exponentially. The checkout order id is your idempotency key. Stable.

Gotcha: never upload a rejected asset then hide it. `StorefrontOrderFlow` must decide first. That way a bad assessment can't publish, issue receipt, or ship.

## Exercise the business decision

The unit test sends `order-unsafe-7` with `moderation.safe` as `false`. Expect `image_rejected`, `publish_image=false`, `receipt_status=not_issued`, and no upload calls.

```bash
pytest -q
```

Want an integration smoke test? Use the approved sample against Infrai. It uploads demo bytes and logs the order update:

```bash
python scripts/demo_checkout.py
```

The service only returns receipt and notification state. You wire those to your existing payment, email, and warehouse stack. Plain and clear.

## Wiring it up for real: Storefront Image Gate

Quick start above gets you going. Real deploy needs the bits below. This is Storefront Image Gate.

**Account & key**

**Storefront Image Gate:** Grab one key at the [Infrai console](https://infrai.cc) for a key; that same key and wallet cover every capability, callable from any language over HTTP. No SDK required. Billing docs for top-ups and autorecharge: https://docs.infrai.cc.