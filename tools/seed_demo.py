#!/usr/bin/env python3
"""Наполняет работающий прототип демонстрационным состоянием.

Создаёт три заявки, показывающие все ветки конвейера:
  1. Кофейня «Весна»      → автоматическое одобрение → выдача
  2. ИП «СтройМастер»     → ручное рассмотрение → контрпредложение андеррайтера
  3. ООО «ТехноПарк»      → ручное рассмотрение (остаётся в очереди)

Запуск: python3 tools/seed_demo.py [--base http://localhost:8000/api]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

PASSWORD = "demo1234"


def call(base: str, path: str, method: str = "GET", body: dict | None = None, token: str | None = None):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as exc:
        print(f"  ✗ {method} {path} → {exc.code}: {exc.read().decode()[:300]}")
        raise


def login(base: str, email: str) -> str:
    return call(base, "/auth/login", "POST", {"email": email, "password": PASSWORD})["token"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000/api")
    parser.add_argument("--wait", type=float, default=2.5, help="пауза на обработку конвейером")
    args = parser.parse_args()
    base = args.base.rstrip("/")

    print("→ проверяем доступность API…")
    try:
        call(base, "/health")
    except Exception:
        print("  API недоступен. Запустите сервер: docker compose up --build")
        return 1

    tokens = {
        "ivan": login(base, "ivan@vesna.ru"),
        "petr": login(base, "petr@stroymaster.ru"),
        "anna": login(base, "anna@tehnopark.ru"),
        "bank": login(base, "underwriter@alfabank.ru"),
    }
    print("✓ авторизация: клиенты и андеррайтер")

    # 1. авто-одобрение → выдача
    app1 = call(base, "/applications", "POST", {
        "product_code": "working_capital", "amount": 700_000, "term_months": 12,
        "purpose": "Закупка товара",
        "purpose_details": "Кофе и упаковка на ноябрь–декабрь",
        "submit": True,
    }, tokens["ivan"])
    time.sleep(args.wait)
    detail = call(base, f"/applications/{app1['id']}", token=tokens["ivan"])
    print(f"✓ заявка 1 ({detail['number']}): {detail['status']}, балл {detail['score']}")
    if detail["status"] == "offer_issued":
        call(base, f"/applications/{app1['id']}/offer/accept", "POST", {"accept": True}, tokens["ivan"])
        call(base, f"/applications/{app1['id']}/sign", "POST", None, tokens["ivan"])
        print("  → оферта принята, документы подписаны, кредит выдан")

    # 2. ручное рассмотрение → контрпредложение
    app2 = call(base, "/applications", "POST", {
        "product_code": "working_capital", "amount": 1_800_000, "term_months": 12,
        "purpose": "Оборотные средства",
        "purpose_details": "Закупка стройматериалов под новый объект",
        "submit": True,
    }, tokens["petr"])
    time.sleep(args.wait)
    detail = call(base, f"/applications/{app2['id']}", token=tokens["petr"])
    print(f"✓ заявка 2 ({detail['number']}): {detail['status']}, балл {detail['score']}")
    if detail["status"] in {"manual_review", "client_info_provided"}:
        call(base, f"/bank/applications/{app2['id']}/decision", "POST", {
            "action": "counter_offer",
            "comment": "Готовы одобрить 1 500 000 ₽ на 18 месяцев под 21,5% — нагрузка останется комфортной",
            "offer_amount": 1_500_000, "offer_rate": 21.5, "offer_term_months": 18,
        }, tokens["bank"])
        print("  → андеррайтер отправил контрпредложение")

    # 3. остаётся в очереди андеррайтера
    app3 = call(base, "/applications", "POST", {
        "product_code": "investment", "amount": 2_000_000, "term_months": 24,
        "purpose": "Оборудование",
        "purpose_details": "Серверное оборудование для нового проекта",
        "submit": True,
    }, tokens["anna"])
    time.sleep(args.wait)
    detail = call(base, f"/applications/{app3['id']}", token=tokens["anna"])
    print(f"✓ заявка 3 ({detail['number']}): {detail['status']}, балл {detail['score']}")

    queue = call(base, "/bank/tasks?tab=queue", token=tokens["bank"])["items"]
    print(f"\nОчередь андеррайтера: {len(queue)} заявок")
    for item in queue:
        print(f"  • {item['number']} · {item['company_name']} · {item['score']} ({item['risk_class']})")
    print("\nГотово. Откройте http://localhost:8080 и войдите под нужной ролью.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
