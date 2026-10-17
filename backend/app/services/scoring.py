"""Скоринг и модель кредитного решения.

Скоринг — балльная модель (0–1000) на основе финансовых показателей, долговой
нагрузки, кредитной истории, возраста бизнеса и параметров заявки. Итоговое
кредитное решение принимается отдельно: по риск-классу, продуктовым лимитам
и affordability-логике. Это позволяет одинаковому риску приводить к разным
условиям по разным продуктам.
"""
from __future__ import annotations

import json
import math
from datetime import date
from typing import Any

from ..models import Application, Company, Product

BANDS = [
    (800, "A", 0.9),
    (680, "B", 2.4),
    (550, "C", 5.8),
    (420, "D", 12.5),
    (0, "E", 24.0),
]

RISK_RATE_ADJUST = {"A": -1.0, "B": 0.0, "C": 1.5, "D": 3.0, "E": 4.0}


def annuity_payment(amount: float, annual_rate: float, months: int) -> float:
    if amount <= 0 or months <= 0:
        return 0.0
    r = annual_rate / 100 / 12
    if r == 0:
        return amount / months
    return amount * r / (1 - (1 + r) ** (-months))


def max_loan_by_payment(payment: float, annual_rate: float, months: int) -> float:
    if payment <= 0 or months <= 0:
        return 0.0
    r = annual_rate / 100 / 12
    if r == 0:
        return payment * months
    return payment * (1 - (1 + r) ** (-months)) / r


def _months_between(start: date | None, end: date | None = None) -> int:
    if not start:
        return 0
    end = end or date.today()
    return max(0, (end.year - start.year) * 12 + end.month - start.month)


def _band(score: int) -> tuple[str, float]:
    for threshold, name, pd in BANDS:
        if score >= threshold:
            return name, pd
    return "E", 24.0


def _factor(code: str, title: str, value: str, points: float, max_points: float) -> dict[str, Any]:
    ratio = points / max_points if max_points else 0
    impact = "positive" if ratio >= 0.7 else ("neutral" if ratio >= 0.4 else "negative")
    return {
        "code": code,
        "title": title,
        "value": value,
        "points": round(points, 1),
        "max_points": max_points,
        "impact": impact,
    }


