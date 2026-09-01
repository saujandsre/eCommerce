# Account Service v0.2

A synchronous FastAPI/PostgreSQL service that owns restaurant purchasing accounts
and transactionally safe Decimal credit reservations.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL='postgresql+psycopg://account_user:password@localhost:5432/account_db'
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
docker build -t account-service:v0.2 .
docker run --rm -p 8000:8000 -e DATABASE_URL="$DATABASE_URL" account-service:v0.2
```

## Endpoints

- `GET /health`
- `GET /ready`
- `GET /accounts`
- `GET /accounts/{restaurant_id}`
- `POST /accounts/{restaurant_id}/reserve-credit`
- `POST /accounts/{restaurant_id}/release-credit`
