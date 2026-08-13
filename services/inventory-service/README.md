# Inventory Service v0.1

An in-memory FastAPI service that owns product stock quantities and reservations.
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
docker build -t inventory-service:v0.1 .
docker run --rm -p 8000:8000 inventory-service:v0.1
```

## Endpoints

- `GET /health`
- `GET /inventory`
- `GET /inventory/{product_id}`
- `POST /inventory/{product_id}/reserve`
- `POST /inventory/{product_id}/release`
