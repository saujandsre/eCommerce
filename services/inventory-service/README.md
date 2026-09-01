# Inventory Service v0.2

A synchronous FastAPI/PostgreSQL service that owns product stock quantities and
transactionally safe reservations.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://inventory_user:password@localhost:5432/inventory_db'
alembic upgrade head
python -m app.seed  # optional, idempotent development data
uvicorn app.main:app --reload
```

## Test

```bash
.venv/bin/pytest
```

## Docker

```bash
docker build -t inventory-service:v0.2 .
docker run --rm -p 8000:8000 -e DATABASE_URL="$DATABASE_URL" inventory-service:v0.2
```

## Endpoints

- `GET /health`
- `GET /ready`
- `GET /inventory`
- `GET /inventory/{product_id}`
- `POST /inventory/{product_id}/reserve`
- `POST /inventory/{product_id}/release`
