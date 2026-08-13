# Order Service v0.1

An in-memory FastAPI service that owns standalone restaurant orders.
It does not call the catalog, inventory, or account services. Data resets whenever the process restarts.

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
