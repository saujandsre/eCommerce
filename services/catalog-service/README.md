# Catalog Service v0.2

A synchronous FastAPI and PostgreSQL catalog for the restaurant procurement platform.

## Configuration

`DATABASE_URL` is required. Use the Psycopg 3 SQLAlchemy URL form:

```bash
export DATABASE_URL='postgresql+psycopg://catalog_user:catalog_password@localhost:5432/catalog_db'
```

In Kubernetes, supply the password or complete URL from a Secret. The in-cluster database host is `postgres:5432`.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

No sample products are inserted automatically.

The API is available at `http://localhost:8000`; interactive documentation is at `/docs`.

## Test with PostgreSQL 17

Start a disposable local database:

```bash
docker run --name catalog-postgres --rm -e POSTGRES_DB=catalog_db -e POSTGRES_USER=catalog_user -e POSTGRES_PASSWORD=catalog_password -p 5432:5432 postgres:17
```

In another shell, install dependencies and run the tests against that database:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://catalog_user:catalog_password@localhost:5432/catalog_db'
.venv/bin/pytest
```

The tests apply Alembic migrations and roll back product changes after each test. Use a dedicated test database because the migration changes its schema.

## Docker

From this directory:

```bash
docker build -t catalog-service:v0.2 .
docker run --rm -p 8000:8000 -e DATABASE_URL="$DATABASE_URL" catalog-service:v0.2
```

Run migrations as a separate deployment step before starting application replicas.

## Endpoints

- `GET /health` — process liveness only
- `GET /ready` — PostgreSQL connectivity
- `GET /products`
- `GET /products/{id}`
- `POST /products`
