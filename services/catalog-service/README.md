# Catalog Service v0.1

A small in-memory FastAPI catalog for the restaurant procurement platform.
Data resets to the five sample products whenever the process restarts.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive documentation is at `/docs`.

## Test

```bash
.venv/bin/pytest
```

## Docker

```bash
docker build -t catalog-service:v0.1 .
docker run --rm -p 8000:8000 catalog-service:v0.1
```

## Endpoints

- `GET /health`
- `GET /products`
- `GET /products/{id}`
- `POST /products`
