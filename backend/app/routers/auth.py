from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Company, User
from ..schemas import CompanyBrief, LoginRequest, LoginResponse, UserOut
from ..security import create_token, get_current_user, verify_password
from ..serializers import company_brief

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    company = db.get(Company, user.company_id) if user.company_id else None
    return LoginResponse(
        token=create_token(user),
        user=UserOut.model_validate(user),
        company=CompanyBrief(**company_brief(company)) if company else None,
    )


@router.get("/me", response_model=LoginResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    company = db.get(Company, user.company_id) if user.company_id else None
    return LoginResponse(
        token="",
        user=UserOut.model_validate(user),
        company=CompanyBrief(**company_brief(company)) if company else None,
    )


@router.get("/demo-accounts")
def demo_accounts():
    """Тестовые учётные записи для проверки сценария (синтетические данные)."""
    return {
        "password": "demo1234",
        "accounts": [
            {"email": "ivan@vesna.ru", "role": "client", "who": "Кофейня «Весна» — сильный профиль, автоматическое одобрение"},
            {"email": "petr@stroymaster.ru", "role": "client", "who": "ИП «СтройМастер» — заявка уходит андеррайтеру"},
            {"email": "anna@tehnopark.ru", "role": "client", "who": "ООО «ТехноПарк» — высокая нагрузка, контрпредложение"},
            {"email": "underwriter@alfabank.ru", "role": "bank", "who": "Андеррайтер МСБ — очередь заявок и решения"},
        ],
    }
