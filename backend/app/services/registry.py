"""Моки внешних источников данных: БКИ, ЕГРЮЛ/ЕГРИП, ФНС «Прозрачный бизнес».

В продакшене здесь были бы клиенты к внешним API. Для автономности решения
используются локальные стабы с синтетическими данными, сохранёнными в БД.
"""
from typing import Any

from ..models import Company


def company_snapshot(company: Company) -> dict[str, Any]:
    """Внутренний профиль клиента (данные из анкеты и обслуживания в банке)."""
    profile = {
        "name": company.name,
        "legal_form": company.legal_form,
        "inn": company.inn,
        "ogrn": company.ogrn,
        "industry": company.industry,
        "region": company.region,
        "employees_count": company.employees_count,
        "founded_date": company.founded_date.isoformat() if company.founded_date else None,
        "revenue_avg_monthly": company.revenue_avg_monthly,
        "revenue_12m": company.revenue_12m,
        "net_profit_12m": company.net_profit_12m,
        "existing_monthly_payments": company.existing_monthly_payments,
        "account_turnover_monthly": company.account_turnover_monthly,
        "has_alfa_account": company.has_alfa_account,
    }
    return profile


def bki_snapshot(company: Company) -> dict[str, Any]:
    """Мок-ответ бюро кредитных историй."""
    cp = company.credit_profile
    if cp is None:
        return {}
    return {
        "source": "Объединённое бюро кредитных историй (мок)",
        "bki_score": cp.bki_score,
        "active_loans": cp.active_loans,
        "total_debt": cp.total_debt,
        "monthly_payments": cp.monthly_payments,
        "max_delay_days_12m": cp.max_delay_days_12m,
        "has_current_overdue": cp.has_current_overdue,
        "delinquencies_12m": cp.delinquencies_12m,
        "inquiries_6m": cp.inquiries_6m,
        "summary": cp.summary,
        "updated_at": cp.updated_at.isoformat() if cp.updated_at else None,
    }


def registry_snapshot(company: Company) -> dict[str, Any]:
    """Мок-ответ ЕГРЮЛ/ЕГРИП + ФНС «Прозрачный бизнес»."""
    reg = company.registry_info
    if reg is None:
        return {"source": "ЕГРЮЛ / ФНС (мок)", "status": "Действующий", "checks": []}
    import json
    return {
        "source": reg.source,
        "status": reg.status,
        "tax_debt": reg.tax_debt,
        "fns_violations": reg.fns_violations,
        "mass_address": reg.mass_address,
        "director_changed_recently": reg.director_changed_recently,
        "founders": json.loads(reg.founders_json or "[]"),
        "employees_reported": reg.employees_reported,
        "last_update": reg.last_update.isoformat() if reg.last_update else None,
    }
