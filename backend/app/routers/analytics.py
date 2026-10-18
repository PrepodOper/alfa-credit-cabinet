from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Application, Product, User
from ..schemas import DashboardOut
from ..security import require_role
from ..serializers import application_out
from ..services.scoring import calculate_scoring, _months_between
from ..services.workflow import ACTIVE_STATUSES
from ..serializers import event_out as event_out

router = APIRouter(prefix="/dashboard", tags=["analytics"])


@router.get("", response_model=DashboardOut)
def dashboard(user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    company = user.company
    apps = (db.query(Application).filter(Application.company_id == company.id)
            .order_by(Application.created_at.desc()).all())
    products = db.query(Product).filter(Product.is_active.is_(True)).order_by(Product.sort_order).all()

    revenue = max(company.revenue_avg_monthly, 1)
    probe_amount = min(2_000_000, max(300_000, revenue * 1.5))
    working = next((p for p in products if p.code == "working_capital"), products[0])
    probe = calculate_scoring(company, working, probe_amount, 12)

    active = next((a for a in apps if a.status in ACTIVE_STATUSES), None)
    funded = [a for a in apps if a.status == "funded"]

    stats = {
        "applications_total": len(apps),
        "active_count": sum(1 for a in apps if a.status in ACTIVE_STATUSES),
        "funded_count": len(funded),
        "portfolio": round(sum(a.offer_amount or a.amount for a in funded), 2),
        "monthly_payment": round(sum(a.offer_monthly_payment or 0 for a in funded), 2),
        "approved_count": sum(1 for a in apps if a.status in {"funded", "signing", "offer_issued"}),
    }

    recommendations = []
    for p in products:
        amount = min(p.max_amount, max(p.min_amount, probe_amount))
        res = calculate_scoring(company, p, amount, max(p.min_term_months, min(12, p.max_term_months)))
        eligible = True
        reason = ""
        if _months_between(company.founded_date) < p.min_business_age_months:
            eligible, reason = False, f"Нужно минимум {p.min_business_age_months} мес. ведения бизнеса"
        elif p.code == "overdraft" and not company.has_alfa_account:
            eligible, reason = False, "Доступно клиентам с расчётным счётом в Альфа-Банке"
        elif p.min_monthly_turnover and company.account_turnover_monthly < p.min_monthly_turnover:
            eligible, reason = False, "Недостаточный оборот по счёту"
        recommendations.append({
            "code": p.code, "name": p.name, "tagline": p.tagline, "icon": p.icon,
            "badge": p.badge, "max_amount": p.max_amount, "min_amount": p.min_amount,
            "estimated_rate": res["recommended_rate"], "eligible": eligible, "reason": reason,
            "monthly_payment": round(res["monthly_payment"] or 0, 2),
        })
    recommendations.sort(key=lambda r: (not r["eligible"],))

    recent_events = []
    if active:
        recent_events = [event_out(e) for e in active.events[-4:]]

    company_payload = {
        "id": company.id, "name": company.name, "short_name": company.short_name,
        "legal_form": company.legal_form, "inn": company.inn, "ogrn": company.ogrn,
        "industry": company.industry, "region": company.region, "city": company.city,
        "director_name": company.director_name, "employees_count": company.employees_count,
        "founded_date": company.founded_date.isoformat() if company.founded_date else None,
        "revenue_avg_monthly": company.revenue_avg_monthly,
        "revenue_12m": company.revenue_12m, "net_profit_12m": company.net_profit_12m,
        "existing_monthly_payments": company.existing_monthly_payments,
        "account_turnover_monthly": company.account_turnover_monthly,
        "has_alfa_account": company.has_alfa_account,
        "alfa_client_since": company.alfa_client_since.isoformat() if company.alfa_client_since else None,
        "collateral_available": company.collateral_available,
        "collateral_desc": company.collateral_desc,
        "okved_name": company.okved_name,
    }

    return DashboardOut(
        company=company_payload,
        stats=stats,
        active_application=application_out(active) if active else None,
        recommendations=recommendations,
        credit_meter={
            "amount": probe["recommended_amount"],
            "rate": probe["recommended_rate"],
            "risk_class": probe["risk_class"],
            "score": probe["score"],
            "debt_load_percent": probe["debt_load_percent"],
            "label": "Предварительный лимит по «Оборотному кредиту»",
        },
    )
