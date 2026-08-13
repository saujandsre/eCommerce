# Account Service v0.1

An in-memory FastAPI service that owns restaurant purchasing accounts and credit reservations.
Data resets whenever the process restarts.

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
docker build -t account-service:v0.1 .
docker run --rm -p 8000:8000 account-service:v0.1
```

## Endpoints

- `GET /health`
- `GET /accounts`
- `GET /accounts/{restaurant_id}`
- `POST /accounts/{restaurant_id}/reserve-credit`
- `POST /accounts/{restaurant_id}/release-credit`
