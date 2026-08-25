# Order Service v0.1

An in-memory FastAPI service that synchronously orchestrates catalog pricing,
inventory reservation, and restaurant credit reservation. Data resets whenever
the process restarts.

## Service configuration

- `CATALOG_SERVICE_URL` (default: `http://localhost:8001`)
- `INVENTORY_SERVICE_URL` (default: `http://localhost:8002`)
- `ACCOUNT_SERVICE_URL` (default: `http://localhost:8003`)

These distinct localhost ports allow all four services to run locally together,
with order-service on port 8000.

## Known consistency limitation

Reservations are not yet coordinated by a transaction or saga. If inventory is
reserved and the subsequent account credit reservation fails, inventory remains
reserved even though no order is created. The API returns the account-service
error. Compensation/rollback will be added later.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test

```bash
.venv/bin/pytest
```

## Docker

```bash
docker build -t order-service:v0.1 .
docker run --rm -p 8000:8000 order-service:v0.1
```

## Endpoints

- `GET /health`
- `GET /orders`
- `GET /orders/{order_id}`
- `POST /orders`
- `POST /orders/{order_id}/confirm`
- `POST /orders/{order_id}/cancel`