def calculate_scoring(company: Company, product: Product, amount: float, term_months: int) -> dict[str, Any]:
    factors: list[dict[str, Any]] = []
    hard_stops: list[str] = []
    cp = company.credit_profile
    reg = company.registry_info
    age_months = _months_between(company.founded_date)
    revenue = max(company.revenue_avg_monthly or 0, 1)
    existing = company.existing_monthly_payments or 0

    # 1. Финансовая устойчивость (250): прибыльность и динамика выручки.
    margin = (company.net_profit_12m / company.revenue_12m * 100) if company.revenue_12m else 0
    dynamics = json.loads(company.monthly_dynamics_json or "[]")
    trend_pct = 0.0
    if len(dynamics) >= 6:
        first = sum(m.get("revenue", 0) for m in dynamics[:3]) / 3
        last = sum(m.get("revenue", 0) for m in dynamics[-3:]) / 3
        trend_pct = (last - first) / first * 100 if first else 0
    fin_points = 0.0
    fin_points += 110 if margin >= 12 else 80 if margin >= 6 else 45 if margin >= 0 else 10
    fin_points += 90 if trend_pct >= 5 else 60 if trend_pct >= -5 else 25
    fin_points += 50 if company.net_profit_12m > 0 else 0
    factors.append(_factor(
        "financial_stability", "Финансовая устойчивость",
        f"Рентабельность {margin:.1f}%, динамика выручки за 6 мес. {trend_pct:+.1f}%",
        min(fin_points, 250), 250,
    ))

    # 2. Долговая нагрузка (200): существующие платежи + новый платёж к выручке.
    approx_rate = product.base_rate
    new_payment = annuity_payment(amount, approx_rate, term_months)
    load = (existing + new_payment) / revenue * 100
    if load <= 25:
        load_points = 200
    elif load <= 40:
        load_points = 150
    elif load <= 55:
        load_points = 95
    elif load <= 70:
        load_points = 45
    else:
        load_points = 10
    if load > 80:
        hard_stops.append(f"Долговая нагрузка {load:.0f}% превышает допустимые 80%")
    factors.append(_factor(
        "debt_load", "Долговая нагрузка",
        f"Платежи {existing + new_payment:,.0f} ₽/мес. = {load:.0f}% выручки".replace(",", " "),
        load_points, 200,
    ))

    # 3. Кредитная история (200): БКИ.
    bki_score = cp.bki_score if cp else 600
    delays = cp.max_delay_days_12m if cp else 0
    overdue = cp.has_current_overdue if cp else False
    delinq = cp.delinquencies_12m if cp else 0
    hist = 0.0
    hist += 90 if bki_score >= 750 else 70 if bki_score >= 680 else 50 if bki_score >= 600 else 25 if bki_score >= 500 else 5
    hist += 60 if delays == 0 else 40 if delays <= 15 else 15 if delays <= 30 else 0
    hist += 50 if (delinq == 0 and not overdue) else 20 if delinq <= 1 else 0
    if overdue:
        hard_stops.append("Есть текущая просроченная задолженность по данным БКИ")
    if delays >= 60:
        hard_stops.append("Просрочка свыше 60 дней за последние 12 месяцев")
    factors.append(_factor(
        "credit_history", "Кредитная история",
        f"Скор БКИ {bki_score}, просрочек за 12 мес.: {delinq}, макс. задержка {delays} дн.",
        min(hist, 200), 200,
    ))

    # 4. Возраст бизнеса (100).
    if age_months >= 36:
        age_points = 100
    elif age_months >= 18:
        age_points = 80
    elif age_months >= 12:
        age_points = 60
    elif age_months >= 6:
        age_points = 35
    else:
        age_points = 0
        hard_stops.append(f"Срок ведения бизнеса {age_months} мес. меньше минимальных {product.min_business_age_months} мес.")
    factors.append(_factor("business_age", "Возраст бизнеса", f"{age_months} мес. с даты регистрации", age_points, 100))

    # 5. Обороты по счёту (100) — стабильность денежного потока.
    turnover_ratio = (company.account_turnover_monthly / revenue * 100) if revenue else 0
    tr_points = 100 if turnover_ratio >= 80 else 75 if turnover_ratio >= 50 else 45 if turnover_ratio >= 25 else 20
    if company.has_alfa_account:
        tr_points = min(100, tr_points + 10)
    factors.append(_factor(
        "turnover", "Обороты по счёту",
        f"Оборот {company.account_turnover_monthly:,.0f} ₽/мес. ({turnover_ratio:.0f}% выручки)".replace(",", " "),
        tr_points, 100,
    ))

    # 6. Соответствие продукту (100).
    fit_points = 100.0
    notes = []
    if product.requires_collateral and not company.collateral_available:
        fit_points -= 45
        notes.append("нет подтверждённого залога")
    if amount > product.max_amount:
        fit_points -= 20
        notes.append("сумма выше лимита продукта")
    if amount > revenue * 6:
        fit_points -= 25
        notes.append("сумма превышает 6 среднемесячных выручек")
    if company.okved_risk:
        fit_points -= 20
        notes.append("повышенный риск вида деятельности")
    fit_points = max(0.0, fit_points)
    factors.append(_factor(
        "product_fit", "Соответствие продукту и сумме",
        "Все параметры в норме" if not notes else "; ".join(notes).capitalize(),
        fit_points, 100,
    ))

    # 7. Профиль клиента (50).
    prof_points = 0.0
    prof_points += 25 if company.has_alfa_account else 10
    prof_points += 15 if company.employees_count >= 5 else 8
    prof_points += 10 if reg and not reg.mass_address else 0
    if reg and reg.mass_address:
        hard_stops.append("Адрес регистрации компании признан массовым")
    if reg and reg.status != "Действующий":
        hard_stops.append(f"Статус компании в ЕГРЮЛ: {reg.status}")
    if reg and reg.tax_debt:
        hard_stops.append("Обнаружена задолженность по налогам (ФНС)")
    factors.append(_factor(
        "profile", "Профиль клиента",
        ("Клиент Альфа-Банка, " if company.has_alfa_account else "") + f"{company.employees_count} сотрудников",
        prof_points, 50,
    ))

    total = int(round(sum(f["points"] for f in factors)))
    total = max(0, min(1000, total))
    risk_class, pd = _band(total)

    decision = "approved"
    if hard_stops:
        decision = "declined"
    elif risk_class in ("A", "B"):
        decision = "approved"
    elif risk_class == "C":
        decision = "counter_offer"
    elif risk_class == "D":
        decision = "counter_offer" if load <= 65 else "declined"
    else:
        decision = "declined"

    # Рекомендованные условия: affordability и продуктовые лимиты.
    rate = product.base_rate + RISK_RATE_ADJUST[risk_class]
    if product.requires_collateral and company.collateral_available:
        rate -= 1.5
    rate = round(max(product.base_rate - 2.0, min(rate, product.max_rate)), 1)
    affordable_payment = max(0.0, revenue * 0.45 - existing)
    affordable_amount = max_loan_by_payment(affordable_payment, rate, term_months)
    recommended_amount = min(amount, product.max_amount, affordable_amount)
    recommended_amount = math.floor(recommended_amount / 10_000) * 10_000
    recommended_amount = max(min(product.min_amount, amount), recommended_amount)
    recommended_term = term_months
    if recommended_amount <= 0:
        recommended_amount = 0

    payment = annuity_payment(recommended_amount, rate, recommended_term)
    new_load = (existing + payment) / revenue * 100
    explanation = (
        f"Балл {total}/1000, риск-класс {risk_class} (PD≈{pd:.1f}%). "
        f"Долговая нагрузка после выдачи ≈{new_load:.0f}% выручки."
    )

    return {
        "score": total,
        "risk_class": risk_class,
        "pd_percent": pd,
        "decision": decision,
        "factors": factors,
        "hard_stops": hard_stops,
        "recommended_amount": recommended_amount,
        "recommended_term_months": recommended_term,
        "recommended_rate": rate,
        "monthly_payment": round(payment, 2),
        "debt_load_percent": round(new_load, 1),
        "explanation": explanation,
    }


