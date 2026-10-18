"""Сквозные и модульные тесты кредитного конвейера.

Запуск: cd backend && pytest -q
"""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/alfa_test.db")
os.environ["DEMO_DELAY_SCALE"] = "0"
os.environ["SEED_ON_START"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.models import Company
from app.services.scoring import annuity_payment, calculate_scoring

CLIENT = {"email": "ivan@vesna.ru", "password": "demo1234"}
BORDERLINE = {"email": "petr@stroymaster.ru", "password": "demo1234"}
BANK = {"email": "underwriter@alfabank.ru", "password": "demo1234"}


@pytest.fixture(scope="session")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


def auth(client, creds) -> dict:
    r = client.post("/api/auth/login", json=creds)
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_login_and_roles(client):
    r = client.post("/api/auth/login", json=CLIENT)
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "client"
    assert r.json()["company"]["short_name"]

    bad = client.post("/api/auth/login", json={"email": CLIENT["email"], "password": "wrong"})
    assert bad.status_code == 401


def test_role_isolation(client):
    client_headers = auth(client, CLIENT)
    assert client.get("/api/bank/tasks", headers=client_headers).status_code == 403
    bank_headers = auth(client, BANK)
    assert bank_headers and client.get("/api/dashboard", headers=bank_headers).status_code == 403


def test_products_and_eligibility(client):
    headers = auth(client, CLIENT)
    products = client.get("/api/products").json()
    assert len(products) >= 4
    codes = {p["code"] for p in products}
    assert {"working_capital", "express", "investment", "overdraft"} <= codes

    ok = client.get("/api/products/working_capital/eligibility?amount=800000&term_months=12", headers=headers)
    assert ok.status_code == 200
    assert ok.json()["eligible"] is True
    assert any(c["name"] == "Срок ведения бизнеса" for c in ok.json()["checks"])


def test_scoring_is_deterministic_and_bounded(client):
    from app.database import SessionLocal
    db = SessionLocal()
    company = db.query(Company).filter(Company.short_name.like("Кофейня%")).first()
    from app.models import Product
    product = db.query(Product).filter(Product.code == "working_capital").first()
    result = calculate_scoring(company, product, 800_000, 12)
    db.close()
    assert 0 <= result["score"] <= 1000
    assert result["risk_class"] in {"A", "B", "C", "D", "E"}
    assert result["decision"] in {"approved", "counter_offer", "declined"}
    assert len(result["factors"]) == 7
    assert result["recommended_rate"] >= product.base_rate - 2.0


def test_annuity_math():
    payment = annuity_payment(100_000, 18.0, 12)
    assert 9000 < payment < 9600  # ~9,168 ₽ при 18% годовых


def test_full_happy_path_end_to_end(client):
    headers = auth(client, CLIENT)
    created = client.post("/api/applications", headers=headers, json={
        "product_code": "working_capital", "amount": 700_000, "term_months": 12,
        "purpose": "Закупка товара", "purpose_details": "Тестовая заявка", "submit": True,
    })
    assert created.status_code == 201, created.text
    app_id = created.json()["id"]

    detail = client.get(f"/api/applications/{app_id}", headers=headers).json()
    assert detail["status"] == "offer_issued"
    assert detail["score"] >= 800
    assert detail["offer"]["amount"] > 0
    statuses = [e["to_status"] for e in detail["events"] if e["to_status"]]
    assert statuses[0] == "draft" and statuses[1] == "submitted"
    assert "offer_issued" in statuses

    accepted = client.post(f"/api/applications/{app_id}/offer/accept", headers=headers, json={"accept": True})
    assert accepted.json()["status"] == "signing"

    signed = client.post(f"/api/applications/{app_id}/sign", headers=headers)
    body = signed.json()
    assert body["status"] == "funded"
    assert body["credit_account"].startswith("40817810")
    assert body["progress_percent"] == 100


def test_manual_review_and_underwriter_counter_offer(client):
    client_headers = auth(client, BORDERLINE)
    bank_headers = auth(client, BANK)

    created = client.post("/api/applications", headers=client_headers, json={
        "product_code": "working_capital", "amount": 1_800_000, "term_months": 12,
        "purpose": "Оборотные средства", "submit": True,
    })
    app_id = created.json()["id"]
    detail = client.get(f"/api/applications/{app_id}", headers=client_headers).json()
    assert detail["status"] == "manual_review"
    assert detail["risk_class"] in {"B", "C"}

    queue = client.get("/api/bank/tasks?tab=queue", headers=bank_headers).json()
    assert any(item["id"] == app_id for item in queue["items"])

    decision = client.post(f"/api/bank/applications/{app_id}/decision", headers=bank_headers, json={
        "action": "counter_offer", "comment": "Снижаем сумму",
        "offer_amount": 1_500_000, "offer_rate": 21.5, "offer_term_months": 12,
    })
    assert decision.status_code == 200, decision.text
    offer = decision.json()["offer"]
    assert offer["is_counter_offer"] is True
    assert offer["amount"] == 1_500_000

    client_view = client.get(f"/api/applications/{app_id}", headers=client_headers).json()
    assert client_view["status"] == "offer_issued"
    assert client_view["offer"]["requested_amount"] == 1_800_000


def test_info_request_flow(client):
    client_headers = auth(client, BORDERLINE)
    bank_headers = auth(client, BANK)
    # Инвестиционный кредит для заёмщика с пограничным риском всегда уходит андеррайтеру
    created = client.post("/api/applications", headers=client_headers, json={
        "product_code": "investment", "amount": 2_000_000, "term_months": 24,
        "purpose": "Оборудование", "submit": True,
    })
    app_id = created.json()["id"]

    req = client.post(f"/api/bank/applications/{app_id}/decision", headers=bank_headers, json={
        "action": "request_info", "comment": "Пришлите расшифровку прочих расходов",
    })
    assert req.status_code == 200, req.text
    assert req.json()["status"] == "info_requested"

    answer = client.post(f"/api/applications/{app_id}/info", headers=client_headers,
                         json={"comment": "Прочие расходы — аренда 120 тыс. ₽/мес"})
    assert answer.json()["status"] == "client_info_provided"


def test_decline_and_audit_trail(client):
    client_headers = auth(client, BORDERLINE)
    bank_headers = auth(client, BANK)
    created = client.post("/api/applications", headers=client_headers, json={
        "product_code": "investment", "amount": 2_000_000, "term_months": 24,
        "purpose": "Расширение производства", "submit": True,
    })
    app_id = created.json()["id"]
    assert client.get(f"/api/applications/{app_id}", headers=client_headers).json()["status"] == "manual_review"

    decision = client.post(f"/api/bank/applications/{app_id}/decision", headers=bank_headers, json={
        "action": "decline", "comment": "Слишком высокая нагрузка",
        "decline_reasons": ["Долговая нагрузка выше допустимой"],
    })
    assert decision.status_code == 200, decision.text
    assert decision.json()["status"] == "declined"
    assert "Долговая нагрузка выше допустимой" in decision.json()["decline_reasons"]

    events = client.get(f"/api/applications/{app_id}", headers=client_headers).json()["events"]
    assert any(e["actor_type"] == "bank" for e in events)
    assert any(e["title"] == "Принято отрицательное решение" for e in events)


def test_news_feed_personalization(client):
    headers = auth(client, CLIENT)
    feed = client.get("/api/news", headers=headers).json()
    assert feed["items"], "лента не должна быть пустой"
    assert feed["context"]["industry"] == "Общественное питание"
    assert any(item["is_personal"] for item in feed["items"])
    assert feed["items"][0]["relevance_score"] >= feed["items"][-1]["relevance_score"]


def test_dashboard_metrics(client):
    headers = auth(client, CLIENT)
    data = client.get("/api/dashboard", headers=headers).json()
    assert "credit_meter" in data and data["credit_meter"]["amount"] > 0
    assert len(data["recommendations"]) == 4
    assert data["stats"]["funded_count"] >= 1


def test_company_profile_mocks(client):
    headers = auth(client, CLIENT)
    data = client.get("/api/company", headers=headers).json()
    assert data["company"]["bki"]["bki_score"] > 0
    assert data["company"]["registry"]["status"] == "Действующий"
    assert len(data["financials"]["dynamics"]) == 6
