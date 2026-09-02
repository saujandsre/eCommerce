import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def service_urls() -> dict[str, str]:
    return {
        "catalog": os.getenv("CATALOG_SERVICE_URL", "http://localhost:8001").rstrip("/"),
        "inventory": os.getenv("INVENTORY_SERVICE_URL", "http://localhost:8002").rstrip("/"),
        "account": os.getenv("ACCOUNT_SERVICE_URL", "http://localhost:8003").rstrip("/"),
        "order": os.getenv("ORDER_SERVICE_URL", "http://localhost:8004").rstrip("/"),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(timeout=5.0)
    yield
    await app.state.http.aclose()


app = FastAPI(title="Commerce Demo UI", version="0.1.0", lifespan=lifespan)


async def fetch_json(client: httpx.AsyncClient, url: str) -> Any:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()


def error_detail(response: httpx.Response) -> str:
    try:
        return str(response.json().get("detail", "Order was rejected"))
    except (ValueError, AttributeError):
        return "Order was rejected"


async def page_data(request: Request, restaurant_id: int | None = None) -> dict[str, Any]:
    urls = service_urls()
    client = request.app.state.http
    accounts, products, inventory, orders = await asyncio.gather(
        fetch_json(client, f"{urls['account']}/accounts"),
        fetch_json(client, f"{urls['catalog']}/products"),
        fetch_json(client, f"{urls['inventory']}/inventory"),
        fetch_json(client, f"{urls['order']}/orders"),
    )
    selected_id = restaurant_id or (accounts[0]["restaurant_id"] if accounts else None)
    selected_account = next(
        (account for account in accounts if account["restaurant_id"] == selected_id), None
    )
    stock = {item["product_id"]: item["quantity_available"] for item in inventory}
    product_rows = [{**product, "available": stock.get(product["id"], 0)} for product in products]
    recent_orders = [order for order in reversed(orders) if order["restaurant_id"] == selected_id][:5]
    return {
        "request": request,
        "accounts": accounts,
        "selected_id": selected_id,
        "selected_account": selected_account,
        "products": product_rows,
        "orders": recent_orders,
        "result": None,
        "error": None,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, restaurant_id: int | None = None):
    try:
        context = await page_data(request, restaurant_id)
    except (httpx.RequestError, httpx.HTTPStatusError):
        context = {
            "request": request, "accounts": [], "selected_id": restaurant_id,
            "selected_account": None, "products": [], "orders": [], "result": None,
            "error": "One or more commerce services are unavailable. Please try again.",
        }
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/orders", response_class=HTMLResponse)
async def place_order(request: Request, restaurant_id: int = Form(...)):
    form = await request.form()
    items = []
    for key, value in form.multi_items():
        if key.startswith("quantity_"):
            try:
                quantity = int(value)
                product_id = int(key.removeprefix("quantity_"))
            except ValueError:
                continue
            if quantity > 0:
                items.append({"product_id": product_id, "quantity": quantity})

    try:
        context = await page_data(request, restaurant_id)
        if not items:
            context["error"] = "Choose at least one product quantity."
        else:
            response = await request.app.state.http.post(
                f"{service_urls()['order']}/orders",
                json={"restaurant_id": restaurant_id, "items": items},
            )
            if response.is_success:
                context["result"] = response.json()
                context = await page_data(request, restaurant_id) | {"result": response.json()}
            else:
                context["error"] = error_detail(response)
    except (httpx.RequestError, httpx.HTTPStatusError):
        context = {
            "request": request, "accounts": [], "selected_id": restaurant_id,
            "selected_account": None, "products": [], "orders": [], "result": None,
            "error": "The order could not be placed because a service is unavailable.",
        }
    return templates.TemplateResponse(request, "index.html", context)
