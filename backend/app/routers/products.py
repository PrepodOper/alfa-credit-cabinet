import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Product, User
from ..schemas import EligibilityOut, ProductOut
from ..security import get_current_user
from ..serializers import product_out
from ..services.scoring import calculate_scoring
from ..services.scoring import _months_between

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.is_active.is_(True)).order_by(Product.sort_order).all()
    return [ProductOut(**product_out(p)) for p in products]


@router.get("/{code}/eligibility", response_model=EligibilityOut)
def eligibility(
    code: str,
    amount: float = Query(500_000, gt=0),
    term_months: int = Query(12, gt=0, le=120),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.query(Product).filter(Product.code == code, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    company = user.company
    if company is None:
        raise HTTPException(status_code=400, detail="Пользователь не привязан к компании")

    checks = []
    eligible = True
    age_months = _months_between(company.founded_date)
    checks.append({
        "name": "Срок ведения бизнеса",
        "ok": age_months >= product.min_business_age_months,
        "detail": f"{age_months} мес. при минимуме {product.min_business_age_months} мес.",
    })
    eligible &= age_months >= product.min_business_age_months

    amount_ok = product.min_amount <= amount <= product.max_amount
    checks.append({
        "name": "Сумма в лимитах продукта",
        "ok": amount_ok,
        "detail": f"от {product.min_amount:,.0f} до {product.max_amount:,.0f} ₽".replace(",", " "),
    })
    eligible &= amount_ok

    if product.requires_collateral:
        checks.append({
            "name": "Обеспечение",
            "ok": True,
            "detail": ("Залог подтверждён: " + company.collateral_desc) if company.collateral_available
                      else "Потребуется залог — андеррайтер обсудит состав обеспечения",
        })

    if product.min_monthly_turnover:
        turnover_ok = company.account_turnover_monthly >= product.min_monthly_turnover
        checks.append({
            "name": "Обороты по расчётному счёту",
            "ok": turnover_ok,
            "detail": f"{company.account_turnover_monthly:,.0f} ₽/мес. при требовании "
                      f"{product.min_monthly_turnover:,.0f} ₽/мес.".replace(",", " "),
        })
        eligible &= turnover_ok

    if code == "overdraft":
        checks.append({
            "name": "Расчётный счёт в Альфа-Банке",
            "ok": company.has_alfa_account,
            "detail": "Счёт открыт" if company.has_alfa_account else "Овердрафт доступен клиентам банка",
        })
        eligible &= company.has_alfa_account

    scoring = calculate_scoring(company, product, min(amount, product.max_amount), term_months)
    if company.okved_risk:
        checks.append({"name": "Вид деятельности", "ok": True,
                       "detail": "Повышенный риск ОКВЭД — ставка может быть выше"})

    return EligibilityOut(
        product_code=code,
        eligible=bool(eligible),
        estimated_rate=scoring["recommended_rate"] or product.base_rate,
        reasons=[c["detail"] for c in checks if not c["ok"]],
        checks=checks,
    )


@router.get("/{code}", response_model=ProductOut)
def product_detail(code: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.code == code, Product.is_active.is_(True)).first()
    if not product:
        raise HTTPException(status_code=404, detail="Продукт не найден")
    return ProductOut(**product_out(product))