def requires_manual_review(scoring_result: dict[str, Any], amount: float) -> bool:
    """Правило маршрутизации в бэк-офис.

    В ручное рассмотрение уходят пограничные риск-классы, крупные суммы
    и заявки с залогом — там решение принимает андеррайтер.
    """
    if scoring_result["hard_stops"]:
        return False  # автоматический отказ, ручное рассмотрение не нужно
    if scoring_result["risk_class"] == "C":
        return True
    if scoring_result["risk_class"] == "B" and amount >= 1_500_000:
        return True
    if scoring_result["risk_class"] == "D" and scoring_result["decision"] == "counter_offer":
        return True
    return False


def declined_reasons(scoring_result: dict[str, Any]) -> list[str]:
    if scoring_result["hard_stops"]:
        return list(scoring_result["hard_stops"])
    reasons = {
        "E": ["Недостаточный уровень кредитоспособности по результатам скоринга"],
        "D": ["Слишком высокая долговая нагрузка при текущих финансовых показателях"],
    }
    return reasons.get(scoring_result["risk_class"], ["Кредитное решение отрицательное"])


def scoring_to_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False)


def scoring_from_application(app: Application) -> dict[str, Any] | None:
    if not app.scoring_json:
        return None
    try:
        return json.loads(app.scoring_json)
    except json.JSONDecodeError:
        return None
