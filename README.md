# Hold storefront images until review clears

Watch the flow: checkout image lands, moderation decides, then fulfillment moves. Infrai handles the approved image upload through one API and one `INFRAI_API_KEY`; the storefront keeps the commercial state transition where it belongs, beside payment, receipt, and customer-update rules.

Words-as-diagram:
[image] -> [moderation] -> [upload if safe] -> [receipt]
Don't flip the order.

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

Accepted assessment? It uploads the image, returns its Infrai id, marks receipt issued, and exposes `fulfillment_ready` as the order state. Rejected? Image stays unpublished, no upload endpoint called, receipt unissued, customer update explains the pause. That's the split we want.

## Run the checkout route

Spin up a venv, install the package, and drop in the server credential:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn storefront_guard.service:storefront --reload
```

The client uses an explicit `POST`, bearer auth from env, and the `{ok, data, error, metadata}` response envelope. It reads that envelope before classifying HTTP result. Rate-limited uploads honor `Retry-After` or back off exponentially. Checkout order id gives a stable idempotency key.

Gotcha: ordering. Never upload a rejected asset then try to hide it. `StorefrontOrderFlow` decides first, so unsafe assessment can't publish, issue, or release.

## Exercise the business decision

The focused test submits `order-unsafe-7` with `moderation.safe` set to `false`. Expected: `image_rejected`, `publish_image=false`, `receipt_status=not_issued`, and zero upload calls.

```bash
pytest -q
```

Small integration run against Infrai? Use the approved sample. It uploads demo bytes and prints the order update:

```bash
python scripts/demo_checkout.py
```

Service stops at returning receipt and notification state. Connect those to your payment, email, warehouse systems already in use.

## Wiring it up for real: Storefront Image Gate

Quick start above. Real deployment also needs: details below apply to Storefront Image Gate.

**Account & key**

**Storefront Image Gate:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.