import pytest
from fastapi.testclient import TestClient

from app.main import SAMPLE_ACCOUNTS, accounts, app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_accounts() -> None:
    accounts.clear()
    accounts.update({account.restaurant_id: account.model_copy() for account in SAMPLE_ACCOUNTS})


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_accounts() -> None:
    response = client.get("/accounts")
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_get_account() -> None:
    response = client.get("/accounts/1")
    assert response.status_code == 200
    assert response.json()["restaurant_name"] == "Himalayan Kitchen"


def test_missing_account_returns_404() -> None:
    response = client.get("/accounts/999")
    assert response.status_code == 404


def test_reserve_credit() -> None:
    response = client.post("/accounts/2/reserve-credit", json={"amount_npr": 10000})
    assert response.status_code == 200
    assert response.json()["available_credit_npr"] == 290000
    assert response.json()["reserved_credit_npr"] == 10000


def test_reserve_credit_requires_positive_amount() -> None:
    response = client.post("/accounts/1/reserve-credit", json={"amount_npr": 0})
    assert response.status_code == 422


def test_reserve_credit_for_missing_account_returns_404() -> None:
    response = client.post("/accounts/999/reserve-credit", json={"amount_npr": 1000})
    assert response.status_code == 404


def test_insufficient_credit_returns_conflict() -> None:
    response = client.post("/accounts/3/reserve-credit", json={"amount_npr": 125001})
    assert response.status_code == 409
    assert response.json() == {"detail": "Insufficient available credit"}


def test_release_credit() -> None:
    response = client.post("/accounts/1/release-credit", json={"amount_npr": 10000})
    assert response.status_code == 200
    assert response.json()["available_credit_npr"] == 460000
    assert response.json()["reserved_credit_npr"] == 40000


def test_excessive_credit_release_returns_conflict() -> None:
    response = client.post("/accounts/1/release-credit", json={"amount_npr": 50001})
    assert response.status_code == 409
    assert response.json() == {"detail": "Cannot release more than reserved credit"}
