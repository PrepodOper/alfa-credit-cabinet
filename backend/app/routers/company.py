from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..security import require_role
from ..serializers import _json_list, client_snapshot

router = APIRouter(prefix="/company", tags=["company"])


@router.get("")
def company_profile(user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    company = user.company
    if company is None:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    return {
        "company": client_snapshot(company),
        "requisites": {
            "name": company.name,
            "short_name": company.short_name,
            "legal_form": company.legal_form,
            "inn": company.inn,
            "ogrn": company.ogrn,
            "kpp": company.kpp,
            "address": company.address,
            "region": company.region,
            "city": company.city,
            "industry": company.industry,
            "okved_code": company.okved_code,
            "okved_name": company.okved_name,
            "director_name": company.director_name,
            "phone": company.phone,
            "email": company.email,
            "employees_count": company.employees_count,
            "founded_date": company.founded_date.isoformat() if company.founded_date else None,
            "has_alfa_account": company.has_alfa_account,
            "alfa_client_since": company.alfa_client_since.isoformat() if company.alfa_client_since else None,
        },
        "financials": {
            "revenue_avg_monthly": company.revenue_avg_monthly,
            "revenue_12m": company.revenue_12m,
            "net_profit_12m": company.net_profit_12m,
            "existing_monthly_payments": company.existing_monthly_payments,
            "account_turnover_monthly": company.account_turnover_monthly,
            "dynamics": _json_list(company.monthly_dynamics_json),
        },
    }
