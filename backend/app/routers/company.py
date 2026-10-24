from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Company, CompanyChange, User
from ..schemas import CompanyUpdate
from ..security import require_role
from ..serializers import _json_list, client_snapshot

router = APIRouter(prefix="/company", tags=["company"])

# Поля, которые клиент может менять сам. Регистрационные данные (название, ИНН,
# ОГРН, КПП, дата регистрации, организационная форма) приходят из ЕГРЮЛ и здесь
# недоступны — их правка означала бы подмену данных реестра.
EDITABLE_FIELDS: dict[str, str] = {
    "phone": "Телефон",
    "email": "Email",
    "region": "Регион",
    "city": "Город",
    "address": "Адрес",
    "director_name": "Руководитель",
    "industry": "Отрасль",
    "okved_code": "ОКВЭД",
    "okved_name": "Вид деятельности",
    "employees_count": "Сотрудников",
    "revenue_avg_monthly": "Средняя выручка в месяц",
    "revenue_12m": "Выручка за 12 месяцев",
    "net_profit_12m": "Прибыль за 12 месяцев",
    "existing_monthly_payments": "Платежи по кредитам в месяц",
    "account_turnover_monthly": "Обороты по счёту в месяц",
    "collateral_available": "Залоговое имущество",
    "collateral_desc": "Описание залога",
}

MONEY_FIELDS = {
    "revenue_avg_monthly", "revenue_12m", "net_profit_12m",
    "existing_monthly_payments", "account_turnover_monthly",
}


def _fmt(field: str, value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "да" if value else "нет"
    if field in MONEY_FIELDS:
        return f"{value:,.0f} ₽".replace(",", " ")
    return str(value)


def company_payload(company: Company, db: Session | None = None) -> dict:
    """Единый контракт профиля: используется и в GET, и в ответе на PATCH."""
    data = {
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
        "editable_fields": EDITABLE_FIELDS,
        "immutable_fields": ["name", "short_name", "legal_form", "inn", "ogrn", "kpp",
                             "founded_date", "has_alfa_account", "alfa_client_since"],
    }
    if db is not None:
        changes = (db.query(CompanyChange)
                   .filter(CompanyChange.company_id == company.id)
                   .order_by(CompanyChange.created_at.desc(), CompanyChange.id.desc())
                   .limit(20).all())
        data["changes"] = [{
            "id": c.id, "field": c.field, "field_label": c.field_label,
            "old_value": c.old_value, "new_value": c.new_value,
            "user_name": c.user_name, "created_at": c.created_at,
        } for c in changes]
    return data


def _company_of(user: User) -> Company:
    if user.company is None:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    return user.company


@router.get("")
def company_profile(user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    return company_payload(_company_of(user), db)


@router.patch("")
def update_company(payload: CompanyUpdate,
                   user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    """Правка профиля компании клиентом.

    Финансовые показатели влияют на скоринг, поэтому после изменения данных
    новые заявки оцениваются по обновлённым значениям; уже поданные заявки
    не пересчитываются — их решение зафиксировано в журнале событий.
    """
    company = db.query(Company).filter(Company.id == _company_of(user).id).first()
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Не передано ни одного поля для изменения")

    changed: list[dict] = []
    for field, value in updates.items():
        if field not in EDITABLE_FIELDS:
            raise HTTPException(status_code=422, detail=f"Поле {field} недоступно для изменения")
        old = getattr(company, field)
        if isinstance(old, float) or field in MONEY_FIELDS:
            same = old is not None and abs(float(old) - float(value)) < 0.01
        else:
            same = old == value
        if same:
            continue
        setattr(company, field, value)
        changed.append({"field": field, "label": EDITABLE_FIELDS[field],
                        "old": _fmt(field, old), "new": _fmt(field, value)})

    if not changed:
        # Идемпотентный ответ: те же данные — ни изменений, ни мусора в журнале.
        payload_out = company_payload(company, db)
        payload_out["changed_fields"] = []
        return payload_out

    # Если поменяли среднюю выручку и не задали годовую явно — пересчитываем годовую.
    if "revenue_avg_monthly" in updates and "revenue_12m" not in updates:
        new_year = round(float(updates["revenue_avg_monthly"]) * 12, 2)
        if abs((company.revenue_12m or 0) - new_year) > 0.01:
            changed.append({"field": "revenue_12m", "label": EDITABLE_FIELDS["revenue_12m"],
                            "old": _fmt("revenue_12m", company.revenue_12m),
                            "new": _fmt("revenue_12m", new_year)})
            company.revenue_12m = new_year

    for item in changed:
        db.add(CompanyChange(
            company_id=company.id, user_id=user.id, user_name=user.full_name,
            field=item["field"], field_label=item["label"],
            old_value=item["old"][:255], new_value=item["new"][:255],
        ))
    db.commit()
    db.refresh(company)
    payload_out = company_payload(company, db)
    payload_out["changed_fields"] = [item["field"] for item in changed]
    return payload_out


@router.get("/changes")
def company_changes(user: User = Depends(require_role("client")), db: Session = Depends(get_db)):
    company = _company_of(user)
    rows = (db.query(CompanyChange)
            .filter(CompanyChange.company_id == company.id)
            .order_by(CompanyChange.created_at.desc(), CompanyChange.id.desc())
            .limit(100).all())
    return {"items": [{
        "id": c.id, "field": c.field, "field_label": c.field_label,
        "old_value": c.old_value, "new_value": c.new_value,
        "user_name": c.user_name, "created_at": c.created_at,
    } for c in rows], "total": len(rows)}
