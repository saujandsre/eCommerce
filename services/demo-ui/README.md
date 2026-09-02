# Commerce Demo UI

A deliberately small, stateless FastAPI page for visually demonstrating the existing commerce workload. It reads accounts, catalog, inventory, and recent orders from the business services and submits orders to order-service. It owns no business data.

## Run locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
CATALOG_SERVICE_URL=http://localhost:8001 \
INVENTORY_SERVICE_URL=http://localhost:8002 \
ACCOUNT_SERVICE_URL=http://localhost:8003 \
ORDER_SERVICE_URL=http://localhost:8004 \
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000>. Health checking is available at `GET /health`.

## Test and package

```bash
.venv/bin/python -m pytest
docker build -t saujandsre/demo-ui:v0.1 .
docker push saujandsre/demo-ui:v0.1
```

The Kubernetes Deployment supplies in-cluster ClusterIP DNS URLs. Deploy from the repository root with `kubectl apply -f kubernetes/demo-ui/`.
