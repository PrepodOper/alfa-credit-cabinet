"""График платежей по кредиту (аннуитетная схема).

График строится по фактическим условиям предложения (сумма, ставка, срок) и
используется в трёх местах: клиентская карточка заявки, карточка андеррайтера
и документ «График платежей» из пакета на подписание.

Правило округления: проценты и тело считаются с точностью до копейки, последний
платёж корректируется так, чтобы остаток долга стал ровно нулём (иначе за 36
месяцев накапливается расхождение в несколько рублей).
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from .scoring import annuity_payment

MONTHS_NOMINATIVE = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def add_months(start: date, months: int) -> date:
    """Сдвиг даты на N месяцев с «прижатием» дня к длине месяца (31.01 + 1 → 28.02)."""
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def build_schedule(amount: float, rate: float, term_months: int,
                   start: date | None = None) -> list[dict[str, Any]]:
    """Аннуитетный график платежей: по строке на каждый месяц."""
    if amount <= 0 or term_months <= 0:
        return []

    start = start or date.today()
    monthly_rate = rate / 100 / 12
    payment = round(annuity_payment(amount, rate, term_months), 2)
    balance = round(amount, 2)

    rows: list[dict[str, Any]] = []
    for number in range(1, term_months + 1):
        interest = round(balance * monthly_rate, 2)
        principal = round(payment - interest, 2)
        if number == term_months or principal >= balance:
            # Последний (или досрочно закрывающий) платёж гасит остаток полностью.
            principal = balance
            payment_row = round(principal + interest, 2)
        else:
            payment_row = payment
        balance = round(balance - principal, 2)
        if balance < 0:
            balance = 0.0
        rows.append({
            "number": number,
            "date": add_months(start, number).isoformat(),
            "payment": payment_row,
            "interest": interest,
            "principal": principal,
            "balance": balance,
        })
    return rows


def schedule_summary(amount: float, rate: float, term_months: int,
                     items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Короткая сводка по графику: платёж, переплата, общая сумма."""
    items = items if items is not None else build_schedule(amount, rate, term_months)
    total_paid = round(sum(row["payment"] for row in items), 2)
    total_interest = round(sum(row["interest"] for row in items), 2)
    return {
        "amount": round(amount, 2),
        "rate": rate,
        "term_months": term_months,
        "monthly_payment": items[0]["payment"] if items else 0.0,
        "payments_count": len(items),
        "total_paid": total_paid,
        "total_interest": total_interest,
        "overpayment_percent": round(total_interest / amount * 100, 1) if amount else 0.0,
        "first_payment_date": items[0]["date"] if items else None,
        "last_payment_date": items[-1]["date"] if items else None,
    }


def payment_schedule(amount: float, rate: float, term_months: int,
                     start: date | None = None) -> dict[str, Any]:
    """Готовый блок для API: сводка + строки графика."""
    items = build_schedule(amount, rate, term_months, start)
    return {"summary": schedule_summary(amount, rate, term_months, items), "items": items}
