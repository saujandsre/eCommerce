# Order Service v0.3

A persistent FastAPI/PostgreSQL service that synchronously orchestrates catalog
pricing, inventory reservation, and restaurant credit reservation.

## Service configuration

- `CATALOG_SERVICE_URL` (default: `http://localhost:8001`)
- `INVENTORY_SERVICE_URL` (default: `http://localhost:8002`)
- `ACCOUNT_SERVICE_URL` (default: `http://localhost:8003`)
- `DATABASE_URL` (required; points only to `order_db`)

These distinct localhost ports allow all four services to run locally together,
with order-service on port 8000.

Obvious partial failures use best-effort HTTP compensation. This is deliberately
not a distributed transaction; failed compensation still requires operator repair.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Test

```bash
.venv/bin/pytest
```

## Docker

```bash
docker build -t order-service:v0.3 .
docker run --rm -p 8000:8000 -e DATABASE_URL="$DATABASE_URL" order-service:v0.3
```

## Endpoints

- `GET /health`
- `GET /ready`
- `GET /orders`
- `GET /orders/{order_id}`
- `POST /orders`
- `POST /orders/{order_id}/confirm`
- `POST /orders/{order_id}/cancel`
