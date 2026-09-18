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


## Inspect metrics locally

`GET /metrics` exposes Prometheus text using the standard Python client, including
its default Python/process metrics. Application metrics have no custom labels:

- `order_creation_attempts_total`: every `POST /orders` attempt, including invalid bodies.
- `order_creation_successes_total`: requests returning 201 after persistence and confirmation.
- `order_creation_failures_total`: error responses or unhandled exceptions.
- `order_creation_duration_seconds`: histogram covering the workflow through response
  creation, including downstream calls, persistence, and compensation on failures.

Other routes and metrics scrapes do not affect these metrics. Values are in memory,
per process, and reset on restart. Use a single Uvicorn worker for manual inspection.

With the service running on port 8000, inspect the starting values:

```bash
curl -s http://localhost:8000/metrics
```

Create an order (requires product 1, restaurant account 1, available inventory and
sufficient credit in the running downstream services; substitute your existing IDs):

```bash
curl -i -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"restaurant_id":1,"items":[{"product_id":1,"quantity":1}]}'
```

Trigger a deterministic validation failure (422):

```bash
curl -i -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"restaurant_id":1,"items":[]}'
```

Inspect the values again:

```bash
curl -s http://localhost:8000/metrics | grep '^order_creation_'
```

After one 201 and one 422, attempts increase by 2, successes by 1, failures by 1,
and the duration histogram's `_count` by 2. Its `_sum` contains elapsed seconds.
