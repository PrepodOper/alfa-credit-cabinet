"""Тесты правок: график платежей, устойчивость конвейера, профиль компании.

Покрывают три замечания к прототипу:
1. график платежей не формировался — теперь строится по фактическим условиям оффера;
2. заявка иногда «теряла» ручное рассмотрение — конвейер идемпотентен и падает в очередь;
3. данные компании нельзя было менять — добавлена правка профиля с журналом изменений.
"""
import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/alfa_test_fixes.db")
os.environ["DEMO_DELAY_SCALE"] = "0"
os.environ["SEED_ON_START"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Application
from app.routers.applications import run_pipeline

CLIENT = {"email": "ivan@vesna.ru", "password": "demo1234"}
BORDERLINE = {"email": "petr@stroymaster.ru", "password": "demo1234"}


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


def create_app(client, headers, *, product="working_capital", amount=700_000, term=12, submit=True):
    r = client.post("/api/applications", headers=headers, json={
        "product_code": product, "amount": amount, "term_months": term,
        "purpose": "Оборотные средства", "purpose_details": "", "submit": submit,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ------------------------------------------------------------------ график платежей
def test_schedule_matches_offer_terms(client):
    headers = auth(client, CLIENT)
    app_id = create_app(client, headers, amount=700_000, term=12)
    detail = client.get(f"/api/applications/{app_id}", headers=headers).json()
    assert detail["status"] == "offer_issued"

    schedule = detail["schedule"]
    assert schedule and schedule["items"], "график должен формироваться вместе с офертой"

    summary, items = schedule["summary"], schedule["items"]
    assert len(items) == detail["offer"]["term_months"] == summary["payments_count"]
    assert abs(sum(i["principal"] for i in items) - detail["offer"]["amount"]) < 0.05
    assert items[-1]["balance"] == 0.0
    assert summary["total_interest"] > 0
    assert abs(summary["total_paid"] - (summary["amount"] + summary["total_interest"])) < 0.05
    # Платёж из графика совпадает с платежом в оферте (расхождение — только округление)
    assert abs(items[0]["payment"] - detail["offer"]["monthly_payment"]) < 1
    # Даты идут по месяцам вперёд
    assert items[0]["date"] < items[-1]["date"]

    single = client.get(f"/api/applications/{app_id}/schedule", headers=headers)
    assert single.status_code == 200
    assert single.json()["items"] == items


def test_schedule_absent_until_offer(client):
    headers = auth(client, CLIENT)
    app_id = create_app(client, headers, submit=False)
    detail = client.get(f"/api/applications/{app_id}", headers=headers).json()
    assert detail["schedule"] is None
    assert client.get(f"/api/applications/{app_id}/schedule", headers=headers).status_code == 404


# ------------------------------------------------------------------ конвейер
def test_repeat_pipeline_run_does_not_override_manual_review(client):
    """Повторный прогон по заявке, ушедшей андеррайтеру, ничего не меняет."""
    headers = auth(client, BORDERLINE)
    app_id = create_app(client, headers, product="investment", amount=2_000_000, term=24)
    detail = client.get(f"/api/applications/{app_id}", headers=headers).json()
    assert detail["status"] == "manual_review"

    events_before = len(detail["events"])
    run_pipeline(app_id)          # «запоздавший» второй прогон
    run_pipeline(app_id)          # и ещё один, для надёжности

    after = client.get(f"/api/applications/{app_id}", headers=headers).json()
    assert after["status"] == "manual_review", "повторный прогон не должен одобрять заявку сам"
    assert len(after["events"]) == events_before, "повторный прогон не должен писать события"
    assert after["offer"] is None


def test_pipeline_is_idempotent_for_approved_application(client):
    headers = auth(client, CLIENT)
    app_id = create_app(client, headers, amount=500_000, term=12)
    first = client.get(f"/api/applications/{app_id}", headers=headers).json()
    assert first["status"] == "offer_issued"
    offer_events = [e for e in first["events"] if e["to_status"] == "offer_issued"]
    assert len(offer_events) == 1

    run_pipeline(app_id)
    again = client.get(f"/api/applications/{app_id}", headers=headers).json()
    assert again["status"] == "offer_issued"
    assert len([e for e in again["events"] if e["to_status"] == "offer_issued"]) == 1


def test_pipeline_failure_hands_application_to_underwriter(client, monkeypatch):
    """Технический сбой автоматики не «теряет» заявку — она уходит в очередь."""
    import app.services.registry as registry_module

    def boom(_company):
        raise RuntimeError("БКИ недоступно")

    monkeypatch.setattr(registry_module, "bki_snapshot", boom)

    headers = auth(client, CLIENT)
    r = client.post("/api/applications", headers=headers, json={
        "product_code": "express", "amount": 300_000, "term_months": 12,
        "purpose": "Пополнение оборотных средств", "submit": True,
    })
    assert r.status_code == 201, r.text
    app_id = r.json()["id"]

    detail = client.get(f"/api/applications/{app_id}", headers=headers).json()
    assert detail["status"] == "manual_review"
    assert any("не завершилась" in e["title"] or "прервана" in e["title"] for e in detail["events"])


# ------------------------------------------------------------------ профиль компании
def test_company_profile_is_editable_with_audit(client):
    headers = auth(client, CLIENT)
    before = client.get("/api/company", headers=headers).json()
    old_phone = before["requisites"]["phone"]
    old_employees = before["requisites"]["employees_count"]
    old_revenue = before["financials"]["revenue_avg_monthly"]

    try:
        updated = client.patch("/api/company", headers=headers, json={
            "phone": "+7 999 123-45-67",
            "employees_count": old_employees + 6,
            "revenue_avg_monthly": old_revenue + 100_000,
            "city": "Санкт-Петербург",
        })
        assert updated.status_code == 200, updated.text
        body = updated.json()
        assert body["requisites"]["phone"] == "+7 999 123-45-67"
        assert body["requisites"]["employees_count"] == old_employees + 6
        assert body["financials"]["revenue_avg_monthly"] == old_revenue + 100_000
        # Годовая выручка пересчитана автоматически
        assert body["financials"]["revenue_12m"] == (old_revenue + 100_000) * 12
        # Изменения попали в журнал
        fields = {c["field"] for c in body["changes"]}
        assert {"phone", "employees_count", "revenue_avg_monthly", "city"} <= fields
        assert body["changes"][0]["user_name"]

        history = client.get("/api/company/changes", headers=headers).json()
        assert history["total"] >= 4

        # Повторная отправка тех же данных идемпотентна и не создаёт мусорных записей
        same = client.patch("/api/company", headers=headers, json={"phone": "+7 999 123-45-67"})
        assert same.status_code == 200
        assert same.json()["changed_fields"] == []
        # Пустое тело — ошибка валидации
        assert client.patch("/api/company", headers=headers, json={}).status_code == 422
    finally:
        client.patch("/api/company", headers=headers, json={
            "phone": old_phone, "employees_count": old_employees,
            "revenue_avg_monthly": old_revenue,
        })


def test_company_update_rejects_immutable_and_invalid_fields(client):
    headers = auth(client, CLIENT)
    # Регистрационные данные меняются только через ЕГРЮЛ
    assert client.patch("/api/company", headers=headers, json={"inn": "7700000000"}).status_code == 422
    assert client.patch("/api/company", headers=headers, json={"email": "not-an-email"}).status_code == 422
    assert client.patch("/api/company", headers=headers, json={"employees_count": -3}).status_code == 422
    assert client.patch("/api/company", headers=headers, json={"phone": "123"}).status_code == 422

    # Профиль компании недоступен банковским ролям
    bank = auth(client, {"email": "underwriter@alfabank.ru", "password": "demo1234"})
    assert client.get("/api/company", headers=bank).status_code == 403


def test_company_update_does_not_rewrite_decided_applications(client):
    """Правка финансов меняет скоринг только новых заявок, решение старых фиксировано."""
    headers = auth(client, CLIENT)
    app_id = create_app(client, headers, amount=400_000, term=12)
    decided = client.get(f"/api/applications/{app_id}", headers=headers).json()
    score_before = decided["score"]

    db = SessionLocal()
    try:
        snapshot_after = db.get(Application, app_id).score
    finally:
        db.close()
    assert snapshot_after == score_before

    assert client.get(f"/api/applications/{app_id}", headers=headers).json()["score"] == score_before
